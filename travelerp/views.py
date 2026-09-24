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


@login_required
def dashboard(request):
    month_start = date.today().replace(day=1)
    trips = Trip.objects.all()
    monthly_trips = trips.filter(start_date__gte=month_start)
    revenue = sum((trip.total_amount for trip in monthly_trips), Decimal('0'))
    expenses = TripExpense.objects.filter(date__gte=month_start).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    receivables = Decimal('0')
    payables = Decimal('0')
    for party in Party.objects.filter(is_active=True):
        balance = calculate_party_ledger(party)['closing_balance']
        if balance >= 0:
            receivables += balance
        else:
            payables += abs(balance)
    return render(request, 'dashboard.html', {
        'active_trips': trips.filter(status__in=['assigned', 'driver_confirmed', 'started']).count(),
        'completed_trips': trips.filter(status='completed').count(),
        'monthly_revenue': revenue,
        'monthly_expenses': expenses,
        'monthly_profit': revenue - expenses,
        'receivables': receivables,
        'payables': payables,
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
