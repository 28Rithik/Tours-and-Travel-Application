import os
import django
from decimal import Decimal
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import (
    Package, PackageTemplate, PackageVehicleTariff, ItineraryDay
)
from package_tours.models import (
    CollegeIVProxy, TourDepartureBatchProxy, BoardingPointProxy, PassengerManifestProxy
)
from core.models import VehicleType

print("=== SEEDING KERALA COLLEGE IV PACKAGE & EXPEDITION ===")

# 1. Create or update the Kerala College IV Package
pkg, created = Package.objects.update_or_create(
    package_code='PKG-KL-IV-05D',
    defaults={
        'name': '4 NIGHTS 5 DAYS KERALA COLLEGE IV (KOCHI IT HUB - VARKALA BEACH - VAGAMON JEEP SAFARI - ALLEPPEY HOUSEBOAT)',
        'category': 'college_iv',
        'destination': 'Kochi, Varkala, Vagamon, Alleppey (Kerala)',
        'duration_days': 5,
        'duration_nights': 4,
        'pricing_type': 'per_person',
        'price_with_food': Decimal('6850.00'),
        'price_without_food': Decimal('4750.00'),
        'base_price': Decimal('6850.00'),
        'min_pax': 100,
        'complementary_staff_count': 6,
        'hotel_star_category': 'Star Category Hotel & Hill Resort',
        'room_sharing_type': '4_sharing',
        'meal_plan': 'AP',
        'vehicle_seating_desc': '3 x Non AC / AC 54 Seated Luxurious Pushback Bus Convoy',
        'bus_amenities_desc': '3 x 54-Seater Luxury Coaches, Tour Captains, Laser Lights, High-Bass JBL DJ System, First Aid Kit, 20L Water Cans',
        'has_campfire_dj': True,
        'has_industrial_visit': True,
        'has_jeep_safari': True,
        'has_boating': True,
        'inclusions': (
            "3 x 54-Seater Luxury 2+2 Air-Suspension Pushback Tourist Coaches (Convoy with Tour Manager).\n"
            "All Inter-State Kerala Tourist Road Tax, Toll Gate clearances, and Commercial Bus Parking.\n"
            "Verified 3-Star category Hotel & Scenic Hill Resort Accommodation on 4-Sharing basis for students.\n"
            "3 Twin-Sharing Deluxe AC Rooms complimentary for 6 Faculty/Staff Members.\n"
            "All Meals Included (AP Plan): 5 Breakfasts, 4 Lunches, 4 Dinners & Evening High Tea with Snacks.\n"
            "Exclusive Traditional Backwater Houseboat Cruise in Alleppey with authentic Kerala Buffet Lunch.\n"
            "Thrilling 4x4 Off-Road Mountain Jeep Safari at Vagamon Hills to Kurisumala/Marmala viewpoints.\n"
            "Entry tickets to Vagamon Pine Forest, Eco Point, and Varkala Cliff walkway.\n"
            "Industrial Visit clearance liaison & gate entry coordination at IT Company (Infopark Kakkanad, Kochi).\n"
            "Grand DJ Dance Night with Stage Lights, High-Bass Sound System, and Campfire at Vagamon Resort.\n"
            "Dedicated Siva Gayathri Tours & Travels Senior Tour Captain escorting the convoy 24/7.\n"
            "Complimentary First-Aid Kits, 20-Litre Mineral Water cans inside all 3 buses, and Tour Banners."
        ),
        'exclusions': (
            "Any personal laundry, room service, or extra food/beverage orders.\n"
            "Personal water sports / activities at Varkala beach.\n"
            "Any camera/video permits at restricted industrial IT premises.\n"
            "Damages caused by students to hotel/coach property (chargeable to institution)."
        ),
        'terms_and_conditions': (
            "Official Institutional Authorization Letter with HOD/Principal sign & seal is mandatory before departure.\n"
            "Student identity cards and emergency contact details must be submitted for the passenger manifest.\n"
            "IT Company Security Protocol: College dress code and photo IDs strictly required inside Kochi Infopark.\n"
            "Boys and Girls hotel rooms and coach allocations will follow institutional disciplinary guidelines.\n"
            "Payment Schedule: 40% advance booking token upon approval, 40% 7 days prior to departure, balance 20% on departure day.\n"
            "Siva Gayathri Tours and Travels reserves the right to alter route sequences in case of unforeseen hill weather or roadblocks."
        ),
        'contact_persons_footer': 'Rithik CA (Managing Director) - 98425 33777, Anandh C (Tour Operations) - 94381 71311',
        'is_active': True,
    }
)
print(f"[{'Created' if created else 'Updated'}] Master Package: {pkg.name} (ID #{pkg.id})")

# 2. Itinerary Days (Day 1 to Day 5)
itinerary_data = [
    (
        1,
        "Day 1: Tamil Nadu to Kochi — IT Company Industrial Visit & Marine Drive",
        "Tamil Nadu to Kochi",
        "Night departure from College campus in Tamil Nadu in 3 x 54-seater luxury coaches. Morning arrival in Kochi. Hotel check-in, freshen up and breakfast. 10:30 AM: Official Industrial Visit entry at Premier IT Company (Infopark Kakkanad / SmartCity Kochi). Interactive tech presentation, cloud infrastructure walkthrough, and industry Q&A session. 01:30 PM: Buffet Lunch. Afternoon visit to Marine Drive, rainbow walkway, and scenic boat jetty. Evening shopping at Lulu Mall / MG Road. Buffet Dinner and overnight stay in Kochi.",
        "Hotel check-in, breakfast & preparation for Industrial Visit",
        "IT Company (Infopark / SmartCity Kakkanad), Marine Drive Rainbow Bridge, Kochi Backwaters Walkway",
        "Lulu Mall / MG Road evening shopping, Grand Buffet Dinner, Overnight Stay",
        "Overnight Stay at Kochi 3-Star Hotel",
        "Breakfast, Lunch, Dinner (AP Plan)",
        "Hotel Abad Plaza / Gokulam Park Kochi",
        "3 x 54-Seated Pushback AC Bus Convoy"
    ),
    (
        2,
        "Day 2: Kochi to Varkala Beach — Coastal Highway Drive & Cliff Sunset",
        "Kochi to Varkala (170 km scenic coastal route)",
        "07:30 AM: Buffet breakfast and checkout from Kochi. Scenic coastal highway journey towards southern Kerala. 01:00 PM: Arrive at Varkala, check-in to beachside resort, and enjoy South Indian lunch. 03:30 PM: Visit the world-famous Varkala Cliff, natural springs, and Papanasam Beach. Relaxed leisure stroll along cliff-side cafes, handicraft shacks, and helipad sunset point. 08:30 PM: Grand dinner spread and overnight stay at Varkala.",
        "Breakfast & checkout, coastal drive via Alappuzha-Kollam highway",
        "Varkala North Cliff, Papanasam Beach, Natural Mineral Springs, Helipad Sunset Viewpoint",
        "Cliff cafe exploration, group beach recreation, Dinner & Beach Resort stay",
        "Overnight Stay at Varkala Beach Resort",
        "Breakfast, Lunch, Dinner (AP Plan)",
        "Clafouti Beach Resort / Black Beach Resort Varkala",
        "3 x 54-Seated Pushback AC Bus Convoy"
    ),
    (
        3,
        "Day 3: Varkala to Vagamon Hill Station — Pine Forest & 4x4 Off-Road Jeep Safari & DJ Campfire",
        "Varkala to Vagamon Hills (135 km Ghat Road)",
        "07:00 AM: Breakfast and checkout. Drive up the lush Western Ghats misty hill roads to Vagamon. 12:30 PM: Check-in at hillside resort and lunch. 02:30 PM: Guided walk inside the majestic Vagamon Pine Forest and green meadows. 04:00 PM: High-adrenaline 4x4 Off-Road Mountain Jeep Ride across rugged rocky terrains, tea plantations, and scenic Kurisumala peak. 07:30 PM: High-energy DJ Dance Party with stage sound & lights, followed by warm bonfire campfire. Barbecue snacks & gala buffet dinner. Overnight stay in Vagamon.",
        "Early breakfast & Ghat road drive up to Vagamon high range",
        "Vagamon Pine Forest, Kurisumala Ashram Viewpoint, Suicide Point & Off-road Mountain Trails",
        "High-Bass DJ Dance Night with Stage Lights, Resort Campfire, Gala Dinner",
        "Overnight Stay at Vagamon Hillside Resort",
        "Breakfast, Lunch, Dinner + Campfire Special",
        "Vagamon Pine County Resort / Chillax Vagamon",
        "Convoy Buses + 25 x 4x4 Off-Road Mountain Jeeps"
    ),
    (
        4,
        "Day 4: Vagamon to Alleppey — Grand Houseboat Day Cruise with Kerala Feast",
        "Vagamon to Alleppey Backwaters (90 km)",
        "08:00 AM: Hillside breakfast and checkout. Descend towards the Venice of the East — Alleppey backwaters. 11:30 AM: Board private luxury Kerala Houseboats at Punnamada jetty. Cruising through tranquil Vembanad lake, lush paddy fields, and palm-fringed canals. 01:00 PM: Traditional Kerala Backwater Buffet Lunch prepared fresh on board (Kerala parotta, fish curry / chicken roast, veg sambar, avial & payasam). 04:30 PM: Houseboat disembarkation and visit to Alleppey beach & historic sea bridge. Dinner at Alleppey.",
        "Breakfast, checkout & journey down the hill range to Punnamada Backwaters",
        "Alleppey Backwaters Cruise, Vembanad Lake, Kuttanad Paddy Fields, Alleppey Sea Beach",
        "Disembarkation, Alleppey beach sea-breeze relaxation, Dinner & Boarding buses for return",
        "Overnight Coach Journey / Hotel Stay",
        "Breakfast, Traditional Houseboat Feast Lunch, Dinner",
        "Private Luxury Houseboats Fleet (Punnamada Jetty)",
        "3 x 54-Seated Coaches + Houseboats Fleet"
    ),
    (
        5,
        "Day 5: Alleppey to Tamil Nadu — Safe Return Drop at College Campus",
        "Alleppey to Tamil Nadu (via Kochi-Palakkad-Coimbatore Highway)",
        "Night convoy journey across Palakkad gap into Tamil Nadu. Morning en-route breakfast stop. 09:30 AM: Safe arrival and drop-off at College campus in Tamil Nadu with sweet memories of Kochi IT hub, Varkala cliff, Vagamon 4x4 safari, and Alleppey backwaters. Tour concludes.",
        "En-route morning highway breakfast & group photography",
        "Scenic highway crossing, Palakkad Pass, Western Ghats foothills",
        "Arrival at College premises, luggage deboarding, student farewell",
        "Safe Campus Drop at Tamil Nadu Institution",
        "En-route Breakfast & Morning Refreshment",
        "Drop at College Campus Ground",
        "3 x 54-Seated Pushback AC Bus Convoy"
    )
]

for d_num, title, r_seg, act, m_act, spots, ev_act, stay_loc, meals, hotel, trnsp in itinerary_data:
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
            'transport_info': trnsp
        }
    )
print(f"Configured {len(itinerary_data)} Detailed Itinerary Days for Kerala IV.")

# 3. Vehicle Tariff for 54-Seater Bus Convoy
bus_vtype = VehicleType.objects.filter(seating_capacity__gte=45).first()
if not bus_vtype:
    bus_vtype = VehicleType.objects.create(name='54-Seater Luxury AC Coach', seating_capacity=54)

PackageVehicleTariff.objects.update_or_create(
    package=pkg,
    vehicle_type=bus_vtype,
    defaults={
        'rate_type': 'outstation_multiday',
        'seating_tier': '54_luxury_coach',
        'package_rate': Decimal('165000.00'),
        'per_day_rate': Decimal('33000.00'),
        'included_km': 1500,
        'extra_km_rate': Decimal('42.00'),
        'extra_hour_rate': Decimal('450.00'),
        'driver_bata_included': True,
        'driver_bata_per_day': Decimal('1500.00'),
        'interstate_permit_included': True,
        'toll_parking_included': True,
    }
)
print("Configured 54-Seater Luxury Bus Tariff.")

# 4. College IV Expedition Record (150 Students + 6 Staff = 156 Pax)
start_dt = datetime.date.today() + datetime.timedelta(days=14)
end_dt = start_dt + datetime.timedelta(days=4)

iv_exp, iv_created = CollegeIVProxy.objects.update_or_create(
    college_name='Tamil Nadu Premier Engineering College (Autonomous)',
    department_and_batch='B.E. Computer Science & Engineering (Final Year 2022–2026 Batch)',
    defaults={
        'package': pkg,
        'faculty_incharge_name': 'Dr. S. K. Narayanan, Ph.D. (HOD - CSE)',
        'faculty_incharge_phone': '9842533777',
        'student_count_male': 90,
        'student_count_female': 60,
        'faculty_count': 6,
        'total_pax': 156,
        'industry_visit_targets': 'Tata Consultancy Services (TCS) / Wipro IT Campus, Infopark Phase-II, Kakkanad, Kochi',
        'permission_status': 'approved',
        'start_date': start_dt,
        'end_date': end_dt,
        'bus_count': 3,
        'tour_manager_assigned': 'Anandh C & S. Murugesan (Siva Gayathri Convoy Team)',
        'has_dj_campfire': True,
        'status': 'confirmed',
        'notes': 'Convoy: 3 x 54-Seater Luxury AC Pushback Coaches. 38 Quad Rooms for 150 students + 3 Twin Rooms for 6 faculty (Total 41 Rooms).'
    }
)
print(f"[{'Created' if iv_created else 'Updated'}] College IV Expedition: {iv_exp.college_name} (156 Pax, 3 Buses Convoy, Confirmed)")
