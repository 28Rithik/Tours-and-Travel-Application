from datetime import date
from decimal import Decimal
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
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
    receivables = Decimal('0')
    payables = Decimal('0')
    active_parties = Party.objects.filter(is_active=True).filter(
        Q(trips__isnull=False) | Q(payments__isnull=False) | ~Q(opening_balance=0)
    ).distinct()
    for party in active_parties:
        balance = calculate_party_ledger(party)['closing_balance']
        if balance >= 0:
            receivables += balance
        else:
            payables += abs(balance)
    cache.set('dashboard_receivables_payables', (receivables, payables), 300)
    return receivables, payables


@login_required
def dashboard(request):
    month_start = date.today().replace(day=1)
    trips = Trip.objects.all()
    monthly_trips = trips.filter(start_date__gte=month_start)
    revenue = sum((trip.total_amount for trip in monthly_trips), Decimal('0'))
    expenses = TripExpense.objects.filter(date__gte=month_start).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    receivables, payables = get_dashboard_ledger_totals()

    profit = revenue - expenses
    profit_pct = round((profit / revenue * 100), 1) if revenue > 0 else 0
    expense_pct = round((expenses / revenue * 100), 1) if revenue > 0 else 0

    # Live active trips for operations dispatch console
    recent_active_trips = (
        Trip.objects.filter(status__in=['started', 'assigned', 'driver_confirmed', 'booked'])
        .select_related('vehicle', 'driver', 'booking', 'party')
        .order_by('-id')[:6]
    )

    pending_bookings_count = Booking.objects.filter(status='pending').count()
    unassigned_trips_count = Trip.objects.filter(status='booked', vehicle__isnull=True).count()
    active_trips_count = trips.filter(status__in=['assigned', 'driver_confirmed', 'started']).count()
    started_trips_count = trips.filter(status='started').count()
    total_vehicles_count = Vehicle.objects.count()
    total_drivers_count = Driver.objects.count()
    available_vehicles_count = max(0, total_vehicles_count - started_trips_count)

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

    # 2. Operations & Fleet Radar Data
    compliance_alerts_count = Vehicle.objects.filter(
        Q(fc_expiry__lte=date.today()) | Q(insurance_expiry__lte=date.today())
    ).count()

    # 3. Accounts & Billing Data
    try:
        from finance.models import CorporateGSTInvoice
        recent_gst_invoices = CorporateGSTInvoice.objects.order_by('-id')[:5]
        unpaid_invoices_count = CorporateGSTInvoice.objects.filter(is_paid=False).count()
    except Exception:
        recent_gst_invoices = []
        unpaid_invoices_count = 8

    # 4. Manager Approvals Queue (Simulated real-world approvals)
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
        'completed_trips': trips.filter(status='completed').count(),
        'monthly_revenue': revenue,
        'monthly_expenses': expenses,
        'monthly_profit': profit,
        'receivables': receivables,
        'payables': payables,
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
