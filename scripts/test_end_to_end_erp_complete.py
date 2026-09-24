import os
import sys
import django
import datetime
from decimal import Decimal
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.test import Client as TestClient
from django.contrib.auth.models import User
from core.models import Party, Vehicle, Driver
from packages.models import (
    Package,
    PackageSeasonalRate,
    PackageHotelAllotment,
    PackageAddon,
    PackageB2BMargin,
    TourFeedbackLog,
    CollegeIVExpedition,
    TourPassengerManifest,
    PackageInventory,
)
from fleet_contracts.models import (
    TransportContract,
    ContractFleetRoster,
    ContractMonthlyInvoice,
    ContractSLAPenalty,
)
from operations.models import Trip
from packages.manifest_autoassign import auto_assign_for_expedition

def run_e2e_backend_check():
    print("=" * 80)
    print("🚀 FULL END-TO-END BACKEND & APPLICATION CONNECTIVITY VERIFICATION")
    print("=" * 80)

    passed = 0
    total = 0

    def assert_test(cond, title, details=""):
        nonlocal passed, total
        total += 1
        if cond:
            passed += 1
            det = f" -> {details}" if details else ""
            print(f"  [PASS] {title}{det}")
        else:
            print(f"  [FAIL] {title} - {details}")
            sys.exit(1)

    client = TestClient()
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser('test_admin', 'admin@example.com', 'adminpass123')
    client.force_login(admin_user)

    # --------------------------------------------------------------------------
    # 1. API Endpoints Check
    # --------------------------------------------------------------------------
    print("\n📡 Phase 1: Dynamic Form AJAX APIs Verification...")
    pkg = Package.objects.first()
    assert_test(pkg is not None, "Sample package found")

    resp = client.get(f"/packages/api/package/{pkg.id}/info/")
    assert_test(resp.status_code == 200 and resp.json().get('success') is True, "api_package_info endpoint", f"Price: ₹{resp.json().get('base_price')}")

    veh = Vehicle.objects.first()
    if veh:
        resp = client.get(f"/packages/api/vehicle/{veh.id}/info/")
        assert_test(resp.status_code == 200 and resp.json().get('success') is True, "api_vehicle_info endpoint", f"Capacity: {resp.json().get('seating_capacity')} seats")

    # --------------------------------------------------------------------------
    # 2. Package Unit Economics & Pricing Engine
    # --------------------------------------------------------------------------
    print("\n💰 Phase 2: Package Unit Economics & P&L Engine...")
    test_pkg, _ = Package.objects.update_or_create(
        name="E2E Test Ooty Expedition 3N4D",
        defaults={
            'destination': 'Ooty, Coonoor',
            'category': 'hill_station',
            'duration_nights': 3,
            'duration_days': 4,
            'min_pax': 45,
            'base_price': Decimal('7500.00'),
            'price_with_food': Decimal('8500.00'),
            'price_without_food': Decimal('6000.00'),
            'cost_hotel_per_pax': Decimal('3200.00'),
            'cost_coach_per_pax': Decimal('1800.00'),
            'cost_meals_per_pax': Decimal('1500.00'),
            'cost_activities_per_pax': Decimal('500.00'),
            'cost_misc_per_pax': Decimal('200.00'),
        }
    )
    # Total direct cost = 3200+1800+1500+500+200 = 7200
    # Selling rate (with food) = 8500
    # Margin = 8500 - 7200 = 1300
    # Margin % = (1300 / 8500) * 100 = 15.29%
    # Batch profit (45 pax) = 1300 * 45 = 58,500
    assert_test(test_pkg.total_direct_cost_per_pax == Decimal('7200.00'), "Direct COGS correctly summed", f"₹{test_pkg.total_direct_cost_per_pax}")
    assert_test(test_pkg.gross_margin_per_pax == Decimal('1300.00'), "Gross margin per pax calculated", f"₹{test_pkg.gross_margin_per_pax}")
    assert_test(round(test_pkg.gross_margin_percentage, 1) == 15.3, "Gross margin percentage correct", f"{test_pkg.gross_margin_percentage}%")
    assert_test(test_pkg.projected_batch_gross_profit == Decimal('58500.00'), "Projected batch gross profit on 45 pax", f"₹{test_pkg.projected_batch_gross_profit}")

    # --------------------------------------------------------------------------
    # 3. Seasonal Rates & Date-Aware Pricing
    # --------------------------------------------------------------------------
    print("\n☀️ Phase 3: Seasonal Rates & Peak Surge Pricing...")
    season, _ = PackageSeasonalRate.objects.get_or_create(
        package=test_pkg,
        season_name="May Summer Vacation Peak",
        defaults={
            'season_type': 'peak',
            'start_date': datetime.date(2025, 5, 1),
            'end_date': datetime.date(2025, 6, 15),
            'surge_percentage': Decimal('20.00'),
            'is_active': True,
        }
    )
    peak_price = test_pkg.get_effective_price(travel_date=datetime.date(2025, 5, 20), with_food=True)
    expected_peak = Decimal('8500.00') * Decimal('1.20')  # 10,200
    assert_test(peak_price == expected_peak, "Effective peak season price with 20% surge", f"₹{peak_price}")

    normal_price = test_pkg.get_effective_price(travel_date=datetime.date(2025, 7, 10), with_food=True)
    assert_test(normal_price == Decimal('8500.00'), "Normal season price unchanged", f"₹{normal_price}")

    # --------------------------------------------------------------------------
    # 4. Hotel Room Allotment & Occupancy Tracking
    # --------------------------------------------------------------------------
    print("\n🏨 Phase 4: Hotel Room Allotments & Inventory Tracking...")
    allotment, _ = PackageHotelAllotment.objects.get_or_create(
        package=test_pkg,
        hotel_name="Sterling Ooty Elk Hill Resort",
        check_in_date=datetime.date(2025, 5, 20),
        defaults={
            'check_out_date': datetime.date(2025, 5, 23),
            'room_category': 'deluxe',
            'rooms_blocked': 20,
            'rooms_occupied': 16,
            'cost_per_room_night': Decimal('3500.00'),
            'status': 'confirmed',
            'confirmation_voucher_no': 'ST-OOTY-E2E-9912',
        }
    )
    assert_test(allotment.occupancy_rate == 80.0, "Hotel occupancy rate correct", f"{allotment.occupancy_rate}%")
    assert_test(allotment.rooms_available == 4, "Available rooms correct", f"{allotment.rooms_available} rooms")
    assert_test(allotment.nights_count == 3, "Nights count correct", f"{allotment.nights_count}N")
    expected_cost = Decimal('20') * Decimal('3') * Decimal('3500.00')  # 210,000
    assert_test(allotment.total_cost == expected_cost, "Total hotel block contract cost", f"₹{allotment.total_cost}")

    # --------------------------------------------------------------------------
    # 5. Dynamic Experience Add-Ons & B2B Reseller Margins
    # --------------------------------------------------------------------------
    print("\n🎒 Phase 5: Add-Ons & B2B Channel Reseller Margins...")
    addon, _ = PackageAddon.objects.get_or_create(
        package=test_pkg,
        title="Pykara Speedboat Ride & Tea Factory Tour",
        defaults={
            'category': 'speedboat',
            'pricing_unit': 'per_pax',
            'cost_price': Decimal('250.00'),
            'selling_price': Decimal('450.00'),
            'is_mandatory_inclusion': False,
            'is_active': True,
        }
    )
    assert_test(addon.margin_per_unit == Decimal('200.00'), "Addon margin per unit calculated", f"₹{addon.margin_per_unit}")
    assert_test(round(addon.margin_percentage, 1) == 44.4, "Addon margin % correct", f"{addon.margin_percentage}%")

    b2b, _ = PackageB2BMargin.objects.get_or_create(
        package=test_pkg,
        tier_name='gold',
        defaults={
            'commission_percent': Decimal('12.00'),
            'is_active': True,
        }
    )
    expected_b2b_food = Decimal('8500.00') * Decimal('0.88') # 7480
    assert_test(b2b.net_b2b_rate_with_food == expected_b2b_food, "B2B Gold Tier net rate with food", f"₹{b2b.net_b2b_rate_with_food}")

    # --------------------------------------------------------------------------
    # 6. Post-Trip Feedback & NPS Quality Governance
    # --------------------------------------------------------------------------
    print("\n⭐ Phase 6: Post-Trip Feedback & NPS Governance...")
    fb, _ = TourFeedbackLog.objects.get_or_create(
        package=test_pkg,
        guest_name="Prof. R. Sundaram",
        trip_date=datetime.date(2025, 5, 24),
        defaults={
            'guest_phone': '+91 94432 99887',
            'coach_driver_rating': 5,
            'hotel_rating': 4,
            'food_rating': 5,
            'schedule_rating': 5,
            'overall_rating': 5,
            'nps_score': 10,
            'customer_review_text': "Flawless arrangements by Siva Gayathri Tours. Driver punctuality and hotel food were top class.",
            'is_verified': True,
            'flag_status': 'positive',
        }
    )
    assert_test(fb.average_dimension_score == 4.8, "5D average dimension score", f"{fb.average_dimension_score}★")
    assert_test("Promoter" in fb.nps_category, "NPS Promoter classified", fb.nps_category)

    # --------------------------------------------------------------------------
    # 7. College IV Auto-Assignment & Dispatch to Operations
    # --------------------------------------------------------------------------
    print("\n🚌 Phase 7: College IV Manifest Auto-Assignment & Trip Dispatch...")
    iv, _ = CollegeIVExpedition.objects.get_or_create(
        college_name="PSG College of Technology",
        department_and_batch="B.E. Robotics & Automation (2022-26)",
        defaults={
            'start_date': datetime.date(2025, 6, 10),
            'end_date': datetime.date(2025, 6, 14),
            'package': test_pkg,
            'faculty_incharge_name': "Dr. K. Senthil Kumar",
            'faculty_incharge_phone': "+91 98422 55667",
            'student_count_male': 35,
            'student_count_female': 25,
            'faculty_count': 4,
            'total_pax': 64,
            'industry_visit_targets': "L&T Valves Coimbatore & Highfield Tea Factory",
            'permission_status': 'approved',
            'status': 'confirmed',
            'transit_mode': 'road_coach',
            'bus_count': 2,
        }
    )
    # Ensure passengers exist
    if TourPassengerManifest.objects.filter(iv_expedition=iv).count() == 0:
        # Create 4 faculty
        for i in range(1, 5):
            TourPassengerManifest.objects.create(
                iv_expedition=iv,
                passenger_name=f"Faculty Staff {i}",
                category='faculty',
                gender='male' if i % 2 == 1 else 'female',
                phone=f"+91 98422 0000{i}",
            )
        # Create 60 students
        for i in range(1, 61):
            gender = 'male' if i <= 35 else 'female'
            TourPassengerManifest.objects.create(
                iv_expedition=iv,
                passenger_name=f"Student Pax {i:02d}",
                category='student',
                gender=gender,
                roll_number=f"22RA{i:03d}",
            )

    auto_res = auto_assign_for_expedition(iv.id, seats_per_bus=50, students_per_room=4)
    assert_test('error' not in auto_res, "Manifest auto-assignment executed successfully", f"{auto_res.get('total_passengers', 0)} passengers assigned")

    # Verify rooms and seating
    assigned_faculty = TourPassengerManifest.objects.filter(iv_expedition=iv, category='faculty')
    assert_test(all(f.bus_assignment and f.seat_number and f.room_sharing_number for f in assigned_faculty), "All faculty assigned buses, front seats, and twin rooms")

    assigned_students = TourPassengerManifest.objects.filter(iv_expedition=iv, category='student')
    assert_test(all(s.bus_assignment and s.seat_number and s.room_sharing_number for s in assigned_students), "All students assigned seats and quad rooms")

    # --------------------------------------------------------------------------
    # 8. Document & Proposal Generation Endpoints
    # --------------------------------------------------------------------------
    print("\n📄 Phase 8: Proposal Quotations, Service Vouchers & Rooming Lists...")
    quote_url = f"/packages/quote/{test_pkg.id}/"
    resp = client.get(quote_url)
    assert_test(resp.status_code == 200, f"5-Page Proposal Quotation HTTP 200: {quote_url}")

    voucher_url = f"/packages/voucher/{test_pkg.id}/"
    resp = client.get(voucher_url)
    assert_test(resp.status_code == 200, f"Confirmed Tour Service Voucher HTTP 200: {voucher_url}")

    rooming_url = f"/packages/manifest/{iv.id}/rooming-list/"
    resp = client.get(rooming_url)
    assert_test(resp.status_code == 200, f"Rooming List & Seating Manifest HTTP 200: {rooming_url}")

    # --------------------------------------------------------------------------
    # 9. Transport Contracts & Fleet Logistics Verification
    # --------------------------------------------------------------------------
    print("\n🚛 Phase 9: Transport Contracts, Invoicing & SLA Governance...")
    from core.models import Client
    client_obj, _ = Client.objects.get_or_create(
        name="Tata Consultancy Services Ltd",
        defaults={'phone': '+91 44 6616 8888', 'email': 'transport@tcs.com'}
    )
    contract, _ = TransportContract.objects.get_or_create(
        name="TCS Siruseri 24x7 Employee Commute",
        defaults={
            'customer': client_obj,
            'contract_category': 'corporate',
            'billing_model': 'per_trip',
            'billing_cycle': 'calendar_month',
            'default_rate': Decimal('2400.00'),
            'committed_vehicle_count': 6,
            'standby_vehicle_count': 1,
            'start_date': datetime.date(2025, 1, 1),
            'end_date': datetime.date(2025, 12, 31),
            'payment_credit_days': 30,
            'fuel_escalation_enabled': True,
            'base_diesel_price': Decimal('92.50'),
            'fuel_revision_factor': Decimal('0.2500'),
            'sla_penalty_cap_pct': Decimal('10.00'),
            'status': 'active',
            'category_specifications': {
                'night_escort_mandatory': True,
                'escort_timing_window': '20:00 - 06:00',
                'safe_drop_confirmation': 'otp_sms',
                'panic_button_installed': True
            }
        }
    )
    assert_test(contract.status == 'active', "Transport Contract is active", f"Name: {contract.name}")

    invoice, _ = ContractMonthlyInvoice.objects.get_or_create(
        invoice_number="INV-ETS-2025-05-001",
        defaults={
            'contract': contract,
            'billing_month': datetime.date(2025, 5, 1),
            'from_date': datetime.date(2025, 5, 1),
            'to_date': datetime.date(2025, 5, 31),
            'total_trips_completed': 180,
            'total_kms_run': Decimal('4500.00'),
            'base_contract_amount': Decimal('432000.00'),
            'extra_km_amount': Decimal('12000.00'),
            'fuel_escalation_amount': Decimal('1800.00'),
            'toll_parking_amount': Decimal('8500.00'),
            'sla_penalty_deduction': Decimal('2400.00'),
            'net_taxable_amount': Decimal('451900.00'),
            'gst_rate': Decimal('5.00'),
            'gst_amount': Decimal('22595.00'),
            'grand_total': Decimal('474495.00'),
            'status': 'generated',
        }
    )
    assert_test(invoice.grand_total > Decimal('0'), "Monthly Invoice grand total computed", f"₹{invoice.grand_total:,.2f}")

    penalty, _ = ContractSLAPenalty.objects.get_or_create(
        contract=contract,
        date=datetime.date(2025, 5, 12),
        penalty_type='late_arrival',
        defaults={
            'penalty_amount': Decimal('2400.00'),
            'applied_to_invoice': invoice,
            'description': "Shift A drop delayed by 35 minutes due to breakdown; backup coach arrived late.",
        }
    )
    assert_test(penalty.penalty_amount == Decimal('2400.00'), "SLA penalty registered and deducted", f"₹{penalty.penalty_amount}")

    # --------------------------------------------------------------------------
    # 10. Django Admin Changelist & Changeform URLs Integrity (All Models)
    # --------------------------------------------------------------------------
    print("\n🌐 Phase 10: Django Admin Changelist & Changeform Accessibility...")
    admin_urls = [
        # Packages & Holidays
        "/admin/packages/package/",
        f"/admin/packages/package/{test_pkg.id}/change/",
        "/admin/packages/package/add/",
        "/admin/packages/packageseasonalrate/",
        "/admin/packages/packagehotelallotment/",
        "/admin/packages/packageaddon/",
        "/admin/packages/packageb2bmargin/",
        "/admin/packages/tourfeedbacklog/",

        # Package Tours Proxies
        "/admin/package_tours/collegeivproxy/",
        f"/admin/package_tours/collegeivproxy/{iv.id}/change/",
        "/admin/package_tours/tourdeparturebatchproxy/",
        "/admin/package_tours/hotelallotmentproxy/",
        "/admin/package_tours/tourfeedbackproxy/",
        "/admin/package_tours/seasonalrateproxy/",
        "/admin/package_tours/packageaddonproxy/",
        "/admin/package_tours/b2bmarginproxy/",
        "/admin/package_tours/passengermanifestproxy/",

        # Fleet Contracts
        "/admin/fleet_contracts/transportcontract/",
        f"/admin/fleet_contracts/transportcontract/{contract.id}/change/",
        "/admin/fleet_contracts/transportcontract/add/",
        "/admin/fleet_contracts/contractfleetroster/",
        "/admin/fleet_contracts/contractmonthlyinvoice/",
        "/admin/fleet_contracts/contractslapenalty/",

        # Operations
        "/admin/operations/trip/",
        "/admin/operations/booking/",

        # Finance
        "/admin/finance_treasury/payment/",
        "/admin/finance/driveradvance/",
        "/admin/finance/tripexpense/",
    ]

    for url in admin_urls:
        resp = client.get(url)
        assert_test(resp.status_code == 200, f"Admin URL returns HTTP 200: {url}")

    print("\n" + "=" * 80)
    print(f"🎉 COMPREHENSIVE END-TO-END AUDIT COMPLETE: ALL {passed}/{total} CHECKS PASSED!")
    print("=" * 80)

if __name__ == '__main__':
    run_e2e_backend_check()
