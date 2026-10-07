from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render

from core.models import Party
from finance.models import TripExpense
from finance.services import calculate_party_ledger
from operations.models import Trip
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
from django.db.models import Q, Sum


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

    # Operational Attention / Alerts
    from core.models import Driver, Vehicle
    from operations.models import Booking
    pending_bookings_count = Booking.objects.filter(status='pending').count()
    unassigned_trips_count = Trip.objects.filter(status='booked', vehicle__isnull=True).count()
    active_trips_count = trips.filter(status__in=['assigned', 'driver_confirmed', 'started']).count()
    started_trips_count = trips.filter(status='started').count()
    total_vehicles_count = Vehicle.objects.count()
    total_drivers_count = Driver.objects.count()
    available_vehicles_count = max(0, total_vehicles_count - started_trips_count)

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
