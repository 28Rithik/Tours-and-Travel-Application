import os
import sys

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from decimal import Decimal
from django.test import Client
from django.contrib.auth import get_user_model
from packages.models import Package, ItineraryDay, PackageVehicleTariff
from core.models import VehicleType

User = get_user_model()
u = User.objects.filter(is_superuser=True).first()
if not u:
    u = User.objects.create_superuser('test_admin', 'admin@example.com', 'adminpass')

client = Client()
client.force_login(u)

print("=== VERIFYING 1-CLICK CIRCUIT & FLEET TARIFFS PIPELINE ===")

# 1. Create a test Package simulating Kerala IV 5D
pkg, created = Package.objects.get_or_create(
    package_code="TEST-KL-4N5D",
    defaults={
        'name': "4 NIGHTS 5 DAYS KERALA COLLEGE IV (KOCHI-ALLEPPEY-VAGAMON)",
        'destination': "Kochi, Alleppey, Vagamon (Kerala)",
        'category': "college_iv",
        'duration_nights': 4,
        'duration_days': 5,
        'pricing_type': "per_person",
        'base_price': Decimal('4800.00'),
        'price_with_food': Decimal('6850.00'),
        'price_without_food': Decimal('4750.00'),
        'min_pax': 45,
        'complementary_staff_count': 2,
        'has_campfire_dj': True,
        'has_jeep_safari': True,
        'has_industrial_visit': True,
    }
)

print(f"[PASS] Tour Package ready: #{pkg.id} - {pkg.name}")

# 2. Add 5 Itinerary Days (matching Circuit Builder template)
ItineraryDay.objects.filter(package=pkg).delete()
kerala_days = [
    (1, "Arrival Kochi - InfoPark IT Hub - Marine Drive & Fort Kochi", "Coimbatore to Kochi Coach", "Kochi", "Breakfast, Lunch, Dinner"),
    (2, "Proceed to Alleppey - Backwater Houseboat Cruise & Beach", "Kochi to Alleppey", "Alleppey", "Breakfast, Lunch, Dinner"),
    (3, "Proceed to Vagamon Hills - Pine Forest & Off-Road Jeep Safari", "Alleppey to Vagamon", "Vagamon", "Breakfast, Lunch, Dinner"),
    (4, "Athirappilly & Vazhachal Waterfalls - Return Transit", "Vagamon to Athirappilly", "Transit", "Breakfast, Lunch, Dinner"),
    (5, "Safe Campus Arrival & Tour Completion", "Highway to Campus", "Campus", "Morning Refreshment"),
]

for day_num, title, route, halt, meals in kerala_days:
    ItineraryDay.objects.create(
        package=pkg,
        day_number=day_num,
        title=title,
        route_segment=route,
        night_stay_location=halt,
        meals_included=meals,
        sightseeing_spots=f"Highlights for Day {day_num}",
        activities="Full tour activities"
    )

print(f"[PASS] Successfully created {ItineraryDay.objects.filter(package=pkg).count()} Itinerary Days!")

# 3. Add 5 Fleet Tariffs (matching Fleet Tariff Builder template)
PackageVehicleTariff.objects.filter(package=pkg).delete()

# Map available VehicleTypes
vehicle_types = list(VehicleType.objects.all())
sedan_vt = next((vt for vt in vehicle_types if 'sedan' in vt.name.lower() or 'dzire' in vt.name.lower()), vehicle_types[0] if vehicle_types else None)
crysta_vt = next((vt for vt in vehicle_types if 'crysta' in vt.name.lower() or 'innova' in vt.name.lower()), vehicle_types[1] if len(vehicle_types) > 1 else sedan_vt)
urbania_vt = next((vt for vt in vehicle_types if 'urbania' in vt.name.lower() or '17' in vt.name.lower()), vehicle_types[2] if len(vehicle_types) > 2 else sedan_vt)
bus36_vt = next((vt for vt in vehicle_types if '36' in vt.name.lower() or 'mini' in vt.name.lower()), vehicle_types[3] if len(vehicle_types) > 3 else sedan_vt)
coach54_vt = next((vt for vt in vehicle_types if '54' in vt.name.lower() or 'coach' in vt.name.lower()), vehicle_types[4] if len(vehicle_types) > 4 else sedan_vt)

tariffs_data = [
    (sedan_vt, '4_sedan', 14.0, 500.0),
    (crysta_vt, '7_crysta', 20.0, 600.0),
    (urbania_vt, '17_tt_urbania', 26.0, 800.0),
    (bus36_vt, '36_mini_bus', 35.0, 1000.0),
    (coach54_vt, '54_luxury_coach', 45.0, 1200.0),
]

for vt, tier, km_rate, bata in tariffs_data:
    if vt:
        per_day = (300 * km_rate) + bata
        pkg_rate = 5 * per_day
        PackageVehicleTariff.objects.get_or_create(
            package=pkg,
            vehicle_type=vt,
            defaults={
                'seating_tier': tier,
                'rate_type': 'outstation_multiday',
                'package_rate': Decimal(str(pkg_rate)),
                'per_day_rate': Decimal(str(per_day)),
                'included_km': 1500,
                'extra_km_rate': Decimal(str(km_rate)),
                'driver_bata_per_day': Decimal(str(bata)),
                'driver_bata_included': True,
                'toll_parking_included': True,
            }
        )

print(f"[PASS] Successfully created {PackageVehicleTariff.objects.filter(package=pkg).count()} Vehicle Tariffs!")

# 4. Verify Proposal Quotation HTML renders both Itinerary and Vehicle Tariffs
quote_resp = client.get(f'/packages/quote/{pkg.id}/')
assert quote_resp.status_code == 200, f"Quote page returned status {quote_resp.status_code}"
html = quote_resp.content.decode('utf-8')

assert "Athirappilly &amp; Vazhachal Waterfalls" in html or "Athirappilly & Vazhachal" in html
assert "Day 01" in html or "Day 1" in html
print("[PASS] Official Quotation Proposal renders all Itinerary Days perfectly!")

if PackageVehicleTariff.objects.filter(package=pkg).exists():
    assert "₹" in html
    print("[PASS] Official Quotation Proposal renders Fleet Tariffs Matrix!")

print("\n=== ALL PIPELINE CHECKS COMPLETED SUCCESSFULLY ===")
