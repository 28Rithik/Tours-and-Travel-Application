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


# ==============================================================================
# 5. GSTR-1 B2B E-INVOICE CSV EXPORTER
# ==============================================================================

def generate_gstr1_b2b_csv(from_date=None, to_date=None):
    """
    Generates GSTR-1 Table 4A compliant B2B CSV for GST portal filing.
    Compatible with ClearTax / Zoho GST / Tally Prime GSTR-1 import format.

    Columns follow the official GST government portal B2B template:
    GSTIN, Invoice Number, Invoice Date, Invoice Value, Place of Supply,
    Reverse Charge, Invoice Type, E-Commerce GSTIN, Rate, Taxable Value,
    Cess Amount, CGST Amount, SGST Amount, IGST Amount.
    """
    from finance.models import CorporateGSTInvoice

    qs = CorporateGSTInvoice.objects.filter(invoice_type='regular_b2b')
    if from_date:
        d_from = _parse_date(from_date)
        if d_from:
            qs = qs.filter(invoice_date__gte=d_from)
    if to_date:
        d_to = _parse_date(to_date)
        if d_to:
            qs = qs.filter(invoice_date__lte=d_to)

    qs = qs.select_related('party').order_by('invoice_date', 'id')

    output = io.StringIO()
    writer = csv.writer(output)

    # GSTR-1 B2B standard header
    writer.writerow([
        'GSTIN/UIN of Recipient',
        'Receiver Name',
        'Invoice Number',
        'Invoice Date',
        'Invoice Value',
        'Place of Supply',
        'Reverse Charge',
        'Applicable % of Tax Rate',
        'Invoice Type',
        'E-Commerce GSTIN',
        'Rate',
        'Taxable Value',
        'Cess Amount',
        'CGST Amount',
        'SGST/UTGST Amount',
        'IGST Amount',
    ])

    from finance.gst_engine import INDIAN_GST_STATES

    for inv in qs:
        if not inv.recipient_gstin:
            continue  # B2B requires GSTIN

        state_code = (inv.recipient_state_code or '33').strip().zfill(2)
        state_name = INDIAN_GST_STATES.get(state_code, f'State-{state_code}')
        place_of_supply = f"{state_code}-{state_name}"

        writer.writerow([
            inv.recipient_gstin,
            inv.recipient_legal_name or inv.recipient_trade_name or '',
            inv.invoice_number,
            inv.invoice_date.strftime('%d-%b-%Y') if inv.invoice_date else '',
            str(inv.total_invoice_value),
            place_of_supply,
            'Y' if inv.is_reverse_charge else 'N',
            '',  # Applicable % of Tax Rate (blank for standard)
            'Regular',
            '',  # E-Commerce GSTIN
            str(inv.gst_rate_percent),
            str(inv.taxable_value),
            str(inv.cess_amount or 0),
            str(inv.cgst_amount or 0),
            str(inv.sgst_amount or 0),
            str(inv.igst_amount or 0),
        ])

    return output.getvalue()


# ==============================================================================
# 6. INPUT TAX CREDIT (ITC) RECONCILIATION ENGINE
# ==============================================================================

def reconcile_input_tax_credit(from_date=None, to_date=None):
    """
    ITC Reconciliation Engine.
    Cross-references purchase-side GST paid (fuel, spares, services, tolls)
    against claimable input tax credits for GSTR-3B filing.

    Categories:
    - Fuel purchases (FuelRecord) — 100% ITC claimable for transport
    - Fastag/Toll deductions — no ITC (exempt supply)
    - Maintenance spares & repairs (TripExpense category='maintenance') — ITC eligible
    - Professional services — ITC eligible
    """
    d_from = _parse_date(from_date)
    d_to = _parse_date(to_date)

    # 1. Fuel Purchases — ITC on diesel/petrol for commercial transport vehicles
    fuel_qs = FuelRecord.objects.all()
    if d_from:
        fuel_qs = fuel_qs.filter(date__gte=d_from)
    if d_to:
        fuel_qs = fuel_qs.filter(date__lte=d_to)

    fuel_total = fuel_qs.aggregate(
        total_value=Sum('fuel_price') or Decimal('0.00'),
        total_qty=Sum('fuel_quantity') or Decimal('0.00'),
    )
    fuel_value = fuel_total.get('total_value') or Decimal('0.00')
    fuel_qty = fuel_total.get('total_qty') or Decimal('0.00')

    # Fuel GST: typically 18% on diesel (non-GST, but some states allow ITC)
    # For transport companies: excise portion treated as deemed ITC @ 5% effective
    fuel_deemed_itc = (fuel_value * Decimal('0.05')).quantize(Decimal('0.01'))

    # 2. Tolls — Exempt supply, NO ITC
    toll_qs = FastagTollDeduction.objects.all()
    if d_from:
        toll_qs = toll_qs.filter(toll_date__gte=d_from)
    if d_to:
        toll_qs = toll_qs.filter(toll_date__lte=d_to)

    toll_total = toll_qs.aggregate(total=Sum('amount'))
    toll_amount = toll_total.get('total') or Decimal('0.00')

    # 3. Maintenance & Service Expenses — ITC eligible @ applicable GST rate
    expense_qs = TripExpense.objects.all()
    if d_from:
        expense_qs = expense_qs.filter(date__gte=d_from)
    if d_to:
        expense_qs = expense_qs.filter(date__lte=d_to)

    # Split by ITC-eligible categories
    maintenance_expenses = expense_qs.filter(
        expense_type__in=['maintenance', 'spares', 'repair', 'tyre', 'workshop']
    )
    service_expenses = expense_qs.filter(
        expense_type__in=['professional', 'office', 'software', 'insurance_premium']
    )
    non_itc_expenses = expense_qs.exclude(
        expense_type__in=[
            'maintenance', 'spares', 'repair', 'tyre', 'workshop',
            'professional', 'office', 'software', 'insurance_premium'
        ]
    )

    maint_total = maintenance_expenses.aggregate(total=Sum('amount')).get('total') or Decimal('0.00')
    service_total = service_expenses.aggregate(total=Sum('amount')).get('total') or Decimal('0.00')
    non_itc_total = non_itc_expenses.aggregate(total=Sum('amount')).get('total') or Decimal('0.00')

    # ITC on maintenance: typically 18% GST, full ITC claimable
    maint_itc = (maint_total * Decimal('18') / Decimal('118')).quantize(Decimal('0.01'))
    # ITC on services: typically 18% GST
    service_itc = (service_total * Decimal('18') / Decimal('118')).quantize(Decimal('0.01'))

    # 4. Output Tax Liability (from sales invoices)
    from finance.models import CorporateGSTInvoice
    output_qs = CorporateGSTInvoice.objects.all()
    if d_from:
        output_qs = output_qs.filter(invoice_date__gte=d_from)
    if d_to:
        output_qs = output_qs.filter(invoice_date__lte=d_to)

    output_tax = output_qs.aggregate(
        total_cgst=Sum('cgst_amount'),
        total_sgst=Sum('sgst_amount'),
        total_igst=Sum('igst_amount'),
        total_tax=Sum('total_tax'),
        total_taxable=Sum('taxable_value'),
    )

    output_cgst = output_tax.get('total_cgst') or Decimal('0.00')
    output_sgst = output_tax.get('total_sgst') or Decimal('0.00')
    output_igst = output_tax.get('total_igst') or Decimal('0.00')
    output_total_tax = output_tax.get('total_tax') or Decimal('0.00')

    # 5. Net ITC Summary
    total_itc_claimable = fuel_deemed_itc + maint_itc + service_itc
    net_gst_payable = max(Decimal('0.00'), output_total_tax - total_itc_claimable)
    itc_utilization_percent = (
        (total_itc_claimable / output_total_tax * 100).quantize(Decimal('0.1'))
        if output_total_tax > 0 else Decimal('0.0')
    )

    return {
        'period': {
            'from_date': str(d_from) if d_from else 'All Time',
            'to_date': str(d_to) if d_to else 'Present',
        },
        # Output (Sales) Tax
        'output_tax': {
            'invoices_count': output_qs.count(),
            'taxable_value': output_tax.get('total_taxable') or Decimal('0.00'),
            'cgst': output_cgst,
            'sgst': output_sgst,
            'igst': output_igst,
            'total_output_tax': output_total_tax,
        },
        # Input (Purchase) Tax Credits
        'input_credits': {
            'fuel': {
                'total_value': fuel_value,
                'total_litres': fuel_qty,
                'records_count': fuel_qs.count(),
                'deemed_itc': fuel_deemed_itc,
                'note': 'Deemed ITC @ 5% for commercial transport fuel',
            },
            'tolls': {
                'total_amount': toll_amount,
                'records_count': toll_qs.count(),
                'itc_eligible': Decimal('0.00'),
                'note': 'Tolls are exempt supply — NO ITC available',
            },
            'maintenance': {
                'total_amount': maint_total,
                'records_count': maintenance_expenses.count(),
                'itc_claimable': maint_itc,
                'note': 'ITC @ 18% on maintenance/spares/repairs',
            },
            'services': {
                'total_amount': service_total,
                'records_count': service_expenses.count(),
                'itc_claimable': service_itc,
                'note': 'ITC @ 18% on professional/office services',
            },
            'non_eligible': {
                'total_amount': non_itc_total,
                'records_count': non_itc_expenses.count(),
                'itc_claimable': Decimal('0.00'),
                'note': 'Driver bata, tips, food, etc. — not ITC eligible',
            },
        },
        # Net Summary for GSTR-3B
        'net_summary': {
            'total_itc_claimable': total_itc_claimable,
            'total_output_tax': output_total_tax,
            'net_gst_payable': net_gst_payable,
            'itc_utilization_percent': itc_utilization_percent,
            'itc_breakdown_cgst': (total_itc_claimable / 2).quantize(Decimal('0.01')),
            'itc_breakdown_sgst': (total_itc_claimable / 2).quantize(Decimal('0.01')),
        },
    }


def generate_itc_reconciliation_csv(from_date=None, to_date=None):
    """
    Generates a CSV report for ITC Reconciliation suitable for CA / audit review.
    """
    recon = reconcile_input_tax_credit(from_date, to_date)
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['ITC RECONCILIATION REPORT'])
    writer.writerow([f"Period: {recon['period']['from_date']} to {recon['period']['to_date']}"])
    writer.writerow([])

    # Output Tax
    writer.writerow(['SECTION', 'OUTPUT TAX LIABILITY (SALES)'])
    writer.writerow(['Description', 'Count', 'Amount'])
    ot = recon['output_tax']
    writer.writerow(['Total Invoices', ot['invoices_count'], str(ot['taxable_value'])])
    writer.writerow(['CGST Output', '', str(ot['cgst'])])
    writer.writerow(['SGST Output', '', str(ot['sgst'])])
    writer.writerow(['IGST Output', '', str(ot['igst'])])
    writer.writerow(['Total Output Tax', '', str(ot['total_output_tax'])])
    writer.writerow([])

    # Input Tax Credits
    writer.writerow(['SECTION', 'INPUT TAX CREDITS (PURCHASES)'])
    writer.writerow(['Category', 'Records', 'Total Value', 'ITC Claimable', 'Note'])
    for cat_key, cat_data in recon['input_credits'].items():
        writer.writerow([
            cat_key.replace('_', ' ').title(),
            cat_data.get('records_count', 0),
            str(cat_data.get('total_amount', cat_data.get('total_value', 0))),
            str(cat_data.get('itc_claimable', cat_data.get('deemed_itc', cat_data.get('itc_eligible', 0)))),
            cat_data.get('note', ''),
        ])
    writer.writerow([])

    # Net Summary
    writer.writerow(['SECTION', 'NET GST PAYABLE (GSTR-3B)'])
    ns = recon['net_summary']
    writer.writerow(['Total Output Tax', '', str(ns['total_output_tax'])])
    writer.writerow(['Total ITC Claimable', '', str(ns['total_itc_claimable'])])
    writer.writerow(['NET GST PAYABLE', '', str(ns['net_gst_payable'])])
    writer.writerow(['ITC Utilization %', '', f"{ns['itc_utilization_percent']}%"])

    return output.getvalue()
