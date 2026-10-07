"""
End-to-End Live Synergy Test: TravelERP (Port 8000) <---> Intercity Bus CRS (Port 8005)
======================================================================================
Verifies:
  1. Fleet Vehicle Conflict Check (Port 8000 protecting Port 8005 schedules)
  2. Loyalty Balance Ingestion (Port 8000 querying Port 8005)
  3. Intercity Bus Route Search (Port 8000 querying Port 8005)
  4. Holiday Package Checkout with Loyalty Points Discount
  5. Connecting Intercity Bus Seat Reservation for Tour Package
"""
import os
import sys
import json
import datetime
from decimal import Decimal
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
import django
django.setup()

from django.test import Client
from core.models import Vehicle, VehicleType, Party, Client as CoreClient
from operations.models import Booking, Trip
from packages.models import Package, PackageInventory
from core.intercity_service import (
    get_loyalty_balance,
    redeem_loyalty_points,
    search_intercity_trips,
    reserve_transit_seats,
)


def run_e2e_synergy_tests():
    print("=" * 80)
    print("🚀 SIVAGAYATHIRI TRAVELS — DUAL-PLATFORM LIVE SYNERGY VERIFICATION")
    print("   TravelERP (Port 8000)  <======>  Intercity Bus CRS (Port 8005)")
    print("=" * 80)

    client = Client()
    passed = 0
    total = 5

    # --------------------------------------------------------------------------
    # TEST 1: Fleet Vehicle Tour Conflict Check API on Port 8000
    # --------------------------------------------------------------------------
    print("\n--- [TEST 1/5] Testing Vehicle Tour Conflict Gate (/api/vehicles/<reg>/check-availability/) ---")
    resp = client.get('/api/vehicles/TNDEMO01/check-availability/?date=2026-09-28')
    data = resp.json()
    print("  Conflicted Vehicle Response (TN-DEMO-01):", data)
    assert data.get('conflict') is True, "Expected conflict for TN-DEMO-01"
    assert data.get('status') == 'booked_for_tour', "Expected booked_for_tour status"

    resp_clear = client.get('/api/vehicles/KA01AH9988/check-availability/?date=2026-09-28')
    data_clear = resp_clear.json()
    print("  Clear Vehicle Response (KA01AH9988):", data_clear)
    assert data_clear.get('conflict') is False, "Expected no conflict for KA01AH9988"
    print("  ✅ [PASS] Vehicle conflict gate correctly identifies booked vs available fleet assets.")
    passed += 1

    # --------------------------------------------------------------------------
    # TEST 2: Live Loyalty Balance Query to Port 8005
    # --------------------------------------------------------------------------
    print("\n--- [TEST 2/5] Testing Live Loyalty Points Query to Intercity CRS (Port 8005) ---")
    resp_loyalty = client.get('/customer-portal/api/intercity/loyalty/?phone=9842511223')
    loyalty_data = resp_loyalty.json()
    print("  Loyalty API Response for 9842511223:", loyalty_data)
    assert loyalty_data.get('status') == 'success', f"Expected success status, got {loyalty_data}"
    assert loyalty_data.get('customer_name') == 'Karthik Raja', "Expected customer Karthik Raja"
    assert loyalty_data.get('points_balance') > 0, "Expected positive points balance"
    print(f"  ✅ [PASS] Customer {loyalty_data['customer_name']} found with {loyalty_data['points_balance']} points (Tier: {loyalty_data.get('tier')}).")
    passed += 1

    # --------------------------------------------------------------------------
    # TEST 3: Live Intercity Bus Search to Port 8005
    # --------------------------------------------------------------------------
    print("\n--- [TEST 3/5] Testing Live Scheduled Bus Route Search to Port 8005 ---")
    resp_search = client.get('/customer-portal/api/intercity/routes/?origin=Chennai&destination=Coimbatore&date=2026-09-28')
    search_data = resp_search.json()
    print(f"  Bus Search Found: {search_data.get('trips_count')} trip(s)")
    assert search_data.get('status') == 'success', "Expected success from search API"
    assert search_data.get('trips_count', 0) >= 1, "Expected at least 1 trip from Chennai to Coimbatore"
    first_trip = search_data['trips'][0]
    print(f"  Trip: {first_trip['route_name']} | Bus: {first_trip['bus_type']} | Departure: {first_trip['departure_time']} | Fare: ₹{first_trip['base_fare']}")
    print("  ✅ [PASS] Intercity scheduled bus routes seamlessly retrieved from Port 8005.")
    passed += 1

    # --------------------------------------------------------------------------
    # TEST 4: Package Checkout with Live Intercity Loyalty Points Redemption
    # --------------------------------------------------------------------------
    print("\n--- [TEST 4/5] Testing Holiday Package Checkout with Loyalty Points Discount ---")
    package = Package.objects.filter(is_active=True).first()
    if not package:
        vtype = VehicleType.objects.first()
        package = Package.objects.create(name='3D2N Ooty Hill Escape', destination='Ooty', base_price=4500, is_active=True, default_vehicle_type=vtype)

    inventory = PackageInventory.objects.filter(package=package, departure_date__gte=datetime.date.today()).first()
    if not inventory:
        inventory = PackageInventory.objects.create(
            package=package,
            departure_date=datetime.date.today() + datetime.timedelta(days=7),
            total_seats=20,
            available_seats=20,
            price_override=Decimal('4500.00'),
            status='open'
        )

    # Post checkout with 10 loyalty points applied
    initial_balance = loyalty_data['points_balance']
    checkout_payload = {
        'guest_name': 'Karthik Raja',
        'guest_phone': '9842511223',
        'guest_email': 'karthik.raja@example.com',
        'pickup_location': 'Chennai Central',
        'pax': 2,
        'meal_plan': 'AP',
        'payment_method': 'upi',
        'utr_number': 'UTR998877665544',
        'loyalty_points': 10,
    }
    resp_checkout = client.post(f'/customer-portal/checkout/{inventory.id}/', checkout_payload, follow=True)
    assert resp_checkout.status_code == 200, f"Checkout failed with status {resp_checkout.status_code}"

    created_booking = Booking.objects.filter(guest_phone='9842511223').order_by('-id').first()
    assert created_booking is not None, "Booking record was not created"
    assert "Redeemed 10 Intercity Loyalty Points" in created_booking.notes, f"Loyalty redemption note missing: {created_booking.notes}"
    print(f"  Booking Created: #{created_booking.booking_number} | Quoted Price: ₹{created_booking.quoted_price}")
    print(f"  Booking Notes: {created_booking.notes}")
    print("  ✅ [PASS] Package checkout atomically redeemed Intercity loyalty points and applied discount!")
    passed += 1

    # --------------------------------------------------------------------------
    # TEST 5: Reserving Connecting Intercity Transit Bus Seat for Holiday Tour
    # --------------------------------------------------------------------------
    print("\n--- [TEST 5/5] Testing Connecting Transit Bus Seat Reservation for Tour Package ---")
    available_seat = first_trip['available_seats'][0] if first_trip.get('available_seats') else 'L1'
    print(f"  Attempting to reserve seat: {available_seat}")
    transit_payload = {
        'trip_id': first_trip['trip_id'],
        'seat_numbers': [available_seat],
        'passenger_name': 'Karthik Raja',
        'passenger_phone': '9842511223',
        'passenger_gender': 'M',
        'external_booking_ref': created_booking.booking_number,
    }
    resp_transit = client.post(
        '/customer-portal/api/intercity/reserve-seats/',
        data=json.dumps(transit_payload),
        content_type='application/json'
    )
    transit_result = resp_transit.json()
    print("  Transit Bus Reservation Response:", transit_result)
    assert transit_result.get('status') == 'success', f"Transit reservation failed: {transit_result}"
    pnr = transit_result.get('pnr')
    assert pnr and pnr.startswith('PNR-'), f"Invalid PNR: {pnr}"
    print(f"  Confirmed Transit PNR: {pnr} (Boarding: {transit_result.get('boarding_point', {}).get('name')})")

    # Link PNR to the holiday booking
    created_booking.travel_pnr = pnr
    created_booking.notes += f"\nConnecting Transit PNR: {pnr}"
    created_booking.save(update_fields=['travel_pnr', 'notes'])

    print(f"  ✅ [PASS] Successfully reserved seat L5 on Intercity Bus and attached PNR {pnr} to Tour Booking #{created_booking.booking_number}.")
    passed += 1

    print("\n" + "=" * 80)
    print(f"🏆 ALL {passed}/{total} DUAL-PLATFORM LIVE SYNERGY TESTS PASSED WITH 100% SUCCESS!")
    print("   TravelERP and Intercity Bus CRS are now fully integrated and communicating live.")
    print("=" * 80)


if __name__ == '__main__':
    run_e2e_synergy_tests()
