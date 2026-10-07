import os
import sys
from pathlib import Path
from datetime import date, time, timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
import django
django.setup()

from django.test import Client
from django.conf import settings
from operations.models import (
    Booking, Trip, BulkContract, BulkContractDay, TrafficFine,
    ContractVehicleRate, ContractDayRequirement
)
from packages.models import Package, PackageInventory
from core.models import Client as PartyClient, Vehicle, Driver, VehicleType
from django.contrib.auth.models import User

def run_end_to_end_verification():
    print("=" * 70)
    print("[RUN] TRAVEL ERP: COMPREHENSIVE END-TO-END OPERATIONS VERIFICATION")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. Navigation Menu Ordering Verification
    # -------------------------------------------------------------
    print("\n[STEP 1/6] Verifying Admin Sidebar Menu Order...")
    nav = settings.UNFOLD.get("SIDEBAR", {}).get("navigation", [])
    nav_titles = [item.get("title", "") for item in nav]
    pkg_index = next((idx for idx, t in enumerate(nav_titles) if "Tour Packages" in t), -1)
    iv_index = next((idx for idx, t in enumerate(nav_titles) if "College IV" in t), -1)
    assert pkg_index != -1, f"[FAIL] 'Tour Packages' not found in nav: {nav_titles}"
    assert iv_index != -1, f"[FAIL] 'College IV & Group Tours' not found in nav: {nav_titles}"
    assert pkg_index < iv_index, f"[FAIL] 'Tour Packages' (index {pkg_index}) must be positioned BEFORE 'College IV & Group Tours' (index {iv_index})!"
    print(f"   [PASS] Tour Packages (Index {pkg_index}) is correctly placed ABOVE College IV & Group Tours (Index {iv_index}) in Unfold.")

    # -------------------------------------------------------------
    # 2. REST & JSON AJAX APIs Verification
    # -------------------------------------------------------------
    print("\n[STEP 2/6] Verifying Dynamic AJAX APIs...")
    c = Client()
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser('e2e_admin', 'e2e@example.com', 'adminpass123')
    c.force_login(admin_user)

    pkg = Package.objects.first()
    assert pkg is not None, "[FAIL] No package found in database!"
    res = c.get(f'/api/packages/{pkg.id}/inventory/')
    assert res.status_code == 200, f"[FAIL] /api/packages/{pkg.id}/inventory/ returned {res.status_code}"
    pkg_data = res.json()
    assert 'package' in pkg_data and 'inventories' in pkg_data, "[FAIL] Invalid API package inventory schema"
    print(f"   [PASS] /api/packages/{pkg.id}/inventory/ OK (Package: {pkg.name}, Batches: {len(pkg_data['inventories'])})")

    res = c.get('/api/vehicle-types/')
    assert res.status_code == 200, f"[FAIL] /api/vehicle-types/ returned {res.status_code}"
    v_types = res.json()
    assert len(v_types) > 0, "[FAIL] No vehicle types returned from API"
    print(f"   [PASS] /api/vehicle-types/ OK ({len(v_types)} vehicle types available)")

    # -------------------------------------------------------------
    # 3. Package Inventory & Departure Batch Setup
    # -------------------------------------------------------------
    print("\n[STEP 3/6] Verifying Package & Departure Batch Seat Management...")
    party = PartyClient.objects.first()
    if not party:
        party = PartyClient.objects.create(name="E2E Test Corporate Client", phone="9876543210")

    dep_date = date.today() + timedelta(days=14)
    ret_date = dep_date + timedelta(days=pkg.duration_nights or 3)
    
    vehicle = Vehicle.objects.exclude(status__in=['maintenance', 'inactive']).first()
    driver = Driver.objects.filter(status='active').first()

    inv, _ = PackageInventory.objects.get_or_create(
        package=pkg,
        departure_date=dep_date,
        defaults={
            'return_date': ret_date,
            'total_seats': 40,
            'booked_seats': 0,
            'available_seats': 40,
            'price_override': 12500,
            'assigned_vehicle': vehicle,
            'assigned_driver': driver,
            'status': 'open',
        }
    )
    initial_booked = inv.booked_seats
    initial_available = inv.available_seats
    print(f"   Departure Batch: {inv.departure_date} | Seats: {initial_booked} booked / {initial_available} free")

    # -------------------------------------------------------------
    # 4. Booking Creation & Auto Seat Sync
    # -------------------------------------------------------------
    print("\n[STEP 4/6] Creating Package Booking & Testing Real-Time Seat Synchronization...")
    booking = Booking.objects.create(
        party=party,
        guest_name="Prof. Sundaram - Academic Tour",
        guest_phone="9876500001",
        pickup_location="Campus Main Gate",
        destination=pkg.destination or "Mysore & Coorg",
        pickup_date=dep_date,
        drop_date=ret_date,
        pickup_time=time(7, 30),
        pax_count=35,
        package=pkg,
        package_inventory=inv,
        billing_type='package',
        quoted_price=175000,
        status='confirmed'
    )
    inv.refresh_from_db()
    assert inv.booked_seats == initial_booked + (booking.pax_count or 1), f"[FAIL] Seat count mismatch: expected {initial_booked + (booking.pax_count or 1)}, got {inv.booked_seats}"
    assert inv.available_seats == max(0, inv.total_seats - inv.booked_seats)
    print(f"   [PASS] Booking #{booking.booking_number} saved. Batch seats auto-synced to: {inv.booked_seats} booked / {inv.available_seats} available.")

    # Verify Booking API
    res = c.get(f'/api/bookings/{booking.id}/')
    assert res.status_code == 200
    b_api = res.json()
    assert b_api['billing_model'] == 'fixed', f"[FAIL] Expected billing_model 'fixed', got {b_api['billing_model']}"
    assert float(b_api['fixed_amount']) == 175000
    print(f"   [PASS] /api/bookings/{booking.id}/ OK (billing_model: {b_api['billing_model']}, fixed_amount: Rs. {b_api['fixed_amount']})")

    # -------------------------------------------------------------
    # 5. Conversion to Trip & Resource Allocation Flow
    # -------------------------------------------------------------
    print("\n[STEP 5/6] Converting Booking to Trip & Verifying Field/Resource Preservation...")
    from operations.admin import BookingAdmin
    from django.contrib.admin.sites import AdminSite
    site = AdminSite()
    bk_admin = BookingAdmin(Booking, site)

    # Perform quick conversion via test client
    conv_res = c.get(f'/admin/operations/booking/{booking.id}/quick-convert/', follow=True)
    assert conv_res.status_code == 200, f"[FAIL] quick-convert returned {conv_res.status_code}"
    booking.refresh_from_db()
    assert booking.status == 'dispatched', f"[FAIL] Expected booking status 'dispatched', got {booking.status}"

    trip = booking.trips.first()
    assert trip is not None, "[FAIL] Trip was not created from booking!"
    assert trip.package_id == pkg.id, f"[FAIL] Package link lost on trip!"
    assert trip.package_inventory_id == inv.id, f"[FAIL] PackageInventory link lost on trip!"
    assert trip.billing_model == 'fixed', f"[FAIL] Trip billing_model should be 'fixed', got {trip.billing_model}"
    assert float(trip.fixed_amount) == 175000, f"[FAIL] Trip fixed_amount should be 175000, got {trip.fixed_amount}"
    if inv.assigned_vehicle:
        assert trip.vehicle_id == inv.assigned_vehicle_id, f"[FAIL] Trip vehicle did not inherit batch vehicle!"
    if inv.assigned_driver:
        assert trip.driver_id == inv.assigned_driver_id, f"[FAIL] Trip driver did not inherit batch driver!"

    print(f"   [PASS] Converted to Trip #{trip.trip_id}:")
    print(f"      - Package: {trip.package.name}")
    print(f"      - Batch: {trip.package_inventory.departure_date}")
    print(f"      - Vehicle: {trip.vehicle}")
    print(f"      - Driver: {trip.driver}")
    print(f"      - Billing Model: {trip.billing_model} (Fixed: Rs. {trip.fixed_amount})")

    # Traffic Fine Auto-Routing test
    print("\n   Testing Traffic Fine auto-routing on Trip...")
    from django.utils import timezone
    fine = TrafficFine.objects.create(
        trip=trip,
        challan_number=f"CH-E2E-{trip.id}",
        date_of_offence=timezone.now(),
        violation_type='seatbelt_passenger',
        fine_amount=1000,
        paid_by='company'
    )
    assert fine.financial_responsibility == 'customer', f"[FAIL] Expected 'customer' responsibility, got {fine.financial_responsibility}"
    trip.refresh_from_db()
    assert trip.customer_billable_fines == 1000, f"[FAIL] customer_billable_fines mismatch: {trip.customer_billable_fines}"
    assert trip.total_amount == 176000, f"[FAIL] Expected total Rs. 176,000 (Rs. 175,000 + Rs. 1,000 fine), got {trip.total_amount}"
    print(f"   [PASS] Seatbelt fine (Rs. {fine.fine_amount}) auto-routed to Customer! Total Trip Bill: Rs. {trip.total_amount}")

    # -------------------------------------------------------------
    # 6. Bulk Contract & Scheduled Trips Automation
    # -------------------------------------------------------------
    print("\n[STEP 6/6] Testing Bulk Contract & Scheduled Trips Engine...")
    c_start = date.today() + timedelta(days=20)
    c_end = c_start + timedelta(days=4)
    contract = BulkContract.objects.create(
        name="E2E Film Production 5-Day Shoot",
        contract_type='cinema',
        customer=party,
        start_date=c_start,
        end_date=c_end,
        billing_model='per_vehicle_day',
        status='active'
    )

    # Action: Auto-generate operating days
    from operations.admin import BulkContractAdmin, BulkContractDayAdmin
    from operations.models import BulkContractDay
    from django.test import RequestFactory
    from django.contrib.messages.storage.fallback import FallbackStorage

    factory = RequestFactory()
    dummy_req = factory.get('/')
    dummy_req.user = admin_user
    dummy_req.session = c.session
    setattr(dummy_req, '_messages', FallbackStorage(dummy_req))

    bc_admin = BulkContractAdmin(BulkContract, site)
    bcd_admin = BulkContractDayAdmin(BulkContractDay, site)

    from operations.admin import generate_operating_days, generate_trips_from_requirements
    generate_operating_days(bc_admin, dummy_req, BulkContract.objects.filter(id=contract.id))
    assert contract.days.count() == 5, f"[FAIL] Expected 5 operating days, got {contract.days.count()}"
    print(f"   [PASS] Contract '{contract.name}' operating days generated: {contract.days.count()} days ({c_start} to {c_end})")

    # Add Vehicle Rate & Requirement
    v_type = VehicleType.objects.first()
    ContractVehicleRate.objects.create(
        contract=contract,
        vehicle_type=v_type,
        agreed_day_rate=4200
    )

    day1 = contract.days.order_by('date').first()
    ContractDayRequirement.objects.create(
        contract_day=day1,
        vehicle_type=v_type,
        quantity=3
    )

    # Action: Generate scheduled trips from requirements
    generate_trips_from_requirements(bcd_admin, dummy_req, BulkContractDay.objects.filter(id=day1.id))
    day1_trips = day1.trips.all()
    assert day1_trips.count() == 3, f"[FAIL] Expected 3 trips generated for day 1, got {day1_trips.count()}"
    for t in day1_trips:
        assert t.billing_model == 'day'
        assert float(t.day_rate) == 4200
        assert t.party_id == contract.customer_id
    print(f"   [PASS] Generated {day1_trips.count()} scheduled trips for Day 1 ({day1.date}) @ Rs. 4,200/day agreed rate.")

    # Clean up test artifacts cleanly
    print("\n   Cleaning up test records...")
    fine.delete()
    trip.delete()
    booking.delete()
    day1_trips.delete()
    contract.delete()
    inv.delete()

    print("\n" + "=" * 70)
    print("[SUCCESS] ALL 6 END-TO-END OPERATIONS WORKFLOW PHASES PASSED 100%!")
    print("=" * 70)

if __name__ == '__main__':
    run_end_to_end_verification()
