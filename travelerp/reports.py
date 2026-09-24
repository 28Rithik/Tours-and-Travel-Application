from decimal import Decimal

from core.models import Party, Vehicle
from finance.models import DriverSettlement, FuelRecord
from operations.models import Trip


def _profitability_rows(queryset, group_field):
    rows = []
    for group in queryset:
        trips = Trip.objects.filter(**{group_field: group}, status__in=['completed', 'billed', 'settled']).prefetch_related('expenses', 'fuel_records', 'settlements', 'supplier_costs')
        revenue = sum((trip.total_amount for trip in trips), Decimal('0'))
        expenses = sum((expense.amount for trip in trips for expense in trip.expenses.all()), Decimal('0'))
        fuel = sum((record.amount for trip in trips for record in trip.fuel_records.all()), Decimal('0'))
        batta = sum((settlement.batta for trip in trips for settlement in trip.settlements.all()), Decimal('0'))
        supplier_cost = sum((cost.amount for trip in trips for cost in trip.supplier_costs.all()), Decimal('0'))
        total_cost = expenses + fuel + batta + supplier_cost
        rows.append({'group': group, 'revenue': revenue, 'cost': total_cost, 'profit': revenue - total_cost})
    return rows


def vehicle_profitability():
    return _profitability_rows(Vehicle.objects.all().order_by('registration_number'), 'vehicle')


def party_profitability():
    return _profitability_rows(Party.objects.all().order_by('name'), 'party')