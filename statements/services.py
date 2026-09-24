from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum

from finance.models import TripExpense, LedgerAdjustment, Payment
from finance.services import calculate_party_ledger, calculate_supplier_ledger, _in_range
from fleet_contracts.models import ContractTripLog
from .models import GeneratedStatement
from operations.models import Booking

import io
from django.core.files.base import ContentFile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors


def build_statement_rows(party, from_date, to_date, vehicle=None, driver=None, status=None, transport_contract=None):
    if transport_contract:
        return _build_contract_statement_rows(transport_contract, from_date, to_date, vehicle, driver, status)
    
    is_supplier = party.party_type == 'supplier'
    ledger = (calculate_supplier_ledger if is_supplier else calculate_party_ledger)(party, from_date, to_date, vehicle=vehicle, driver=driver, status=status)
    rows = []
    if is_supplier:
        for cost in ledger['supplier_costs']:
            trip = cost.trip
            commission = trip.commission if trip else Decimal('0')
            rows.append({
                'date': cost.date, 'row_type': 'trip', 'description': 'OUTSOURCED TRIP',
                'booking_number': trip.booking.booking_number if trip and trip.booking else '', 
                'guest_name': trip.guest_name if trip else '',
                'vehicle_type': trip.vehicle.vehicle_type if trip and trip.vehicle else '',
                'supplier_name': cost.supplier.name,
                'vehicle_number': cost.vehicle.registration_number if cost.vehicle else '', 
                'start_date': trip.start_date if trip else '',
                'start_time': trip.start_time if trip else '', 
                'end_date': trip.end_date if trip else '', 
                'end_time': trip.end_time if trip else '',
                'days': trip.days_count if trip else 1, 
                'rent': cost.amount, 
                'commission': commission,
                'total': cost.amount - commission,
                'received': Decimal('0'), 'balance': cost.amount - commission,
                'taxable': cost.amount,
            })
            
        for fuel in ledger.get('fuel_records', []):
            rows.append({
                'date': fuel.date, 'row_type': 'expense', 
                'description': f"FUEL DEDUCTION: {fuel.vehicle.registration_number}",
                'total': -fuel.amount,  # Negative because it reduces the payable amount
                'taxable': Decimal('0'),
            })
    else:
        for trip in ledger['trips'].select_related('vehicle', 'booking').prefetch_related('expenses'):
            expenses = {}
            for expense in trip.expenses.all():
                expenses[expense.expense_type] = expenses.get(expense.expense_type, Decimal('0')) + expense.amount
            rows.append({
                'date': trip.start_date,
                'row_type': 'trip',
                'booking_number': trip.booking.booking_number if trip.booking else (f'Contract: {trip.bulk_contract_day.contract.name}' if trip.bulk_contract_day else ''),
                'guest_name': trip.guest_name,
                'vehicle_type': trip.vehicle.vehicle_type if trip.vehicle else '',
                'supplier_name': trip.vehicle.owner_party.name if trip.vehicle and trip.vehicle.ownership_type == 'outsourced' and trip.vehicle.owner_party_id else '',
                'vehicle_number': trip.vehicle.registration_number if trip.vehicle else '',
                'start_date': trip.start_date,
                'start_time': trip.start_time,
                'end_date': trip.end_date,
                'end_time': trip.end_time,
                'days': trip.days_count,
                'rent': trip.day_amount,
                'used_km': trip.used_km,
                'km_rate': trip.km_rate,
                'km_amount': trip.km_amount,
                'day_amount': trip.day_amount,
                'bill_value': trip.bill_value,
                'commission': trip.commission,
                'batta': trip.driver_bata,
                'toll': expenses.get('toll', Decimal('0')),
                'permit': expenses.get('permit', Decimal('0')),
                'parking': expenses.get('parking', Decimal('0')),
                'fines': trip.customer_billable_fines,
                'taxable': trip.bill_value + trip.total_expenses + trip.customer_billable_fines,
                'gst_amount': trip.gst_amount,
                'total': trip.total_amount,
                'advance': Decimal('0'),
                'received': trip.received_amount,
                'balance': trip.balance,
            })

    for payment in ledger['payments']:
        rows.append({
            'date': payment.date,
            'row_type': 'payment',
            'description': payment.get_payment_type_display().upper(),
            'total': payment.amount,
            'received': payment.amount if payment.payment_type == 'customer_receipt' else Decimal('0'),
        })
    for adjustment in ledger['adjustments']:
        rows.append({
            'date': adjustment.date,
            'row_type': 'adjustment',
            'description': adjustment.description,
            'total': adjustment.amount,
        })
    return sorted(rows, key=lambda row: (row['date'], row['row_type']))


def calculate_contract_ledger(transport_contract, from_date, to_date, vehicle=None, driver=None, status=None):
    logs = _in_range(ContractTripLog.objects.filter(shift__route__contract=transport_contract, status='completed'), 'date', from_date, to_date)
    if vehicle:
        logs = logs.filter(vehicle=vehicle)
    if driver:
        logs = logs.filter(driver=driver)

    payments = _in_range(Payment.objects.filter(contract_trip__shift__route__contract=transport_contract), 'date', from_date, to_date)
    
    trip_total = Decimal('0')
    gst_total = Decimal('0')
    expenses_total = Decimal('0')
    
    if transport_contract.billing_model == 'fixed_monthly':
        trip_total = transport_contract.default_rate
    elif transport_contract.billing_model == 'per_trip':
        # Sum rate_override or default_rate for each log
        for log in logs:
            rate = log.shift.route.rate_override if log.shift.route.rate_override else transport_contract.default_rate
            trip_total += rate
    elif transport_contract.billing_model == 'per_km':
        for log in logs:
            if log.opening_km is not None and log.closing_km is not None:
                distance = log.closing_km - log.opening_km
                trip_total += Decimal(str(distance)) * transport_contract.default_rate
                
    # Add billable expenses linked to these contract trips
    expenses = TripExpense.objects.filter(contract_trip__in=logs, billable_to_customer=True)
    expenses_total = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    taxable_amount = trip_total + expenses_total
    
    if transport_contract.gst_rate > 0:
        gst_total = (taxable_amount * transport_contract.gst_rate) / Decimal('100')
        
    grand_total = taxable_amount + gst_total
    
    receipt_total = payments.filter(payment_type='customer_receipt').aggregate(total=Sum('amount'))['total'] or Decimal('0')
    closing_balance = grand_total - receipt_total
    
    return {
        'logs': logs,
        'payments': payments,
        'expenses': expenses,
        'trip_total': trip_total,
        'expenses_total': expenses_total,
        'taxable_amount': taxable_amount,
        'gst_amount': gst_total,
        'grand_total': grand_total,
        'receipt_total': receipt_total,
        'closing_balance': closing_balance,
        'opening_balance': Decimal('0'),
    }


def _build_contract_statement_rows(transport_contract, from_date, to_date, vehicle=None, driver=None, status=None):
    ledger = calculate_contract_ledger(transport_contract, from_date, to_date, vehicle, driver, status)
    rows = []
    
    if transport_contract.billing_model == 'fixed_monthly':
        rows.append({
            'date': to_date,
            'row_type': 'contract_trip',
            'description': f"Fixed Monthly Rent - {from_date.strftime('%B %Y')}",
            'rent': ledger['trip_total'],
            'taxable': ledger['trip_total'],
            'total': ledger['trip_total']
        })
    else:
        # Group by route for per_trip and per_km to provide summary
        route_summary = {}
        for log in ledger['logs']:
            route_id = log.shift.route_id
            if route_id not in route_summary:
                route_summary[route_id] = {
                    'route_name': log.shift.route.name,
                    'count': 0,
                    'kms': 0,
                    'total': Decimal('0'),
                }
            
            route_summary[route_id]['count'] += 1
            if log.opening_km is not None and log.closing_km is not None:
                route_summary[route_id]['kms'] += (log.closing_km - log.opening_km)
                
            if transport_contract.billing_model == 'per_trip':
                rate = log.shift.route.rate_override if log.shift.route.rate_override else transport_contract.default_rate
                route_summary[route_id]['total'] += rate
            elif transport_contract.billing_model == 'per_km' and log.opening_km is not None and log.closing_km is not None:
                distance = log.closing_km - log.opening_km
                route_summary[route_id]['total'] += Decimal(str(distance)) * transport_contract.default_rate

        for route_id, summary in route_summary.items():
            desc = f"Route Summary: {summary['route_name']} ({summary['count']} Trips)"
            if transport_contract.billing_model == 'per_km':
                desc += f" - {summary['kms']} Total KMs"
                
            rows.append({
                'date': to_date,
                'row_type': 'contract_trip',
                'description': desc,
                'rent': summary['total'],
                'taxable': summary['total'],
                'total': summary['total']
            })
            
    # Add expenses
    expenses_grouped = {}
    for expense in ledger['expenses']:
        expenses_grouped[expense.expense_type] = expenses_grouped.get(expense.expense_type, Decimal('0')) + expense.amount
        
    for exp_type, amt in expenses_grouped.items():
        rows.append({
            'date': to_date,
            'row_type': 'expense',
            'description': f"Additional Expense: {exp_type.title()}",
            'total': amt,
            'taxable': amt
        })

    for payment in ledger['payments']:
        rows.append({
            'date': payment.date,
            'row_type': 'payment',
            'description': payment.get_payment_type_display().upper(),
            'total': payment.amount,
            'received': payment.amount if payment.payment_type == 'customer_receipt' else Decimal('0'),
        })
        
    return sorted(rows, key=lambda row: (row['date'], row['row_type']))


def generate_invoice_for_booking(booking: Booking):
    """
    Auto-generates a GST invoice for a given booking when payment is confirmed.
    """
    total_amount = booking.quoted_price or 0
    gst_rate = booking.gst_rate or 5.0
    
    # Simple back-calculation assuming quoted_price is inclusive of GST
    subtotal = Decimal(total_amount) / (1 + Decimal(gst_rate) / 100)
    gst_amount = Decimal(total_amount) - subtotal
    
    # Split GST into CGST/SGST (assuming intra-state for simplicity)
    cgst = gst_amount / 2
    sgst = gst_amount / 2

    # TCS calculation (e.g. 5% for overseas tour packages)
    tcs = Decimal(total_amount) * Decimal('0.05') if booking.journey_type == 'outstation' else Decimal('0.0')
    
    closing_balance = Decimal(total_amount) + tcs

    statement = GeneratedStatement.objects.create(
        party=booking.party,
        from_date=booking.pickup_date,
        to_date=booking.drop_date or booking.pickup_date,
        file_format='pdf',
        subtotal=subtotal,
        cgst_amount=cgst,
        sgst_amount=sgst,
        tcs_collected=tcs,
        opening_balance=0,
        closing_balance=closing_balance,
        status='paid'
    )
    
    # Generate Physical PDF using ReportLab
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    
    # Header
    p.setFont("Helvetica-Bold", 24)
    p.drawString(50, 800, "Sivagayathiri Tours and Travels")
    p.setFont("Helvetica", 14)
    p.drawString(50, 775, "INVOICE")
    
    # Details
    p.setFont("Helvetica", 12)
    p.drawString(50, 740, f"Invoice No: {statement.id}")
    p.drawString(50, 720, f"Booking Ref: {booking.booking_number}")
    if booking.party:
        p.drawString(50, 700, f"Bill To: {booking.party.name}")
    p.drawString(50, 680, f"Date: {timezone.now().date()}")
    
    # Amounts
    y_pos = 630
    p.drawString(50, y_pos, "Description")
    p.drawString(400, y_pos, "Amount (INR)")
    p.line(50, y_pos - 5, 500, y_pos - 5)
    
    y_pos -= 30
    p.drawString(50, y_pos, f"Package Booking: {booking.destination}")
    p.drawString(400, y_pos, f"{subtotal:.2f}")
    
    y_pos -= 20
    p.drawString(50, y_pos, f"CGST")
    p.drawString(400, y_pos, f"{cgst:.2f}")
    
    y_pos -= 20
    p.drawString(50, y_pos, f"SGST")
    p.drawString(400, y_pos, f"{sgst:.2f}")
    
    if tcs > 0:
        y_pos -= 20
        p.drawString(50, y_pos, f"TCS (5%)")
        p.drawString(400, y_pos, f"{tcs:.2f}")
        
    p.line(50, y_pos - 15, 500, y_pos - 15)
    y_pos -= 35
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y_pos, "Total (INR)")
    p.drawString(400, y_pos, f"{closing_balance:.2f}")
    
    # Footer
    p.setFont("Helvetica", 10)
    p.setFillColor(colors.gray)
    p.drawString(50, 50, "Thank you for traveling with us!")
    
    p.showPage()
    p.save()
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    # Save to model
    file_name = f"invoice_{booking.booking_number}.pdf"
    statement.file.save(file_name, ContentFile(pdf_bytes), save=True)
    
    return statement
