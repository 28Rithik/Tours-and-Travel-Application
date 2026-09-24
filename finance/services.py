from decimal import Decimal

from django.db.models import Sum

from finance.models import LedgerAdjustment, Payment, SupplierTripCost
from operations.models import Trip


def _in_range(queryset, field, from_date=None, to_date=None):
    if from_date:
        queryset = queryset.filter(**{f'{field}__gte': from_date})
    if to_date:
        queryset = queryset.filter(**{f'{field}__lte': to_date})
    return queryset


def calculate_party_ledger(party, from_date=None, to_date=None, vehicle=None, driver=None, status=None):
    trips = _in_range(
        Trip.objects.filter(party=party, status__in=['completed', 'billed', 'settled']),
        'start_date', from_date, to_date,
    )
    if vehicle:
        trips = trips.filter(vehicle=vehicle)
    if driver:
        trips = trips.filter(driver=driver)
    if status:
        trips = trips.filter(status=status)
        
    payments = _in_range(Payment.objects.filter(party=party), 'date', from_date, to_date)
    adjustments = _in_range(LedgerAdjustment.objects.filter(party=party), 'date', from_date, to_date)

    trip_total = sum((trip.total_amount for trip in trips), Decimal('0'))
    
    receipt_total = payments.filter(payment_type='customer_receipt').aggregate(total=Sum('amount'))['total'] or Decimal('0')
    supplier_total = payments.filter(payment_type__in=['supplier_payment', 'advance']).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    adjustment_total = adjustments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    closing_balance = party.opening_balance + trip_total - receipt_total + supplier_total + adjustment_total
    return {
        'trips': trips,
        'payments': payments,
        'adjustments': adjustments,
        'trip_total': trip_total,
        'receipt_total': receipt_total,
        'supplier_total': supplier_total,
        'adjustment_total': adjustment_total,
        'opening_balance': party.opening_balance,
        'closing_balance': closing_balance,
    }


def calculate_supplier_ledger(supplier, from_date=None, to_date=None, vehicle=None, driver=None, status=None):
    costs = _in_range(SupplierTripCost.objects.filter(supplier=supplier), 'date', from_date, to_date)
    costs = costs.filter(trip__status__in=['completed', 'billed', 'settled']).select_related('trip', 'vehicle')
    if vehicle:
        costs = costs.filter(vehicle=vehicle)
    if driver:
        costs = costs.filter(trip__driver=driver)
    if status:
        costs = costs.filter(trip__status=status)
        
    payments = _in_range(Payment.objects.filter(party=supplier, payment_type__in=['supplier_payment', 'advance']), 'date', from_date, to_date)
    adjustments = _in_range(LedgerAdjustment.objects.filter(party=supplier), 'date', from_date, to_date)
    
    # Calculate Deductions: Fuel paid by company for supplier vehicles
    from finance.models import FuelRecord
    fuel_records = _in_range(FuelRecord.objects.filter(vehicle__owner_party=supplier), 'date', from_date, to_date)
    if vehicle:
        fuel_records = fuel_records.filter(vehicle=vehicle)
    
    cost_total = costs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Calculate Commission deductions from those trips
    commission_total = Decimal('0')
    for cost in costs:
        if cost.trip_id and cost.trip:
            commission_total += cost.trip.commission
            
    fuel_total = Decimal('0')
    for fuel in fuel_records:
        fuel_total += fuel.amount

    paid_total = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    adjustment_total = adjustments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Net Supplier Earnings = Gross Cost - Commission - Fuel
    net_earnings = cost_total - commission_total - fuel_total
    
    closing_balance = supplier.opening_balance + net_earnings - paid_total + adjustment_total
    return {
        'supplier_costs': costs,
        'payments': payments,
        'adjustments': adjustments,
        'fuel_records': fuel_records,
        'cost_total': cost_total,
        'commission_total': commission_total,
        'fuel_total': fuel_total,
        'net_earnings': net_earnings,
        'trip_total': net_earnings,  # For backwards compatibility with standard template logic
        'supplier_cost_total': cost_total,
        'receipt_total': Decimal('0'),
        'supplier_total': paid_total,
        'adjustment_total': adjustment_total,
		'opening_balance': supplier.opening_balance,
		'closing_balance': closing_balance,
	}

def calculate_owned_fleet_pl(from_date=None, to_date=None, vehicle=None):
	# Gross Revenue from Trips
	trips = _in_range(
		Trip.objects.filter(vehicle__ownership_type='owned', status__in=['completed', 'billed', 'settled']),
		'start_date', from_date, to_date
	).select_related('vehicle')
	if vehicle:
		trips = trips.filter(vehicle=vehicle)

	gross_revenue = sum((trip.total_amount for trip in trips), Decimal('0'))

	# Fuel Costs
	from finance.models import FuelRecord
	fuel_records = _in_range(FuelRecord.objects.filter(vehicle__ownership_type='owned'), 'date', from_date, to_date)
	if vehicle:
		fuel_records = fuel_records.filter(vehicle=vehicle)
	total_fuel = fuel_records.aggregate(total=Sum('amount'))['total'] or Decimal('0')

	# Driver Pay (Batta + Expenses paid by company for these trips)
	driver_pay = Decimal('0')
	for trip in trips:
		driver_pay += trip.driver_bata + trip.company_paid_expenses

	# Maintenance Costs
	from maintenance.models import ServiceRecord
	service_records = _in_range(ServiceRecord.objects.filter(vehicle__ownership_type='owned'), 'date', from_date, to_date)
	if vehicle:
		service_records = service_records.filter(vehicle=vehicle)
	total_maintenance = service_records.aggregate(total=Sum('total_cost'))['total'] or Decimal('0')

	# True Net Profit
	true_net_profit = gross_revenue - total_fuel - driver_pay - total_maintenance

	return {
		'gross_revenue': gross_revenue,
		'total_fuel': total_fuel,
		'driver_pay': driver_pay,
		'total_maintenance': total_maintenance,
		'true_net_profit': true_net_profit,
		'trips_count': trips.count(),
		'trips': trips,
		'fuel_records': fuel_records,
		'service_records': service_records
	}
