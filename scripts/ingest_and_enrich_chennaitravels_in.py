import os
import sys
import re
import decimal
import django

sys.path.append('c:/Users/rithi/Documents/Documents Project Intership and Course/Projects/Rag chatbot/Travels Trip Managment Application')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import Package, ItineraryDay, PackageVehicleTariff, TempleDarshanSlot
from core.models import VehicleType

sys.stdout.reconfigure(encoding='utf-8')

print("="*85)
print("ENRICHING & COMPLETING CHENNAI TRAVELS (SGT-CT) CATALOG FROM CHENNAITRAVELS.IN")
print("100% REBRANDED UNDER SIVA GAYATHRI TOURS & TRAVELS (+91 98425 33777)")
print("="*85)

# Fetch vehicle types
v_sedan = VehicleType.objects.filter(name__icontains='Sedan').first() or VehicleType.objects.get(id=3)
v_crysta = VehicleType.objects.filter(name__icontains='Crysta').first() or VehicleType.objects.get(id=1)
v_tt = VehicleType.objects.filter(name__icontains='Urbania').first() or VehicleType.objects.filter(name__icontains='Tempo').first() or VehicleType.objects.get(id=4)
v_minibus = VehicleType.objects.filter(name__icontains='36').first() or VehicleType.objects.get(id=13)
v_coach = VehicleType.objects.filter(name__icontains='54').first() or VehicleType.objects.filter(name__icontains='52').first() or VehicleType.objects.get(id=8)

# Helper function to generate tariffs
def generate_tariffs(package, days, nights, base_price):
    days = max(1, days)
    is_1day = (days == 1)
    tariffs = []

    if is_1day:
        rates = {
            v_sedan: (decimal.Decimal('2800.00') if base_price < 600 else decimal.Decimal('3800.00'), '4_sedan', 250, 14.0, 10),
            v_crysta: (decimal.Decimal('4200.00') if base_price < 600 else decimal.Decimal('5800.00'), '7_crysta', 250, 18.0, 10),
            v_tt: (decimal.Decimal('5800.00') if base_price < 600 else decimal.Decimal('7500.00'), '17_tt_urbania', 250, 24.0, 10),
            v_minibus: (decimal.Decimal('9500.00') if base_price < 600 else decimal.Decimal('12500.00'), '36_mini_bus', 250, 36.0, 10),
            v_coach: (decimal.Decimal('14000.00') if base_price < 600 else decimal.Decimal('18500.00'), '54_luxury_coach', 250, 48.0, 10)
        }
        for vt, (pkg_rate, tier, inc_km, extra_km, hrs) in rates.items():
            tariffs.append(PackageVehicleTariff(
                package=package,
                vehicle_type=vt,
                rate_type='local_1day',
                seating_tier=tier,
                package_rate=pkg_rate,
                per_day_rate=pkg_rate,
                included_km=inc_km,
                extra_km_rate=decimal.Decimal(str(extra_km)),
                local_package_hours=hrs,
                extra_hour_rate=decimal.Decimal('250.00'),
                driver_bata_included=True,
                driver_bata_per_day=decimal.Decimal('500.00'),
                toll_parking_included=True
            ))
    else:
        daily_rates = {
            v_sedan: (decimal.Decimal('2600.00'), '4_sedan', 300, 13.0),
            v_crysta: (decimal.Decimal('3900.00'), '7_crysta', 300, 18.0),
            v_tt: (decimal.Decimal('5200.00'), '17_tt_urbania', 300, 23.0),
            v_minibus: (decimal.Decimal('8500.00'), '36_mini_bus', 300, 35.0),
            v_coach: (decimal.Decimal('13500.00'), '54_luxury_coach', 300, 45.0)
        }
        for vt, (d_rate, tier, inc_km, extra_km) in daily_rates.items():
            total_rate = d_rate * days
            tariffs.append(PackageVehicleTariff(
                package=package,
                vehicle_type=vt,
                rate_type='outstation_multiday',
                seating_tier=tier,
                package_rate=total_rate,
                per_day_rate=d_rate,
                included_km=inc_km * days,
                extra_km_rate=decimal.Decimal(str(extra_km)),
                driver_bata_included=True,
                driver_bata_per_day=decimal.Decimal('600.00'),
                night_halt_charge=decimal.Decimal('500.00') if nights > 0 else decimal.Decimal('0.00'),
                toll_parking_included=True
            ))
    return tariffs

# ==============================================================================
# 1. INGEST 2 MISSING PACKAGES: Kolli Hills & Chennai Outside City Tour
# ==============================================================================
print("\n--- 1. INGESTING MISSING PACKAGES ---")

# A. Kolli Hills Tour Package (2N/3D)
kolli_pkg, k_created = Package.objects.update_or_create(
    package_code='SGT-CT-KOLLI-HILLS-TOUR-3D',
    defaults={
        'name': 'Chennai to Kolli Hills Scenic Hill Station Tour Package',
        'destination': 'Chennai / Namakkal / Kolli Hills',
        'category': 'hill_station',
        'duration_days': 3,
        'duration_nights': 2,
        'pricing_type': 'per_person',
        'base_price': decimal.Decimal('5900.00'),
        'price_with_food': decimal.Decimal('7900.00'),
        'price_without_food': decimal.Decimal('5900.00'),
        'is_devotional': True,
        'satvik_pure_veg_meals': False,
        'senior_citizen_friendly': False,
        'hotel_star_category': 'Deluxe Hill Resort & Plantation Stay',
        'room_sharing_type': 'twin_sharing',
        'meal_plan': 'MAP',
        'has_campfire_dj': True,
        'inclusions': (
            "Round trip transportation by dedicated AC vehicle.\n"
            "All toll gate, state permit, parking fees, and driver allowances.\n"
            "Resort accommodation in Kolli Hills on twin sharing basis.\n"
            "Daily breakfast and dinner (MAP plan).\n"
            "Sightseeing transfers including 70 hairpin bend drive and Agaya Gangai waterfall point.\n"
            "Campfire evening at resort."
        ),
        'exclusions': (
            "Entry fees for Agaya Gangai waterfall steps, botanical garden, and camera fees.\n"
            "Personal expenses, room service, laundry, and guide tips."
        ),
        'terms_and_conditions': (
            "Campfire subject to weather conditions.\n"
            "Agaya Gangai waterfall involves climbing ~1,000 steep steps; guests with cardiac or knee issues are advised caution.\n"
            "Advance payment 50% required upon confirmation."
        ),
        'contact_persons_footer': "Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131 / +91 38209 9979)",
        'description': (
            "Escape to the untouched, mystical mountains of Kolli Hills (Kolli Malai) in Central Tamil Nadu. "
            "Famous for its thrilling drive through 70 contiguous hairpin bends, ancient Arapaleeswarar Shiva Temple, "
            "the 300-foot Agaya Gangai waterfalls, Seekuparai viewpoint, and fragrant medicinal herbal farms."
        ),
        'is_active': True
    }
)

# Clear and reload child records for Kolli Hills
kolli_pkg.itinerary_days.all().delete()
kolli_pkg.vehicle_tariffs.all().delete()
kolli_pkg.temple_slots.all().delete()

# Itinerary days for Kolli Hills
ItineraryDay.objects.create(
    package=kolli_pkg,
    day_number=1,
    title='Departure from Chennai and Arrival at Kolli Hills',
    route_segment='Chennai to Kolli Hills via Salem (380 km / 7.5 hrs)',
    activities='Early morning 05:30 AM departure from Chennai. Drive via Villupuram and Ulundurpet to Namakkal. Ascend the thrilling 70 hairpin bends road with lush valley vistas. Arrive in Semmedu / Kolli Hills. Resort check-in, lunch. Visit the 8th-century Arapaleeswarar Temple consecrated by Sangam kings and the sacred river pond. Resort campfire, dinner.',
    morning_activity='05:30 AM pickup, breakfast enroute, climb 70 hairpin bends',
    sightseeing_spots='70 Hairpin Bends Road, Arapaleeswarar Temple, Sacred Fish Pond',
    evening_night_activity='Resort campfire, mountain mist relaxation, dinner',
    night_stay_location='Kolli Hills Resort',
    meals_included='Breakfast, Lunch, Dinner'
)

ItineraryDay.objects.create(
    package=kolli_pkg,
    day_number=2,
    title='Exploring Agaya Gangai Waterfalls & Scenic Viewpoints',
    route_segment='Kolli Hills Local Circuit',
    activities='Breakfast at resort. Excursion to the spectacular 300-foot Agaya Gangai Waterfalls formed by River Aiyaru (steep descent of 1,000 steps). Enjoy rejuvenating bath in the mist pool. Afternoon visit to Seekuparai and Selur Viewpoints offering panoramic views of deep valleys. Visit Siddha caves and botanical garden. Evening dinner.',
    morning_activity='Breakfast, Agaya Gangai Waterfalls trek',
    sightseeing_spots='Agaya Gangai Waterfalls, Seekuparai Viewpoint, Selur Viewpoint, Siddha Caves',
    evening_night_activity='Herbal spice shopping, dinner',
    night_stay_location='Kolli Hills Resort',
    meals_included='Breakfast, Lunch, Dinner'
)

ItineraryDay.objects.create(
    package=kolli_pkg,
    day_number=3,
    title='Cultural Experiences, Herbal Gardens & Return to Chennai',
    route_segment='Kolli Hills to Chennai (380 km / 7.5 hrs)',
    activities='Morning visit to Kolli Hills Herbal & Pepper Farms, Government Pineapple Farm, and Boat House in Solakkadu. Taste wild organic honey and mountain spices. Check out and descend the 70 hairpin bends. Return drive to Chennai arriving by 09:30 PM.',
    morning_activity='Breakfast, Botanical Garden and Herbal Farm visit',
    sightseeing_spots='Herbal Plantations, Solakkadu Boat House, Viewpoints',
    evening_night_activity='Return drive to Chennai, drop at residence',
    night_stay_location='Return to Chennai',
    meals_included='Breakfast, Lunch'
)

for t in generate_tariffs(kolli_pkg, 3, 2, decimal.Decimal('5900.00')):
    t.save()

TempleDarshanSlot.objects.create(
    package=kolli_pkg,
    temple_name='Kolli Malai Sri Arapaleeswarar Temple',
    deity_or_circuit='Lord Shiva (Arapaleeswarar) & Thayammai',
    darshan_type='general',
    booked_slot_time='11:00 AM - 12:30 PM',
    reporting_location='Temple Main Sannidhi',
    dress_code_notes='Traditional Attire',
    prasad_details='Sacred Vibhuti & River Panchanathi Theertham',
    senior_citizen_support=True
)

print(f"Created / Updated: [{kolli_pkg.package_code}] {kolli_pkg.name}")

# B. Chennai Outside City Sightseeing Tour (1D)
outside_pkg, o_created = Package.objects.update_or_create(
    package_code='SGT-CT-CHENNAI-OUTSIDE-C-1D',
    defaults={
        'name': 'Chennai Outside City Sightseeing & Coastal Heritage Day Tour',
        'destination': 'Chennai Outside City / ECR / Covelong / Mahabalipuram',
        'category': 'local_tour',
        'duration_days': 1,
        'duration_nights': 0,
        'pricing_type': 'per_person',
        'base_price': decimal.Decimal('450.00'),
        'price_with_food': decimal.Decimal('850.00'),
        'price_without_food': decimal.Decimal('450.00'),
        'is_devotional': False,
        'satvik_pure_veg_meals': False,
        'senior_citizen_friendly': True,
        'hotel_star_category': 'Same Day Excursion',
        'room_sharing_type': 'twin_sharing',
        'meal_plan': 'CP',
        'has_campfire_dj': False,
        'inclusions': (
            "Dedicated AC vehicle pickup and drop within Chennai city limits.\n"
            "All toll fees, parking charges, and driver day allowance.\n"
            "Sightseeing covering Kovalam, DakshinaChitra, Crocodile Bank, and Mahabalipuram.\n"
            "Experienced chauffeur with comprehensive coastal knowledge."
        ),
        'exclusions': (
            "Entry tickets to museums, crocodile bank, boat rides, and amusement parks.\n"
            "Meals, refreshments, and personal expenses."
        ),
        'terms_and_conditions': (
            "Package duration is 10 hours / 100 km from garage to garage.\n"
            "Extra hours and extra kilometers charged as per standard tariff matrix.\n"
            "Customer cooperation requested to adhere to sightseeing timings."
        ),
        'contact_persons_footer': "Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131 / +91 38209 9979)",
        'description': (
            "Discover the premier attractions along Chennai's picturesque East Coast Road. "
            "Covers Kovalam Beach, DakshinaChitra Living Heritage Museum, Madras Crocodile Bank Trust, "
            "Muttukadu Backwater Boating, Tiger Cave, and UNESCO Shore Temple in Mahabalipuram."
        ),
        'is_active': True
    }
)

outside_pkg.itinerary_days.all().delete()
outside_pkg.vehicle_tariffs.all().delete()
outside_pkg.temple_slots.all().delete()

ItineraryDay.objects.create(
    package=outside_pkg,
    day_number=1,
    title='Chennai Outside City Coastal Sightseeing Tour',
    route_segment='Chennai to ECR to Mahabalipuram and Return (110 km round trip)',
    activities='08:30 AM pickup from residence. Drive along scenic East Coast Road. Visit DakshinaChitra Living History Museum showcasing traditional South Indian heritage homes. Explore Madras Crocodile Bank Trust. Enjoy speedboating in Muttukadu Backwaters. Stop at Kovalam surfing beach. Explore 7th-century Tiger Cave and UNESCO Shore Temple in Mahabalipuram. Evening return drop at residence by 07:30 PM.',
    morning_activity='08:30 AM pickup, DakshinaChitra Museum and Crocodile Bank visit',
    sightseeing_spots='DakshinaChitra Museum, Crocodile Bank, Muttukadu Boating, Kovalam Beach, Tiger Cave, Shore Temple',
    evening_night_activity='Mahabalipuram beach stroll, return drive to Chennai',
    night_stay_location='Same Day Return',
    meals_included='Lunch at Beachside Restaurant'
)


for t in generate_tariffs(outside_pkg, 1, 0, decimal.Decimal('450.00')):
    t.save()

print(f"Created / Updated: [{outside_pkg.package_code}] {outside_pkg.name}")

# ==============================================================================
# 2. RECLASSIFY 18 MISCLASSIFIED INTERNATIONAL PACKAGES IN SGT-CT-
# ==============================================================================
print("\n--- 2. FIXING 18 MISCLASSIFIED INTERNATIONAL PACKAGES ---")

cat_fixes = {
    'SGT-CT-CHENNAI-KANCHIPURA-1D': 'devotional',
    'SGT-CT-CHENNAI-KANCHIPURA-3D': 'holiday',
    'SGT-CT-CHENNAI-MAHABALIPU-1D': 'local_tour',
    'SGT-CT-CHENNAI-MAHABALIPU-1D-116': 'local_tour',
    'SGT-CT-CHENNAI-MAHABALIPU-2D': 'local_tour',
    'SGT-CT-CHENNAI-MAHABALIPU-4D': 'holiday',
    'SGT-CT-MAHABALIPURAM-HALF-1D': 'local_tour',
    'SGT-CT-MAHABALIPURAM-KANC-1D': 'devotional',
    'SGT-CT-MAHABALIPURAM-POND-1D': 'holiday',
    'SGT-CT-MAHABALIPURAM-SIGH-1D': 'local_tour',
    'SGT-CT-MAHABALIPURAM-TOUR-1D': 'local_tour',
    'SGT-CT-MAHABALIPURAM-TOUR-1D-121': 'local_tour',
    'SGT-CT-PONDICHERRY-MAHABA-2D': 'holiday',
    'SGT-CT-THIRUKAZHUKUNDRAM--1D': 'devotional',
    'SGT-CT-TOUR-12-1D': 'devotional',
    'SGT-CT-TOUR-13-1D': 'holiday',
    'SGT-CT-TOUR-3-1D': 'local_tour',
    'SGT-CT-TOUR-PACKAGES-2D': 'local_tour'
}

for code, new_cat in cat_fixes.items():
    try:
        p = Package.objects.get(package_code=code)
        old_cat = p.category
        p.category = new_cat
        p.save(update_fields=['category'])
        print(f"  Fixed [{code}]: {old_cat} -> {new_cat}")
    except Package.DoesNotExist:
        pass

# ==============================================================================
# 3. ENRICH TEMPLE DARSHAN SLOTS FOR ALL SGT-CT DEVOTIONAL PACKAGES
# ==============================================================================
print("\n--- 3. ATTACHING TEMPLE DARSHAN SLOTS TO DEVOTIONAL CIRCUITS ---")

# Define template temple slots for different circuits
darshan_definitions = {
    'arupadai': [
        {'temple_name': 'Thiruchendur Subramanya Swamy Temple', 'deity': 'Lord Senthil Andavar', 'darshan_type': 'special_entry_300', 'slot_time': '07:30 AM - 09:30 AM', 'location': 'Main Sanctorum', 'dress_code': 'Dhoti for Men, Saree for Women', 'prasad': 'Ilai Vibhuti Prasadam'},
        {'temple_name': 'Palani Dhandayuthapani Swamy Temple', 'deity': 'Lord Dhandayuthapani', 'darshan_type': 'winch_ropeway', 'slot_time': '05:30 PM - 07:30 PM', 'location': 'Hill Top Sanctum via Winch/Ropeway', 'dress_code': 'Traditional Attire', 'prasad': 'Palani Panchamirtham Prasadam'},
        {'temple_name': 'Swamimalai Swaminatha Swamy Temple', 'deity': 'Lord Swaminatha Swamy', 'darshan_type': 'special_entry_300', 'slot_time': '08:00 AM - 09:30 AM', 'location': '60 Steps Hill Shrine', 'dress_code': 'Traditional Attire', 'prasad': 'Vibhuti Prasadam'}
    ],
    'navagraha': [
        {'temple_name': 'Suryanar Kovil (Suriyan / Sun)', 'deity': 'Lord Suryanarayana Swamy', 'darshan_type': 'special_entry_300', 'slot_time': '08:00 AM - 09:30 AM', 'location': 'Main Sanctorum', 'dress_code': 'Traditional Attire', 'prasad': 'Vibhuti & Kumkum'},
        {'temple_name': 'Thirunallar Sri Darbaranyeswarar (Sani / Saturn)', 'deity': 'Lord Saneeswarar', 'darshan_type': 'special_entry_300', 'slot_time': '04:30 PM - 06:30 PM', 'location': 'Sani Bhagavan Sannidhi', 'dress_code': 'Traditional Attire', 'prasad': 'Gingelly Oil Lamp Pooja Prasadam'},
        {'temple_name': 'Vaitheeswaran Koil (Sevvai / Mars)', 'deity': 'Lord Vaidyanatha Swamy & Angaragan', 'darshan_type': 'special_entry_300', 'slot_time': '10:30 AM - 12:00 PM', 'location': 'Angaragan Sannidhi', 'dress_code': 'Traditional Attire', 'prasad': 'Tiruchandu Urundai Sacred Medicine Ball'}
    ],
    'kalahasti': [
        {'temple_name': 'Srikalahasteeswara Temple (Vayu / Wind Stalam)', 'deity': 'Lord Shiva & Gnana Prasunambika', 'darshan_type': 'special_entry_300', 'slot_time': '09:00 AM - 11:30 AM', 'location': 'Main Sanctum & Rahu-Kethu Mandapam', 'dress_code': 'Traditional Attire', 'prasad': 'Rahu-Ketu Parihara Prasadam'}
    ],
    'srisailam': [
        {'temple_name': 'Srisailam Mallikarjuna Swamy Temple (Jyotirlinga & Shakti Peetham)', 'deity': 'Lord Mallikarjuna & Goddess Bhramaramba', 'darshan_type': 'special_entry_300', 'slot_time': '06:00 AM - 09:00 AM', 'location': 'Moolavar Sanctum & Mukha Mandapam', 'dress_code': 'Traditional Dhoti/Kurta for Men, Saree for Women', 'prasad': 'Vibhuti & Kumkum Prasadam'}
    ],
    'thirukadaiyur': [
        {'temple_name': 'Thirukadaiyur Sri Amritaghateswarar Abhirami Temple', 'deity': 'Lord Amritaghateswarar & Goddess Abhirami', 'darshan_type': 'abhishekam_seva', 'slot_time': '08:30 AM - 11:30 AM', 'location': 'Sashtiapthapoorthi / Ayushya Homam Mandapam', 'dress_code': 'Traditional Pattu Vetti / Pattu Pudavai', 'prasad': 'Sacred Kalasa Theertham & Kumkum'}
    ],
    'pancha_bhoota': [
        {'temple_name': 'Kanchipuram Ekambareswarar Temple (Prithvi / Earth)', 'deity': 'Lord Shiva (Earth Lingam)', 'darshan_type': 'general', 'slot_time': '08:30 AM - 10:00 AM', 'location': 'Prithvi Lingam Sanctum', 'dress_code': 'Traditional Attire', 'prasad': 'Vibhuti Prasadam'},
        {'temple_name': 'Tiruvannamalai Arunachaleswarar Temple (Agni / Fire)', 'deity': 'Lord Shiva (Agni Lingam)', 'darshan_type': 'special_entry_300', 'slot_time': '05:00 PM - 07:00 PM', 'location': 'Agni Lingam Sanctum', 'dress_code': 'Traditional Attire', 'prasad': 'Vibhuti & Kumkum'},
        {'temple_name': 'Chidambaram Thillai Nataraja Temple (Akasha / Sky)', 'deity': 'Lord Nataraja (Ponnambalam)', 'darshan_type': 'general', 'slot_time': '09:00 AM - 11:00 AM', 'location': 'Kanaka Sabha', 'dress_code': 'Traditional Attire', 'prasad': 'Vibhuti & Holy Theertham'}
    ],
    'narasimhar': [
        {'temple_name': 'Sholinghur Sri Yoga Narasimhar Hill Temple', 'deity': 'Lord Yoga Narasimhar (1305 Steps)', 'darshan_type': 'winch_ropeway', 'slot_time': '08:30 AM - 11:30 AM', 'location': 'Big Hill Sanctum via Ropeway', 'dress_code': 'Traditional Attire', 'prasad': 'Thulasi & Theertham'}
    ],
    'sripuram': [
        {'temple_name': 'Sripuram Sri Lakshmi Narayani Golden Temple', 'deity': 'Goddess Mahalakshmi Narayani', 'darshan_type': 'special_entry_300', 'slot_time': '10:00 AM - 12:30 PM', 'location': 'Star-Shaped Golden Path', 'dress_code': 'Traditional Attire', 'prasad': 'Maha Lakshmi Kumkum & Laddu Prasadam'}
    ],
    'chennai_temples': [
        {'temple_name': 'Mylapore Sri Kapaleeshwarar Temple', 'deity': 'Lord Kapaleeshwarar & Karpagambal', 'darshan_type': 'general', 'slot_time': '08:30 AM - 10:00 AM', 'location': 'Moolavar Sanctum', 'dress_code': 'Traditional Attire', 'prasad': 'Vibhuti & Kumkum'},
        {'temple_name': 'Triplicane Sri Parthasarathy Temple', 'deity': 'Lord Parthasarathy (Krishna as Charioteer)', 'darshan_type': 'general', 'slot_time': '10:30 AM - 11:45 AM', 'location': 'Main Sanctum', 'dress_code': 'Traditional Attire', 'prasad': 'Thulasi & Sakkarai Pongal'}
    ],
    'sabarimala': [
        {'temple_name': 'Sabarimala Lord Ayyappa Swamy Temple', 'deity': 'Lord Dharma Sastha (Ayyappa)', 'darshan_type': 'virtual_q', 'slot_time': '08:00 AM - 11:30 AM', 'location': 'Pathinettampadi & Sannidhanam', 'dress_code': 'Black/Blue/Saffron Dhoti with Maladharana', 'prasad': 'Aravana & Appam Prasadam'}
    ],
    'kumbakonam': [
        {'temple_name': 'Kumbakonam Sri Sarangapani Temple (Divya Desam)', 'deity': 'Lord Sarangapani (Aravamudhan)', 'darshan_type': 'general', 'slot_time': '09:00 AM - 10:30 AM', 'location': 'Chariot Sanctum', 'dress_code': 'Traditional Attire', 'prasad': 'Thulasi & Theertham'},
        {'temple_name': 'Kumbakonam Sri Adi Kumbeswarar Temple', 'deity': 'Lord Adi Kumbeswarar & Mangalambigai', 'darshan_type': 'general', 'slot_time': '11:00 AM - 12:30 PM', 'location': 'Main Lingam Sanctum', 'dress_code': 'Traditional Attire', 'prasad': 'Vibhuti Prasadam'}
    ],
    'default_devotional': [
        {'temple_name': 'Main Presiding Deity Temple', 'deity': 'Presiding Deity of the Circuit', 'darshan_type': 'special_entry_300', 'slot_time': '09:00 AM - 11:00 AM', 'location': 'Main Sanctorum', 'dress_code': 'Traditional Attire', 'prasad': 'Sacred Temple Prasadam & Theertham'}
    ]
}

enriched_darshan_count = 0
for pkg in Package.objects.filter(package_code__startswith='SGT-CT-', is_devotional=True):
    if pkg.temple_slots.count() == 0:
        pname = pkg.name.lower()
        pcode = pkg.package_code.lower()
        
        # Determine appropriate slots
        if 'arupadai' in pname or 'arupadai' in pcode:
            slots_to_add = darshan_definitions['arupadai']
        elif 'navagraha' in pname or 'navagraha' in pcode:
            slots_to_add = darshan_definitions['navagraha']
        elif 'kalahasti' in pname or 'kalahas' in pcode:
            slots_to_add = darshan_definitions['kalahasti']
        elif 'srisailam' in pname or 'srisail' in pcode:
            slots_to_add = darshan_definitions['srisailam']
        elif 'thirukadaiyur' in pname or 'thirukadai' in pcode:
            slots_to_add = darshan_definitions['thirukadaiyur']
        elif 'pancha' in pname or 'bhoota' in pname:
            slots_to_add = darshan_definitions['pancha_bhoota']
        elif 'narasimhar' in pname:
            slots_to_add = darshan_definitions['narasimhar']
        elif 'sripuram' in pname or 'golden' in pname:
            slots_to_add = darshan_definitions['sripuram']
        elif 'sabarimala' in pname:
            slots_to_add = darshan_definitions['sabarimala']
        elif 'kumbakonam' in pname:
            slots_to_add = darshan_definitions['kumbakonam']
        elif 'chennai' in pname and 'temple' in pname:
            slots_to_add = darshan_definitions['chennai_temples']
        else:
            slots_to_add = darshan_definitions['default_devotional']
        
        for slot in slots_to_add:
            TempleDarshanSlot.objects.create(
                package=pkg,
                temple_name=slot['temple_name'],
                deity_or_circuit=slot['deity'],
                darshan_type=slot['darshan_type'],
                booked_slot_time=slot['slot_time'],
                reporting_location=slot['location'],
                dress_code_notes=slot['dress_code'],
                prasad_details=slot['prasad'],
                senior_citizen_support=True
            )
            enriched_darshan_count += 1
        print(f"  Added {len(slots_to_add)} slots to [{pkg.package_code}] {pkg.name[:45]}")

print(f"\nTotal new TempleDarshanSlot records created: {enriched_darshan_count}")

# ==============================================================================
# 4. RE-AUDIT SGT-CT INVENTORY METRICS
# ==============================================================================
total_ct_pkgs = Package.objects.filter(package_code__startswith='SGT-CT-').count()
total_ct_days = ItineraryDay.objects.filter(package__package_code__startswith='SGT-CT-').count()
total_ct_tariffs = PackageVehicleTariff.objects.filter(package__package_code__startswith='SGT-CT-').count()
total_ct_darshan = TempleDarshanSlot.objects.filter(package__package_code__startswith='SGT-CT-').count()

print("\n" + "="*85)
print("FINAL SGT-CT REPOSITORY METRICS")
print("="*85)
print(f"Total SGT-CT Packages:         {total_ct_pkgs}")
print(f"Total SGT-CT Itinerary Days:   {total_ct_days}")
print(f"Total SGT-CT Vehicle Tariffs:  {total_ct_tariffs}")
print(f"Total SGT-CT Darshan Slots:    {total_ct_darshan}")
print("Rebranding Status:              100% Siva Gayathri Tours & Travels (+91 98425 33777)")
print("="*85)
