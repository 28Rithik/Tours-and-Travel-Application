"""
Siva Gayathri Tours and Travels — Production Package Catalog Seeder
Seeds:
- 10 Devotional & Pilgrimage Yatra Packages (with Temple Darshan Slots, Satvik Food, Traditional Dress Codes)
- 15 College Industrial Visit (IV) Expeditions (with Factory Liaison, Quad Sharing, DJ Campfires, Jeep Safaris, Dual Pricing AP/EP)
- 5 Corporate Team Offsite & Outbound Packages (with Conference AV, Facilitated Team Games, Executive Twin Sharing)
- 5 Additional Packages (Hill Stations, International Tours, 1-Day Local)

Total: 35 Fully Populated Packages complete with Day-by-Day Itineraries and 5-Tier Fleet Tariffs.
"""

import os
import sys
from decimal import Decimal

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import (
    Package,
    ItineraryDay,
    PackageVehicleTariff,
    TempleDarshanSlot,
    InternationalDocumentChecklist,
)
from core.models import VehicleType

print("=" * 80)
print("  SIVA GAYATHRI TOURS & TRAVELS — MASTER PACKAGE SEEDER")
print("=" * 80)

# 1. Fetch or Verify Vehicle Types
vtypes = list(VehicleType.objects.all())
sedan_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['sedan', 'dzire', 'etios'])), vtypes[0] if vtypes else None)
crysta_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['crysta', 'innova'])), vtypes[1] if len(vtypes) > 1 else sedan_vt)
urbania_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['urbania', 'tempo', '17'])), vtypes[2] if len(vtypes) > 2 else sedan_vt)
bus36_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['36', 'mini', '40'])), vtypes[3] if len(vtypes) > 3 else sedan_vt)
coach54_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['54', 'coach', '52', 'volvo'])), vtypes[4] if len(vtypes) > 4 else sedan_vt)

TARIFF_CONFIGS = [
    (sedan_vt, '4_sedan', 14.0, 500.0, 80, 2200.0),
    (crysta_vt, '7_crysta', 20.0, 600.0, 80, 3500.0),
    (urbania_vt, '17_tt_urbania', 26.0, 800.0, 80, 5500.0),
    (bus36_vt, '36_mini_bus', 35.0, 1000.0, 80, 8500.0),
    (coach54_vt, '54_luxury_coach', 45.0, 1200.0, 80, 12000.0),
]

def attach_tariffs(pkg):
    """Attaches the 5-tier vehicle tariffs to a package."""
    PackageVehicleTariff.objects.filter(package=pkg).delete()
    days = pkg.duration_days
    is_local = (pkg.category == 'local_tour' or days == 1)

    for vt, tier, km_rate, bata, local_km, local_rate in TARIFF_CONFIGS:
        if not vt:
            continue
        if is_local:
            PackageVehicleTariff.objects.create(
                package=pkg,
                vehicle_type=vt,
                seating_tier=tier,
                rate_type='local_1day',
                package_rate=Decimal(str(local_rate)),
                per_day_rate=Decimal(str(local_rate)),
                included_km=local_km,
                extra_km_rate=Decimal(str(km_rate)),
                driver_bata_per_day=Decimal(str(bata)),
                driver_bata_included=True,
                toll_parking_included=True,
                interstate_permit_included=False,
            )
        else:
            per_day = (300 * km_rate) + bata
            pkg_rate = days * per_day
            total_km = days * 300
            PackageVehicleTariff.objects.create(
                package=pkg,
                vehicle_type=vt,
                seating_tier=tier,
                rate_type='outstation_multiday',
                package_rate=Decimal(str(pkg_rate)),
                per_day_rate=Decimal(str(per_day)),
                included_km=total_km,
                extra_km_rate=Decimal(str(km_rate)),
                driver_bata_per_day=Decimal(str(bata)),
                driver_bata_included=True,
                toll_parking_included=True,
                interstate_permit_included=True if 'kerala' in pkg.destination.lower() or 'karnataka' in pkg.destination.lower() else False,
            )

def attach_days(pkg, days_list):
    """Attaches itinerary days to a package."""
    ItineraryDay.objects.filter(package=pkg).delete()
    for day_data in days_list:
        ItineraryDay.objects.create(
            package=pkg,
            day_number=day_data['day'],
            title=day_data['title'],
            route_segment=day_data.get('route', ''),
            night_stay_location=day_data.get('halt', ''),
            meals_included=day_data.get('meals', 'Breakfast, Lunch, Dinner'),
            morning_activity=day_data.get('morning', ''),
            sightseeing_spots=day_data.get('spots', ''),
            evening_night_activity=day_data.get('evening', ''),
            activities=day_data.get('activities', '')
        )

# ==============================================================================
# 1. DEVOTIONAL YATRA PACKAGES (10 Packages)
# ==============================================================================
devotional_packages = [
    {
        'code': 'DEV-ARUPADAI-4N5D',
        'name': '4 NIGHTS 5 DAYS ARUPADAI VEEDU MURUGAN PILGRIMAGE YATRA',
        'destination': 'Palani, Madurai, Tiruchendur, Swamimalai, Thiruthani',
        'category': 'devotional',
        'nights': 4, 'days': 5,
        'ap': 8500, 'ep': 6200, 'base': 8500,
        'meal': 'AP', 'sharing': 'triple_sharing', 'pax': 45,
        'devotional': True, 'satvik': True, 'senior': True,
        'dress': 'Strict Traditional: Dhoti/Kurta for Men, Saree/Chudidar for Women',
        'darshan_info': 'Fast-track Special Entry Darshan tokens configured at all 6 sacred abodes of Lord Murugan.',
        'inclusions': "Coimbatore roundtrip 2x2 luxury pushback AC coach.\nHotel accommodation on triple sharing basis.\n100% Satvik Pure Vegetarian South Indian meals.\nSpecial Entry Darshan passes at major shrines.\nExperienced Spiritual Coordinator from Siva Gayathri Tours.\nWheelchair and battery buggy assistance for senior citizens.",
        'exclusions': "Special archana tickets, personal tonsure fees, and homams.\nPersonal laundry, room service, and personal tips.",
        'terms': "Strict compliance with temple traditional dress code is mandatory.\nDarshan timings are subject to temple crowd and VIP seva protocol.\nPayment: 50% advance on confirmation, 50% prior to departure.",
        'days': [
            {'day': 1, 'title': 'Palani Dhandayuthapani Swamy Darshan & Winch Car Seva', 'route': 'Coimbatore to Palani', 'halt': 'Palani', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Palani Foothills Giri Veedhi, Hilltop Shrine, Winch Car Seva'},
            {'day': 2, 'title': 'Thirupparankundram & Madurai Meenakshi Amman Temple', 'route': 'Palani to Madurai', 'halt': 'Madurai', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Thirupparankundram Cave Temple, Sri Meenakshi Sundareswarar Temple'},
            {'day': 3, 'title': 'Tiruchendur Subramanya Swamy Seashore Temple & Abhishekam', 'route': 'Madurai to Tiruchendur', 'halt': 'Tiruchendur', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Agnitheertham Sea Shore, Nazhikinaru Holy Spring, Shanmuga Vilasam'},
            {'day': 4, 'title': 'Swamimalai Murugan Temple & Thanjavur Brihadeeswarar', 'route': 'Tiruchendur to Kumbakonam', 'halt': 'Kumbakonam', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Swamimalai Hilltop Temple, Thanjavur Big Temple Chola Architecture'},
            {'day': 5, 'title': 'Thiruthani Murugan Temple & Safe Return', 'route': 'Kumbakonam to Thiruthani to Coimbatore', 'halt': 'Home Return', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Thiruthani 365 Steps Hilltop Shrine, Final Blessing Darshan'}
        ]
    },
    {
        'code': 'DEV-NAVAGRAHA-3N4D',
        'name': '3 NIGHTS 4 DAYS NAVAGRAHA 9 CELESTIAL TEMPLES SACRED YATRA',
        'destination': 'Kumbakonam, Thanjavur, Thirunallar, Vaitheeswaran Koil',
        'category': 'devotional',
        'nights': 3, 'days': 4,
        'ap': 7200, 'ep': 5200, 'base': 7200,
        'meal': 'AP', 'sharing': 'twin_sharing', 'pax': 40,
        'devotional': True, 'satvik': True, 'senior': True,
        'dress': 'Traditional South Indian Dhoti / Saree',
        'darshan_info': 'Covers all 9 Navagraha shrines in astrological sequence (Suriyanar, Thingalur, Vaitheeswaran, Thiruvenkadu, Alangudi, Kanjanoor, Thirunallar, Thirunageswaram, Keezhperumpallam).',
        'inclusions': "Pushback coach transport with experienced devotional driver.\nAC hotel accommodation in Kumbakonam on twin sharing.\nPure Satvik vegetarian breakfast, lunch, and dinner.\nNavagraha temple archana and pooja sequence coordination.",
        'exclusions': "Navagraha special dosha parihara homams and individual archana thalis.\nPersonal expenses.",
        'terms': "Astrological temple circuit schedule strictly maintained to cover all 9 shrines.\n50% advance booking confirmation required.",
        'days': [
            {'day': 1, 'title': 'Sooriyanar Koil (Sun) & Thingalur (Moon) Temples', 'route': 'Coimbatore to Kumbakonam', 'halt': 'Kumbakonam', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Thingalur Chandran Temple, Sooriyanar Surya Temple, Kanjanoor Sukran Temple'},
            {'day': 2, 'title': 'Vaitheeswaran Koil (Mars) & Thiruvenkadu (Mercury)', 'route': 'Kumbakonam to Sirkazhi Circuit', 'halt': 'Kumbakonam', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Vaitheeswaran Angarakan Temple, Thiruvenkadu Budhan Temple, Keezhperumpallam Kethu Shrine'},
            {'day': 3, 'title': 'Thirunallar (Saturn) & Alangudi (Jupiter) Shrines', 'route': 'Kumbakonam to Karaikal Circuit', 'halt': 'Kumbakonam', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Thirunallar Saneeswarar Temple Nala Theertham, Alangudi Guru Temple'},
            {'day': 4, 'title': 'Thirunageswaram (Rahu) & Maha Kumbeswarar Temple Return', 'route': 'Kumbakonam to Return', 'halt': 'Home Return', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Thirunageswaram Rahu Milk Abhishekam, Kumbakonam Adi Kumbeswarar Temple'}
        ]
    },
    {
        'code': 'DEV-RAMESHWARAM-4N5D',
        'name': '4 NIGHTS 5 DAYS RAMESHWARAM, DHANUSHKODI, KANYAKUMARI & MADURAI',
        'destination': 'Madurai, Rameshwaram, Dhanushkodi, Kanyakumari',
        'category': 'devotional',
        'nights': 4, 'days': 5,
        'ap': 8900, 'ep': 6600, 'base': 8900,
        'meal': 'AP', 'sharing': 'triple_sharing', 'pax': 45,
        'devotional': True, 'satvik': True, 'senior': True,
        'dress': 'Traditional Pilgrimage Dress Code',
        'darshan_info': 'Holy Snanam in 22 Kundams/Theerthams of Ramanathaswamy Temple, Triveni Sangamam bath in Kanyakumari.',
        'inclusions': "AC Tourist Bus transfer.\nHotel stay in Madurai, Rameshwaram and Kanyakumari.\nAll Satvik South Indian meals.\nSpecial pass for 22 Theertham holy snanam.\nSunrise and sunset ferry boat passes at Kanyakumari.",
        'exclusions': "Personal tonsure charges and sea bathing gear.\nCamera permits.",
        'terms': "22 Theerthams snanam requires dry change of clothes before sanctum entry.\n50% advance upon booking.",
        'days': [
            {'day': 1, 'title': 'Arrival Madurai - Meenakshi Amman Temple & Alagar Kovil', 'route': 'Coimbatore to Madurai', 'halt': 'Madurai', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Madurai Meenakshi Amman Temple, Alagar Kovil Sundararaja Perumal'},
            {'day': 2, 'title': 'Pamban Sea Bridge & Rameshwaram Island Arrival', 'route': 'Madurai to Rameshwaram', 'halt': 'Rameshwaram', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Pamban Ocean Bridge, Agnitheertham Sea Shore, APJ Abdul Kalam Memorial'},
            {'day': 3, 'title': '22 Holy Theerthams Snanam & Dhanushkodi Ocean Border', 'route': 'Rameshwaram to Dhanushkodi', 'halt': 'Rameshwaram', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': '22 Holy Wells Snanam, Ramanathaswamy Sanctum Darshan, Dhanushkodi Ghost Town & Ram Setu Point'},
            {'day': 4, 'title': 'Proceed to Kanyakumari - Triveni Sangamam & Sunset Point', 'route': 'Rameshwaram to Kanyakumari', 'halt': 'Kanyakumari', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Suchindram Thanumalayan Temple, Bhagavathi Amman Temple, Sunset Point'},
            {'day': 5, 'title': 'Kanyakumari Sunrise, Vivekananda Rock Memorial & Return', 'route': 'Kanyakumari to Coimbatore', 'halt': 'Home Return', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Triveni Sangamam Sunrise, Vivekananda Rock Ferry Boating, Thiruvalluvar Statue'}
        ]
    },
    {
        'code': 'DEV-TIRUPATI-2N3D',
        'name': '2 NIGHTS 3 DAYS TIRUPATI BALAJI VIP SEEDHA DARSHAN & KALAHASTI',
        'destination': 'Tirupati, Tirumala, Sri Kalahasti (Andhra Pradesh)',
        'category': 'devotional',
        'nights': 2, 'days': 3,
        'ap': 5900, 'ep': 4400, 'base': 5900,
        'meal': 'AP', 'sharing': 'twin_sharing', 'pax': 45,
        'devotional': True, 'satvik': True, 'senior': True,
        'dress': 'TTD Mandatory Dress: Dhoti/Angavastram for Men, Saree for Women',
        'darshan_info': 'TTD ₹300 Special Entry Seeghra Darshan slot pre-booked + authentic TTD Laddoo prasadam.',
        'inclusions': "Coimbatore to Tirupati AC Coach travel.\nTTD Hill Toll & Permit clearances.\nAC Hotel stay in Tirupati.\nPure Vegetarian Meals.\nPre-booked ₹300 Special Entry Darshan pass.\nTwo authentic TTD Tirupati Laddoos per pilgrim.",
        'exclusions': "Special seva tickets (Kalyanotsavam / Arjitha Seva).\nTonsure / Kalyanakatta offerings.",
        'terms': "Original Aadhaar Card is strictly mandatory for TTD biometric entry.\nReporting time at Vaikuntam Queue Complex must be strictly adhered to.",
        'days': [
            {'day': 1, 'title': 'Coimbatore Departure & Arrival Tirupati Foot Hills', 'route': 'Coimbatore to Tirupati via Salem-Chittoor', 'halt': 'Tirupati', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Scenic highway transit, hotel check-in at Tirupati, evening briefing'},
            {'day': 2, 'title': 'Tirumala Balaji VIP Special Entry Darshan & Padmavathi Temple', 'route': 'Tirupati to Tirumala Ghat Road', 'halt': 'Tirupati', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Tirumala Venkateswara Swamy Sanctum, Akhilandam, Tiruchanoor Padmavathi Ammavari Temple'},
            {'day': 3, 'title': 'Sri Kalahasti Rahu-Ketu Vayu Lingam Temple & Return', 'route': 'Tirupati to Kalahasti to Coimbatore', 'halt': 'Home Return', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Sri Kalahasteeswara Temple (Vayu Sthalam), Swarnamukhi River, Return Journey'}
        ]
    },
    {
        'code': 'DEV-PANCHABHOOTA-3N4D',
        'name': '3 NIGHTS 4 DAYS PANCHA BHOOTA SHIVA TEMPLES PILGRIMAGE YATRA',
        'destination': 'Tiruvannamalai, Chidambaram, Kalahasti, Kanchipuram, Trichy',
        'category': 'devotional',
        'nights': 3, 'days': 4,
        'ap': 7800, 'ep': 5800, 'base': 7800,
        'meal': 'AP', 'sharing': 'triple_sharing', 'pax': 40,
        'devotional': True, 'satvik': True, 'senior': True,
        'dress': 'Traditional Dhoti / Saree',
        'darshan_info': 'Sacred circuit of all 5 Shiva temples representing Earth, Water, Fire, Air, and Space.',
        'inclusions': "Pushback coach transport with devotional tour manager.\nHotel accommodation in Chidambaram, Tiruvannamalai and Kanchipuram.\nSatvik pure vegetarian meals.\nTemple entry passes.",
        'exclusions': "Special abhishekam tickets and personal donations.",
        'terms': "Girivalam walk at Tiruvannamalai is optional; battery buggies arranged for elders.\n50% advance upon booking.",
        'days': [
            {'day': 1, 'title': 'Chidambaram Thillai Nataraja Temple (Space / Akasha Lingam)', 'route': 'Coimbatore to Chidambaram', 'halt': 'Chidambaram', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Chidambaram Golden Roof Temple, Chidambara Rahasyam Darshan, Sivaganga Tank'},
            {'day': 2, 'title': 'Tiruvannamalai Arunachaleswarar Temple (Fire / Agni Lingam)', 'route': 'Chidambaram to Tiruvannamalai', 'halt': 'Tiruvannamalai', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Arunachaleswarar Temple Gopuram, Agni Lingam, Ramana Maharshi Ashram, Girivalam'},
            {'day': 3, 'title': 'Kanchipuram Ekambareswarar Temple (Earth / Prithvi Lingam)', 'route': 'Tiruvannamalai to Kanchipuram', 'halt': 'Kanchipuram', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Ekambareswarar Temple 3500-yr old Mango Tree, Kanchi Kamakshi Amman Temple, Silk Weaving'},
            {'day': 4, 'title': 'Trichy Jambukeswarar Temple (Water / Appu Lingam) & Return', 'route': 'Kanchipuram to Trichy to Coimbatore', 'halt': 'Home Return', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Thiruvanaikaval Jambukeswarar Water Sanctum, Srirangam Temple View, Return'}
        ]
    },
    {
        'code': 'DEV-KERALA-4N5D',
        'name': '4 NIGHTS 5 DAYS KERALA MAHA DIVINE & PADMANABHASWAMY YATRA',
        'destination': 'Guruvayur, Chottanikkara, Sabarimala View / Vaikom, Trivandrum',
        'category': 'devotional',
        'nights': 4, 'days': 5,
        'ap': 8600, 'ep': 6400, 'base': 8600,
        'meal': 'AP', 'sharing': 'triple_sharing', 'pax': 45,
        'devotional': True, 'satvik': True, 'senior': True,
        'dress': 'Kerala Traditional: Mundu (Men - bare chest inside sanctum), Kasavu Saree (Women)',
        'darshan_info': 'Special Nirmalya Darshan at Guruvayur, Guruthi pooja at Chottanikkara, Ananthasayanam darshan at Sree Padmanabhaswamy Temple.',
        'inclusions': "Interstate tourist bus with Kerala border road tax and permits.\nHotel stay in Guruvayur, Cochin and Trivandrum.\nAuthentic Kerala/Tamil Satvik vegetarian meals.\nTemple guide services.",
        'exclusions': "Temple prasad thulis and special archana tickets.\nPersonal locker charges.",
        'terms': "Sree Padmanabhaswamy temple strictly enforces mundu/dhoti dress code without shirt.\nNo leather items or mobile phones allowed inside.",
        'days': [
            {'day': 1, 'title': 'Guruvayur Sri Krishna Temple Darshan & Elephant Camp', 'route': 'Coimbatore to Guruvayur', 'halt': 'Guruvayur', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Guruvayurappan Temple Sanctum, Punnathur Kotta Anakkotta Elephant Sanctuary'},
            {'day': 2, 'title': 'Chottanikkara Bhagavathy Temple - Makam Thozhal & Guruthi', 'route': 'Guruvayur to Ernakulam', 'halt': 'Kochi', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Chottanikkara Kizhukkavu Temple, Evening Powerful Guruthi Pooja Darshan'},
            {'day': 3, 'title': 'Vaikom Mahadeva & Ettumanoor Shiva Temple Circuit', 'route': 'Kochi to Kottayam to Alleppey', 'halt': 'Alleppey', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Vaikom Shiva Temple Annadhanam, Ettumanoor Ezharaponnana Shrine, Ambalapuzha Palpayasam'},
            {'day': 4, 'title': 'Trivandrum Sree Padmanabhaswamy Temple (World Rich Temple)', 'route': 'Alleppey to Thiruvananthapuram', 'halt': 'Trivandrum', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Padmanabhaswamy Temple 3 Doors Ananthasayanam Darshan, Attukal Bhagavathy Temple'},
            {'day': 5, 'title': 'Kovalam Beach Stroll & Safe Return Journey', 'route': 'Trivandrum to Coimbatore', 'halt': 'Home Return', 'meals': 'Satvik Breakfast, Lunch, Dinner', 'spots': 'Kovalam Light House Beach Morning Breeze, Highway Return'}
        ]
    },
    {
        'code': 'DEV-PALANI-2N3D',
        'name': '2 NIGHTS 3 DAYS PALANI & DINDIGUL SACRED MURUGAN YATRA',
        'destination': 'Palani, Dindigul, Sivagiri (Tamil Nadu)',
        'category': 'devotional',
        'nights': 2, 'days': 3,
        'ap': 4200, 'ep': 3100, 'base': 4200,
        'meal': 'AP', 'sharing': 'triple_sharing', 'pax': 45,
        'devotional': True, 'satvik': True, 'senior': True,
        'dress': 'Traditional Dhoti / Saree',
        'darshan_info': 'Fast-track Palani Rope Car / Winch Car tickets and authentic Palani Panchamirtham prasad box.',
        'inclusions': "Coimbatore roundtrip pushback vehicle.\nHill road parking & permit.\nAC Hotel stay in Palani.\nSatvik South Indian pure veg food.\nWinch Car pass.\nPanchamirtham gift pack.",
        'exclusions': "Tonsure charges and abhishekam tickets.",
        'terms': "Winch car operation is subject to temple maintenance schedules.\n50% advance upon booking.",
        'days': [
            {'day': 1, 'title': 'Coimbatore to Palani - Foothills Girivalam & Temple Ascent', 'route': 'Coimbatore to Palani', 'halt': 'Palani', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Palani Giri Veedhi, Padavinayagar Shrine, Winch Car Ascent to Hilltop'},
            {'day': 2, 'title': 'Dhandayuthapani Swamy Special Darshan & Golden Chariot', 'route': 'Palani Hill Circuit', 'halt': 'Palani', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Navapashanam Idol Darshan, Bhogar Samadhi Shrine, Evening Golden Chariot Procession'},
            {'day': 3, 'title': 'Thiru Avinankudi Temple & Return Journey', 'route': 'Palani to Coimbatore', 'halt': 'Home Return', 'meals': 'Breakfast, Lunch', 'spots': 'Thiru Avinankudi Murugan Temple (Foot of the Hill), Return Transit'}
        ]
    },
    {
        'code': 'DEV-MANTRALAYAM-3N4D',
        'name': '3 NIGHTS 4 DAYS MANTRALAYAM & AHOBILAM 9 NARASIMHA SHRINES',
        'destination': 'Mantralayam, Ahobilam, Mahanandi (Andhra Pradesh)',
        'category': 'devotional',
        'nights': 3, 'days': 4,
        'ap': 7900, 'ep': 5900, 'base': 7900,
        'meal': 'AP', 'sharing': 'triple_sharing', 'pax': 40,
        'devotional': True, 'satvik': True, 'senior': False,
        'dress': 'Traditional Indian Dress',
        'darshan_info': 'Guru Raghavendra Swamy Brindavan Moola Seva and Ahobilam 9 Narasimha cave trekking.',
        'inclusions': "Deluxe Tourist Coach transport.\nHotel / Guest House accommodation in Mantralayam & Ahobilam.\nSatvik pure vegetarian meals.\nLocal forest jeep transfers for Ahobilam hill shrines.",
        'exclusions': "Parihara pooja fees and individual trekking porters.",
        'terms': "Ahobilam upper shrines involve mild rocky terrain walk.\n50% advance confirmation required.",
        'days': [
            {'day': 1, 'title': 'Coimbatore to Mantralayam - Tungabhadra River Arrival', 'route': 'Coimbatore to Mantralayam via Bangalore', 'halt': 'Mantralayam', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Tungabhadra River Holy Dip, Sri Raghavendra Swamy Mutt check-in'},
            {'day': 2, 'title': 'Sri Guru Raghavendra Swamy Brindavan Special Darshan', 'route': 'Mantralayam Sacred Complex', 'halt': 'Mantralayam', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Moola Brindavan Darshan, Panchamukhi Anjaneya Temple, Annadhanam'},
            {'day': 3, 'title': 'Proceed to Ahobilam - Nava Narasimha Sacred Kshetram', 'route': 'Mantralayam to Ahobilam', 'halt': 'Ahobilam', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Jwala Narasimha, Ahobila Narasimha, Prahlada Varada Cave Temples'},
            {'day': 4, 'title': 'Mahanandi Temple Freshwater Springs & Return Journey', 'route': 'Ahobilam to Mahanandi to Coimbatore', 'halt': 'Home Return', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Mahanandiswara Temple Crystal Clear Springs, Return Journey'}
        ]
    },
    {
        'code': 'DEV-KASHI-AYODHYA-5N6D',
        'name': '5 NIGHTS 6 DAYS KASHI, PRAYAGRAJ & AYODHYA RAM MANDIR YATRA',
        'destination': 'Varanasi, Prayagraj, Ayodhya (Uttar Pradesh)',
        'category': 'devotional',
        'nights': 5, 'days': 6,
        'ap': 22500, 'ep': 18500, 'base': 22500,
        'meal': 'AP', 'sharing': 'twin_sharing', 'pax': 35,
        'devotional': True, 'satvik': True, 'senior': True,
        'dress': 'Traditional Modest Indian Attire',
        'darshan_info': 'Kashi Vishwanath Jyotirlinga Sparsha Darshan, Ganga Aarti, Triveni Sangam Holy Snanam, Ayodhya Shri Ram Janmabhoomi Mandir Darshan.',
        'inclusions': "Return flight options available / AC Volvo coach in UP.\n3-Star Deluxe Hotel stay in Varanasi & Ayodhya.\nPure Vegetarian North/South Indian meals.\nPrivate boat cruise for Ganga Sunrise Aarti.\nTriveni Sangam private boat & priest assistance.\nAyodhya Ram Mandir VIP queue facilitation.",
        'exclusions': "Pind Daan / Pitru Karma priest dakshina.\nAirline tickets (unless added to package).",
        'terms': "Aadhaar Card strictly mandatory for Ayodhya Ram Janmabhoomi security check.\n50% advance booking required.",
        'days': [
            {'day': 1, 'title': 'Varanasi Arrival - Evening Ganga Aarti at Dashashwamedh Ghat', 'route': 'Arrival Varanasi Airport / Station', 'halt': 'Varanasi', 'meals': 'Lunch, Dinner', 'spots': 'Dashashwamedh Ghat Grand Evening Ganga Aarti from Private Boat'},
            {'day': 2, 'title': 'Kashi Vishwanath Jyotirlinga, Annapurna & Kalbhairav Darshan', 'route': 'Varanasi Sacred Corridor', 'halt': 'Varanasi', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Kashi Vishwanath Corridor, Mata Annapurna Temple, Sankat Mochan, Kalbhairav'},
            {'day': 3, 'title': 'Day Excursion to Prayagraj (Allahabad) - Triveni Sangam', 'route': 'Varanasi to Prayagraj & Back', 'halt': 'Varanasi', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Triveni Sangam Ganga-Yamuna-Saraswati Confluence, Anand Bhavan, Alopi Devi'},
            {'day': 4, 'title': 'Proceed to Ayodhya - Sarayu River Aarti & Hotel Check-in', 'route': 'Varanasi to Ayodhya Highway', 'halt': 'Ayodhya', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Sarayu River Holy Ghats, Evening Sarayu Aarti, Ram Ki Paidi'},
            {'day': 5, 'title': 'Grand Shri Ram Janmabhoomi Mandir & Hanuman Garhi', 'route': 'Ayodhya Temple Complex', 'halt': 'Ayodhya', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Shri Ram Mandir Grand Sanctum, Hanuman Garhi, Kanak Bhavan, Dashrath Mahal'},
            {'day': 6, 'title': 'Return Flight / Train Departure to Coimbatore', 'route': 'Ayodhya / Varanasi Departure', 'halt': 'Home Return', 'meals': 'Breakfast', 'spots': 'Shopping for Banarasi Sarees & departure transit'}
        ]
    },
    {
        'code': 'DEV-SHIRDI-SHANI-4N5D',
        'name': '4 NIGHTS 5 DAYS SHIRDI SAI BABA, SHANI SHINGNAPUR & TRIMBAKESHWAR',
        'destination': 'Shirdi, Shani Shingnapur, Nashik, Trimbakeshwar (Maharashtra)',
        'category': 'devotional',
        'nights': 4, 'days': 5,
        'ap': 9800, 'ep': 7600, 'base': 9800,
        'meal': 'AP', 'sharing': 'twin_sharing', 'pax': 45,
        'devotional': True, 'satvik': True, 'senior': True,
        'dress': 'Traditional Indian Attire',
        'darshan_info': 'Sai Baba Samadhi Mandir VIP Darshan Pass + Trimbakeshwar Jyotirlinga Sparsha Darshan.',
        'inclusions': "AC Deluxe Coach transit with interstate road taxes.\nHotel stay in Shirdi and Nashik on twin sharing.\nPure Vegetarian Meals (South & North Indian).\nShirdi Sai Sansthan VIP Darshan passes.\nShani Shingnapur taila abhishekam facilitation.",
        'exclusions': "Special pooja rituals and personal donations.",
        'terms': "Advance registration required for Sai Baba Aarti passes.\n50% advance upon confirmation.",
        'days': [
            {'day': 1, 'title': 'Coimbatore to Shirdi - Long-Haul Coach / Train Arrival', 'route': 'Coimbatore to Shirdi', 'halt': 'Shirdi', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Shirdi arrival, check-in, evening visit to Dwarkamai & Chavadi'},
            {'day': 2, 'title': 'Shirdi Sai Baba Samadhi Mandir VIP Darshan & Gurusthan', 'route': 'Shirdi Temple Complex', 'halt': 'Shirdi', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Samadhi Mandir Kakad / Madhyan Aarti, Gurusthan Neem Tree, Lendi Baug, Sai Heritage Village'},
            {'day': 3, 'title': 'Shani Shingnapur Village (No Doors) & Proceed to Nashik', 'route': 'Shirdi to Shani Shingnapur to Nashik', 'halt': 'Nashik', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Shani Shingnapur Open-Sky Swayambhu Idol, Panchavati Sita Gufa in Nashik'},
            {'day': 4, 'title': 'Trimbakeshwar Jyotirlinga Temple & Godavari Kushavarta', 'route': 'Nashik to Trimbakeshwar', 'halt': 'Nashik', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Trimbakeshwar Three-Faced Jyotirlinga, Kushavarta Holy Pond, Brahmagiri Hill View'},
            {'day': 5, 'title': 'Return Journey to Coimbatore', 'route': 'Nashik to Coimbatore Return', 'halt': 'Home Return', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Safe highway return transit'}
        ]
    }
]

# ==============================================================================
# 2. COLLEGE INDUSTRIAL VISIT (IV) EXPEDITIONS (15 Packages)
# ==============================================================================
college_iv_packages = [
    {
        'code': 'IV-KERALA-4N5D',
        'name': '4 NIGHTS 5 DAYS KERALA COLLEGE IV (KOCHI-ALLEPPEY-VAGAMON-ATHIRAPPILLY)',
        'destination': 'Kochi, Alleppey, Vagamon, Athirappilly (Kerala)',
        'category': 'college_iv',
        'nights': 4, 'days': 5,
        'ap': 6850, 'ep': 4750, 'base': 6850,
        'meal': 'AP', 'sharing': '4_sharing', 'pax': 50,
        'has_dj': True, 'has_safari': True, 'has_iv': True,
        'inclusions': "Tamilnadu-Kerala 2x2 luxury pushback AC convoy bus.\nAll interstate road permits, toll gates & parking charges.\nAccommodation on 4-sharing basis in verified tourist hotel/resort.\nKochi InfoPark IT Corridor factory clearance liaison.\nAlleppey Houseboat Day Cruise with authentic Kerala buffet.\nVagamon Extreme 4x4 Off-Road Jeep Safari to deep viewpoints.\nHigh-energy DJ Music Party with warm Campfire.\nSiva Gayathri Tour Escort throughout trip.",
        'exclusions': "Damages caused by students to hotel or vehicle property.\nPersonal recreation and shopping.",
        'terms': "Principal permission NOC and student list mandatory prior to departure.\n50% advance on confirmation, balance 50% before coach starts.",
        'days': [
            {'day': 1, 'title': 'Arrival Kochi - InfoPark IT Hub - Marine Drive & Fort Kochi', 'route': 'Campus to Kochi', 'halt': 'Kochi', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'InfoPark IT Corridor, Fort Kochi Beach, Chinese Fishing Nets, Marine Drive Boating'},
            {'day': 2, 'title': 'Proceed Alleppey - Backwater Houseboat Cruise & Beach', 'route': 'Kochi to Alleppey', 'halt': 'Alleppey', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Exclusive Day Houseboat Cruise on Vembanad Lake, Alleppey Beach & Lighthouse'},
            {'day': 3, 'title': 'Proceed Vagamon Hills - Pine Forest & Off-Road Jeep Safari', 'route': 'Alleppey to Vagamon', 'halt': 'Vagamon', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Vagamon Pine Forest, Kurisumala, 4x4 Off-Road Jeep Safari & Resort Campfire DJ'},
            {'day': 4, 'title': 'Athirappilly & Vazhachal Waterfalls - Return Transit', 'route': 'Vagamon to Athirappilly', 'halt': 'Overnight Bus', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Athirappilly Niagara of India Waterfalls, Vazhachal Forest Waterfalls'},
            {'day': 5, 'title': 'Early Morning Safe Campus Arrival', 'route': 'Highway to Campus', 'halt': 'Campus Return', 'meals': 'Morning Refreshment', 'spots': 'Safe campus de-boarding and tour completion'}
        ]
    },
    {
        'code': 'IV-MYSORE-COORG-3N4D',
        'name': '3 NIGHTS 4 DAYS MYSORE, COORG & CHIKMAGALUR NATURE & IV EXPEDITION',
        'destination': 'Mysore, Coorg, Chikmagalur (Karnataka)',
        'category': 'college_iv',
        'nights': 3, 'days': 4,
        'ap': 5700, 'ep': 4200, 'base': 5700,
        'meal': 'AP', 'sharing': '4_sharing', 'pax': 50,
        'has_dj': True, 'has_safari': True, 'has_iv': True,
        'inclusions': "Tamilnadu-Karnataka luxury tourist coach.\n4-sharing hotel/resort stay.\nBuffet breakfast, lunch, and dinner.\nMysore Sandalwood & Silk industrial clearance.\nChikmagalur Mullayanagiri 4x4 Jeep Safari.\nCampfire with DJ Music in Coorg plantation resort.",
        'exclusions': "Camera tickets and personal shopping.",
        'terms': "Student discipline mandatory. 50% advance upon confirmation.",
        'days': [
            {'day': 1, 'title': 'Arrive Mysore - Palace, Sandalwood Industry & Brindavan Gardens', 'route': 'Campus to Mysore', 'halt': 'Mysore', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Mysore Palace, Sandalwood Oil Factory, KRS Dam & Brindavan Garden Musical Fountain'},
            {'day': 2, 'title': 'Proceed Coorg - Golden Temple Bylakuppe & Dubare Elephant Camp', 'route': 'Mysore to Coorg', 'halt': 'Coorg', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Tibetan Monastery, Dubare Elephant Camp, Raja Seat Sunset, Evening Resort DJ Campfire'},
            {'day': 3, 'title': 'Proceed Chikmagalur - Mullayanagiri Peak 4x4 Jeep Safari', 'route': 'Coorg to Chikmagalur', 'halt': 'Chikmagalur', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Highest Peak Mullayanagiri 4x4 Safari, Baba Budangiri, Coffee Estate Walk'},
            {'day': 4, 'title': 'Belur & Halebidu Hoysala Temple Architecture & Return', 'route': 'Chikmagalur to Campus', 'halt': 'Campus Return', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Belur Chennakesava Temple UNESCO Heritage Rock Carvings, Return Transit'}
        ]
    },
    {
        'code': 'IV-BANGALORE-DANDELI-4N5D',
        'name': '4 NIGHTS 5 DAYS BANGALORE TECH & DANDELI WHITE WATER RAFTING IV',
        'destination': 'Bangalore, Dandeli, Hubli (Karnataka)',
        'category': 'college_iv',
        'nights': 4, 'days': 5,
        'ap': 7800, 'ep': 5600, 'base': 7800,
        'meal': 'AP', 'sharing': '4_sharing', 'pax': 45,
        'has_dj': True, 'has_safari': True, 'has_iv': True,
        'inclusions': "Luxury AC Sleeper / Semi-Sleeper Coach.\nResort stay in Dandeli jungle lodge.\nAll buffet meals included.\nIndustrial visit to Bangalore Tech Park / HAL Aerospace.\nDandeli Kali River White Water Rafting with certified life jackets.\nJungle Jeep Safari & Campfire DJ.",
        'exclusions': "Optional extreme adventure rides (Zipline / Kayaking).",
        'terms': "Life jacket mandatory during water rafting. Alcohol strictly prohibited.",
        'days': [
            {'day': 1, 'title': 'Bangalore IT Corridor & HAL Aerospace Museum Industrial Visit', 'route': 'Campus to Bangalore', 'halt': 'Bangalore', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'HAL Aerospace Museum, Electronic City IT Corridor, Visvesvaraya Museum'},
            {'day': 2, 'title': 'Overnight Journey to Dandeli Western Ghats Jungle', 'route': 'Bangalore to Dandeli', 'halt': 'Dandeli Resort', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Scenic Western Ghats forest drive, Jungle eco-resort check-in'},
            {'day': 3, 'title': 'Kali River White Water Rafting & Natural Jacuzzi Bath', 'route': 'Dandeli River Circuit', 'halt': 'Dandeli Resort', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Kali River Rafting, Supa Dam Viewpoint, Crocodile Park, Night Jungle DJ Campfire'},
            {'day': 4, 'title': 'Dandeli Jungle Jeep Safari & Syntheri Rocks Exploration', 'route': 'Dandeli to Hubli', 'halt': 'Overnight Coach', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Wildlife Jungle Safari, 300ft monolithic Syntheri Rocks, Return Transit'},
            {'day': 5, 'title': 'Arrival Back at College Campus', 'route': 'Highway to Campus', 'halt': 'Campus Return', 'meals': 'Morning Breakfast', 'spots': 'Safe campus reporting and dispersal'}
        ]
    },
    {
        'code': 'IV-GOA-COASTAL-4N5D',
        'name': '4 NIGHTS 5 DAYS GOA COASTAL, PORT & MARITIME INDUSTRIAL EXPEDITION',
        'destination': 'Panaji, Calangute, Baga, Mormugao (Goa)',
        'category': 'college_iv',
        'nights': 4, 'days': 5,
        'ap': 8200, 'ep': 5900, 'base': 8200,
        'meal': 'AP', 'sharing': '4_sharing', 'pax': 50,
        'has_dj': True, 'has_safari': False, 'has_iv': True,
        'inclusions': "AC Convoy Bus with Goa border taxes & permits.\nDeluxe hotel stay in North Goa on 4-sharing.\nSouth & North Indian buffet meals.\nMormugao Major Port Trust industrial liaison.\nMandovi River Sunset Cruise with Goan cultural dance.\nPrivate Beachside DJ Night Party.",
        'exclusions': "Personal water sports tickets (Parasailing / Jet Ski).\nClub entry fees.",
        'terms': "Strict faculty curfew rules at night. Swimming in rough sea prohibited.",
        'days': [
            {'day': 1, 'title': 'Campus Departure & Scenic Konkan Western Ghats Transit', 'route': 'Campus to Goa via Hubli', 'halt': 'Overnight Bus', 'meals': 'Dinner', 'spots': 'Night transit through scenic Konkan ghat road'},
            {'day': 2, 'title': 'Arrival Goa - Hotel Check-in & Calangute-Baga Beach Leisure', 'route': 'Goa Border to North Goa', 'halt': 'North Goa Resort', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Resort check-in, Calangute Beach, Baga Beach Walk, Anjuna Viewpoint'},
            {'day': 3, 'title': 'Mormugao Port Trust Industrial Visit & South Goa Heritage', 'route': 'North Goa to South Goa', 'halt': 'North Goa Resort', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Mormugao Port Container Terminal, Basilica of Bom Jesus, Se Cathedral, Mandovi River Sunset Cruise'},
            {'day': 4, 'title': 'Aguada Fort, Chapora Dil Chahta Hai Fort & DJ Party', 'route': 'North Goa Circuit', 'halt': 'North Goa Resort', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Aguada Portuguese Fort & Lighthouse, Chapora Fort, Evening Grand Gala DJ Night Party'},
            {'day': 5, 'title': 'Dudhsagar Waterfalls View & Safe Return Transit', 'route': 'Goa to Campus', 'halt': 'Campus Return', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Dudhsagar Waterfalls highway view, Non-stop return transit to campus'}
        ]
    },
    {
        'code': 'IV-OOTY-WAYANAD-3N4D',
        'name': '3 NIGHTS 4 DAYS OOTY & WAYANAD DUAL-HILL HIGH ALTITUDE IV',
        'destination': 'Ooty (Tamil Nadu), Wayanad (Kerala)',
        'category': 'college_iv',
        'nights': 3, 'days': 4,
        'ap': 5400, 'ep': 3900, 'base': 5400,
        'meal': 'AP', 'sharing': '4_sharing', 'pax': 45,
        'has_dj': True, 'has_safari': True, 'has_iv': True,
        'inclusions': "Luxury tourist vehicle with hill road green tax.\nTea & Spice manufacturing unit industrial visit.\nResort stay in Ooty and Wayanad on 4-sharing.\nAll buffet meals included.\n4x4 Jeep Safari in Wayanad hills.\nDJ campfire party.",
        'exclusions': "Boating tickets and camera fees.",
        'terms': "Warm clothing mandatory for night weather. 50% advance confirmation.",
        'days': [
            {'day': 1, 'title': 'Ascend Nilgiris - Tea Factory Industrial Visit & Ooty Lake', 'route': 'Campus to Ooty', 'halt': 'Ooty', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Highfield Tea & Chocolate Factory industrial process, Botanical Garden, Ooty Lake Boating'},
            {'day': 2, 'title': 'Scenic Gudalur Forest Drive to Wayanad & Banasura Sagar Dam', 'route': 'Ooty to Wayanad', 'halt': 'Wayanad', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Mudumalai Forest Corridor, Banasura Sagar Earthen Dam, Karlad Lake Zipline'},
            {'day': 3, 'title': 'Edakkal Caves Prehistoric Petroglyphs & 4x4 Jeep Safari', 'route': 'Wayanad Circuit', 'halt': 'Wayanad', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Edakkal Caves Neolithic carvings, Chembra Peak 4x4 Jeep Safari, DJ Campfire Night'},
            {'day': 4, 'title': 'Soochipara Waterfalls Trekking & Return to Campus', 'route': 'Wayanad to Calicut to Campus', 'halt': 'Campus Return', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Soochipara 3-tiered Waterfalls, Thamarassery Ghat 9 hairpin bends, Return'}
        ]
    },
    {
        'code': 'IV-HYDERABAD-4N5D',
        'name': '4 NIGHTS 5 DAYS HYDERABAD AEROSPACE, BIOTECH & RAMOJI FILM CITY IV',
        'destination': 'Hyderabad, Secunderabad (Telangana)',
        'category': 'college_iv',
        'nights': 4, 'days': 5,
        'ap': 7900, 'ep': 5700, 'base': 7900,
        'meal': 'AP', 'sharing': '4_sharing', 'pax': 50,
        'has_dj': True, 'has_safari': False, 'has_iv': True,
        'inclusions': "AC Tourist Bus transfer.\n3-Star City Hotel stay on 4-sharing.\nBuffet meals including authentic Hyderabadi Biryani.\nFull-Day Ramoji Film City entrance ticket with shows.\nGenome Valley / T-Hub IT incubator industrial liaison.\nSound & Light show at Golconda Fort.",
        'exclusions': "Ramoji adventure rides outside ticket package.\nPersonal shopping at Charminar.",
        'terms': "Formal attire for industrial research park visits.\n50% advance upon booking.",
        'days': [
            {'day': 1, 'title': 'Campus Departure to the City of Pearls (Hyderabad)', 'route': 'Campus to Hyderabad', 'halt': 'Overnight Bus', 'meals': 'Dinner', 'spots': 'Highway convoy journey, movies & entertainment onboard'},
            {'day': 2, 'title': 'T-Hub IT Incubator Industrial Visit & Golconda Fort', 'route': 'Hyderabad City Circuit', 'halt': 'Hyderabad', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'T-Hub Innovation Park, Golconda Fort Grand Acoustics, Sound & Light Show, Hussain Sagar Laser Show'},
            {'day': 3, 'title': 'Full Day Mega Studio Tour at Ramoji Film City', 'route': 'City to Ramoji Film City', 'halt': 'Hyderabad', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Ramoji Film City Studios, Movie Magic Sets, Action Stunt Show, Wild West Stunt Show'},
            {'day': 4, 'title': 'Salar Jung Museum, Charminar & Pearl Market Shopping', 'route': 'Old Hyderabad Circuit', 'halt': 'Hyderabad', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Salar Jung Museum Clock & Antique Art, Charminar, Mecca Masjid, Laad Bazaar'},
            {'day': 5, 'title': 'Birla Science Museum & Non-Stop Return Journey', 'route': 'Hyderabad to Campus', 'halt': 'Campus Return', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'B.M. Birla Planetarium & Dinosaurium, Return highway transit to campus'}
        ]
    },
    {
        'code': 'IV-KODAI-THEKKADY-3N4D',
        'name': '3 NIGHTS 4 DAYS KODAIKANAL & THEKKADY SPICE & WILDLIFE IV',
        'destination': 'Kodaikanal, Thekkady (Tamil Nadu & Kerala)',
        'category': 'college_iv',
        'nights': 3, 'days': 4,
        'ap': 5200, 'ep': 3800, 'base': 5200,
        'meal': 'AP', 'sharing': '4_sharing', 'pax': 45,
        'has_dj': True, 'has_safari': True, 'has_iv': True,
        'inclusions': "AC Tourist Bus.\nResort stay in Kodai & Thekkady.\nBuffet meals.\nSpice plantation extraction industrial briefing.\nPeriyar Lake boat cruise passes.\nCampfire with DJ Music.",
        'exclusions': "Boating tickets in Kodai Lake and optional elephant rides.",
        'terms': "Strict compliance with forest department wildlife rules.",
        'days': [
            {'day': 1, 'title': 'Ascend Palani Hills to Kodaikanal & Lake Boating', 'route': 'Campus to Kodaikanal', 'halt': 'Kodaikanal', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Silver Cascade Falls, Kodaikanal Star-Shaped Lake Boating, Coaker Walk'},
            {'day': 2, 'title': 'Pillar Rocks, Pine Forest & Proceed to Thekkady', 'route': 'Kodaikanal to Thekkady', 'halt': 'Thekkady', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Pillar Rocks, Guna Caves, Pine Forest, Thekkady check-in, DJ Campfire Night'},
            {'day': 3, 'title': 'Periyar Wildlife Boating & Organic Spice Plantation IV', 'route': 'Thekkady Circuit', 'halt': 'Thekkady', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Periyar Lake Wildlife Boat Safari (Elephant/Bison spotting), Cardamom & Pepper Plantation Tour'},
            {'day': 4, 'title': 'Suruli Waterfalls & Safe Return Journey to Campus', 'route': 'Thekkady to Cumbum to Campus', 'halt': 'Campus Return', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Cumbum Grapes Vineyard industrial visit, Suruli Falls, Return'}
        ]
    },
    {
        'code': 'IV-HOSUR-WONDERLA-2N3D',
        'name': '2 NIGHTS 3 DAYS HOSUR AUTOMOBILE CLUSTER & WONDERLA THEME PARK IV',
        'destination': 'Hosur, Bangalore (Tamil Nadu & Karnataka)',
        'category': 'college_iv',
        'nights': 2, 'days': 3,
        'ap': 4600, 'ep': 3400, 'base': 4600,
        'meal': 'AP', 'sharing': '4_sharing', 'pax': 50,
        'has_dj': True, 'has_safari': False, 'has_iv': True,
        'inclusions': "Pushback coach transport.\nHotel stay on 4-sharing.\nAll meals.\nHosur Automobile / Titan Watch industrial visit clearance.\nWonderla Amusement Park full-day entry pass with water park access.\nEvening DJ dinner.",
        'exclusions': "Fast-track park passes and locker charges.",
        'terms': "Nylon swimwear mandatory for Wonderla water rides.\n50% advance confirmation.",
        'days': [
            {'day': 1, 'title': 'Hosur Automobile Manufacturing Hub Industrial Clearance', 'route': 'Campus to Hosur', 'halt': 'Hosur', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Ashok Leyland / Titan Watch Manufacturing Unit, Precision Tooling Briefing'},
            {'day': 2, 'title': 'Full-Day Thrills at Wonderla Amusement & Water Theme Park', 'route': 'Hosur to Wonderla Bangalore', 'halt': 'Bangalore', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Wonderla Roller Coasters, Recoil, Wave Pool, Rain Disco, Evening DJ Dinner'},
            {'day': 3, 'title': 'Visvesvaraya Industrial & Technological Museum & Return', 'route': 'Bangalore to Campus', 'halt': 'Campus Return', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'VITM Engine Galleries, Space Tech Pavilions, Return Transit'}
        ]
    },
    {
        'code': 'IV-GOKARNA-MURUDESHWAR-4N5D',
        'name': '4 NIGHTS 5 DAYS GOKARNA, MURUDESHWAR & ST. MARY ISLAND COASTAL IV',
        'destination': 'Murudeshwar, Gokarna, Udupi (Karnataka)',
        'category': 'college_iv',
        'nights': 4, 'days': 5,
        'ap': 7400, 'ep': 5300, 'base': 7400,
        'meal': 'AP', 'sharing': '4_sharing', 'pax': 45,
        'has_dj': True, 'has_safari': False, 'has_iv': True,
        'inclusions': "AC Convoy Coach.\nBeachside resort stay on 4-sharing.\nSouth Indian buffet meals.\nSt. Mary's Island ferry boat tickets.\nMurudeshwar 123ft Shiva Temple lift ticket.\nBeachside DJ Campfire Party.",
        'exclusions': "Water sports tickets and personal shopping.",
        'terms': "Sea swimming only permitted within designated lifeguard zones.",
        'days': [
            {'day': 1, 'title': 'Campus Departure to Karnataka Konkan Seashore', 'route': 'Campus to Coastal Karnataka', 'halt': 'Overnight Coach', 'meals': 'Dinner', 'spots': 'Night convoy transit with music and student recreation'},
            {'day': 2, 'title': 'Udupi Malpe Beach Walk & St. Mary Island Hexagonal Rocks', 'route': 'Udupi Coastal Belt', 'halt': 'Udupi', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Malpe Sea Walk, Speedboat to St. Mary Island volcanic hexagonal basalt columns'},
            {'day': 3, 'title': 'Murudeshwar 123ft Shiva Statue & Raja Gopuram Lift View', 'route': 'Udupi to Murudeshwar', 'halt': 'Murudeshwar', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Murudeshwar Temple Surrounded by Arabian Sea, 18-Story Lift View, Beach DJ Campfire'},
            {'day': 4, 'title': 'Gokarna Om Beach, Kudle Beach & Yana Rock Formations', 'route': 'Murudeshwar to Gokarna', 'halt': 'Overnight Coach', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Gokarna Om Beach, Kudle Beach Cliff Walk, Yana Giant Black Rocks Exploration'},
            {'day': 5, 'title': 'Safe Morning Arrival at College Campus', 'route': 'Highway to Campus', 'halt': 'Campus Return', 'meals': 'Morning Breakfast', 'spots': 'Safe campus reporting and tour sign-off'}
        ]
    },
    {
        'code': 'IV-MUNNAR-VAGAMON-3N4D',
        'name': '3 NIGHTS 4 DAYS MUNNAR & VAGAMON HIGH RANGES TEA & SPICE IV',
        'destination': 'Munnar, Vagamon (Kerala)',
        'category': 'college_iv',
        'nights': 3, 'days': 4,
        'ap': 5800, 'ep': 4200, 'base': 5800,
        'meal': 'AP', 'sharing': '4_sharing', 'pax': 45,
        'has_dj': True, 'has_safari': True, 'has_iv': True,
        'inclusions': "Pushback coach with Kerala hill permits.\nResort accommodation on 4-sharing.\nFull board meals (Breakfast, Lunch, Dinner).\nTata Tea Museum & Tea Processing factory visit.\nVagamon 4x4 Off-Road Jeep Safari.\nCampfire with DJ Sound & Lights.",
        'exclusions': "Speed boating in Mattupetty Dam.",
        'terms': "Warm jackets required. 50% advance upon confirmation.",
        'days': [
            {'day': 1, 'title': 'Ascend Western Ghats to Misty Munnar - Cheeyappara Falls', 'route': 'Campus to Munnar', 'halt': 'Munnar', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Cheeyappara Waterfalls, Valara Waterfalls, Munnar Tea Valley View, Hotel Check-in'},
            {'day': 2, 'title': 'Tata Tea Museum Industrial Visit & Mattupetty Echo Point', 'route': 'Munnar Sightseeing Circuit', 'halt': 'Munnar', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Tata Tea Processing Unit, Mattupetty Dam, Echo Point, Kundala Lake, Resort Campfire'},
            {'day': 3, 'title': 'Proceed Vagamon - Pine Forest & Extreme 4x4 Jeep Safari', 'route': 'Munnar to Vagamon', 'halt': 'Vagamon', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Vagamon Pine Valley, Kurisumala Ashram, Suicide Point, 4x4 Off-Road Safari, DJ Night Party'},
            {'day': 4, 'title': 'Illikkal Kallu High Cliff Viewpoint & Return to Campus', 'route': 'Vagamon to Campus', 'halt': 'Campus Return', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Illikkal Kallu 4000ft Cliff View, Return Highway Transit'}
        ]
    },
    {
        'code': 'IV-CHENNAI-PONDY-4N5D',
        'name': '4 NIGHTS 5 DAYS CHENNAI AUTOMOBILE & PONDICHERRY FRENCH COLONY IV',
        'destination': 'Chennai, Mahabalipuram, Pondicherry (Tamil Nadu)',
        'category': 'college_iv',
        'nights': 4, 'days': 5,
        'ap': 6400, 'ep': 4600, 'base': 6400,
        'meal': 'AP', 'sharing': '4_sharing', 'pax': 50,
        'has_dj': True, 'has_safari': False, 'has_iv': True,
        'inclusions': "2x2 Luxury Pushback AC Coach.\nHotel accommodation on 4-sharing.\nBuffet meals.\nChennai Auto Cluster (Hyundai/Ford/Chennai Port) clearance liaison.\nMahabalipuram UNESCO monuments pass.\nPondicherry French Quarter & Promenade Beach visit.\nBeachside DJ party.",
        'exclusions': "Personal water sports at Paradise Beach.",
        'terms': "Faculty supervision required. 50% advance confirmation.",
        'days': [
            {'day': 1, 'title': 'Chennai Automobile Corridor Industrial Clearance Visit', 'route': 'Campus to Chennai', 'halt': 'Chennai', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Automobile Assembly Line Visit, IIT Madras Research Park Industrial Briefing'},
            {'day': 2, 'title': 'Chennai Port Trust & Marina Beach Promenade Stroll', 'route': 'Chennai City Circuit', 'halt': 'Chennai', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Chennai Harbour Overview, Marina Beach (World 2nd Longest Beach), Guindy Snake Park'},
            {'day': 3, 'title': 'Mahabalipuram UNESCO Shore Temple & Proceed Pondicherry', 'route': 'Chennai to Pondicherry via ECR', 'halt': 'Pondicherry', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Mahabalipuram Shore Temple, Arjuna Penance, Pancha Rathas, Butter Ball, Pondy check-in'},
            {'day': 4, 'title': 'Pondicherry French Quarter, Auroville & Paradise Beach DJ', 'route': 'Pondicherry Circuit', 'halt': 'Pondicherry', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Auroville Matrimandir View, French White Town Colony, Paradise Beach Speedboat, Resort DJ Night'},
            {'day': 5, 'title': 'Promenade Beach Sunrise & Safe Return to Campus', 'route': 'Pondicherry to Campus', 'halt': 'Campus Return', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Rock Beach Sunrise Walk, Return Transit'}
        ]
    },
    {
        'code': 'IV-CHIKMAGALUR-UDUPI-3N4D',
        'name': '3 NIGHTS 4 DAYS CHIKMAGALUR PEAKS & UDUPI MALPE BEACH IV',
        'destination': 'Chikmagalur, Kudremukh, Udupi (Karnataka)',
        'category': 'college_iv',
        'nights': 3, 'days': 4,
        'ap': 5600, 'ep': 4100, 'base': 5600,
        'meal': 'AP', 'sharing': '4_sharing', 'pax': 45,
        'has_dj': True, 'has_safari': True, 'has_iv': True,
        'inclusions': "AC Tourist Bus.\nResort stay on 4-sharing.\nBuffet meals.\nMullayanagiri 4x4 Jeep Safari.\nMalpe Beach Sea Walk.\nCampfire with DJ Party.",
        'exclusions': "Personal water sports and room service.",
        'terms': "Student discipline mandatory. 50% advance confirmation.",
        'days': [
            {'day': 1, 'title': 'Campus Departure to Coffee County Chikmagalur', 'route': 'Campus to Chikmagalur', 'halt': 'Chikmagalur', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Scenic Western Ghats drive, check-in, coffee plantation walk'},
            {'day': 2, 'title': 'Mullayanagiri Peak 4x4 Jeep Safari & Jhari Waterfalls', 'route': 'Chikmagalur Peaks Circuit', 'halt': 'Chikmagalur', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Mullayanagiri Highest Peak Safari, Jhari Buttermilk Falls, Evening Resort DJ Campfire'},
            {'day': 3, 'title': 'Descent to Udupi - Malpe Beach Sea Walk & Sunset', 'route': 'Chikmagalur to Udupi', 'halt': 'Udupi', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Agumbe Ghat Viewpoint, Malpe Beach Sea Walk, Evening Beach Games'},
            {'day': 4, 'title': 'St. Mary Island Volcanic Rocks & Return to Campus', 'route': 'Udupi to Campus', 'halt': 'Campus Return', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'St. Mary Island Boat Cruise, Return Highway Transit'}
        ]
    },
    {
        'code': 'IV-NORTH-KERALA-COORG-5N6D',
        'name': '5 NIGHTS 6 DAYS NORTH KERALA & COORG DUAL-STATE MEGA IV',
        'destination': 'Calicut, Bekal, Wayanad, Coorg (Kerala & Karnataka)',
        'category': 'college_iv',
        'nights': 5, 'days': 6,
        'ap': 9200, 'ep': 6800, 'base': 9200,
        'meal': 'AP', 'sharing': '4_sharing', 'pax': 50,
        'has_dj': True, 'has_safari': True, 'has_iv': True,
        'inclusions': "Pushback coach with dual-state interstate permits.\nResort stay in Bekal, Wayanad and Coorg on 4-sharing.\nFull board meals.\nBekal Sea Fort entry.\n4x4 Jeep Safari in Wayanad.\nDJ Campfire Night.",
        'exclusions': "Personal recreational sports.",
        'terms': "50% advance on confirmation. College NOC required.",
        'days': [
            {'day': 1, 'title': 'Calicut Kozhikode Halwa Street & Beypore Dhow Shipyard IV', 'route': 'Campus to Calicut', 'halt': 'Calicut', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Beypore Wooden Dhow Ship Building Yard, Kozhikode Beach'},
            {'day': 2, 'title': 'Bekal Fort Arabian Sea Cliff Walk & Kasaragod Coast', 'route': 'Calicut to Bekal', 'halt': 'Bekal', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Bekal Ocean Fort (Movie Shoot Location), Kappil Beach'},
            {'day': 3, 'title': 'Ascend Wayanad Hills - Banasura Sagar Dam & Zipline', 'route': 'Bekal to Wayanad', 'halt': 'Wayanad', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Banasura Sagar Dam, Karlad Lake Adventure Zipline, Resort Campfire'},
            {'day': 4, 'title': 'Edakkal Caves & Cross Border to Coorg Coffee Country', 'route': 'Wayanad to Coorg', 'halt': 'Coorg', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Edakkal Caves, Kutta Border, Dubare Elephant Camp, Raja Seat'},
            {'day': 5, 'title': 'Bylakuppe Golden Temple & Grand DJ Campfire Night', 'route': 'Coorg Plantation Circuit', 'halt': 'Coorg', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Tibetan Golden Temple, Coffee Roasting Unit, Gala DJ Campfire Night'},
            {'day': 6, 'title': 'Mysore Palace Express Stop & Safe Return to Campus', 'route': 'Coorg to Mysore to Campus', 'halt': 'Campus Return', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Mysore Palace Exterior Photo Stop, Return Transit'}
        ]
    },
    {
        'code': 'IV-HAMPI-JINDAL-4N5D',
        'name': '4 NIGHTS 5 DAYS HAMPI UNESCO RUINS & JINDAL STEEL METALLURGY IV',
        'destination': 'Hampi, Hospet, Bellary (Karnataka)',
        'category': 'college_iv',
        'nights': 4, 'days': 5,
        'ap': 6900, 'ep': 4900, 'base': 6900,
        'meal': 'AP', 'sharing': '4_sharing', 'pax': 45,
        'has_dj': True, 'has_safari': False, 'has_iv': True,
        'inclusions': "AC Tourist Coach.\nHotel stay in Hospet on 4-sharing.\nBuffet meals.\nJSW Steel Toranagallu industrial metallurgy clearance.\nHampi UNESCO ASI Monuments entry passes.\nTungabhadra Dam garden light show.\nDJ Night Party.",
        'exclusions': "Coracle boat ride in Tungabhadra river.",
        'terms': "Safety shoes mandatory for JSW steel plant visit. 50% advance confirmation.",
        'days': [
            {'day': 1, 'title': 'Campus Departure to Vijayanagara Heritage Capital', 'route': 'Campus to Hospet', 'halt': 'Overnight Bus', 'meals': 'Dinner', 'spots': 'Overnight convoy transit through Karnataka heartland'},
            {'day': 2, 'title': 'JSW Steel Toranagallu Mega Industrial Metallurgy Clearance', 'route': 'Hospet to Toranagallu', 'halt': 'Hospet', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'JSW Steel Blast Furnace, Hot Strip Mill, Metallurgical Process Briefing'},
            {'day': 3, 'title': 'Hampi UNESCO World Heritage Monuments & Stone Chariot', 'route': 'Hospet to Hampi', 'halt': 'Hospet', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Vijaya Vittala Temple Stone Chariot, Virupaksha Temple, Lotus Mahal, Elephant Stables'},
            {'day': 4, 'title': 'Matanga Hill Sunrise, Coracle Boating & Tungabhadra Dam', 'route': 'Hampi to Tungabhadra Dam', 'halt': 'Hospet', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Matanga Hill View, Tungabhadra River Coracle Ride, TB Dam Musical Gardens, DJ Night'},
            {'day': 5, 'title': 'Chitradurga Kallina Kote Stone Fort & Return to Campus', 'route': 'Hospet to Chitradurga to Campus', 'halt': 'Campus Return', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Chitradurga 7-Circuits Stone Fort, Return Highway Transit'}
        ]
    },
    {
        'code': 'IV-YERCAUD-SALEM-2N3D',
        'name': '2 NIGHTS 3 DAYS YERCAUD HILLS & SAIL SALEM STEEL PLANT IV',
        'destination': 'Salem, Yercaud (Tamil Nadu)',
        'category': 'college_iv',
        'nights': 2, 'days': 3,
        'ap': 3950, 'ep': 2850, 'base': 3950,
        'meal': 'AP', 'sharing': '4_sharing', 'pax': 50,
        'has_dj': True, 'has_safari': False, 'has_iv': True,
        'inclusions': "Pushback coach transport.\nResort stay in Yercaud on 4-sharing.\nFull board meals.\nSteel Authority of India (SAIL) Salem Steel Plant visit.\nYercaud Lake boating & viewpoint entry.\nCampfire with DJ Music.",
        'exclusions': "Personal recreational orders.",
        'terms': "College NOC required. 50% advance confirmation.",
        'days': [
            {'day': 1, 'title': 'SAIL Salem Steel Plant Industrial Metallurgy Clearance', 'route': 'Campus to Salem', 'halt': 'Salem', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Steel Authority of India Limited (SAIL) Stainless Steel Rolling Mill Process Briefing'},
            {'day': 2, 'title': 'Ascend Shevaroy Hills to Yercaud - Lake Boating & DJ Night', 'route': 'Salem to Yercaud', 'halt': 'Yercaud', 'meals': 'Breakfast, Lunch, Dinner', 'spots': '20 Hairpin Bends Hill Climb, Yercaud Emerald Lake Boating, Anna Park, Evening DJ Campfire'},
            {'day': 3, 'title': 'Lady Seat, Pagoda Point & Safe Return to Campus', 'route': 'Yercaud to Campus', 'halt': 'Campus Return', 'meals': 'Breakfast, Lunch, Dinner', 'spots': 'Lady Seat Telescope View, Pagoda Point, Shevarayan Temple, Return Transit'}
        ]
    }
]

# ==============================================================================
# 3. CORPORATE TEAM OUTBOUND & OFFSITE PACKAGES (5 Packages)
# ==============================================================================
corporate_packages = [
    {
        'code': 'CORP-COORG-2N3D',
        'name': '2 NIGHTS 3 DAYS COORG LUXURY RESORT LEADERSHIP RETREAT & OFFSITE',
        'destination': 'Madikeri, Coorg (Karnataka)',
        'category': 'corporate_offsite',
        'nights': 2, 'days': 3,
        'ap': 9800, 'ep': 7200, 'base': 9800,
        'meal': 'AP', 'sharing': 'twin_sharing', 'pax': 35,
        'has_dj': True, 'has_safari': True, 'has_iv': False,
        'inclusions': "Executive AC Coach transfer ex-Bangalore or Coimbatore.\n4-Star Luxury Coffee Plantation Resort on Twin Sharing.\nFull Board Gourmet Buffet Meals (Breakfast, Executive Lunch, Gala Dinner).\nConference Hall facility with Projector, Sound System & High-Speed Wi-Fi for 4 hours.\nOutdoor Team Building Games with certified professional facilitator.\nEvening DJ Music & Barbeque Campfire Night.",
        'exclusions': "Alcoholic beverages, spa treatments, and personal laundry.",
        'terms': "Corporate Purchase Order (PO) with GSTIN details required. 50% advance upon confirmation.",
        'days': [
            {'day': 1, 'title': 'Executive Coach Arrival Coorg & Evening Icebreaker Mixer', 'route': 'City to Coorg Resort', 'halt': 'Coorg Luxury Resort', 'meals': 'Lunch, Gala Dinner', 'spots': 'Welcome drink, resort check-in, plantation walk, evening cocktail mixer & bonfire'},
            {'day': 2, 'title': 'Strategy Half-Day Conference & Outdoor Team Building Games', 'route': 'Resort Grounds', 'halt': 'Coorg Luxury Resort', 'meals': 'Breakfast, Buffet Lunch, Barbeque Gala Dinner', 'spots': 'Strategy conference, AV presentation, outdoor trust & team challenges, grand DJ Barbeque Night'},
            {'day': 3, 'title': 'Dubare Riverfront Relaxation & Executive Return Transit', 'route': 'Coorg to Return City', 'halt': 'Home Return', 'meals': 'Breakfast, Lunch', 'spots': 'Morning nature trail, Dubare Riverfront visit, checkout and return transit'}
        ]
    },
    {
        'code': 'CORP-KABINI-2N3D',
        'name': '2 NIGHTS 3 DAYS KABINI WILDLIFE JUNGLE LODGE CORPORATE OFFSITE',
        'destination': 'Kabini, Nagarhole (Karnataka)',
        'category': 'corporate_offsite',
        'nights': 2, 'days': 3,
        'ap': 14500, 'ep': 11000, 'base': 14500,
        'meal': 'AP', 'sharing': 'twin_sharing', 'pax': 30,
        'has_dj': True, 'has_safari': True, 'has_iv': False,
        'inclusions': "Dedicated Luxury Coach.\nPremium Riverfront Eco-Resort stay on Twin Sharing.\nAll buffet meals included.\nNagarhole National Park River Boat Safari.\nWildlife Naturalist escort.\nEvening poolside cocktails & campfire acoustic music.",
        'exclusions': "Bar bills and personal room service.",
        'terms': "Wildlife quiet hours strictly respected after 10 PM. Corporate invoice with GST provided.",
        'days': [
            {'day': 1, 'title': 'Arrival Kabini Riverfront Resort & Sunset Boat Cruise', 'route': 'City to Kabini', 'halt': 'Kabini River Lodge', 'meals': 'Lunch, Dinner', 'spots': 'Resort check-in, Kabini river backwaters sunset cruise, evening campfire networking'},
            {'day': 2, 'title': 'Nagarhole Jungle Jeep Safari & Executive Strategy Session', 'route': 'Nagarhole Forest Belt', 'halt': 'Kabini River Lodge', 'meals': 'Breakfast, Lunch, Gala Dinner', 'spots': 'Early morning jungle safari (Leopard/Tiger/Elephant sightings), strategy brainstorming, Gala Dinner'},
            {'day': 3, 'title': 'Coracle River Ride & Executive Departure Transit', 'route': 'Kabini to City', 'halt': 'Home Return', 'meals': 'Breakfast, Lunch', 'spots': 'Morning birdwatching, coracle river ride, return coach transit'}
        ]
    },
    {
        'code': 'CORP-GOA-3N4D',
        'name': '3 NIGHTS 4 DAYS GOA CORPORATE BEACHSIDE SUMMIT & WATER SPORTS',
        'destination': 'South Goa Beach Resort, Panaji (Goa)',
        'category': 'corporate_offsite',
        'nights': 3, 'days': 4,
        'ap': 16800, 'ep': 12500, 'base': 16800,
        'meal': 'AP', 'sharing': 'twin_sharing', 'pax': 40,
        'has_dj': True, 'has_safari': False, 'has_iv': False,
        'inclusions': "Airport pickup & drop in Luxury Coach.\n5-Star Beachside Resort on Twin Sharing.\nFull Board buffet meals.\nHalf-day air-conditioned conference ballroom with LED screen & AV setup.\nPrivate Catamaran Cruise on the Arabian Sea.\nBeach volleyball & customized corporate team challenges.\nGala Dinner with live band & DJ.",
        'exclusions': "Alcohol consumption beyond company package agreement.",
        'terms': "Corporate PO with GSTIN required. 50% advance confirmation.",
        'days': [
            {'day': 1, 'title': 'Airport Welcome, Resort Check-In & Beachside Networking', 'route': 'Goa Airport to 5-Star Resort', 'halt': 'South Goa 5-Star Resort', 'meals': 'Lunch, Gala Dinner', 'spots': 'Traditional Goan welcome, check-in, sundowner beach mixer & dinner'},
            {'day': 2, 'title': 'Annual Strategy Summit & Arabian Sea Catamaran Cruise', 'route': 'Resort Ballroom & Marina', 'halt': 'South Goa 5-Star Resort', 'meals': 'Breakfast, Lunch, Seafood Gala Dinner', 'spots': 'Half-day conference summit, leadership presentations, private sunset catamaran cruise'},
            {'day': 3, 'title': 'Beach Team Olympics & Grand Award Ceremony with DJ', 'route': 'Private Beachfront', 'halt': 'South Goa 5-Star Resort', 'meals': 'Breakfast, Lunch, Gala Dinner', 'spots': 'Facilitated beach team challenges, water sports, formal awards night with DJ dance party'},
            {'day': 4, 'title': 'Morning Yoga, Souvenir Shopping & Departure Flight Drop', 'route': 'Resort to Airport', 'halt': 'Flight Return', 'meals': 'Breakfast', 'spots': 'Morning beach yoga, checkout and luxury coach airport drop'}
        ]
    },
    {
        'code': 'CORP-WAYANAD-2N3D',
        'name': '2 NIGHTS 3 DAYS WAYANAD MISTY VALLEY CORPORATE WELLNESS RETREAT',
        'destination': 'Vythiri, Wayanad (Kerala)',
        'category': 'corporate_offsite',
        'nights': 2, 'days': 3,
        'ap': 8800, 'ep': 6600, 'base': 8800,
        'meal': 'AP', 'sharing': 'twin_sharing', 'pax': 35,
        'has_dj': True, 'has_safari': True, 'has_iv': False,
        'inclusions': "Deluxe AC Coach.\nEco-luxury rainforest resort on Twin Sharing.\nOrganic Kerala & Continental meals.\nTeam bonding facilitator.\nRainforest stream walk & bamboo rafting.\nEvening acoustic campfire.",
        'exclusions': "Personal Ayurvedic massages and laundry.",
        'terms': "Corporate booking terms apply. 50% advance upon confirmation.",
        'days': [
            {'day': 1, 'title': 'Ascend to Rainforest Resort & Evening Wellness Briefing', 'route': 'City to Wayanad', 'halt': 'Wayanad Rainforest Resort', 'meals': 'Lunch, Dinner', 'spots': 'Scenic ghat drive, resort welcome, rainforest nature trail, evening campfire networking'},
            {'day': 2, 'title': 'Team Strategy Brainstorming & Bamboo River Rafting', 'route': 'Resort Grounds & River', 'halt': 'Wayanad Rainforest Resort', 'meals': 'Breakfast, Lunch, Gala Dinner', 'spots': 'Morning open-air strategy session, afternoon bamboo rafting team race, DJ musical night'},
            {'day': 3, 'title': 'Morning Mist Meditation & Return Transit', 'route': 'Wayanad to City', 'halt': 'Home Return', 'meals': 'Breakfast, Lunch', 'spots': 'Sunrise meditation at viewpoint, organic spice buying, return transit'}
        ]
    },
    {
        'code': 'CORP-ANAIKATTI-1N2D',
        'name': '1 NIGHT 2 DAYS ANAIKATTI & SIRUVANI QUICK STRATEGY OFFSITE',
        'destination': 'Anaikatti, Siruvani (Tamil Nadu & Kerala Border)',
        'category': 'corporate_offsite',
        'nights': 1, 'days': 2,
        'ap': 4200, 'ep': 3200, 'base': 4200,
        'meal': 'AP', 'sharing': 'twin_sharing', 'pax': 40,
        'has_dj': True, 'has_safari': False, 'has_iv': False,
        'inclusions': "Coimbatore roundtrip vehicle transfer.\nResort accommodation on Twin Sharing.\nFull board buffet meals.\nConference hall facility with projector & audio setup.\nTeam building activities in resort open lawns.\nPool party & campfire DJ night.",
        'exclusions': "Personal beverages and optional off-road buggy ride.",
        'terms': "100% advance for 1-night corporate retreats. GST invoice provided.",
        'days': [
            {'day': 1, 'title': 'Morning Check-In, Strategy Summit, Poolside Games & DJ', 'route': 'Coimbatore to Anaikatti', 'halt': 'Anaikatti Resort', 'meals': 'Lunch, Gala Dinner', 'spots': 'Check-in, 3-hour strategy conference, team obstacle games, evening pool party & DJ campfire'},
            {'day': 2, 'title': 'Siruvani Nature Stream Walk & Return Transit', 'route': 'Anaikatti to Coimbatore', 'halt': 'Home Return', 'meals': 'Breakfast, Lunch', 'spots': 'Morning birdwatching stream walk, buffet lunch, return to office/city'}
        ]
    }
]

# ==============================================================================
# 4. ADDITIONAL HIGH-VALUE PACKAGES (5 Packages)
# ==============================================================================
additional_packages = [
    {
        'code': 'INTL-DUBAI-4N5D',
        'name': '4 NIGHTS 5 DAYS DUBAI & ABU DHABI DESERT EXTRAVAGANZA (FLIGHT INCLUSIVE)',
        'destination': 'Dubai, Abu Dhabi (United Arab Emirates)',
        'category': 'international',
        'nights': 4, 'days': 5,
        'ap': 58000, 'ep': 49000, 'base': 58000,
        'meal': 'AP', 'sharing': 'twin_sharing', 'pax': 30,
        'has_dj': True, 'has_safari': True, 'has_iv': False,
        'is_intl': True, 'country': 'United Arab Emirates (UAE)', 'curr': 'AED',
        'inclusions': "Return Economy Flight Ex-Coimbatore or Chennai with 20kg baggage.\n4-Star Luxury City Hotel accommodation.\n30 Days Tourist eVisa & Overseas Medical Travel Insurance.\nDaily Indian Buffet Breakfast & Dinners.\nBurj Khalifa At The Top 124th Floor Entry Pass.\nDesert Safari with 4x4 Dune Bashing, Camel Ride, BBQ Gala & Fire Show.\nMarina Dhow Cruise Dinner with live Tanoura dance.\nFull-Day Abu Dhabi Tour covering Sheikh Zayed Grand Mosque.\nDeluxe AC Tourist Coach transfers throughout.",
        'exclusions': "Tourism Dirham Fee (approx AED 15/room/night payable at hotel).\nPersonal shopping and tips.",
        'terms': "Original Passport must have at least 6 months validity from return date.\nClear scanned copy of passport and white-background photo required for visa.",
        'days': [
            {'day': 1, 'title': 'Flight Arrival DXB, 4-Star Hotel Check-In & Marina Dhow Cruise', 'route': 'Flight to Dubai Airport (DXB)', 'halt': 'Dubai 4-Star Hotel', 'meals': 'Buffet Dinner', 'spots': 'Dubai Marina Skyline, Luxury Dhow Cruise with International Buffet & Live Shows'},
            {'day': 2, 'title': 'Dubai City Tour, Burj Khalifa (124th Flr) & Dubai Mall Fountains', 'route': 'Dubai Sightseeing Circuit', 'halt': 'Dubai 4-Star Hotel', 'meals': 'Breakfast, Dinner', 'spots': 'Palm Jumeirah, Burj Al Arab Photo Stop, Burj Khalifa 124th Floor, Dubai Mall Fountain Show'},
            {'day': 3, 'title': '4x4 Desert Safari, Dune Bashing, Camel Ride & BBQ Gala Dinner', 'route': 'Red Dunes Desert Camp', 'halt': 'Dubai 4-Star Hotel', 'meals': 'Breakfast, Desert BBQ Dinner', 'spots': 'Red Dunes 4x4 Dune Bashing, Sandboarding, Henna, Belly Dance, Tanoura, BBQ Buffet'},
            {'day': 4, 'title': 'Abu Dhabi Day Tour - Sheikh Zayed Grand Mosque & Ferrari World', 'route': 'Dubai to Abu Dhabi Corridor', 'halt': 'Dubai 4-Star Hotel', 'meals': 'Breakfast, Dinner', 'spots': 'Sheikh Zayed Grand Mosque, Abu Dhabi Corniche, Emirates Palace, Ferrari World photo stop'},
            {'day': 5, 'title': 'Dubai Frame, Miracle Garden, Gold Souk & Departure Flight', 'route': 'Hotel to DXB Airport', 'halt': 'Flight Return', 'meals': 'Breakfast', 'spots': 'Dubai Frame Glass Bridge, Miracle Garden, Deira Gold Souk Shopping, Departure Transit'}
        ]
    },
    {
        'code': 'INTL-SINGAPORE-MALAYSIA-5N6D',
        'name': '5 NIGHTS 6 DAYS SINGAPORE & MALAYSIA DUAL-COUNTRY WONDER',
        'destination': 'Singapore & Kuala Lumpur, Genting (Malaysia)',
        'category': 'international',
        'nights': 5, 'days': 6,
        'ap': 68500, 'ep': 59000, 'base': 68500,
        'meal': 'AP', 'sharing': 'twin_sharing', 'pax': 30,
        'has_dj': False, 'has_safari': False, 'has_iv': False,
        'is_intl': True, 'country': 'Singapore & Malaysia', 'curr': 'SGD',
        'inclusions': "Return Economy Airfare Ex-Chennai or Bangalore.\nSingapore Tourist Visa & Malaysia eVisa.\n3-Star / 4-Star Hotels (2N Singapore + 3N Malaysia).\nDaily Buffet Breakfast & Dinners at authentic Indian restaurants.\nUniversal Studios Singapore Full-Day Pass.\nSentosa Island Cable Car, Wings of Time.\nBatu Caves & Genting Highlands Cable Car.\nPetronas Twin Towers observation stop.\nAC Coach transfers between Singapore and Kuala Lumpur.",
        'exclusions': "Tourism tax payable directly at hotels.\nPersonal expenses.",
        'terms': "Minimum 6 months passport validity required. 50% advance confirmation.",
        'days': [
            {'day': 1, 'title': 'Flight Arrival Singapore - Night Safari World First Nocturnal Zoo', 'route': 'Flight to Changi Airport', 'halt': 'Singapore Hotel', 'meals': 'Dinner', 'spots': 'Changi Airport Jewel Waterfall, Night Safari Tram Ride & Creatures of the Night Show'},
            {'day': 2, 'title': 'Universal Studios Singapore Movie Thrills & Sentosa Island', 'route': 'Sentosa Island Circuit', 'halt': 'Singapore Hotel', 'meals': 'Breakfast, Dinner', 'spots': 'Universal Studios Transformers 3D, Battlestar Galactica, Sentosa Cable Car, Wings of Time'},
            {'day': 3, 'title': 'Gardens by the Bay & Cross Border Transit to Kuala Lumpur', 'route': 'Singapore to Kuala Lumpur Coach', 'halt': 'Kuala Lumpur Hotel', 'meals': 'Breakfast, Dinner', 'spots': 'Gardens by the Bay Supertree Grove, Flower Dome, Cross-border highway drive to KL'},
            {'day': 4, 'title': 'Batu Caves Murugan Shrine & Genting Highlands Skyway Cable Car', 'route': 'KL to Genting Highlands', 'halt': 'Kuala Lumpur Hotel', 'meals': 'Breakfast, Dinner', 'spots': 'Batu Caves 140ft Golden Murugan Statue, Genting Skyway Cable Car, Casino & Theme Park'},
            {'day': 5, 'title': 'Kuala Lumpur Panoramic City Tour & Petronas Twin Towers', 'route': 'KL City Tour', 'halt': 'Kuala Lumpur Hotel', 'meals': 'Breakfast, Dinner', 'spots': 'Petronas Twin Towers Photo Stop, King Palace, National Monument, Independence Square'},
            {'day': 6, 'title': 'Putrajaya Administrative Capital & Return Flight Departure', 'route': 'KL to KLIA Airport', 'halt': 'Flight Return', 'meals': 'Breakfast', 'spots': 'Putrajaya Pink Mosque, Putra Bridge, Airport Drop for Return Flight'}
        ]
    },
    {
        'code': 'HOL-OOTY-COONOOR-2N3D',
        'name': '2 NIGHTS 3 DAYS OOTY, COONOOR & MUDUMALAI SCENIC GETAWAY',
        'destination': 'Ooty, Coonoor, Mudumalai (Tamil Nadu)',
        'category': 'holiday',
        'nights': 2, 'days': 3,
        'ap': 4600, 'ep': 3200, 'base': 4600,
        'meal': 'MAP', 'sharing': 'twin_sharing', 'pax': 25,
        'has_dj': True, 'has_safari': True, 'has_iv': False,
        'inclusions': "Coimbatore roundtrip private tourist vehicle.\nHill station green tax, parking and toll charges.\nDeluxe resort stay with scenic valley views.\nDaily breakfast and dinner (MAP Plan).\nSightseeing covering viewpoints, tea gardens & boating.\nCampfire evening at resort.",
        'exclusions': "Boating tickets, botanical garden entry passes and camera fees.",
        'terms': "Sightseeing schedule subject to hill weather. 50% advance confirmation.",
        'days': [
            {'day': 1, 'title': 'Ascend Nilgiris - Botanical Gardens, Rose Garden & Ooty Lake Boating', 'route': 'Coimbatore to Ooty via 36 Hairpins', 'halt': 'Ooty Resort', 'meals': 'Breakfast, Dinner', 'spots': 'Government Botanical Garden, Rose Garden, Ooty Lake Boating, Doddabetta Peak'},
            {'day': 2, 'title': 'Coonoor Sims Park, Dolphin Nose, Tea Factory & Campfire', 'route': 'Ooty to Coonoor Circuit', 'halt': 'Ooty Resort', 'meals': 'Breakfast, Dinner', 'spots': 'Sims Park, Dolphin Nose Valley View, Highfield Tea Factory, Resort Bonfire'},
            {'day': 3, 'title': 'Pykara Waterfalls, Mudumalai Tiger Reserve Safari & Return', 'route': 'Ooty to Mudumalai to Coimbatore', 'halt': 'Home Return', 'meals': 'Breakfast, Lunch', 'spots': 'Pykara Falls, Pykara Speed Boating, Mudumalai Tiger Reserve Jeep Safari, Return Transit'}
        ]
    },
    {
        'code': 'HOL-KODAI-2N3D',
        'name': '2 NIGHTS 3 DAYS KODAIKANAL PRINCESS OF HILLS ESCAPE',
        'destination': 'Kodaikanal (Tamil Nadu)',
        'category': 'holiday',
        'nights': 2, 'days': 3,
        'ap': 4400, 'ep': 3100, 'base': 4400,
        'meal': 'MAP', 'sharing': 'twin_sharing', 'pax': 25,
        'has_dj': True, 'has_safari': False, 'has_iv': False,
        'inclusions': "Dedicated private tourist coach.\nDeluxe hotel stay in Kodaikanal on twin sharing.\nDaily breakfast and dinner.\nLocal sightseeing covering lake, waterfalls and viewpoints.\nEvening campfire.",
        'exclusions': "Boating tickets and personal recreation.",
        'terms': "Check-in 12 PM / Check-out 11 AM. 50% advance booking.",
        'days': [
            {'day': 1, 'title': 'Ascend Palani Hills to Misty Kodaikanal & Star Lake Boating', 'route': 'Coimbatore to Kodaikanal', 'halt': 'Kodaikanal Hotel', 'meals': 'Breakfast, Dinner', 'spots': 'Silver Cascade Waterfalls, Kodaikanal Lake Boating, Coaker Walk Sunset'},
            {'day': 2, 'title': 'Pillar Rocks, Guna Caves, Pine Forest & Resort Campfire', 'route': 'Kodaikanal Circuit', 'halt': 'Kodaikanal Hotel', 'meals': 'Breakfast, Dinner', 'spots': 'Pillar Rocks, Guna Caves, Dense Pine Forest, Bryant Park, Evening Warm Campfire'},
            {'day': 3, 'title': 'Kurinji Andavar Temple, Chettiar Park & Return Descent', 'route': 'Kodaikanal to Coimbatore', 'halt': 'Home Return', 'meals': 'Breakfast, Lunch', 'spots': 'Kurinji Andavar Murugan Temple Valley View, Homemade Chocolate Shopping, Return'}
        ]
    },
    {
        'code': 'LOC-COIMBATORE-ISHA-1D',
        'name': '1-DAY COIMBATORE SIGHTSEEING, MARUDHAMALAI & ISHA YOGA TOUR',
        'destination': 'Coimbatore Local, Marudhamalai, Isha Adiyogi',
        'category': 'local_tour',
        'nights': 0, 'days': 1,
        'ap': 2200, 'ep': 1800, 'base': 2200,
        'meal': 'EP', 'sharing': 'twin_sharing', 'pax': 15,
        'has_dj': False, 'has_safari': False, 'has_iv': False,
        'inclusions': "Coimbatore city 8 Hours / 80 KMs dedicated private AC vehicle.\nFuel and chauffeur allowances included.\nAll city toll gates and commercial parking fees.",
        'exclusions': "Extra kilometers beyond 80 km (billed at vehicle tariff rate).\nExtra hours beyond 8 hours.\nTemple entrance tickets & food.",
        'terms': "Garage-to-garage timing and kilometer calculation.",
        'days': [
            {'day': 1, 'title': 'Marudhamalai Temple, GD Car Museum & Isha Yoga Adiyogi Laser Show', 'route': 'Coimbatore City Circuit', 'halt': 'Same Day Return', 'meals': 'On Own', 'spots': 'Marudhamalai Hilltop Murugan Temple, Gedee Car Museum, Perur Pateeswarar Temple, Isha Foundation 112ft Adiyogi Statue & Divya Sound & Light Show'}
        ]
    }
]

ALL_PACKAGE_GROUPS = [
    ("Devotional Yatra (10 Packages)", devotional_packages),
    ("College IV Expeditions (15 Packages)", college_iv_packages),
    ("Corporate Team Offsites (5 Packages)", corporate_packages),
    ("Additional Packages (5 Packages)", additional_packages),
]

seeded_count = 0

for group_title, pkg_list in ALL_PACKAGE_GROUPS:
    print(f"\n---> SEEDING: {group_title}...")
    for data in pkg_list:
        code = data['code']
        pkg, created = Package.objects.get_or_create(
            package_code=code,
            defaults={
                'name': data['name'],
                'destination': data['destination'],
                'category': data['category'],
                'duration_nights': data['nights'],
                'duration_days': len(data['days']),
                'base_price': Decimal(str(data['base'])),
                'price_with_food': Decimal(str(data['ap'])),
                'price_without_food': Decimal(str(data['ep'])),
                'pricing_type': 'per_person' if data['category'] != 'local_tour' else 'vehicle_rate',
                'meal_plan': data['meal'],
                'room_sharing_type': data['sharing'],
                'min_pax': data['pax'],
                'complementary_staff_count': 2 if data['category'] == 'college_iv' else 0,
                'has_campfire_dj': data.get('has_dj', False),
                'has_jeep_safari': data.get('has_safari', False),
                'has_industrial_visit': data.get('has_iv', False),
                'is_devotional': data.get('devotional', False),
                'satvik_pure_veg_meals': data.get('satvik', False),
                'senior_citizen_friendly': data.get('senior', False),
                'temple_dress_code': data.get('dress', ''),
                'temple_darshan_info': data.get('darshan_info', ''),
                'is_international': data.get('is_intl', False),
                'destination_country': data.get('country', ''),
                'currency_code': data.get('curr', 'INR'),
                'flight_inclusive': True if 'FLIGHT' in data['name'] or data.get('is_intl') else False,
                'inclusions': data['inclusions'],
                'exclusions': data['exclusions'],
                'terms_and_conditions': data['terms'],
                'contact_persons_footer': "Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131)",
                'is_active': True,
            }
        )

        if not created:
            # Update existing to ensure full fidelity
            pkg.name = data['name']
            pkg.destination = data['destination']
            pkg.category = data['category']
            pkg.duration_nights = data['nights']
            pkg.duration_days = len(data['days'])
            pkg.base_price = Decimal(str(data['base']))
            pkg.price_with_food = Decimal(str(data['ap']))
            pkg.price_without_food = Decimal(str(data['ep']))
            pkg.meal_plan = data['meal']
            pkg.room_sharing_type = data['sharing']
            pkg.min_pax = data['pax']
            pkg.has_campfire_dj = data.get('has_dj', False)
            pkg.has_jeep_safari = data.get('has_safari', False)
            pkg.has_industrial_visit = data.get('has_iv', False)
            pkg.is_devotional = data.get('devotional', False)
            pkg.satvik_pure_veg_meals = data.get('satvik', False)
            pkg.senior_citizen_friendly = data.get('senior', False)
            pkg.temple_dress_code = data.get('dress', '')
            pkg.temple_darshan_info = data.get('darshan_info', '')
            pkg.is_international = data.get('is_intl', False)
            pkg.destination_country = data.get('country', '')
            pkg.currency_code = data.get('curr', 'INR')
            pkg.flight_inclusive = True if 'FLIGHT' in data['name'] or data.get('is_intl') else False
            pkg.inclusions = data['inclusions']
            pkg.exclusions = data['exclusions']
            pkg.terms_and_conditions = data['terms']
            pkg.save()

        # Attach days and tariffs
        attach_days(pkg, data['days'])
        attach_tariffs(pkg)

        # Attach temple slots if devotional
        if data.get('devotional'):
            TempleDarshanSlot.objects.filter(package=pkg).delete()
            for day_data in data['days']:
                if 'Temple' in day_data['title'] or 'Darshan' in day_data['title']:
                    TempleDarshanSlot.objects.create(
                        package=pkg,
                        temple_name=day_data['title'].split('-')[0].strip(),
                        deity_or_circuit=pkg.destination,
                        darshan_type='special_entry',
                        reporting_location='Temple Main Entrance Gate',
                        dress_code_notes=pkg.temple_dress_code or 'Traditional Dhoti / Saree',
                        senior_citizen_support=True
                    )

        seeded_count += 1
        status_tag = "CREATED" if created else "UPDATED"
        print(f"  [{status_tag}] #{pkg.id} {pkg.package_code}: {pkg.name[:55]}... ({pkg.duration_nights}N/{pkg.duration_days}D | AP: Rs.{pkg.price_with_food} | EP: Rs.{pkg.price_without_food})")

print("\n" + "=" * 80)
print(f"  SUCCESSFULLY SEEDED {seeded_count} PRODUCTION-READY TOUR PACKAGES!")
print(f"  Total Packages in Database: {Package.objects.count()}")
print(f"  Total Itinerary Days in Database: {ItineraryDay.objects.count()}")
print(f"  Total Vehicle Tariffs in Database: {PackageVehicleTariff.objects.count()}")
print("=" * 80)
