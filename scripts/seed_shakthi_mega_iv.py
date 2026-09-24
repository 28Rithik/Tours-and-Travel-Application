import os
import django
from decimal import Decimal
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import (
    PackageTemplate, Package, PackageVehicleTariff, ItineraryDay,
    TourPassengerManifest, PackageInventory
)
from package_tours.models import CollegeIVProxy
from core.models import VehicleType

print("=== SEEDING SRI SHAKTHI COLLEGE MEGA IV (350 STUDENTS + 14 STAFF = 364 PAX) ===")

# 1. Create Reusable Package Template
tmpl, tmpl_created = PackageTemplate.objects.update_or_create(
    name="5 Nights 6 Days Karnataka & Kerala Dual-State Mega IV Circuit",
    defaults={
        'destination': "Mysore, Coorg, Kochi, Vagamon, Alleppey (Karnataka & Kerala)",
        'category': 'college_iv',
        'duration_days': 6,
        'duration_nights': 5,
        'base_price': Decimal('7950.00'),
        'description': "Flagship dual-state mega educational expedition covering Mysore historical heritage, Coorg nature & coffee estates, Kochi IT Hub industrial visit, Vagamon off-road jeep safari & DJ night, and Alleppey luxury backwaters houseboat cruise.",
        'is_active': True,
    }
)
print(f"[{'Created' if tmpl_created else 'Updated'}] Template: {tmpl.name}")

# 2. Create Master Package
pkg, created = Package.objects.update_or_create(
    package_code='PKG-KA-KL-IV-06D',
    defaults={
        'template': tmpl,
        'name': '5 NIGHTS 6 DAYS KARNATAKA & KERALA MEGA COLLEGE IV (MYSORE - COORG - KOCHI IT HUB - VAGAMON - ALLEPPEY)',
        'destination': 'Mysore, Coorg, Kochi, Vagamon, Alleppey (Karnataka & Kerala)',
        'category': 'college_iv',
        'duration_days': 6,
        'duration_nights': 5,
        'pricing_type': 'per_person',
        'base_price': Decimal('7950.00'),
        'price_with_food': Decimal('7950.00'),
        'price_without_food': Decimal('5450.00'),
        'min_pax': 350,
        'complementary_staff_count': 14,
        'hotel_star_category': '3-Star Hotel & Hilltop Resort Clusters (Twin Properties for Boys & Girls)',
        'room_sharing_type': '4_sharing',
        'meal_plan': 'AP',
        'vehicle_seating_desc': '7 x 54-Seater Luxury Air-Suspension Pushback Coaches (Convoy with Lead Pilot Car)',
        'bus_amenities_desc': '7 Luxury Coaches, Laser Light, High-Bass JBL Sound System, Lead Pilot Car, First Aid Kit, 20L Water Cans in each bus',
        'has_campfire_dj': True,
        'has_jeep_safari': True,
        'has_boating': True,
        'has_industrial_visit': True,
        'inclusions': (
            "Convoy of 7 x 54-Seater Luxury 2+2 Air-Suspension Pushback Tourist Coaches + 1 Lead Pilot Car.\n"
            "Inter-State Passenger Road Taxes & Entry Clearances for both Karnataka & Kerala pre-paid online.\n"
            "All toll gate clearances, commercial bus parking, and highway checkpoints.\n"
            "Verified 3-Star Hotels & Scenic Hilltop Resorts on 4-Sharing basis for students.\n"
            "7 Deluxe Twin-Sharing AC Rooms 100% Complimentary for 14 accompanying Faculty/Staff members.\n"
            "All Meals Included (AP Plan): 6 Buffet Breakfasts, 5 Lunches, 5 Dinners + Evening High Tea & Snacks.\n"
            "Catering Logistics: 4 Parallel Buffet Serving Counters (2 for Boys, 2 for Girls) to avoid dining delays.\n"
            "Official Industrial Visit Clearance at Premier IT Company (Infopark Phase-II Kakkanad, Kochi).\n"
            "Thrilling 61 x 4x4 Mountain Off-Road Jeep Safari across Vagamon hills to Kurisumala rocky trails.\n"
            "Exclusive Backwater Cruise on Fleet of 7 Luxury Houseboats in Alleppey with authentic Kerala Buffet Feast.\n"
            "Grand DJ Dance Night with Concert-Grade Sound, Stage Lighting, and Bonfire Campfire at Vagamon Resort.\n"
            "All entry passes: Mysore Palace, Brindavan Garden musical fountain, Bylakuppe Golden Temple, Abbey Falls, Vagamon Pine Forest.\n"
            "Senior Tour Escort Team from Siva Gayathri Tours (1 Convoy Commander + 7 Bus Captains) accompanying 24/7."
        ),
        'exclusions': (
            "Any personal laundry, room service, or extra food/beverage orders outside the buffet.\n"
            "Personal adventure activities or water sports at Alleppey beach.\n"
            "Damages caused by students to hotel/coach property (chargeable to institution).\n"
            "Camera fees at restricted historical or industrial premises."
        ),
        'terms_and_conditions': (
            "Official Institutional Authorization Letter with HOD and Principal seal required before convoy departure.\n"
            "Complete student passenger manifest with roll numbers and emergency parent contacts mandatory.\n"
            "Strict disciplinary segregation: Separate resort blocks/wings and buses maintained for Male and Female students.\n"
            "Each bus will have 2 designated Faculty In-Charges as Bus Captains to conduct roll call before any transit.\n"
            "Payment Terms: 40% advance booking token upon approval, 40% 7 days prior to departure, balance 20% on departure morning.\n"
            "Siva Gayathri Tours and Travels reserves the right to alter route sequences in case of unforeseen hill landslides or road closures."
        ),
        'contact_persons_footer': 'Rithik CA (Managing Director) - 98425 33777, Anandh C (Convoy Operations) - 94381 71311',
        'is_active': True,
    }
)
print(f"[{'Created' if created else 'Updated'}] Master Package: {pkg.name} (ID #{pkg.id})")

# 3. Itinerary Days (Day 1 to Day 6)
itinerary_days_data = [
    (
        1,
        "Day 1: Coimbatore to Mysore — Chamundi Hills, Grand Palace & Brindavan Musical Fountain",
        "Coimbatore to Mysore via Chamarajanagar Highway (210 km)",
        "05:00 AM: Convoy flags off from Sri Shakthi College campus in 7 luxury coaches with pilot car. En-route highway breakfast. 11:30 AM: Arrive in Mysore, check-in to twin hotels, and buffet lunch. 02:30 PM: Guided tour of Mysore Palace (Amba Vilas) — royal durbar hall, ivory throne, and architecture. 05:30 PM: Proceed to KRS Dam & Brindavan Gardens for the famous musical dancing fountain show. 08:30 PM: Buffet dinner and overnight stay in Mysore.",
        "Early morning convoy departure, highway breakfast & hotel check-in",
        "Chamundi Hills Viewpoint, Mysore Palace, KRS Dam & Brindavan Musical Fountain Gardens",
        "Brindavan musical fountain show, 4-counter grand buffet dinner, overnight stay",
        "Overnight Stay at Mysore 3-Star Hotel (Hotel Grand Mercure / Sandesh The Prince)",
        "Breakfast, Lunch, Dinner (AP Plan)",
        "Hotel Sandesh The Prince / Roopa Elite Mysore",
        "Convoy of 7 x 54-Seater Luxury AC Buses"
    ),
    (
        2,
        "Day 2: Mysore to Coorg / Madikeri — Bylakuppe Tibetan Golden Temple, Coffee Estates & Abbey Falls",
        "Mysore to Coorg / Madikeri (120 km scenic hill drive)",
        "07:30 AM: Buffet breakfast and checkout. Journey into the Scotland of India — Coorg. 10:00 AM: Visit Bylakuppe Golden Temple (Namdroling Tibetan Monastery) with 40-foot golden Buddha statues. 01:00 PM: Arrive in Madikeri, resort check-in, and traditional Kodava & South Indian lunch. 03:00 PM: Guided walk inside fragrant coffee & cardamom plantations. 04:30 PM: Visit roaring Abbey Falls amidst spice valleys, followed by Raja's Seat sunset viewpoint. 08:30 PM: Buffet dinner and overnight stay in Coorg.",
        "Breakfast, checkout & drive up the misty Western Ghats to Coorg",
        "Bylakuppe Golden Temple, Coffee & Cardamom Plantation, Abbey Falls, Raja's Seat Sunset",
        "Raja's Seat sunset, Coorg spice shopping, grand buffet dinner, resort stay",
        "Overnight Stay at Coorg Hillside Resort (Resort Cluster: Boys & Girls Wings)",
        "Breakfast, Lunch, Dinner (AP Plan)",
        "Coorg Cliffs Resort / Windflower Resort Coorg",
        "Convoy of 7 x 54-Seater Luxury AC Buses"
    ),
    (
        3,
        "Day 3: Coorg to Kerala Coastal Highway — Ghat Descent to Kochi & Marine Drive Leisure",
        "Coorg to Kochi via Virajpet-Mattannur Coastal Highway (310 km)",
        "06:30 AM: Early breakfast and checkout from Coorg. Descend the lush Virajpet ghats crossing the Kerala border at Kootupuzha. Scenic coastal highway journey through Malabar with a traditional Malabar lunch stop. 05:00 PM: Arrive in Kochi (Cochin) — Queen of the Arabian Sea. Hotel check-in and refreshment. 06:30 PM: Evening stroll along Kochi Marine Drive, Rainbow Walkway, and boat jetty breeze. 08:30 PM: Buffet dinner and overnight stay in Kochi.",
        "Early breakfast, ghat road descent crossing into Kerala state",
        "Western Ghats descent, Malabar coastal corridor, Kochi Marine Drive & Rainbow Bridge",
        "Marine Drive evening stroll, Lulu Mall shopping, buffet dinner, overnight stay",
        "Overnight Stay at Kochi 3-Star Hotel (Hotel Abad Plaza / Gokulam Park)",
        "Breakfast, Lunch, Dinner (AP Plan)",
        "Abad Plaza / Gokulam Park Kochi",
        "Convoy of 7 x 54-Seater Luxury AC Buses"
    ),
    (
        4,
        "Day 4: Kochi IT Hub Industrial Visit — AI & Data Center Lab to Vagamon High Ranges & DJ Campfire",
        "Kochi to Vagamon Hills via Thodupuzha (105 km high range drive)",
        "07:30 AM: Buffet breakfast. 09:30 AM: Convoy arrives at Premier IT Company (Infopark Kakkanad / TCS / Cognizant campus). Industrial Visit entry: Specialized technical session for B.Tech AI & DS students on Cloud infrastructure, GPU clusters, Large Language Model deployments, and Enterprise AI workflows. Interactive Q&A with Senior Solution Architects. 01:30 PM: Buffet lunch. 02:30 PM: Proceed up the high-range tea hills to Vagamon. 06:30 PM: Check-in to hilltop resort. 07:30 PM: High-Voltage DJ Dance Party with stage concert sound, moving-head laser lights, and grand resort bonfire campfire with barbecue. 09:30 PM: Gala buffet dinner and overnight stay in Vagamon.",
        "Breakfast, IT campus entry badges, corporate clearance & presentations",
        "Infopark Phase-II Kakkanad, Cloud Data Center, AI Labs, Vagamon High Ranges",
        "High-Bass DJ Dance Night with Stage Lights, Resort Campfire, Gala Buffet Dinner",
        "Overnight Stay at Vagamon Hilltop Resort (Pine Valley / Chillax Resorts)",
        "Breakfast, Lunch, Dinner + Campfire Barbecue",
        "Vagamon Pine County Resort / Chillax Vagamon",
        "Convoy of 7 x 54-Seater Luxury AC Buses"
    ),
    (
        5,
        "Day 5: Vagamon 4x4 Mountain Jeep Safari to Alleppey — Grand Houseboats Backwaters Day Cruise",
        "Vagamon to Alleppey Backwaters (90 km)",
        "07:30 AM: Breakfast. 08:30 AM: Pine forest nature trek. 09:30 AM: Adrenaline-packed 61 x 4x4 Mountain Off-Road Jeep Safari across rocky ridges and Kurisumala peak. 11:30 AM: Checkout and descend hills to Alleppey (Venice of the East). 01:30 PM: Board fleet of 7 Luxury Houseboats at Punnamada Jetty. Private backwater cruise through Vembanad Lake and palm canals. Authentic Kerala Backwater Feast prepared on board (Kerala parotta, fish curry / chicken roast, veg avial, sambar & payasam). 05:00 PM: Disembark and visit historic Alleppey Beach & sea pier. 08:00 PM: Dinner at Alleppey. 09:30 PM: Board return convoy for overnight highway journey.",
        "Pine forest trek & 61 x 4x4 Mountain Jeep Safari across rugged hill trails",
        "Vagamon Pine Forest, Kurisumala Peak, Vembanad Lake Backwaters, Alleppey Sea Beach",
        "Houseboat cruise, Alleppey beach sunset, dinner, boarding return night convoy",
        "Overnight Highway Convoy Journey with Pilot Car Escort",
        "Breakfast, Houseboat Feast Lunch, Dinner (AP Plan)",
        "Fleet of 7 Private Luxury Houseboats (Punnamada Jetty)",
        "7 Luxury Coaches + 61 Jeeps + 7 Houseboats"
    ),
    (
        6,
        "Day 6: Alleppey to Coimbatore — Highway Breakfast Stop & Safe Campus Arrival",
        "Alleppey to Coimbatore via Kochi-Palakkad Gap Highway (225 km)",
        "Smooth night convoy journey with rolling security escort across the Palakkad gap into Tamil Nadu. 07:00 AM: En-route highway breakfast and group photography stop. 09:30 AM: Safe arrival and triumphant drop-off at Sri Shakthi Institute of Engineering and Technology campus, Coimbatore. Trophies & photo session. Tour successfully concludes.",
        "Early morning highway breakfast, freshen up & group photo",
        "Palakkad Pass, Western Ghats foothills, Coimbatore highway",
        "Arrival at Sri Shakthi College Campus, luggage unloading, farewell",
        "Safe Campus Drop at Sri Shakthi College, Coimbatore",
        "En-route Morning Breakfast",
        "Drop at Sri Shakthi College Ground",
        "Convoy of 7 x 54-Seater Luxury AC Buses"
    )
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
print("Configured 6 Detailed Itinerary Days for Sri Shakthi Mega IV.")

# 4. Vehicle Tariff for 54-Seater Luxury Bus Convoy
bus_vtype = VehicleType.objects.filter(seating_capacity__gte=45).first()
if not bus_vtype:
    bus_vtype = VehicleType.objects.create(name='54-Seater Luxury AC Coach', seating_capacity=54)

PackageVehicleTariff.objects.update_or_create(
    package=pkg,
    vehicle_type=bus_vtype,
    defaults={
        'rate_type': 'outstation_multiday',
        'seating_tier': '54_luxury_coach',
        'package_rate': Decimal('198000.00'),
        'per_day_rate': Decimal('33000.00'),
        'included_km': 1800,
        'extra_km_rate': Decimal('42.00'),
        'extra_hour_rate': Decimal('450.00'),
        'driver_bata_included': True,
        'driver_bata_per_day': Decimal('1500.00'),
        'interstate_permit_included': True,
        'toll_parking_included': True,
    }
)
print("Configured 54-Seater Luxury Bus Tariff (Rs. 1,98,000 / coach for 6-day circuit).")

# 5. College IV Expedition Record (350 Students + 14 Staff = 364 Pax)
start_dt = datetime.date.today() + datetime.timedelta(days=21)
end_dt = start_dt + datetime.timedelta(days=5)

iv_exp, iv_created = CollegeIVProxy.objects.update_or_create(
    college_name='Sri Shakthi Institute of Engineering and Technology (Autonomous)',
    department_and_batch='B.Tech Artificial Intelligence & Data Science (Final Year Batch 2022–2026)',
    defaults={
        'package': pkg,
        'faculty_incharge_name': 'Dr. A. Ramesh Kumar, Ph.D. (HOD - AI & DS)',
        'faculty_incharge_phone': '9842533777',
        'student_count_male': 210,
        'student_count_female': 140,
        'faculty_count': 14,
        'total_pax': 364,
        'industry_visit_targets': 'Tata Consultancy Services (TCS) AI & Cloud Innovation Lab / Wipro Infopark Phase-II, Kakkanad, Kochi',
        'permission_status': 'approved',
        'start_date': start_dt,
        'end_date': end_dt,
        'bus_count': 7,
        'tour_manager_assigned': 'Rithik CA (Convoy Commander) & Anandh C + 7 Bus Captains',
        'has_dj_campfire': True,
        'status': 'confirmed',
        'notes': 'Mega Convoy: 7 x 54-Seater Coaches + 1 Pilot Car. 88 Quad Rooms for 350 students + 7 Twin Rooms for 14 faculty (Total 95 Rooms in Twin-Resort Clusters).'
    }
)
print(f"[{'Created' if iv_created else 'Updated'}] College IV Expedition: {iv_exp.college_name} (364 Pax, 7 Buses Convoy, Confirmed)")

# 6. Bulk Sample Manifest Generation (364 Pax: 14 Faculty + 350 Students)
# We generate the complete manifest to demonstrate instant bulk capability
manifest_records = []

# Faculty: 14 members (2 per bus as Bus Captains, 7 Twin Rooms)
faculty_names = [
    ("Dr. A. Ramesh Kumar", "male", "FAC-01", "Bus 01", "01A", "Room 101 (Twin - Faculty)"),
    ("Dr. S. K. Narayanan", "male", "FAC-02", "Bus 01", "01B", "Room 101 (Twin - Faculty)"),
    ("Prof. P. Karthikeyan", "male", "FAC-03", "Bus 02", "01A", "Room 102 (Twin - Faculty)"),
    ("Prof. M. Saravanan", "male", "FAC-04", "Bus 02", "01B", "Room 102 (Twin - Faculty)"),
    ("Dr. R. Vijay Anand", "male", "FAC-05", "Bus 03", "01A", "Room 103 (Twin - Faculty)"),
    ("Prof. K. Senthil Nathan", "male", "FAC-06", "Bus 03", "01B", "Room 103 (Twin - Faculty)"),
    ("Dr. V. Deepalakshmi", "female", "FAC-07", "Bus 04", "01A", "Room 104 (Twin - Faculty)"),
    ("Dr. K. Malarvizhi", "female", "FAC-08", "Bus 04", "01B", "Room 104 (Twin - Faculty)"),
    ("Prof. G. Revathi", "female", "FAC-09", "Bus 05", "01A", "Room 105 (Twin - Faculty)"),
    ("Prof. N. Mythili", "female", "FAC-10", "Bus 05", "01B", "Room 105 (Twin - Faculty)"),
    ("Dr. T. Geetha", "female", "FAC-11", "Bus 06", "01A", "Room 106 (Twin - Faculty)"),
    ("Prof. P. Kavitha", "female", "FAC-12", "Bus 06", "01B", "Room 106 (Twin - Faculty)"),
    ("Dr. E. Rajesh", "male", "FAC-13", "Bus 07", "01A", "Room 107 (Twin - Faculty)"),
    ("Prof. B. Mohan", "male", "FAC-14", "Bus 07", "01B", "Room 107 (Twin - Faculty)"),
]

for name, gen, roll, bus, seat, room in faculty_names:
    manifest_records.append(
        TourPassengerManifest(
            iv_expedition=iv_exp,
            passenger_name=name,
            category='faculty',
            gender=gen,
            roll_number=roll,
            age=40,
            bus_assignment=bus,
            seat_number=seat,
            room_sharing_number=room,
            phone='9842533777',
            emergency_contact='9438171311',
            senior_assistance_needed=False
        )
    )

# Students: 350 (210 Boys in Buses 1-4, 140 Girls in Buses 5-7)
# Boys: 210 students -> 52.5 ~ 53 Quad Rooms (Rooms 201 to 253)
boy_names_sample = [
    "Aakash", "Abishek", "Ajay", "Anand", "Arun", "Ashwin", "Balaji", "Bhuvanesh", "Chandran", "Deepak",
    "Dhanush", "Dinesh", "Elango", "Ganesh", "Gautham", "Gokul", "Hari", "Harish", "Iniyan", "Jeeva",
    "Kailash", "Karthik", "Kishore", "Madhavan", "Manoj", "Mithun", "Mukesh", "Naveen", "Nikhil", "Nithish",
    "Pradeep", "Praveen", "Rahul", "Rajesh", "Raman", "Rohit", "Sachin", "Sai", "Sanjay", "Santosh",
    "Sarath", "Sathish", "Shankar", "Shiva", "Surya", "Tharun", "Varun", "Vignesh", "Vijay", "Yashwant"
]

girl_names_sample = [
    "Abhinaya", "Ananya", "Anu", "Archana", "Bhavana", "Brindha", "Charulatha", "Deepa", "Divya", "Harini",
    "Hema", "Ishwarya", "Janani", "Jeevitha", "Kalpana", "Kavya", "Keerthana", "Krithika", "Lavanya", "Madhumitha",
    "Meenakshi", "Monika", "Nandhini", "Nisha", "Nithya", "Pavithra", "Pooja", "Preethi", "Priya", "Ramya",
    "Sandhya", "Sangeetha", "Saranya", "Shalini", "Sneha", "Soundarya", "Swathi", "Vaishnavi", "Varsha", "Vinitha"
]

# Create 210 Male Students
for i in range(1, 211):
    bus_num = f"Bus 0{((i - 1) // 52) + 1}"
    seat_num = f"{((i - 1) % 52) + 2:02d}A"
    room_num = f"Room {200 + ((i - 1) // 4) + 1} (4 Sharing - Boys)"
    base_name = boy_names_sample[(i - 1) % len(boy_names_sample)]
    manifest_records.append(
        TourPassengerManifest(
            iv_expedition=iv_exp,
            passenger_name=f"{base_name} {chr(65 + (i % 26))}",
            category='student',
            gender='male',
            roll_number=f"711522205{i:03d}",
            age=21,
            bus_assignment=bus_num,
            seat_number=seat_num,
            room_sharing_number=room_num,
            phone=f"98425{i:05d}",
            emergency_contact=f"94430{i:05d}",
            senior_assistance_needed=False
        )
    )

# Create 140 Female Students
for i in range(1, 141):
    bus_num = f"Bus 0{4 + ((i - 1) // 48) + 1}"
    seat_num = f"{((i - 1) % 48) + 2:02d}A"
    room_num = f"Room {300 + ((i - 1) // 4) + 1} (4 Sharing - Girls)"
    base_name = girl_names_sample[(i - 1) % len(girl_names_sample)]
    manifest_records.append(
        TourPassengerManifest(
            iv_expedition=iv_exp,
            passenger_name=f"{base_name} {chr(65 + (i % 26))}",
            category='student',
            gender='female',
            roll_number=f"711522205{210 + i:03d}",
            age=21,
            bus_assignment=bus_num,
            seat_number=seat_num,
            room_sharing_number=room_num,
            phone=f"98426{i:05d}",
            emergency_contact=f"94431{i:05d}",
            senior_assistance_needed=False
        )
    )

# Clear existing manifest for this expedition and bulk insert all 364 records
TourPassengerManifest.objects.filter(iv_expedition=iv_exp).delete()
TourPassengerManifest.objects.bulk_create(manifest_records, batch_size=100)
print(f"Successfully Bulk-Inserted {len(manifest_records)} Passenger Manifest Records (14 Faculty + 210 Boys + 140 Girls = 364 Pax) across 7 Buses & 95 Rooms!")
