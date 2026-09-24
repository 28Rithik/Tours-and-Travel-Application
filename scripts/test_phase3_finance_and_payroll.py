import calendar
import csv
import io
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from decimal import Decimal

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from django.test import Client, RequestFactory
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Driver, Party, Vehicle, VehicleType, Client as ClientModel
from operations.models import Booking, Trip, TrafficFine
from fleet_contracts.models import (
    TransportContract,
    Route,
    Shift,
    ContractTripLog,
    ContractMonthlyInvoice,
)
from finance.models import (
    CorporatePetroAccount,
    FuelRecord,
    TripExpense,
    CorporateFastagAccount,
    FastagTollDeduction,
    DriverSalaryProfile,
    DriverPayslip,
    DriverAdvance,
)
from finance.export_services import (
    generate_tally_sales_xml,
    generate_tally_expense_xml,
    generate_zoho_sales_csv,
    generate_zoho_expense_csv,
    calculate_driver_duty_days,
    calculate_driver_monthly_deductions,
    generate_monthly_driver_payslip,
    generate_batch_payroll,
)


def run_phase3_verification():
    print("=" * 80)
    print("🚀 RUNNING PHASE 3: FINANCIAL & GOVERNANCE INTEGRATIONS TEST SUITE")
    print("=" * 80)

    # 1. SETUP COMMON TEST DATA
    print("\n[STEP 1] Setting up mock entities for financial testing...")

    test_party, _ = Party.objects.get_or_create(
        name="Phase 3 Corporate Client Ltd",
        defaults={
            'party_type': 'corporate',
            'phone': '9876543210',
            'email': 'finance@phase3corp.com',
            'gstin': '33ABCDE1234F1Z5',
        }
    )

    test_vtype, _ = VehicleType.objects.get_or_create(
        name="P3 Luxury Bus 40 Seater",
        defaults={
            'seating_capacity': 40,
            'default_day_rate': Decimal('8000.00'),
            'default_km_rate': Decimal('25.00'),
            'fuel_type': 'diesel',
        }
    )

    test_vehicle, _ = Vehicle.objects.get_or_create(
        registration_number="TN 38 P3 9999",
        defaults={
            'vehicle_type': test_vtype,
            'ownership_type': 'owned',
            'status': 'available',
            'current_km': 50000,
        }
    )

    test_driver, _ = Driver.objects.get_or_create(
        name="P3 Test Pilot Murugan",
        defaults={
            'driver_type': 'owned',
            'phone': '9876500001',
            'status': 'active',
            'license_number': 'TN38-2026-P3PILOT',
        }
    )

    salary_profile, _ = DriverSalaryProfile.objects.update_or_create(
        driver=test_driver,
        defaults={
            'basic_salary': Decimal('24000.00'),
            'allowances': Decimal('6000.00'),
            'epf_number': 'EPF/TN/998877/P3',
            'esi_number': 'ESI/TN/554433/P3',
            'epf_deduction_rate': Decimal('12.00'),
            'esi_deduction_rate': Decimal('0.75'),
        }
    )

    # Setup Completed Billable Trip
    test_booking, _ = Booking.objects.get_or_create(
        guest_name="P3 Corporate Delegation",
        defaults={
            'party': test_party,
            'vehicle_type': test_vtype,
            'pickup_date': date(2026, 9, 10),
            'pickup_time': datetime.strptime('09:00', '%H:%M').time(),
            'drop_date': date(2026, 9, 12),
            'pickup_location': 'Coimbatore Airport',
            'destination': 'Ooty Botanical Gardens',
            'pax_count': 35,
            'status': 'confirmed',
            'gst_rate': Decimal('5.00'),
        }
    )

    test_trip, _ = Trip.objects.get_or_create(
        trip_id="TR-P3-TEST-001",
        defaults={
            'booking': test_booking,
            'party': test_party,
            'vehicle': test_vehicle,
            'driver': test_driver,
            'start_date': date(2026, 9, 10),
            'end_date': date(2026, 9, 12),
            'status': 'completed',
            'opening_km': 50000,
            'closing_km': 50600,
            'day_rate': Decimal('8000.00'),
            'km_rate': Decimal('25.00'),
            'driver_bata': Decimal('600.00'),
        }
    )

    # Setup Contract & Monthly Invoice
    test_contract, _ = TransportContract.objects.get_or_create(
        name="P3 Campus Daily Shuttle 2026",
        defaults={
            'contract_category': 'corporate',
            'customer': test_party,
            'start_date': date(2026, 1, 1),
            'end_date': date(2026, 12, 31),
            'billing_model': 'fixed_monthly',
            'default_rate': Decimal('150000.00'),
            'gst_rate': Decimal('5.00'),
        }
    )

    contract_invoice, _ = ContractMonthlyInvoice.objects.update_or_create(
        invoice_number="INV-P3-ETS-2026-09",
        defaults={
            'contract': test_contract,
            'billing_month': date(2026, 9, 1),
            'from_date': date(2026, 9, 1),
            'to_date': date(2026, 9, 30),
            'base_contract_amount': Decimal('150000.00'),
            'extra_km_amount': Decimal('5000.00'),
            'status': 'generated',
        }
    )

    # Setup Fuel, Trip Expense, FASTag Toll
    petro_acct, _ = CorporatePetroAccount.objects.get_or_create(
        account_number="PETRO-HPCL-P3",
        defaults={
            'account_name': 'HPCL DriveTrack Phase 3',
            'balance': Decimal('50000.00'),
        }
    )

    fuel_rec, _ = FuelRecord.objects.get_or_create(
        api_reference_number="P3-HPCL-TXN-101",
        defaults={
            'vehicle': test_vehicle,
            'trip': test_trip,
            'date': date(2026, 9, 11),
            'fuel_quantity': Decimal('60.00'),
            'fuel_price': Decimal('95.50'),
            'fuel_station': 'HPCL Highway Pump Avinashi',
            'petro_account': petro_acct,
        }
    )

    trip_exp, _ = TripExpense.objects.get_or_create(
        description="P3 Hill Permit and Checkpost Toll",
        defaults={
            'trip': test_trip,
            'expense_type': 'permit',
            'amount': Decimal('1200.00'),
            'date': date(2026, 9, 11),
            'paid_by': 'company',
            'billable_to_customer': True,
        }
    )

    fastag_acct, _ = CorporateFastagAccount.objects.get_or_create(
        account_number="FASTAG-ICICI-P3",
        defaults={
            'account_name': 'ICICI FASTag Corporate P3',
            'balance': Decimal('25000.00'),
        }
    )

    fastag_toll, _ = FastagTollDeduction.objects.get_or_create(
        toll_plaza="Kaniyur Toll Plaza P3",
        defaults={
            'account': fastag_acct,
            'vehicle': test_vehicle,
            'trip': test_trip,
            'date': timezone.make_aware(datetime(2026, 9, 10, 14, 30)),
            'amount': Decimal('245.00'),
        }
    )

    print("✓ Common test entities initialized successfully.")

    # ==========================================================================
    # TEST 1: TALLY PRIME SALES XML EXPORT
    # ==========================================================================
    print("\n[TEST 1] Verifying Tally Prime Sales XML Generation...")
    sales_xml = generate_tally_sales_xml(from_date="2026-09-01", to_date="2026-09-30")
    assert sales_xml is not None and len(sales_xml) > 0, "Sales XML string must not be empty"

    root = ET.fromstring(sales_xml)
    assert root.tag == 'ENVELOPE', f"Root tag must be ENVELOPE, got {root.tag}"
    tally_req = root.find('.//HEADER/TALLYREQUEST')
    assert tally_req is not None and tally_req.text == 'Import Data', "Tally request header must be 'Import Data'"

    vouchers = root.findall('.//VOUCHER')
    assert len(vouchers) >= 2, f"Expected at least 2 sales vouchers (Trip + Contract Invoice), found {len(vouchers)}"

    # Check Trip Voucher
    trip_vouchers = [v for v in vouchers if v.find('VOUCHERNUMBER') is not None and v.find('VOUCHERNUMBER').text == 'TR-P3-TEST-001']
    assert len(trip_vouchers) == 1, "Trip TR-P3-TEST-001 must appear in Tally Sales XML"
    tv = trip_vouchers[0]
    assert tv.attrib.get('VCHTYPE') == 'Sales', "VCHTYPE must be Sales"
    assert tv.find('PARTYLEDGERNAME').text == test_party.name, "Party ledger name must match customer"
    
    # Check that entries have ISDEEMEDPOSITIVE and AMOUNT
    entries = tv.findall('ALLLEDGERENTRIES.LIST')
    assert len(entries) >= 2, "Sales voucher must have at least debit and credit ledger entries"
    print("  ✓ Tally Sales XML syntax and schema verified (Trip + Contract monthly invoice included).")

    # ==========================================================================
    # TEST 2: TALLY PRIME EXPENSES XML EXPORT
    # ==========================================================================
    print("\n[TEST 2] Verifying Tally Prime Expenses & Fuel XML Generation...")
    exp_xml = generate_tally_expense_xml(from_date="2026-09-01", to_date="2026-09-30")
    assert exp_xml is not None and len(exp_xml) > 0, "Expenses XML string must not be empty"

    exp_root = ET.fromstring(exp_xml)
    exp_vouchers = exp_root.findall('.//VOUCHER')
    assert len(exp_vouchers) >= 3, f"Expected at least 3 expense vouchers (Fuel, TripExpense, FASTag), found {len(exp_vouchers)}"

    vch_types = [v.attrib.get('VCHTYPE') for v in exp_vouchers]
    assert all(vt == 'Payment' for vt in vch_types), "All expense vouchers must have VCHTYPE='Payment'"

    narrations = [v.find('NARRATION').text for v in exp_vouchers if v.find('NARRATION') is not None]
    assert any("HPCL" in n or "Fuel" in n for n in narrations), "Fuel narration must be present in payment voucher"
    assert any("FASTag" in n for n in narrations), "FASTag narration must be present in payment voucher"
    print("  ✓ Tally Expenses XML syntax verified (Fuel, Trip Expenses, FASTag vouchers generated).")

    # ==========================================================================
    # TEST 3: ZOHO BOOKS SALES INVOICES CSV EXPORT
    # ==========================================================================
    print("\n[TEST 3] Verifying Zoho Books Customer Invoices CSV Generation...")
    sales_csv = generate_zoho_sales_csv(from_date="2026-09-01", to_date="2026-09-30")
    reader = list(csv.reader(io.StringIO(sales_csv)))
    assert len(reader) >= 3, f"Expected header + at least 2 rows, got {len(reader)}"

    header = reader[0]
    expected_headers = ['Invoice Number', 'Customer Name', 'Invoice Date', 'Due Date', 'Item Name', 'Item Description']
    for eh in expected_headers:
        assert eh in header, f"Header {eh} missing from Zoho Sales CSV"

    inv_numbers = [row[0] for row in reader[1:]]
    assert "TR-P3-TEST-001" in inv_numbers, "Trip TR-P3-TEST-001 must be present in Zoho Sales CSV"
    assert "INV-P3-ETS-2026-09" in inv_numbers, "Contract invoice must be present in Zoho Sales CSV"
    print("  ✓ Zoho Books Sales Invoices CSV verified with accurate column schema and data rows.")

    # ==========================================================================
    # TEST 4: ZOHO BOOKS OPERATIONAL EXPENSES CSV EXPORT
    # ==========================================================================
    print("\n[TEST 4] Verifying Zoho Books Fleet Expenses CSV Generation...")
    exp_csv = generate_zoho_expense_csv(from_date="2026-09-01", to_date="2026-09-30")
    exp_reader = list(csv.reader(io.StringIO(exp_csv)))
    assert len(exp_reader) >= 4, f"Expected header + at least 3 expense rows, got {len(exp_reader)}"

    exp_hdr = exp_reader[0]
    for h in ['Expense Date', 'Expense Account', 'Paid Through', 'Amount', 'Vendor Name', 'Vehicle Number']:
        assert h in exp_hdr, f"Header {h} missing from Zoho Expense CSV"

    veh_numbers = [row[exp_hdr.index('Vehicle Number')] for row in exp_reader[1:]]
    assert "TN 38 P3 9999" in veh_numbers, "Vehicle registration must be properly populated in expense CSV"
    print("  ✓ Zoho Books Fleet Expenses CSV verified with proper accounts and vehicle mapping.")

    # ==========================================================================
    # TEST 5: DUTY ATTENDANCE CALCULATION (TRIPS + CONTRACT TRIP LOGS)
    # ==========================================================================
    print("\n[TEST 5] Verifying Attendance Bridge (Trips + Contract Shifts)...")
    # Driver Murugan is on Trip TR-P3-TEST-001 from 2026-09-10 to 2026-09-12 (3 days: 10, 11, 12).
    # Let's add 2 additional ContractTripLog shifts on 2026-09-15 and 2026-09-16.
    test_route, _ = Route.objects.get_or_create(
        name="Coimbatore - Saravanampatti IT Park Express",
        defaults={
            'contract': test_contract,
            'origin': 'Gandhipuram',
            'destination': 'CHIL SEZ IT Park',
            'distance_km': 19,
        }
    )
    test_shift, _ = Shift.objects.get_or_create(
        route=test_route,
        shift_name="Morning Login 08:30 AM",
        defaults={
            'direction': 'pickup',
            'timing': datetime.strptime('07:30', '%H:%M').time(),
        }
    )

    ct_log1, _ = ContractTripLog.objects.get_or_create(
        shift=test_shift,
        date=date(2026, 9, 15),
        defaults={
            'vehicle': test_vehicle,
            'driver': test_driver,
            'status': 'on_time',
        }
    )
    ct_log2, _ = ContractTripLog.objects.get_or_create(
        shift=test_shift,
        date=date(2026, 9, 16),
        defaults={
            'vehicle': test_vehicle,
            'driver': test_driver,
            'status': 'delayed',
        }
    )

    attendance = calculate_driver_duty_days(test_driver, month=9, year=2026)
    expected_days = {date(2026, 9, 10), date(2026, 9, 11), date(2026, 9, 12), date(2026, 9, 15), date(2026, 9, 16)}
    assert set(attendance['duty_dates']) == expected_days, f"Expected duty dates {expected_days}, got {set(attendance['duty_dates'])}"
    assert attendance['duty_days_count'] == 5, f"Expected 5 duty days present, got {attendance['duty_days_count']}"
    print(f"  ✓ Attendance calculated correctly: {attendance['duty_days_count']} verified duty days across regular & contract trips.")

    # ==========================================================================
    # TEST 6: DEDUCTIONS & PAYROLL PRORATION ENGINE
    # ==========================================================================
    print("\n[TEST 6] Verifying Deductions & Proration Engine...")
    # Add a TrafficFine on 2026-09-11
    fine, _ = TrafficFine.objects.get_or_create(
        challan_number="P3-CHALLAN-SPEED-909",
        defaults={
            'vehicle': test_vehicle,
            'driver': test_driver,
            'trip': test_trip,
            'date_of_offence': timezone.make_aware(datetime(2026, 9, 11, 16, 45)),
            'violation_type': 'speeding',
            'fine_amount': Decimal('1000.00'),
            'financial_responsibility': 'driver',
            'paid_by': 'unpaid',
        }
    )

    # Add a DriverAdvance on 2026-09-05
    advance, _ = DriverAdvance.objects.get_or_create(
        notes="P3 Fuel emergency advance cash",
        defaults={
            'driver': test_driver,
            'date': date(2026, 9, 5),
            'amount': Decimal('2000.00'),
        }
    )

    deductions = calculate_driver_monthly_deductions(test_driver, month=9, year=2026)
    assert deductions['traffic_fines_deduction'] == Decimal('1000.00'), f"Expected ₹1000 fine, got {deductions['traffic_fines_deduction']}"
    assert deductions['advances_recovered'] == Decimal('2000.00'), f"Expected ₹2000 advance, got {deductions['advances_recovered']}"

    # Generate Payslip
    payslip = generate_monthly_driver_payslip(test_driver, month=9, year=2026)
    # Basic = 24,000 * (5 / 30) = 4,000.00
    # Allowances = 6,000 * (5 / 30) = 1,000.00
    # Gross = 5,000.00
    # EPF (12% of 4000) = 480.00
    # ESI (0.75% of 5000) = 37.50
    # Fines = 1000.00
    # Advances = 2000.00
    # Total Deductions = 480 + 37.50 + 1000 + 2000 = 3517.50
    # Net = 5000 - 3517.50 = 1482.50
    assert payslip.days_present == 5, f"Expected 5 days present, got {payslip.days_present}"
    assert payslip.basic_salary == Decimal('4000.00'), f"Expected 4000 basic, got {payslip.basic_salary}"
    assert payslip.allowances == Decimal('1000.00'), f"Expected 1000 allowances, got {payslip.allowances}"
    assert payslip.gross_earnings == Decimal('5000.00'), f"Expected 5000 gross, got {payslip.gross_earnings}"
    assert payslip.epf_deduction == Decimal('480.00'), f"Expected 480 EPF, got {payslip.epf_deduction}"
    assert payslip.esi_deduction == Decimal('37.50'), f"Expected 37.50 ESI, got {payslip.esi_deduction}"
    assert payslip.traffic_fines_deduction == Decimal('1000.00'), f"Expected 1000 fines, got {payslip.traffic_fines_deduction}"
    assert payslip.advances_recovered == Decimal('2000.00'), f"Expected 2000 advances, got {payslip.advances_recovered}"
    assert payslip.net_payable == Decimal('1482.50'), f"Expected 1482.50 net take-home, got {payslip.net_payable}"

    print(f"  ✓ Driver Payslip calculated with exact proration:")
    print(f"    - Gross Earnings: ₹{payslip.gross_earnings:,.2f} (Basic ₹{payslip.basic_salary} + Allowances ₹{payslip.allowances})")
    print(f"    - Total Deductions: ₹{payslip.total_deductions:,.2f} (EPF ₹{payslip.epf_deduction}, ESI ₹{payslip.esi_deduction}, Challan ₹{payslip.traffic_fines_deduction}, Advance ₹{payslip.advances_recovered})")
    print(f"    - Net Take-Home Salary: ₹{payslip.net_payable:,.2f}")

    # ==========================================================================
    # TEST 7: 1-CLICK BATCH PAYROLL GENERATOR
    # ==========================================================================
    print("\n[TEST 7] Verifying 1-Click Batch Driver Payroll...")
    batch_res = generate_batch_payroll(month=9, year=2026)
    assert batch_res['payslips_count'] >= 1, "Must generate at least 1 driver payslip"
    assert batch_res['total_duty_days'] >= 5, "Total duty days must include Murugan's 5 days"
    assert batch_res['total_net_payable'] > 0, "Total net payroll payable must be positive"
    print(f"  ✓ Batch Payroll Generator generated {batch_res['payslips_count']} driver payslips (Total Net: ₹{batch_res['total_net_payable']:,.2f}).")

    # ==========================================================================
    # TEST 8: HTTP ENDPOINTS (DASHBOARD, EXPORTS & PAYSLIP VIEW)
    # ==========================================================================
    print("\n[TEST 8] Verifying Web Endpoints & Download Views...")
    test_user, _ = User.objects.get_or_create(username='admin_p3_tester', defaults={'is_staff': True, 'is_superuser': True})
    client = Client()
    client.force_login(test_user)

    # 1. Accounting Dashboard
    resp = client.get('/finance/accounting/?from_date=2026-09-01&to_date=2026-09-30&month=9&year=2026')
    assert resp.status_code == 200, f"Dashboard returned {resp.status_code}"
    assert "Tally, Zoho & Automated Payroll Bridge" in resp.content.decode('utf-8'), "Hero title missing in dashboard"
    assert "Download Tally Sales XML" in resp.content.decode('utf-8'), "Export button missing"

    # 2. Tally Sales XML Download
    resp_tally_s = client.get('/finance/export/tally/sales/?from_date=2026-09-01&to_date=2026-09-30')
    assert resp_tally_s.status_code == 200, f"Tally Sales returned {resp_tally_s.status_code}"
    assert 'application/xml' in resp_tally_s['Content-Type'], f"Expected application/xml, got {resp_tally_s['Content-Type']}"
    assert 'attachment' in resp_tally_s['Content-Disposition'], "Expected attachment disposition"
    assert '<VOUCHER VCHTYPE="Sales"' in resp_tally_s.content.decode('utf-8')

    # 3. Tally Expenses XML Download
    resp_tally_e = client.get('/finance/export/tally/expenses/?from_date=2026-09-01&to_date=2026-09-30')
    assert resp_tally_e.status_code == 200, f"Tally Expenses returned {resp_tally_e.status_code}"
    assert 'application/xml' in resp_tally_e['Content-Type']
    assert '<VOUCHER VCHTYPE="Payment"' in resp_tally_e.content.decode('utf-8')

    # 4. Zoho Sales CSV Download
    resp_zoho_s = client.get('/finance/export/zoho/sales/?from_date=2026-09-01&to_date=2026-09-30')
    assert resp_zoho_s.status_code == 200
    assert 'text/csv' in resp_zoho_s['Content-Type']
    assert 'Invoice Number' in resp_zoho_s.content.decode('utf-8')

    # 5. Zoho Expenses CSV Download
    resp_zoho_e = client.get('/finance/export/zoho/expenses/?from_date=2026-09-01&to_date=2026-09-30')
    assert resp_zoho_e.status_code == 200
    assert 'text/csv' in resp_zoho_e['Content-Type']
    assert 'Expense Account' in resp_zoho_e.content.decode('utf-8')

    # 6. Driver Payslip Printable Detail View
    resp_slip = client.get(f'/finance/payslips/{payslip.id}/')
    assert resp_slip.status_code == 200, f"Payslip view returned {resp_slip.status_code}"
    slip_html = resp_slip.content.decode('utf-8')
    assert "Sivagayathiri Travels & Fleet Solutions" in slip_html
    assert test_driver.name in slip_html
    assert "NET TAKE-HOME SALARY" in slip_html
    assert "1482.50" in slip_html or "1,482.50" in slip_html

    # 7. Batch Payroll POST Trigger
    resp_post = client.post('/finance/payroll/batch-run/', {'month': 9, 'year': 2026}, follow=True)
    assert resp_post.status_code == 200, f"Batch payroll POST failed with {resp_post.status_code}"
    assert "Batch payroll for September 2026 executed successfully" in resp_post.content.decode('utf-8')

    print("  ✓ All 7 HTTP views & file download responses verified (Status 200 OK, exact headers, correct content types).")

    print("\n" + "=" * 80)
    print("🏆 ALL PHASE 3 SUITE TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 80)


if __name__ == '__main__':
    run_phase3_verification()
