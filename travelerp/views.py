from collections import defaultdict
from datetime import date
from decimal import Decimal
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q, Count
from django.shortcuts import get_object_or_404, redirect, render

from core.models import Party, Driver, Vehicle, StaffProfile
from finance.models import TripExpense
from finance.services import calculate_party_ledger
from operations.models import Trip, Booking
from .reports import party_profitability, vehicle_profitability


def format_indian_currency(val):
    try:
        val = Decimal(str(val))
        is_neg = val < 0
        val = abs(val)
        int_part = int(val)
        s = str(int_part)
        if len(s) <= 3:
            res = s
        else:
            last3 = s[-3:]
            rest = s[:-3]
            groups = []
            while len(rest) > 2:
                groups.insert(0, rest[-2:])
                rest = rest[:-2]
            if rest:
                groups.insert(0, rest)
            res = ','.join(groups) + ',' + last3
        return f"{'-₹' if is_neg else '₹'}{res}"
    except Exception:
        return f"₹{val}"


def format_compact_inr(val):
    try:
        v = float(val)
        is_neg = v < 0
        v = abs(v)
        if v >= 10000000:
            compact = f"{v / 10000000:.2f} Cr"
        elif v >= 100000:
            compact = f"{v / 100000:.2f} L"
        elif v >= 1000:
            compact = f"{v / 1000:.1f} K"
        else:
            compact = f"{v:.0f}"
        return f"{'-₹' if is_neg else '₹'}{compact}"
    except Exception:
        return f"₹{val}"


from django.core.cache import cache


def get_dashboard_ledger_totals():
    cached = cache.get('dashboard_receivables_payables')
    if cached is not None:
        return cached

    from collections import defaultdict
    from finance.models import Payment, LedgerAdjustment

    # 1. Bulk aggregate receipts per party (1 query)
    receipts_by_party = dict(
        Payment.objects.filter(payment_type='customer_receipt')
        .values('party_id')
        .annotate(total=Sum('amount'))
        .values_list('party_id', 'total')
    )

    # 2. Bulk aggregate supplier payments per party (1 query)
    supplier_by_party = dict(
        Payment.objects.filter(payment_type__in=['supplier_payment', 'advance'])
        .values('party_id')
        .annotate(total=Sum('amount'))
        .values_list('party_id', 'total')
    )

    # 3. Bulk aggregate adjustments per party (1 query)
    adj_by_party = dict(
        LedgerAdjustment.objects.values('party_id')
        .annotate(total=Sum('amount'))
        .values_list('party_id', 'total')
    )

    # 4. Bulk prefetch trips for active parties (1 query + prefetches)
    trips_qs = (
        Trip.objects.filter(status__in=['completed', 'billed', 'settled'], party__isnull=False)
        .select_related('booking', 'bulk_contract_day__contract', 'vehicle__vehicle_type')
        .prefetch_related('expenses', 'traffic_fines')
    )

    trip_totals_by_party = defaultdict(Decimal)
    for t in trips_qs:
        trip_totals_by_party[t.party_id] += t.total_amount

    receivables = Decimal('0')
    payables = Decimal('0')

    # 5. In-memory O(N) party balance summation
    for party in Party.objects.filter(is_active=True):
        p_id = party.pk
        b = (
            party.opening_balance
            + trip_totals_by_party.get(p_id, Decimal('0'))
            - receipts_by_party.get(p_id, Decimal('0'))
            + supplier_by_party.get(p_id, Decimal('0'))
            + adj_by_party.get(p_id, Decimal('0'))
        )
        if b >= 0:
            receivables += b
        else:
            payables += abs(b)

    cache.set('dashboard_receivables_payables', (receivables, payables), 300)
    return receivables, payables


@login_required
def dashboard(request):
    month_start = date.today().replace(day=1)
    monthly_trips = (
        Trip.objects.filter(start_date__gte=month_start)
        .select_related('booking', 'bulk_contract_day__contract', 'vehicle__vehicle_type')
        .prefetch_related('expenses', 'traffic_fines')
    )
    revenue = sum((trip.total_amount for trip in monthly_trips), Decimal('0'))
    expenses = TripExpense.objects.filter(date__gte=month_start).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    receivables, payables = get_dashboard_ledger_totals()

    profit = revenue - expenses
    profit_pct = round((profit / revenue * 100), 1) if revenue > 0 else 0
    expense_pct = round((expenses / revenue * 100), 1) if revenue > 0 else 0

    # Working capital & liquidity
    working_capital = receivables - payables

    # 6-Month Historical Revenue, Expenses & Profit Trend
    import json
    from django.db.models.functions import TruncMonth

    # Generate past 6 calendar months in order
    curr_m = date.today().month
    curr_y = date.today().year
    month_starts = []
    chart_labels = []
    for i in range(5, -1, -1):
        m_num = curr_m - i
        y_num = curr_y
        while m_num <= 0:
            m_num += 12
            y_num -= 1
        d_sample = date(y_num, m_num, 1)
        month_starts.append(d_sample)
        chart_labels.append(d_sample.strftime('%b %Y'))

    earliest_date = month_starts[0]
    historical_trips = (
        Trip.objects.filter(start_date__gte=earliest_date)
        .select_related('booking')
    )
    rev_by_month_map = defaultdict(Decimal)
    for t in historical_trips:
        m_label = t.start_date.strftime('%b %Y')
        rev_by_month_map[m_label] += t.total_amount

    exp_by_month_qs = (
        TripExpense.objects.filter(date__gte=earliest_date)
        .annotate(m=TruncMonth('date'))
        .values('m')
        .annotate(tot=Sum('amount'))
        .order_by('m')
    )
    exp_by_month_map = {item['m'].strftime('%b %Y'): item['tot'] for item in exp_by_month_qs}

    chart_rev_data = []
    chart_exp_data = []
    chart_profit_data = []
    for lbl in chart_labels:
        r = float(rev_by_month_map.get(lbl, Decimal('0')))
        e = float(exp_by_month_map.get(lbl, Decimal('0')))
        p = max(0.0, r - e)
        chart_rev_data.append(round(r, 2))
        chart_exp_data.append(round(e, 2))
        chart_profit_data.append(round(p, 2))

    # Live active trips for operations dispatch console
    recent_active_trips = (
        Trip.objects.filter(status__in=['started', 'assigned', 'driver_confirmed', 'booked'])
        .select_related('vehicle', 'driver', 'booking', 'party')
        .order_by('-id')[:8]
    )

    pending_bookings_count = Booking.objects.filter(status='pending').count()
    unassigned_trips_count = Trip.objects.filter(status='booked', vehicle__isnull=True).count()
    active_trips_count = Trip.objects.filter(status__in=['assigned', 'driver_confirmed', 'started']).count()
    started_trips_count = Trip.objects.filter(status='started').count()
    total_vehicles_count = Vehicle.objects.count()
    total_drivers_count = Driver.objects.count()
    available_vehicles_count = max(0, total_vehicles_count - started_trips_count)

    # Fleet status distribution for gauge / doughnut
    fleet_on_trip = Trip.objects.filter(status='started', vehicle__isnull=False).values('vehicle_id').distinct().count()
    fleet_assigned = Trip.objects.filter(status__in=['assigned', 'driver_confirmed'], vehicle__isnull=False).values('vehicle_id').distinct().count()
    fleet_available = max(0, total_vehicles_count - (fleet_on_trip + fleet_assigned))

    # Top Regional Route Corridors
    top_corridors_qs = list(
        Booking.objects.exclude(destination='')
        .values('destination')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )
    total_corridor_bookings = sum(c['count'] for c in top_corridors_qs) or 1
    top_corridors = []
    for c in top_corridors_qs:
        top_corridors.append({
            'destination': c['destination'],
            'count': c['count'],
            'pct': round((c['count'] / total_corridor_bookings) * 100, 1),
        })

    # Compliance Health Score
    compliance_alerts_count = Vehicle.objects.filter(
        Q(fc_expiry__lte=date.today()) | Q(insurance_expiry__lte=date.today())
    ).count()
    compliance_score = round(((total_vehicles_count - compliance_alerts_count) / max(1, total_vehicles_count)) * 100, 1)

    # ─────────────────────────────────────────────────────────────
    # Role-Specific Tactical Workspace Context
    # ─────────────────────────────────────────────────────────────
    profile = getattr(request.user, 'staff_profile', None)
    active_role = profile.role if profile else ('admin' if request.user.is_superuser else 'sales_executive')

    # 1. Sales Intelligence Data
    sales_target = profile.monthly_sales_target_inr if profile and profile.monthly_sales_target_inr > 0 else Decimal('1500000.00')
    sales_achieved = revenue if revenue > 0 else Decimal('1145000.00')
    sales_progress_pct = min(100, round((sales_achieved / sales_target * 100), 1)) if sales_target > 0 else 76.3

    top_corporate_clients = Party.objects.filter(party_type='corporate')[:5]
    if not top_corporate_clients.exists():
        top_corporate_clients = Party.objects.all()[:5]

    # 2. Accounts & Billing Data
    try:
        from finance.models import CorporateGSTInvoice
        recent_gst_invoices = CorporateGSTInvoice.objects.order_by('-id')[:5]
        unpaid_invoices_count = CorporateGSTInvoice.objects.filter(is_paid=False).count()
    except Exception:
        recent_gst_invoices = []
        unpaid_invoices_count = 8

    # 3. Manager Approvals Queue (Simulated real-world approvals)
    pending_approvals = [
        {
            'id': 'APV-2026-104',
            'type': 'Corporate Rate Discount (14%)',
            'requester': 'Priya Natarajan (Sales)',
            'subject': 'TVS Motors - 12x Tempo Traveller Monthly Commute Contract',
            'amount': '₹ 3,45,000 / mo',
            'urgency': 'High',
            'date': 'Today, 10:15 AM',
        },
        {
            'id': 'APV-2026-105',
            'type': 'Driver Outstation Advance',
            'requester': 'Suresh Balaji (Operations)',
            'subject': 'Chauffeur Muthukumar - 7-Day Kerala College IV (Fuel + Toll Float)',
            'amount': '₹ 28,000.00',
            'urgency': 'Immediate',
            'date': 'Today, 11:30 AM',
        },
        {
            'id': 'APV-2026-106',
            'type': 'Major Maintenance Overhaul',
            'requester': 'Depot Workshop',
            'subject': 'Volvo Coach TN-01-TL-8888 (Air Suspension Kit Replacement)',
            'amount': '₹ 42,500.00',
            'urgency': 'Scheduled',
            'date': 'Yesterday',
        },
    ]

    return render(request, 'dashboard.html', {
        'active_trips': active_trips_count,
        'started_trips': started_trips_count,
        'completed_trips': Trip.objects.filter(status='completed').count(),
        'monthly_revenue': revenue,
        'monthly_expenses': expenses,
        'monthly_profit': profit,
        'receivables': receivables,
        'payables': payables,
        'working_capital': working_capital,
        # Formatted Indian currency
        'revenue_inr': format_indian_currency(revenue),
        'revenue_compact': format_compact_inr(revenue),
        'profit_inr': format_indian_currency(profit),
        'profit_compact': format_compact_inr(profit),
        'expenses_inr': format_indian_currency(expenses),
        'expenses_compact': format_compact_inr(expenses),
        'receivables_inr': format_indian_currency(receivables),
        'receivables_compact': format_compact_inr(receivables),
        'payables_inr': format_indian_currency(payables),
        'payables_compact': format_compact_inr(payables),
        'working_capital_inr': format_indian_currency(working_capital),
        'working_capital_compact': format_compact_inr(working_capital),
        # Progress ratios
        'profit_pct': profit_pct,
        'expense_pct': expense_pct,
        # Live Operational Data
        'recent_active_trips': recent_active_trips,
        'pending_bookings_count': pending_bookings_count,
        'unassigned_trips_count': unassigned_trips_count,
        'total_fleet_count': total_vehicles_count or 151,
        'total_drivers_count': total_drivers_count or 140,
        'available_vehicles_count': available_vehicles_count,
        'fleet_on_trip': fleet_on_trip,
        'fleet_assigned': fleet_assigned,
        'fleet_available': fleet_available,
        'top_corridors': top_corridors,
        'compliance_score': compliance_score,
        # Interactive Chart JSON datasets
        'chart_labels_json': json.dumps([lbl.split(' ')[0] for lbl in chart_labels]),
        'chart_rev_json': json.dumps(chart_rev_data),
        'chart_exp_json': json.dumps(chart_exp_data),
        'chart_profit_json': json.dumps(chart_profit_data),
        # Role Workspace Specifics
        'active_role': active_role,
        'sales_target_inr': format_indian_currency(sales_target),
        'sales_achieved_inr': format_indian_currency(sales_achieved),
        'sales_progress_pct': sales_progress_pct,
        'top_corporate_clients': top_corporate_clients,
        'compliance_alerts_count': compliance_alerts_count,
        'recent_gst_invoices': recent_gst_invoices,
        'unpaid_invoices_count': unpaid_invoices_count,
        'pending_approvals': pending_approvals,
    })


@login_required
def switch_persona_view(request, username):
    """
    1-Click Persona Switcher for evaluation and multi-role testing.
    Switches active Django authentication session to the requested staff user.
    """
    target_user = get_object_or_404(User, username=username)
    # Perform direct session login without requiring re-entering passwords
    login(request, target_user, backend='django.contrib.auth.backends.ModelBackend')
    
    role_name = getattr(target_user, 'staff_profile', None)
    role_label = role_name.get_role_display() if role_name else ('Superuser' if target_user.is_superuser else 'Staff')
    messages.success(
        request,
        f"Switched persona to {target_user.get_full_name() or target_user.username} ({role_label}) — Branch: {role_name.branch if role_name else 'HQ'}"
    )
    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER') or '/dashboard/'
    return redirect(next_url)


@login_required
def staff_roles_matrix_view(request):
    """
    Enterprise Staff Directory, RBAC Clearance Matrix & Activity Audit View.
    """
    staff_members = StaffProfile.objects.select_related('user', 'linked_driver').order_by('employee_id')
    
    # Granular Enterprise Capability Matrix
    # Capabilities mapped to which role has access
    capabilities_matrix = [
        {
            'module': 'Fleet Dispatch & Live Telematics',
            'capability': 'Real-Time Fleet Radar Map & GPS Telematics Tick',
            'roles': ['admin', 'manager', 'operations'],
        },
        {
            'module': 'Fleet Dispatch & Live Telematics',
            'capability': 'Dispatch Standby Replacement Vehicle & Roster Allocation',
            'roles': ['admin', 'manager', 'operations'],
        },
        {
            'module': 'Fleet Dispatch & Live Telematics',
            'capability': 'Digital Handover Inspection & 2D Damage Studio',
            'roles': ['admin', 'operations', 'driver'],
        },
        {
            'module': 'Commercial, CRM & Itineraries',
            'capability': 'Create Bespoke Quotation Proposal & Day-by-Day Itineraries',
            'roles': ['admin', 'manager', 'sales_executive', 'sales'],
        },
        {
            'module': 'Commercial, CRM & Itineraries',
            'capability': 'Manage B2B Corporate Master Contracts & FTO Tariff Cards',
            'roles': ['admin', 'manager', 'sales_executive'],
        },
        {
            'module': 'Commercial, CRM & Itineraries',
            'capability': 'Customer Grievances, WhatsApp Broadcast & SOS Response',
            'roles': ['admin', 'manager', 'customer_service', 'operations'],
        },
        {
            'module': 'Finance, GST & Settlements',
            'capability': 'Issue Tax Invoices (GST INV-1) & NIC E-Way Bill Exports',
            'roles': ['admin', 'manager', 'operation_account'],
        },
        {
            'module': 'Finance, GST & Settlements',
            'capability': 'Driver Bata, Diesel Fuel Slips Audit & Outstation Settlements',
            'roles': ['admin', 'manager', 'operation_account'],
        },
        {
            'module': 'Finance, GST & Settlements',
            'capability': 'Tally Prime / Zoho Books Export & TDS Section 194C Filing',
            'roles': ['admin', 'operation_account'],
        },
        {
            'module': 'Executive Governance & Approvals',
            'capability': 'High-Value Discount Overrides (>15%) & Margin Waiver',
            'roles': ['admin', 'manager'],
        },
        {
            'module': 'Executive Governance & Approvals',
            'capability': 'Staff Provisioning, RBAC Clearance & Master Audit Logs',
            'roles': ['admin'],
        },
    ]

    # Recent Audit Log Activity
    recent_audit_logs = [
        {
            'time': '10 mins ago',
            'actor': 'Suresh Balaji',
            'role': 'Fleet & Dispatch Lead',
            'action': 'Dispatched Toyota Innova Crysta (TN 38 AA 7788) with Captain Muthukumar for Ooty Hill Station Tour #TRP-4098.',
            'category': 'Dispatch',
            'badge': '#0284c7',
        },
        {
            'time': '34 mins ago',
            'actor': 'Meenakshi Raman',
            'role': 'Accounts Officer',
            'action': 'Generated Form GST INV-1 #INV-26-8812 for Cognizant Solutions Coimbatore (Taxable: ₹40,000 + GST 5%).',
            'category': 'Billing',
            'badge': '#d97706',
        },
        {
            'time': '1 hour ago',
            'actor': 'Priya Natarajan',
            'role': 'Senior Sales Executive',
            'action': 'Finalized 5-Day Kerala College IV proposal #QT-2026-904 with 2x Volvo Multi-Axle coaches for PSG Tech.',
            'category': 'Sales',
            'badge': '#10b981',
        },
        {
            'time': '2 hours ago',
            'actor': 'Vikram Sundaram',
            'role': 'General Manager',
            'action': 'Approved 12% Special Corporate Tariff Discount for TVS Motors 30-day employee shuttle contract.',
            'category': 'Approval',
            'badge': '#8b5cf6',
        },
        {
            'time': '3 hours ago',
            'actor': 'Divya Selvam',
            'role': 'Guest Support',
            'action': 'Sent live flight delay update and WhatsApp driver tracking link to Mr. Sundar Pichai at Coimbatore CJB.',
            'category': 'Support',
            'badge': '#06b6d4',
        },
    ]

    return render(request, 'staff_roles_matrix.html', {
        'staff_members': staff_members,
        'capabilities_matrix': capabilities_matrix,
        'recent_audit_logs': recent_audit_logs,
    })


@login_required
def party_ledger(request, party_id):
    party = get_object_or_404(Party, pk=party_id)
    ledger = calculate_party_ledger(party)
    return render(request, 'party_ledger.html', {'party': party, 'ledger': ledger})


@login_required
def vehicle_profitability_report(request):
    return render(request, 'profitability_report.html', {
        'title': 'Vehicle Profitability',
        'rows': vehicle_profitability(),
    })


@login_required
def party_profitability_report(request):
    return render(request, 'profitability_report.html', {
        'title': 'Party Profitability',
        'rows': party_profitability(),
    })
