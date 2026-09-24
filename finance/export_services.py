import calendar
import csv
import io
import xml.etree.ElementTree as ET
from datetime import date, datetime
from decimal import Decimal

from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

from core.models import Driver, Party
from operations.models import Trip, TrafficFine
from fleet_contracts.models import ContractTripLog, ContractMonthlyInvoice
from finance.models import (
    FuelRecord,
    TripExpense,
    FastagTollDeduction,
    DriverSalaryProfile,
    DriverPayslip,
    DriverAdvance,
)


def _parse_date(date_val):
    if not date_val:
        return None
    if isinstance(date_val, str):
        return datetime.strptime(date_val, '%Y-%m-%d').date()
    if isinstance(date_val, datetime):
        return date_val.date()
    return date_val


def _format_tally_date(date_val):
    d = _parse_date(date_val)
    if d:
        return d.strftime('%Y%m%d')
    return timezone.now().strftime('%Y%m%d')


def _format_iso_date(date_val):
    d = _parse_date(date_val)
    if d:
        return d.strftime('%Y-%m-%d')
    return timezone.now().strftime('%Y-%m-%d')


def _xml_prettify(elem):
    """Return pretty-printed XML string with UTF-8 declaration."""
    import xml.dom.minidom
    rough_string = ET.tostring(elem, encoding='utf-8')
    reparsed = xml.dom.minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding="utf-8").decode('utf-8')


# ==============================================================================
# 1. TALLY PRIME XML EXPORTERS
# ==============================================================================

def generate_tally_sales_xml(from_date=None, to_date=None, party_id=None):
    """
    Generates Tally Prime compliant XML for sales vouchers.
    Includes completed/billed/settled Trips and ContractMonthlyInvoices.
    """
    d_from = _parse_date(from_date)
    d_to = _parse_date(to_date)

    envelope = ET.Element('ENVELOPE')
    header = ET.SubElement(envelope, 'HEADER')
    tally_req = ET.SubElement(header, 'TALLYREQUEST')
    tally_req.text = 'Import Data'

    body = ET.SubElement(envelope, 'BODY')
    import_data = ET.SubElement(body, 'IMPORTDATA')
    req_data = ET.SubElement(import_data, 'REQUESTDATA')

    # 1. Regular Trips
    trips_qs = Trip.objects.filter(status__in=['completed', 'billed', 'settled'])
    if d_from:
        trips_qs = trips_qs.filter(start_date__gte=d_from)
    if d_to:
        trips_qs = trips_qs.filter(start_date__lte=d_to)
    if party_id:
        trips_qs = trips_qs.filter(party_id=party_id)

    trips_qs = trips_qs.select_related('party', 'vehicle', 'driver').order_by('start_date', 'id')

    for trip in trips_qs:
        total = Decimal(str(trip.total_amount or '0.00'))
        if total <= 0:
            continue

        party_name = trip.party.name if trip.party else (trip.guest_name or "Cash Customer")
        tally_msg = ET.SubElement(req_data, 'TALLYMESSAGE')
        tally_msg.set('xmlns:UDF', 'TallyUDF')

        voucher = ET.SubElement(tally_msg, 'VOUCHER')
        voucher.set('VCHTYPE', 'Sales')
        voucher.set('ACTION', 'Create')

        ET.SubElement(voucher, 'DATE').text = _format_tally_date(trip.start_date)
        ET.SubElement(voucher, 'VOUCHERTYPENAME').text = 'Sales'
        ET.SubElement(voucher, 'VOUCHERNUMBER').text = str(trip.trip_id)
        ET.SubElement(voucher, 'PARTYLEDGERNAME').text = party_name
        
        veh_str = f" ({trip.vehicle.registration_number})" if trip.vehicle else ""
        narration = f"Trip {trip.trip_id} for {party_name}{veh_str} from {trip.start_date} to {trip.end_date}"
        ET.SubElement(voucher, 'NARRATION').text = narration

        # Party Ledger Entry (Debit in Sales Voucher)
        party_entry = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
        ET.SubElement(party_entry, 'LEDGERNAME').text = party_name
        ET.SubElement(party_entry, 'ISDEEMEDPOSITIVE').text = 'Yes'
        ET.SubElement(party_entry, 'AMOUNT').text = f"-{total:.2f}"

        # Sales Revenue Ledger Entry (Credit)
        taxable = Decimal(str(trip.bill_value + trip.total_expenses + trip.customer_billable_fines))
        gst = Decimal(str(trip.gst_amount or '0.00'))

        sales_entry = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
        ET.SubElement(sales_entry, 'LEDGERNAME').text = 'Tour & Transport Revenue'
        ET.SubElement(sales_entry, 'ISDEEMEDPOSITIVE').text = 'No'
        ET.SubElement(sales_entry, 'AMOUNT').text = f"{taxable:.2f}"

        # Output GST Entry (if applicable)
        if gst > 0:
            gst_entry = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
            ET.SubElement(gst_entry, 'LEDGERNAME').text = 'Output GST (Transport Services)'
            ET.SubElement(gst_entry, 'ISDEEMEDPOSITIVE').text = 'No'
            ET.SubElement(gst_entry, 'AMOUNT').text = f"{gst:.2f}"

    # 2. Monthly Contract Invoices
    inv_qs = ContractMonthlyInvoice.objects.exclude(status='draft')
    if d_from:
        inv_qs = inv_qs.filter(billing_month__gte=d_from)
    if d_to:
        inv_qs = inv_qs.filter(billing_month__lte=d_to)
    if party_id:
        inv_qs = inv_qs.filter(contract__customer_id=party_id)

    inv_qs = inv_qs.select_related('contract__customer').order_by('billing_month', 'id')

    for inv in inv_qs:
        total = Decimal(str(inv.grand_total or '0.00'))
        if total <= 0:
            continue

        cust_name = inv.contract.customer.name if inv.contract.customer else "Corporate Client"
        tally_msg = ET.SubElement(req_data, 'TALLYMESSAGE')
        tally_msg.set('xmlns:UDF', 'TallyUDF')

        voucher = ET.SubElement(tally_msg, 'VOUCHER')
        voucher.set('VCHTYPE', 'Sales')
        voucher.set('ACTION', 'Create')

        ET.SubElement(voucher, 'DATE').text = _format_tally_date(inv.billing_month or inv.from_date)
        ET.SubElement(voucher, 'VOUCHERTYPENAME').text = 'Sales'
        ET.SubElement(voucher, 'VOUCHERNUMBER').text = str(inv.invoice_number)
        ET.SubElement(voucher, 'PARTYLEDGERNAME').text = cust_name
        
        narration = f"Monthly Transport Contract Invoice {inv.invoice_number} - {inv.contract.name} ({inv.from_date} to {inv.to_date})"
        ET.SubElement(voucher, 'NARRATION').text = narration

        # Party Entry (Debit)
        party_entry = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
        ET.SubElement(party_entry, 'LEDGERNAME').text = cust_name
        ET.SubElement(party_entry, 'ISDEEMEDPOSITIVE').text = 'Yes'
        ET.SubElement(party_entry, 'AMOUNT').text = f"-{total:.2f}"

        # Contract Revenue (Credit)
        taxable = Decimal(str(inv.net_taxable_amount or '0.00'))
        gst = Decimal(str(inv.gst_amount or '0.00'))

        sales_entry = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
        ET.SubElement(sales_entry, 'LEDGERNAME').text = 'Corporate Contract Transport Revenue'
        ET.SubElement(sales_entry, 'ISDEEMEDPOSITIVE').text = 'No'
        ET.SubElement(sales_entry, 'AMOUNT').text = f"{taxable:.2f}"

        if gst > 0:
            gst_entry = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
            ET.SubElement(gst_entry, 'LEDGERNAME').text = 'Output GST (Corporate Commute)'
            ET.SubElement(gst_entry, 'ISDEEMEDPOSITIVE').text = 'No'
            ET.SubElement(gst_entry, 'AMOUNT').text = f"{gst:.2f}"

    return _xml_prettify(envelope)


def generate_tally_expense_xml(from_date=None, to_date=None):
    """
    Generates Tally Prime compliant XML for payment/purchase expense vouchers.
    Includes FuelRecord, TripExpense, and FastagTollDeduction.
    """
    d_from = _parse_date(from_date)
    d_to = _parse_date(to_date)

    envelope = ET.Element('ENVELOPE')
    header = ET.SubElement(envelope, 'HEADER')
    tally_req = ET.SubElement(header, 'TALLYREQUEST')
    tally_req.text = 'Import Data'

    body = ET.SubElement(envelope, 'BODY')
    import_data = ET.SubElement(body, 'IMPORTDATA')
    req_data = ET.SubElement(import_data, 'REQUESTDATA')

    # 1. Fuel Records
    fuel_qs = FuelRecord.objects.all()
    if d_from:
        fuel_qs = fuel_qs.filter(date__gte=d_from)
    if d_to:
        fuel_qs = fuel_qs.filter(date__lte=d_to)
    fuel_qs = fuel_qs.select_related('vehicle', 'petro_account').order_by('date', 'id')

    for fuel in fuel_qs:
        amt = Decimal(str(fuel.amount or '0.00'))
        if amt <= 0:
            continue

        pay_ledger = fuel.petro_account.account_name if fuel.petro_account else "Company Cash / Bank"
        vch_num = f"FUEL-{fuel.id:04d}"

        tally_msg = ET.SubElement(req_data, 'TALLYMESSAGE')
        tally_msg.set('xmlns:UDF', 'TallyUDF')

        voucher = ET.SubElement(tally_msg, 'VOUCHER')
        voucher.set('VCHTYPE', 'Payment')
        voucher.set('ACTION', 'Create')

        ET.SubElement(voucher, 'DATE').text = _format_tally_date(fuel.date)
        ET.SubElement(voucher, 'VOUCHERTYPENAME').text = 'Payment'
        ET.SubElement(voucher, 'VOUCHERNUMBER').text = vch_num
        ET.SubElement(voucher, 'PARTYLEDGERNAME').text = pay_ledger

        narration = f"Fuel {fuel.fuel_quantity}L @ ₹{fuel.fuel_price}/L for {fuel.vehicle.registration_number} at {fuel.fuel_station or 'Station'}"
        ET.SubElement(voucher, 'NARRATION').text = narration

        # Expense Ledger (Debit)
        exp_entry = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
        ET.SubElement(exp_entry, 'LEDGERNAME').text = 'Vehicle Fuel Expenses'
        ET.SubElement(exp_entry, 'ISDEEMEDPOSITIVE').text = 'Yes'
        ET.SubElement(exp_entry, 'AMOUNT').text = f"-{amt:.2f}"

        # Paid Through Account (Credit)
        pay_entry = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
        ET.SubElement(pay_entry, 'LEDGERNAME').text = pay_ledger
        ET.SubElement(pay_entry, 'ISDEEMEDPOSITIVE').text = 'No'
        ET.SubElement(pay_entry, 'AMOUNT').text = f"{amt:.2f}"

    # 2. Trip Expenses (Tolls, permits, parking, repairs, etc.)
    exp_qs = TripExpense.objects.filter(paid_by__in=['company', 'driver'])
    if d_from:
        exp_qs = exp_qs.filter(date__gte=d_from)
    if d_to:
        exp_qs = exp_qs.filter(date__lte=d_to)
    exp_qs = exp_qs.select_related('trip', 'contract_trip').order_by('date', 'id')

    for exp in exp_qs:
        amt = Decimal(str(exp.amount or '0.00'))
        if amt <= 0:
            continue

        exp_ledger = f"Trip {exp.get_expense_type_display()} Expenses"
        pay_ledger = "Company Cash Account" if exp.paid_by == 'company' else "Driver Imprest / Advance Account"
        vch_num = f"EXP-{exp.id:04d}"

        tally_msg = ET.SubElement(req_data, 'TALLYMESSAGE')
        tally_msg.set('xmlns:UDF', 'TallyUDF')

        voucher = ET.SubElement(tally_msg, 'VOUCHER')
        voucher.set('VCHTYPE', 'Payment')
        voucher.set('ACTION', 'Create')

        ET.SubElement(voucher, 'DATE').text = _format_tally_date(exp.date)
        ET.SubElement(voucher, 'VOUCHERTYPENAME').text = 'Payment'
        ET.SubElement(voucher, 'VOUCHERNUMBER').text = vch_num
        ET.SubElement(voucher, 'PARTYLEDGERNAME').text = pay_ledger

        parent = f"Trip {exp.trip.trip_id}" if exp.trip else (f"Contract Shift {exp.contract_trip}" if exp.contract_trip else "")
        narration = f"{exp.get_expense_type_display()}: {exp.description or 'Duty incurred expense'} ({parent})"
        ET.SubElement(voucher, 'NARRATION').text = narration

        # Expense (Debit)
        exp_entry = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
        ET.SubElement(exp_entry, 'LEDGERNAME').text = exp_ledger
        ET.SubElement(exp_entry, 'ISDEEMEDPOSITIVE').text = 'Yes'
        ET.SubElement(exp_entry, 'AMOUNT').text = f"-{amt:.2f}"

        # Paid Through (Credit)
        pay_entry = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
        ET.SubElement(pay_entry, 'LEDGERNAME').text = pay_ledger
        ET.SubElement(pay_entry, 'ISDEEMEDPOSITIVE').text = 'No'
        ET.SubElement(pay_entry, 'AMOUNT').text = f"{amt:.2f}"

    # 3. FASTag Toll Deductions
    toll_qs = FastagTollDeduction.objects.all()
    if d_from:
        toll_qs = toll_qs.filter(date__date__gte=d_from)
    if d_to:
        toll_qs = toll_qs.filter(date__date__lte=d_to)
    toll_qs = toll_qs.select_related('account', 'vehicle').order_by('date', 'id')

    for toll in toll_qs:
        amt = Decimal(str(toll.amount or '0.00'))
        if amt <= 0:
            continue

        pay_ledger = toll.account.account_name if toll.account else "Corporate FASTag Master Wallet"
        vch_num = f"TOLL-{toll.id:04d}"

        tally_msg = ET.SubElement(req_data, 'TALLYMESSAGE')
        tally_msg.set('xmlns:UDF', 'TallyUDF')

        voucher = ET.SubElement(tally_msg, 'VOUCHER')
        voucher.set('VCHTYPE', 'Payment')
        voucher.set('ACTION', 'Create')

        toll_date = toll.date.date() if hasattr(toll.date, 'date') else toll.date
        ET.SubElement(voucher, 'DATE').text = _format_tally_date(toll_date)
        ET.SubElement(voucher, 'VOUCHERTYPENAME').text = 'Payment'
        ET.SubElement(voucher, 'VOUCHERNUMBER').text = vch_num
        ET.SubElement(voucher, 'PARTYLEDGERNAME').text = pay_ledger

        narration = f"FASTag highway toll at {toll.toll_plaza or 'NHAI Toll'} for {toll.vehicle.registration_number}"
        ET.SubElement(voucher, 'NARRATION').text = narration

        # Expense (Debit)
        exp_entry = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
        ET.SubElement(exp_entry, 'LEDGERNAME').text = 'Highway FASTag Toll Expenses'
        ET.SubElement(exp_entry, 'ISDEEMEDPOSITIVE').text = 'Yes'
        ET.SubElement(exp_entry, 'AMOUNT').text = f"-{amt:.2f}"

        # Paid Through (Credit)
        pay_entry = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
        ET.SubElement(pay_entry, 'LEDGERNAME').text = pay_ledger
        ET.SubElement(pay_entry, 'ISDEEMEDPOSITIVE').text = 'No'
        ET.SubElement(pay_entry, 'AMOUNT').text = f"{amt:.2f}"

    return _xml_prettify(envelope)


# ==============================================================================
# 2. ZOHO BOOKS CSV EXPORTERS
# ==============================================================================

def generate_zoho_sales_csv(from_date=None, to_date=None, party_id=None):
    """
    Generates standard Zoho Books compatible CSV for customer invoices.
    """
    d_from = _parse_date(from_date)
    d_to = _parse_date(to_date)

    output = io.StringIO()
    writer = csv.writer(output)

    # Standard Zoho Books Invoice Headers
    writer.writerow([
        'Invoice Number',
        'Customer Name',
        'Invoice Date',
        'Due Date',
        'Item Name',
        'Item Description',
        'Quantity',
        'Rate',
        'Discount',
        'Tax Name',
        'Tax Percentage',
        'Item Total',
        'Status',
        'Notes',
    ])

    # 1. Trips
    trips_qs = Trip.objects.filter(status__in=['completed', 'billed', 'settled'])
    if d_from:
        trips_qs = trips_qs.filter(start_date__gte=d_from)
    if d_to:
        trips_qs = trips_qs.filter(start_date__lte=d_to)
    if party_id:
        trips_qs = trips_qs.filter(party_id=party_id)

    trips_qs = trips_qs.select_related('party', 'vehicle').order_by('start_date', 'id')

    for trip in trips_qs:
        total = Decimal(str(trip.total_amount or '0.00'))
        if total <= 0:
            continue

        customer_name = trip.party.name if trip.party else (trip.guest_name or "Walk-in Customer")
        inv_date = _format_iso_date(trip.start_date)
        due_date = _format_iso_date(trip.end_date or trip.start_date)
        
        taxable = Decimal(str(trip.bill_value + trip.total_expenses + trip.customer_billable_fines))
        gst_rate = Decimal('5.00')
        if trip.booking_id and trip.booking.gst_rate:
            gst_rate = trip.booking.gst_rate
        elif trip.bulk_contract_day_id and trip.bulk_contract_day.contract.gst_rate:
            gst_rate = trip.bulk_contract_day.contract.gst_rate

        tax_name = f"GST {gst_rate:.1f}%" if gst_rate > 0 else "None"
        veh_str = f" [{trip.vehicle.registration_number}]" if trip.vehicle else ""
        desc = f"Trip from {trip.pickup_location} to {trip.destination}{veh_str} ({trip.days_count} days)"

        status_str = "Paid" if trip.status == 'settled' else ("Sent" if trip.status == 'billed' else "Confirmed")

        writer.writerow([
            trip.trip_id,
            customer_name,
            inv_date,
            due_date,
            'Vehicle Rental & Tour Services',
            desc,
            1,
            f"{taxable:.2f}",
            0,
            tax_name,
            f"{gst_rate:.2f}",
            f"{total:.2f}",
            status_str,
            f"Automated ERP export for Trip {trip.trip_id}",
        ])

    # 2. Monthly Contract Invoices
    inv_qs = ContractMonthlyInvoice.objects.exclude(status='draft')
    if d_from:
        inv_qs = inv_qs.filter(billing_month__gte=d_from)
    if d_to:
        inv_qs = inv_qs.filter(billing_month__lte=d_to)
    if party_id:
        inv_qs = inv_qs.filter(contract__customer_id=party_id)

    inv_qs = inv_qs.select_related('contract__customer').order_by('billing_month', 'id')

    for inv in inv_qs:
        total = Decimal(str(inv.grand_total or '0.00'))
        if total <= 0:
            continue

        customer_name = inv.contract.customer.name if inv.contract.customer else "Corporate Client"
        inv_date = _format_iso_date(inv.billing_month or inv.from_date)
        due_date = _format_iso_date(inv.due_date or inv.to_date)
        taxable = Decimal(str(inv.net_taxable_amount or '0.00'))
        gst_rate = Decimal(str(inv.gst_rate or '5.00'))

        writer.writerow([
            inv.invoice_number,
            customer_name,
            inv_date,
            due_date,
            'Dedicated Fleet Staff Commute Services',
            f"Monthly Billing for {inv.contract.name} ({inv.from_date} to {inv.to_date})",
            1,
            f"{taxable:.2f}",
            0,
            f"GST {gst_rate:.1f}%",
            f"{gst_rate:.2f}",
            f"{total:.2f}",
            inv.get_status_display(),
            inv.notes or f"Generated via TravelERP Transport Contracts",
        ])

    return output.getvalue()


def generate_zoho_expense_csv(from_date=None, to_date=None):
    """
    Generates standard Zoho Books compatible CSV for fleet operational expenses.
    """
    d_from = _parse_date(from_date)
    d_to = _parse_date(to_date)

    output = io.StringIO()
    writer = csv.writer(output)

    # Standard Zoho Books Expense Headers
    writer.writerow([
        'Expense Date',
        'Expense Account',
        'Paid Through',
        'Amount',
        'Tax Name',
        'Vendor Name',
        'Reference#',
        'Customer Name',
        'Notes',
        'Vehicle Number',
    ])

    # 1. Fuel Records
    fuel_qs = FuelRecord.objects.all()
    if d_from:
        fuel_qs = fuel_qs.filter(date__gte=d_from)
    if d_to:
        fuel_qs = fuel_qs.filter(date__lte=d_to)
    fuel_qs = fuel_qs.select_related('vehicle', 'petro_account').order_by('date', 'id')

    for fuel in fuel_qs:
        amt = Decimal(str(fuel.amount or '0.00'))
        if amt <= 0:
            continue

        paid_thru = fuel.petro_account.account_name if fuel.petro_account else "Petty Cash"
        vendor = fuel.fuel_station or (fuel.petro_account.account_name if fuel.petro_account else "Fuel Station")
        ref_no = fuel.api_reference_number or f"FUEL-{fuel.id:04d}"
        notes = f"{fuel.fuel_quantity}L @ ₹{fuel.fuel_price}/L (Opening: {fuel.opening_km or '-'}, Closing: {fuel.closing_km or '-'})"

        writer.writerow([
            _format_iso_date(fuel.date),
            'Automobile Fuel Expenses',
            paid_thru,
            f"{amt:.2f}",
            'Non-Taxable',
            vendor,
            ref_no,
            '',
            notes,
            fuel.vehicle.registration_number,
        ])

    # 2. Trip Expenses
    exp_qs = TripExpense.objects.filter(paid_by__in=['company', 'driver'])
    if d_from:
        exp_qs = exp_qs.filter(date__gte=d_from)
    if d_to:
        exp_qs = exp_qs.filter(date__lte=d_to)
    exp_qs = exp_qs.select_related('trip__party', 'contract_trip').order_by('date', 'id')

    for exp in exp_qs:
        amt = Decimal(str(exp.amount or '0.00'))
        if amt <= 0:
            continue

        acct = f"Travel & Toll - {exp.get_expense_type_display()}"
        paid_thru = "Petty Cash" if exp.paid_by == 'company' else "Driver Imprest Advance"
        customer = ""
        if exp.trip and exp.trip.party:
            customer = exp.trip.party.name
        
        veh_num = ""
        if exp.trip and exp.trip.vehicle:
            veh_num = exp.trip.vehicle.registration_number
        elif exp.contract_trip and exp.contract_trip.vehicle:
            veh_num = exp.contract_trip.vehicle.registration_number

        writer.writerow([
            _format_iso_date(exp.date),
            acct,
            paid_thru,
            f"{amt:.2f}",
            'Non-Taxable',
            exp.get_paid_by_display(),
            f"EXP-{exp.id:04d}",
            customer,
            exp.description or exp.get_expense_type_display(),
            veh_num,
        ])

    # 3. FASTag Toll Deductions
    toll_qs = FastagTollDeduction.objects.all()
    if d_from:
        toll_qs = toll_qs.filter(date__date__gte=d_from)
    if d_to:
        toll_qs = toll_qs.filter(date__date__lte=d_to)
    toll_qs = toll_qs.select_related('account', 'vehicle', 'trip__party').order_by('date', 'id')

    for toll in toll_qs:
        amt = Decimal(str(toll.amount or '0.00'))
        if amt <= 0:
            continue

        paid_thru = toll.account.account_name if toll.account else "FASTag ICICI Wallet"
        vendor = toll.toll_plaza or "NHAI FASTag Toll"
        customer = toll.trip.party.name if (toll.trip and toll.trip.party) else ""

        toll_date = toll.date.date() if hasattr(toll.date, 'date') else toll.date
        writer.writerow([
            _format_iso_date(toll_date),
            'Highway FASTag Toll Charges',
            paid_thru,
            f"{amt:.2f}",
            'Non-Taxable',
            vendor,
            f"TOLL-{toll.id:04d}",
            customer,
            f"Toll deduction at {toll.toll_plaza}",
            toll.vehicle.registration_number,
        ])

    return output.getvalue()


# ==============================================================================
# 3. ATTENDANCE-TO-PAYROLL AUTOMATED BRIDGE
# ==============================================================================

def calculate_driver_duty_days(driver, month, year):
    """
    Computes exact unique duty days worked by a driver in a given calendar month
    from both regular Trip records and fleet ContractTripLog shifts.
    """
    _, last_day = calendar.monthrange(year, month)
    start_of_month = date(year, month, 1)
    end_of_month = date(year, month, last_day)

    duty_dates = set()

    # 1. Regular Trips
    trips = Trip.objects.filter(
        driver=driver,
        status__in=['assigned', 'driver_confirmed', 'started', 'completed', 'billed', 'settled'],
        start_date__lte=end_of_month,
    ).filter(
        models.Q(end_date__gte=start_of_month) | models.Q(end_date__isnull=True, start_date__gte=start_of_month)
    )

    for trip in trips:
        t_start = max(trip.start_date, start_of_month)
        t_end = min(trip.end_date or trip.start_date, end_of_month)
        cur = t_start
        from datetime import timedelta
        while cur <= t_end:
            duty_dates.add(cur)
            cur += timedelta(days=1)

    # 2. Fleet Contract Trip Logs
    contract_logs = ContractTripLog.objects.filter(
        driver=driver,
        date__gte=start_of_month,
        date__lte=end_of_month,
    ).exclude(status='cancelled')

    for log in contract_logs:
        duty_dates.add(log.date)

    days_present = len(duty_dates)
    # Cap at total days in the month
    if days_present > last_day:
        days_present = last_day

    return {
        'duty_dates': sorted(list(duty_dates)),
        'duty_days_count': days_present,
        'total_trips': trips.count(),
        'total_contract_shifts': contract_logs.count(),
        'days_in_month': last_day,
    }


def calculate_driver_monthly_deductions(driver, month, year):
    """
    Computes traffic fine deductions and advance recoveries for the driver in month.
    """
    _, last_day = calendar.monthrange(year, month)
    start_of_month = date(year, month, 1)
    end_of_month = date(year, month, last_day)

    # Traffic fines where financial_responsibility='driver' and not already paid by driver out of pocket
    fines = TrafficFine.objects.filter(
        driver=driver,
        financial_responsibility='driver',
        paid_by__in=['company', 'unpaid'],
        date_of_offence__date__gte=start_of_month,
        date_of_offence__date__lte=end_of_month,
    )
    total_fines = fines.aggregate(total=Sum('fine_amount'))['total'] or Decimal('0.00')

    # Advances disbursed in this calendar month
    advances = DriverAdvance.objects.filter(
        driver=driver,
        date__gte=start_of_month,
        date__lte=end_of_month,
    )
    total_advances = advances.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    return {
        'traffic_fines_deduction': Decimal(str(total_fines)),
        'advances_recovered': Decimal(str(total_advances)),
        'fines_list': list(fines),
        'advances_list': list(advances),
    }


def generate_monthly_driver_payslip(driver, month, year, override_days=None):
    """
    Generates or recalculates a DriverPayslip for the given driver, month, and year.
    Connects duty logs to prorated basic salary + allowances, EPF, ESI, and deductions.
    """
    attendance = calculate_driver_duty_days(driver, month, year)
    days_present = override_days if override_days is not None else attendance['duty_days_count']

    deductions = calculate_driver_monthly_deductions(driver, month, year)
    total_fines = deductions['traffic_fines_deduction']
    total_advances = deductions['advances_recovered']

    # Prorate from DriverSalaryProfile if present
    basic_salary = Decimal('0.00')
    allowances = Decimal('0.00')
    epf_deduction = Decimal('0.00')
    esi_deduction = Decimal('0.00')

    if hasattr(driver, 'salary_profile'):
        profile = driver.salary_profile
        # Standard Indian payroll proration: 30 days divisor
        proration = Decimal(str(days_present)) / Decimal('30.0')
        basic_salary = round(profile.basic_salary * proration, 2)
        allowances = round(profile.allowances * proration, 2)
        gross = basic_salary + allowances

        if profile.epf_number:
            epf_deduction = round(basic_salary * (profile.epf_deduction_rate / Decimal('100.0')), 2)
        if profile.esi_number:
            esi_deduction = round(gross * (profile.esi_deduction_rate / Decimal('100.0')), 2)

    gross = basic_salary + allowances
    statutory_deductions = epf_deduction + esi_deduction
    available_for_recovery = max(Decimal('0.00'), gross - statutory_deductions)

    actual_fines = min(total_fines, available_for_recovery)
    available_for_advances = max(Decimal('0.00'), available_for_recovery - actual_fines)
    actual_advances = min(total_advances, available_for_advances)

    payslip, created = DriverPayslip.objects.update_or_create(
        driver=driver,
        month=month,
        year=year,
        defaults={
            'days_present': days_present,
            'basic_salary': basic_salary,
            'allowances': allowances,
            'epf_deduction': epf_deduction,
            'esi_deduction': esi_deduction,
            'traffic_fines_deduction': actual_fines,
            'advances_recovered': actual_advances,
        }
    )

    return payslip


def generate_batch_payroll(month, year):
    """
    Executes 1-click batch payroll generation for all active drivers.
    Returns comprehensive run stats.
    """
    active_drivers = Driver.objects.filter(status='active').order_by('name')
    
    total_drivers = active_drivers.count()
    payslips = []
    total_gross = Decimal('0.00')
    total_deductions = Decimal('0.00')
    total_net = Decimal('0.00')
    total_duty_days = 0

    for driver in active_drivers:
        payslip = generate_monthly_driver_payslip(driver, month, year)
        payslips.append(payslip)
        total_gross += payslip.gross_earnings
        total_deductions += payslip.total_deductions
        total_net += payslip.net_payable
        total_duty_days += payslip.days_present

    return {
        'month': month,
        'year': year,
        'total_drivers': total_drivers,
        'payslips_count': len(payslips),
        'total_duty_days': total_duty_days,
        'total_gross': total_gross,
        'total_deductions': total_deductions,
        'total_net_payable': total_net,
        'payslips': payslips,
    }
