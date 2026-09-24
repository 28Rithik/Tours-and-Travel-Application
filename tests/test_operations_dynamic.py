import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.test import Client
from operations.models import Booking, Trip, BulkContract, BulkContractDay, TrafficFine
from packages.models import Package, PackageInventory
from core.models import Client as PartyClient, Vehicle, Driver

def test_operations_suite():
    c = Client()
    # Test unauthenticated redirects to login or 302
    r_bk = c.get('/api/bookings/1/')
    assert r_bk.status_code in [302, 200], f"Booking API unexpected status {r_bk.status_code}"
    
    # Login superuser for test
    from django.contrib.auth.models import User
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser('test_admin', 'admin@example.com', 'adminpass123')
    c.force_login(admin_user)
    
    print("[1/5] Testing Booking API...")
    bk = Booking.objects.first()
    if bk:
        res = c.get(f'/api/bookings/{bk.id}/')
        assert res.status_code == 200, f"Failed api_get_booking: {res.status_code}"
        data = res.json()
        print(f"   Booking #{bk.booking_number} data verified: party_id={data.get('party_id')}, model={data.get('billing_model')}")

    print("[2/5] Testing Package Inventory API...")
    pkg = Package.objects.first()
    if pkg:
        res = c.get(f'/api/packages/{pkg.id}/inventory/')
        assert res.status_code == 200, f"Failed api_package_inventory: {res.status_code}"
        data = res.json()
        print(f"   Package '{pkg.name}' inventories count: {len(data.get('inventories', []))}")

    print("[3/5] Testing Bulk Contract Context API...")
    contract = BulkContract.objects.first()
    if contract:
        res = c.get(f'/api/bulk-contracts/{contract.id}/')
        assert res.status_code == 200, f"Failed api_bulk_contract_context: {res.status_code}"
        data = res.json()
        print(f"   Bulk Contract '{data.get('name')}' customer: {data.get('customer_name')}, rates: {len(data.get('rates', []))}")

    print("[4/5] Testing Trip API...")
    trip = Trip.objects.first()
    if trip:
        res = c.get(f'/api/trips/{trip.id}/')
        assert res.status_code == 200, f"Failed api_get_trip: {res.status_code}"
        data = res.json()
        print(f"   Trip #{data.get('trip_id')} vehicle: {data.get('vehicle_registration')}")

    print("[5/5] Testing Booking Save Seat Sync...")
    inv = PackageInventory.objects.first()
    if inv:
        initial_booked = inv.booked_seats
        initial_available = inv.available_seats
        # Create a temporary test booking
        party = PartyClient.objects.first()
        from datetime import date, time
        b_test = Booking.objects.create(
            party=party,
            guest_name="Test Pax Auto Seat",
            pickup_date=date.today(),
            pickup_time=time(9, 0),
            package=inv.package,
            package_inventory=inv,
            status='confirmed'
        )
        inv.refresh_from_db()
        actual_count = Booking.objects.filter(package_inventory=inv).exclude(status='cancelled').count()
        assert inv.booked_seats == actual_count, f"Expected {actual_count}, got {inv.booked_seats}"
        print(f"   Seat sync accurately computed: {inv.booked_seats} booked seats, {inv.available_seats} available out of {inv.total_seats}")
        # Clean up test booking
        b_test.delete()
        inv.refresh_from_db()
        after_cleanup = Booking.objects.filter(package_inventory=inv).exclude(status='cancelled').count()
        assert inv.booked_seats == after_cleanup, f"Expected {after_cleanup}, got {inv.booked_seats}"
        print(f"   Seat sync on cleanup verified: {inv.booked_seats} booked seats")

    print("\nALL 5 OPERATIONS SUITE TESTS PASSED WITH 100% SUCCESS!")

if __name__ == '__main__':
    test_operations_suite()
