import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import (
    PackageTemplate, Package, PackageVehicleTariff, ItineraryDay
)
from core.models import VehicleType

print("=== SEEDING 3-DAY FRIENDS GROUP GETAWAY (OOTY-COONOOR-MUDUMALAI) ===")

# 1. Create Reusable Package Template
tmpl, tmpl_created = PackageTemplate.objects.update_or_create(
    name="2 Nights 3 Days Ooty - Coonoor - Mudumalai Friends Getaway Circuit",
    defaults={
        'destination': "Ooty, Coonoor, Mudumalai (Tamil Nadu)",
        'category': 'holiday',
        'duration_days': 3,
        'duration_nights': 2,
        'base_price': Decimal('3950.00'),
        'description': "Classic Nilgiris hill station getaway for friend groups and families. Includes tea estates, lake boating, viewpoints, campfire night, and Mudumalai wildlife safari.",
        'is_active': True,
    }
)
print(f"[{'Created' if tmpl_created else 'Updated'}] Template: {tmpl.name}")

# 2. Create Active Master Package
pkg, created = Package.objects.update_or_create(
    package_code='PKG-OOTY-3D-FRND',
    defaults={
        'template': tmpl,
        'name': '2 NIGHTS 3 DAYS OOTY - COONOOR - MUDUMALAI SCENIC GETAWAY (FRIENDS & FAMILY SPECIAL)',
        'destination': 'Ooty, Coonoor, Mudumalai (Tamil Nadu)',
        'category': 'holiday',
        'duration_days': 3,
        'duration_nights': 2,
        'pricing_type': 'vehicle_rate',
        'base_price': Decimal('3950.00'),
        'price_with_food': Decimal('3950.00'),
        'price_without_food': Decimal('2650.00'),
        'min_pax': 6,
        'complementary_staff_count': 0,
        'hotel_star_category': 'Deluxe Hillside Cottage / Tea Estate Resort',
        'room_sharing_type': '6_sharing',
        'meal_plan': 'MAP',
        'vehicle_seating_desc': 'Private Innova Crysta (6-7 Pax) / Force Urbania (12-17 Pax)',
        'bus_amenities_desc': 'AC Chauffeur Driven Luxury Vehicle, Hill permits, Music System, Mineral Water',
        'has_campfire_dj': True,
        'has_jeep_safari': True,
        'has_boating': True,
        'has_industrial_visit': False,
        'inclusions': (
            "Roundtrip private luxury tourist vehicle (Innova Crysta / Force Urbania) from Coimbatore/Tiruppur.\n"
            "2 Nights Deluxe Hillside Cottage / Villa Stay with scenic valley view.\n"
            "Flexible Rooming: 6-Sharing Family Suites or Twin/Triple Sharing rooms as per group preference.\n"
            "Daily Buffet Breakfast & Gourmet Hill Station Dinners (MAP Plan).\n"
            "Private Campfire evening with music & barbecue arrangements at cottage.\n"
            "Local sightseeing: Coonoor Sims Park, Tea Factory, Doddabetta Peak & Pykara Lake.\n"
            "Mudumalai Tiger Reserve Jeep Safari coordination.\n"
            "All hill entry road green tax, interstate tourist permits, toll gates, and professional driver bata included."
        ),
        'exclusions': (
            "Lunch and personal cafe bills.\n"
            "Pykara boat ride tickets & forest department safari entry fees.\n"
            "Personal activities (Horse riding, chocolate shopping, camera tickets)."
        ),
        'terms_and_conditions': (
            "Standard check-in 12:00 PM / check-out 11:00 AM.\n"
            "Vehicle will strictly adhere to hill road safety timings (Nilgiris ghat road operates 6:00 AM to 10:00 PM).\n"
            "Payment: 50% advance token to reserve cottage and vehicle; balance 50% upon boarding."
        ),
        'contact_persons_footer': 'Rithik CA (MD) - 98425 33777, Anandh C (Tour Operations) - 94381 71311',
        'is_active': True,
    }
)
print(f"[{'Created' if created else 'Updated'}] Package: {pkg.name} (ID #{pkg.id})")

# 3. Itinerary Days (Day 1 to Day 3)
itinerary_days_data = [
    (
        1,
        "Day 1: Coimbatore to Coonoor & Ooty — Tea Plantations, Sims Park & Campfire Night",
        "Coimbatore to Ooty via Coonoor Ghat Road",
        "Morning pickup from Coimbatore in your private AC vehicle. Scenic drive up the Nilgiri hills. Stop at Coonoor: visit Sims Park, Dolphin's Nose viewpoint, and a working Nilgiri Tea Factory to taste freshly brewed tea and handmade chocolates. Afternoon: Arrive in Ooty, check-in to hillside cottage. Evening: Leisure walk around Ooty Lake. Night: Private resort bonfire/campfire with music and barbecue dinner.",
        "Pickup from Coimbatore & scenic uphill drive through Mettupalayam ghats",
        "Sims Park Coonoor, Lamb's Rock, Dolphin's Nose, Tea Factory & Ooty Lake",
        "Campfire evening at resort with music, barbecue & buffet dinner",
        "Overnight Stay in Ooty Hillside Cottage",
        "Dinner (MAP Plan)",
        "Mystique Mountain Resort / Pine Valley Cottage Ooty",
        "Private AC Innova Crysta / Force Urbania"
    ),
    (
        2,
        "Day 2: Ooty High Peaks & Pykara Lake Boating & Shooting Point",
        "Ooty & Pykara Circuit (60 km)",
        "08:30 AM: Buffet breakfast. Drive to Doddabetta Peak — the highest point in South India with panoramic Nilgiri views. Next, visit 9th Mile (Shooting Medu) pine slopes. Proceed to Pykara Lake & Waterfalls: enjoy speed boating amidst pristine eucalyptus forests. Evening visit to Government Botanical Garden & Tibetan Market for woolen shopping. Gourmet buffet dinner and overnight stay.",
        "Buffet breakfast at resort and drive towards Doddabetta Peak",
        "Doddabetta Peak, 9th Mile Shooting Point, Pykara Lake Boating, Pykara Waterfalls",
        "Botanical Garden, Commercial Road shopping, dinner at resort",
        "Overnight Stay in Ooty Hillside Cottage",
        "Breakfast & Dinner (MAP Plan)",
        "Mystique Mountain Resort / Pine Valley Cottage Ooty",
        "Private AC Innova Crysta / Force Urbania"
    ),
    (
        3,
        "Day 3: Ooty to Mudumalai Tiger Reserve Safari & Return to Coimbatore",
        "Ooty - Kalhatty Ghat - Mudumalai - Coimbatore (160 km)",
        "08:00 AM: Breakfast and checkout. Drive down the adventurous 36-hairpin Kalhatty Ghat Road into the Mudumalai Tiger Reserve. Enjoy a thrilling 4x4 Jeep Safari or forest department bus safari through the sanctuary (spot elephants, spotted deer, peacocks, and Indian gaurs). Visit Theppakadu Elephant Camp. Afternoon: scenic highway drive back to Coimbatore. Evening safe drop-off at home / pickup point. Tour concludes.",
        "Breakfast, checkout & drive down the 36 hairpin bends to Mudumalai",
        "Mudumalai National Park, Theppakadu Elephant Camp, Bandipur Border Forest",
        "Return highway drive via Mettupalayam to Coimbatore with happy memories",
        "Safe Drop-off at Coimbatore",
        "Breakfast (MAP Plan)",
        "Drop at Home / Airport / Railway Station",
        "Private AC Innova Crysta / Force Urbania"
    ),
]

for d_num, title, r_seg, act, m_act, spots, ev_act, stay_loc, meals, hotel, trnsp in itinerary_days_data:
    ItineraryDay.objects.update_or_create(
        package=pkg,
        day_number=d_num,
        defaults={
            'title': title,
            'route_segment': r_seg,
            'activities': act,
            'morning_activity': m_act,
            'sightseeing_spots': spots,
            'evening_night_activity': ev_act,
            'night_stay_location': stay_loc,
            'meals_included': meals,
            'hotel_info': hotel,
            'transport_info': trnsp,
        }
    )
print("Configured 3 Detailed Itinerary Days for Friends Tour.")

# 4. Vehicle Tariffs for Friends Group: Sedan, Crysta, Urbania
# A) Innova Crysta (6-7 Seats)
crysta_vtype = VehicleType.objects.filter(name__icontains='Crysta').first()
if not crysta_vtype:
    crysta_vtype = VehicleType.objects.filter(seating_capacity=7).first()
if not crysta_vtype:
    crysta_vtype = VehicleType.objects.create(name='Innova Crysta', seating_capacity=7)

PackageVehicleTariff.objects.update_or_create(
    package=pkg,
    vehicle_type=crysta_vtype,
    defaults={
        'rate_type': 'outstation_multiday',
        'seating_tier': '7_crysta',
        'package_rate': Decimal('21000.00'),
        'per_day_rate': Decimal('7000.00'),
        'included_km': 650,
        'extra_km_rate': Decimal('20.00'),
        'driver_bata_included': True,
        'driver_bata_per_day': Decimal('600.00'),
        'toll_parking_included': True,
        'interstate_permit_included': True,
    }
)

# B) Force Urbania / Tempo Traveller (12-17 Seats)
urbania_vtype = VehicleType.objects.filter(name__icontains='Urbania').first()
if not urbania_vtype:
    urbania_vtype = VehicleType.objects.filter(seating_capacity__gte=12, seating_capacity__lte=17).first()
if not urbania_vtype:
    urbania_vtype = VehicleType.objects.create(name='Force Urbania 17-Seater', seating_capacity=17)

PackageVehicleTariff.objects.update_or_create(
    package=pkg,
    vehicle_type=urbania_vtype,
    defaults={
        'rate_type': 'outstation_multiday',
        'seating_tier': '17_tt_urbania',
        'package_rate': Decimal('32000.00'),
        'per_day_rate': Decimal('10667.00'),
        'included_km': 650,
        'extra_km_rate': Decimal('26.00'),
        'driver_bata_included': True,
        'driver_bata_per_day': Decimal('800.00'),
        'toll_parking_included': True,
        'interstate_permit_included': True,
    }
)

# C) Compact Sedan (4 Seats)
sedan_vtype = VehicleType.objects.filter(name__icontains='Sedan').first()
if not sedan_vtype:
    sedan_vtype = VehicleType.objects.filter(seating_capacity=4).first()
if not sedan_vtype:
    sedan_vtype = VehicleType.objects.create(name='Swift Dzire / Etios Sedan', seating_capacity=4)

PackageVehicleTariff.objects.update_or_create(
    package=pkg,
    vehicle_type=sedan_vtype,
    defaults={
        'rate_type': 'outstation_multiday',
        'seating_tier': '4_sedan',
        'package_rate': Decimal('14000.00'),
        'per_day_rate': Decimal('4667.00'),
        'included_km': 650,
        'extra_km_rate': Decimal('14.00'),
        'driver_bata_included': True,
        'driver_bata_per_day': Decimal('500.00'),
        'toll_parking_included': True,
        'interstate_permit_included': True,
    }
)

print("Configured Fleet Tariffs for Friends Tour: Sedan (Rs.14k), Crysta (Rs.21k), Urbania (Rs.32k).")
