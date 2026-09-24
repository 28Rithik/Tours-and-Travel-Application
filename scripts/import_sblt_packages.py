import os
import sys
import re
from decimal import Decimal

# Setup Django environment
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from packages.models import (
    Package,
    ItineraryDay,
    PackageVehicleTariff,
    TempleDarshanSlot,
)
from core.models import VehicleType

sys.stdout.reconfigure(encoding='utf-8')

print("=" * 80)
print("  SIVA GAYATHRI TOURS & TRAVELS — SBLT PACKAGES IMPORTER")
print("=" * 80)

# Fetch Vehicle Types
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

def clean_rebrand(text):
    if not text:
        return ""
    replacements = [
        (re.compile(r'Sri\s+Bhagiyalakshmi\s+Tours\s*(?:&|and)\s*Travels', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Sri\s+Bhagiyalakshmi\s+Travels', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Sri\s+Bhagiyalakshmi', re.IGNORECASE), 'Siva Gayathri'),
        (re.compile(r'Bhagiyalakshmi', re.IGNORECASE), 'Siva Gayathri'),
        (re.compile(r'SBLT\s+Tours\s*(?:&|and)\s*Travels', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'SBLT\s+Travel\s+Agency', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'SBLT\s+Travels', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'SBLT\s+Tours', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'SBLT', re.IGNORECASE), 'Siva Gayathri'),
        (re.compile(r'tours@sblt\.co\.in', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'sblt\.co\.in', re.IGNORECASE), 'sivagayathritravels.com'),
        (re.compile(r'\+91\s*98650\s*89000'), '+91 98425 33777'),
    ]
    cleaned = text
    for pattern, repl in replacements:
        cleaned = pattern.sub(repl, cleaned)
    return cleaned.strip()

def attach_tariffs(pkg):
    PackageVehicleTariff.objects.filter(package=pkg).delete()
    days = pkg.duration_days
    is_local = (pkg.category == 'local_tour' or days <= 1)

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
            dest_lower = pkg.destination.lower()
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
                interstate_permit_included=True if any(s in dest_lower for s in ['kerala', 'karnataka', 'nepal', 'kashmir', 'maharashtra', 'varanasi', 'andhra']) else False,
            )

# Comprehensive definitions for the 14 SBLT packages
SBLT_PACKAGES = [
    {
        'code': 'SGT-SBLT-ARUPADAI-3D',
        'name': '2 NIGHTS 3 DAYS ARUPADAI VEEDU MURUGAN YATRA FROM CHENNAI',
        'destination': 'Chennai, Tiruthani, Swamimalai, Pazhamudircholai, Tiruparankundram, Tiruchendur, Palani',
        'category': 'devotional',
        'nights': 2, 'days': 3,
        'ap': 6900, 'ep': 4900,
        'is_devotional': True,
        'darshan_info': 'Special entry passes coordinated for all six sacred abodes of Lord Murugan.',
        'days_plan': [
            {'day': 1, 'title': 'Chennai Departure & Tiruthani Darshan to Swamimalai', 'route': 'Chennai to Tiruthani to Swamimalai', 'halt': 'Swamimalai', 'spots': 'Tiruthani Subramanya Swamy Hill Temple (365 steps), Sri Swaminatha Swamy Temple Swamimalai'},
            {'day': 2, 'title': 'Pazhamudircholai, Thirupparankundram & Tiruchendur Seashore', 'route': 'Swamimalai to Madurai to Tiruchendur', 'halt': 'Tiruchendur', 'spots': 'Pazhamudircholai Solaimalai Murugan Temple, Thirupparankundram Rock-cut Cave Temple, Tiruchendur Subramanya Swamy Temple'},
            {'day': 3, 'title': 'Tiruchendur Early Sea Snanam, Palani Winch & Return', 'route': 'Tiruchendur to Palani to Chennai', 'halt': 'Chennai Return', 'spots': 'Tiruchendur Nazhikinaru holy spring, Palani Dhandayuthapani Swamy Hilltop Shrine, Panchamirtham Prasadam Seva'}
        ]
    },
    {
        'code': 'SGT-SBLT-MUKTINATH-8D',
        'name': '7 NIGHTS 8 DAYS MUKTINATH & PASHUPATINATH NEPAL YATRA (FLIGHT INCLUSIVE)',
        'destination': 'Kathmandu, Pokhara, Jomsom, Muktinath (Nepal)',
        'category': 'international',
        'is_intl': True, 'country': 'Nepal', 'flight': True,
        'nights': 7, 'days': 8,
        'ap': 99000, 'ep': 85000,
        'is_devotional': True,
        'darshan_info': 'Pashupatinath Temple evening Ganga Aarti, 108 Sacred Muktidhara Water Spouts Snanam in Muktinath.',
        'days_plan': [
            {'day': 1, 'title': 'Flight to Kathmandu & Pashupatinath Evening Aarti', 'route': 'Chennai to Kathmandu', 'halt': 'Kathmandu', 'spots': 'Tribhuvan International Airport arrival, Hotel check-in, Holy Pashupatinath Temple Bagmati River Ganga Aarti'},
            {'day': 2, 'title': 'Kathmandu Sacred Shrines & Budhanilkantha Sleeping Vishnu', 'route': 'Kathmandu City Tour', 'halt': 'Kathmandu', 'spots': 'Budhanilkantha (Jal Narayan 5m floating stone Vishnu), Guhyeshwari Shaktipeeth Temple, Swayambhunath Stupa'},
            {'day': 3, 'title': 'Kathmandu to Pokhara via Manakamana Wish-Fulfilling Devi', 'route': 'Kathmandu to Pokhara', 'halt': 'Pokhara', 'spots': 'Manakamana Devi Temple via high-speed cable car, Scenic Trisuli river gorge, Pokhara Phewa Lake boating'},
            {'day': 4, 'title': 'Himalayan Flight to Jomsom & Muktinath Temple Darshan', 'route': 'Pokhara to Jomsom to Muktinath', 'halt': 'Jomsom', 'spots': 'Scenic mountain flight over Annapurna & Dhaulagiri peaks, 4x4 Jeep drive to Muktinath (3,710m), 108 sacred water spouts bath & Vishnu Shaligram Darshan'},
            {'day': 5, 'title': 'Jomsom to Pokhara & Valley Sightseeing', 'route': 'Jomsom to Pokhara', 'halt': 'Pokhara', 'spots': 'Return flight to Pokhara, Devi’s Falls, Gupteshwor Mahadev Cave, Bindhyabasini Temple, Pokhara World Peace Pagoda'},
            {'day': 6, 'title': 'Pokhara to Kathmandu Scenic Drive & Cultural Souvenirs', 'route': 'Pokhara to Kathmandu', 'halt': 'Kathmandu', 'spots': 'Scenic highway transit through lush valleys, Thamel handicraft market, Rudraksha & Shaligram shopping'},
            {'day': 7, 'title': 'Patan Durbar Square & Doleshwor Mahadev', 'route': 'Kathmandu Valley Circuit', 'halt': 'Kathmandu', 'spots': 'Patan Durbar Square UNESCO world heritage, Doleshwor Mahadev Temple (sacred head of Kedarnath Lord Shiva)'},
            {'day': 8, 'title': 'Final Blessing & Kathmandu to Chennai Return Flight', 'route': 'Kathmandu to Chennai', 'halt': 'Chennai Return', 'spots': 'Final blessing prayers, Souvenir checkout, Transfer to Tribhuvan Airport for safe return flight'}
        ]
    },
    {
        'code': 'SGT-SBLT-PANCHABHOOTA-2D',
        'name': '1 NIGHT 2 DAYS PANCHA BHOOTA SHIVA STHALAM YATRA FROM CHENNAI',
        'destination': 'Kalahasti, Kanchipuram, Tiruvannamalai, Chidambaram, Trichy',
        'category': 'devotional',
        'nights': 1, 'days': 2,
        'ap': 5500, 'ep': 4200,
        'is_devotional': True,
        'darshan_info': 'All 5 Element Temples: Kalahasti (Air), Kanchi (Earth), Tiruvannamalai (Fire), Chidambaram (Space), Trichy (Water).',
        'days_plan': [
            {'day': 1, 'title': 'Kalahasti (Air) & Kanchipuram (Earth) to Tiruvannamalai (Fire)', 'route': 'Chennai to Kalahasti to Kanchipuram to Tiruvannamalai', 'halt': 'Tiruvannamalai', 'spots': 'Sri Kalahasteeswara Temple (Air Lingam), Kanchipuram Ekambareswarar Temple (Earth Lingam), Tiruvannamalai Arunachaleswarar Temple (Fire Lingam)'},
            {'day': 2, 'title': 'Chidambaram (Space) & Trichy Thiruvanaikaval (Water)', 'route': 'Tiruvannamalai to Chidambaram to Trichy to Chennai', 'halt': 'Chennai Return', 'spots': 'Chidambaram Natarajar Temple & Akasha Rahasyam (Space Lingam), Trichy Jambukeswarar Temple (Water/Appu Lingam)'}
        ]
    },
    {
        'code': 'SGT-SBLT-SABARIMALA-2D',
        'name': '1 NIGHT 2 DAYS SABARIMALA SPEED YATRA FROM CHENNAI',
        'destination': 'Chennai, Nilakkal, Pamba, Sabarimala Sannidhanam',
        'category': 'devotional',
        'nights': 1, 'days': 2,
        'ap': 8500, 'ep': 6800,
        'is_devotional': True,
        'darshan_info': 'Complete Irumudi Kettu coordination, Pamba holy river snanam, 18 Golden Steps climb, Lord Ayyappa Neyyabhishekam.',
        'days_plan': [
            {'day': 1, 'title': 'Chennai Irumudi Kettu & Transit to Nilakkal Base Camp', 'route': 'Chennai to Nilakkal to Pamba', 'halt': 'Pamba/Nilakkal', 'spots': 'Anna Nagar Ayyappan Temple Irumudi preparation, Nilakkal KSRTC shuttle transit, Pamba holy river snanam'},
            {'day': 2, 'title': 'Sabarimala Sannidhanam 18 Steps Ascent & Return', 'route': 'Pamba to Sannidhanam to Chennai', 'halt': 'Chennai Return', 'spots': 'Neeli Mala & Appachimedu trek, 18 Holy Golden Steps climb, Lord Ayyappa Sanctum Darshan & Harivarasanam'}
        ]
    },
    {
        'code': 'SGT-SBLT-NAVAGRAHA-3N2D',
        'name': '3 NIGHTS 2 DAYS NAVAGRAHA 9 CELESTIAL PLANETARY TEMPLES YATRA',
        'destination': 'Kumbakonam, Thanjavur, Thirunallar, Vaitheeswaran Koil, Mayiladuthurai',
        'category': 'devotional',
        'nights': 3, 'days': 2,
        'ap': 5500, 'ep': 4200,
        'is_devotional': True,
        'darshan_info': 'All 9 Navagraha planetary shrines covered systematically in 2 packed days.',
        'days_plan': [
            {'day': 1, 'title': 'Chennai Overnight Transit & 4 Planetary Shrines', 'route': 'Chennai to Kumbakonam', 'halt': 'Mayiladuthurai', 'spots': 'Thingaloor Chandran (Moon), Alangudi Guru (Jupiter), Thirunageswaram Rahu, Suryanar Kovil (Sun), Kanjanur Sukran (Venus)'},
            {'day': 2, 'title': 'Remaining 4 Planetary Shrines, Sani Shingnapur/Thirunallar & Return', 'route': 'Mayiladuthurai to Thirunallar to Chennai', 'halt': 'Chennai Return', 'spots': 'Vaitheeswaran Koil Chevvai (Mars), Thiruvenkadu Budhan (Mercury), Keezhaperumpallam Ketu, Thirunallar Sani (Saturn) Nallaru Snanam'}
        ]
    },
    {
        'code': 'SGT-SBLT-KARNATAKA-PILGRIM-4D',
        'name': '3 NIGHTS 4 DAYS KARNATAKA PILGRIMAGE SACRED SHRINES TOUR',
        'destination': 'Sringeri, Horanadu, Dharmasthala, Kukke Subramanya, Murudeshwar, Kollur, Udupi',
        'category': 'devotional',
        'nights': 3, 'days': 4,
        'ap': 23000, 'ep': 18500,
        'is_devotional': True,
        'darshan_info': 'Adi Shankaracharya Sringeri Sharada Peetham, Kukke Sarpa Samskara, Murudeshwar Arabian Sea Shiva, Udupi Krishna Kanakana Kindi.',
        'days_plan': [
            {'day': 1, 'title': 'Bangalore to Sringeri Sharada Peetham & Horanadu', 'route': 'Bangalore/Chennai to Sringeri to Horanadu', 'halt': 'Horanadu', 'spots': 'Sringeri Sharadamba Temple, Vidyashankara 12 Zodiac Pillars Temple, Horanadu Annapoorneshwari Annadhanam'},
            {'day': 2, 'title': 'Dharmasthala Manjunatha & Kukke Subramanya', 'route': 'Horanadu to Dharmasthala to Kukke', 'halt': 'Kukke Subramanya', 'spots': 'Dharmasthala Manjunatha Swamy Temple, Bahubali Monolith, Kukke Subramanya Kumaradhara holy river snanam'},
            {'day': 3, 'title': 'Murudeshwar 123ft Shiva Statue & Kollur Mookambika', 'route': 'Kukke to Murudeshwar to Kollur', 'halt': 'Kollur', 'spots': 'Murudeshwar Arabian Sea cliff-top Shiva Temple & Raja Gopuram lift, Kollur Mookambika Temple Souparnika holy river'},
            {'day': 4, 'title': 'Udupi Sri Krishna Mutt & Mangalore Return', 'route': 'Kollur to Udupi to Mangalore to Chennai', 'halt': 'Chennai Return', 'spots': 'Udupi Sri Krishna Temple Kanakana Kindi darshan, Mangalore Mangaladevi Temple, Kadri Manjunatha'}
        ]
    },
    {
        'code': 'SGT-SBLT-RAMESWARAM-3D',
        'name': '3 NIGHTS 3 DAYS RAMESWARAM, DHANUSHKODI & MADURAI PILGRIMAGE YATRA',
        'destination': 'Pillayarpatti, Devipattinam, Rameswaram, Dhanushkodi, Uthirakosamangai, Madurai',
        'category': 'devotional',
        'nights': 3, 'days': 3,
        'ap': 6500, 'ep': 4900,
        'is_devotional': True,
        'darshan_info': 'Pillayarpatti Ganesha, 22 Sacred Wells Theertha Snanam Rameswaram, Emerald Nataraja Uthirakosamangai, Madurai Meenakshi.',
        'days_plan': [
            {'day': 1, 'title': 'Pillayarpatti Karpaga Vinayagar & Devipattinam Navapashanam', 'route': 'Chennai to Pillayarpatti to Devipattinam to Rameswaram', 'halt': 'Rameswaram', 'spots': 'Pillayarpatti Karpaga Vinayagar Cave Temple, Devipattinam Navapashanam 9 stone deities in shallow sea water'},
            {'day': 2, 'title': 'Rameswaram 22 Theerthams, Ramanathaswamy & Dhanushkodi Ghost Town', 'route': 'Rameswaram & Dhanushkodi Circuit', 'halt': 'Rameswaram', 'spots': 'Agni Theertham sea bath, 22 Holy Wells Snanam inside Ramanathaswamy Temple, Spatika Lingam Puja, Dhanushkodi Ram Setu Point'},
            {'day': 3, 'title': 'Uthirakosamangai Emerald Nataraja & Madurai Meenakshi Amman', 'route': 'Rameswaram to Uthirakosamangai to Madurai to Chennai', 'halt': 'Chennai Return', 'spots': 'Uthirakosamangai Mangalanathar 3000-year-old single Emerald Natarajar, Madurai Meenakshi Sundareswarar Temple'}
        ]
    },
    {
        'code': 'SGT-SBLT-SABARIMALA-4D',
        'name': '3 NIGHTS 4 DAYS SABARIMALA & PALANI DUAL SACRED YATRA FROM CHENNAI',
        'destination': 'Chennai, Erumeli, Pamba, Sabarimala Sannidhanam, Palani',
        'category': 'devotional',
        'nights': 3, 'days': 4,
        'ap': 8700, 'ep': 6900,
        'is_devotional': True,
        'darshan_info': 'Erumeli Pettai Thullal, Sannidhanam Harivarasanam, Palani Murugan Ropeway Darshan.',
        'days_plan': [
            {'day': 1, 'title': 'Chennai Departure with Irumudi Kettu to Erumeli', 'route': 'Chennai to Erumeli', 'halt': 'Erumeli', 'spots': 'Anna Nagar Ayyappan Temple Irumudi, Erumeli Kochambalam & Sastha Temple, Pettai Thullal tradition'},
            {'day': 2, 'title': 'Pamba River Snanam & Sannidhanam 18 Steps Ascent', 'route': 'Erumeli to Pamba to Sabarimala Sannidhanam', 'halt': 'Sannidhanam', 'spots': 'Holy Pamba River bath, trekking via Appachimedu, 18 Golden Steps climb, Sanctum Sanctorum Lord Ayyappa Darshan'},
            {'day': 3, 'title': 'Morning Harivarasanam, Descent to Pamba & Transit to Palani', 'route': 'Sannidhanam to Pamba to Palani', 'halt': 'Palani', 'spots': 'Malikappuram Devi Temple, descent through Swami Ayyappan Road to Pamba, drive to sacred Murugan abode Palani'},
            {'day': 4, 'title': 'Palani Dhandayuthapani Swamy Hilltop Darshan & Safe Return', 'route': 'Palani to Chennai', 'halt': 'Chennai Return', 'spots': 'Palani Hilltop Winch/Ropeway, Lord Murugan Navapashanam idol darshan, Panchamirtham prasadam, Return to Chennai'}
        ]
    },
    {
        'code': 'SGT-SBLT-SHIRDI-4D',
        'name': '3 NIGHTS 4 DAYS SHIRDI SAI BABA, TRIMBAKESHWAR, SHANI & ELLORA CAVES',
        'destination': 'Nashik, Trimbakeshwar, Shirdi, Shani Shingnapur, Grishneshwar, Ellora, Pandharpur',
        'category': 'devotional',
        'nights': 3, 'days': 4,
        'ap': 26990, 'ep': 22500,
        'flight': True,
        'is_devotional': True,
        'darshan_info': 'Flight to Pune/Mumbai, Trimbakeshwar Jyotirlinga, Shirdi VIP Samadhi Darshan, Grishneshwar Jyotirlinga, Ellora UNESCO Caves.',
        'days_plan': [
            {'day': 1, 'title': 'Flight to Mumbai/Pune, Trimbakeshwar Jyotirlinga & Shirdi Check-in', 'route': 'Chennai to Pune to Nashik to Shirdi', 'halt': 'Shirdi', 'spots': 'Flight transit, Trimbakeshwar Jyotirlinga Kushavarta Kund snanam, Nashik Panchavati, Kalaram Temple, Sita Gufa'},
            {'day': 2, 'title': 'Shirdi Sai Baba VIP Samadhi Darshan & Shani Shingnapur', 'route': 'Shirdi to Shani Shingnapur to Shirdi', 'halt': 'Shirdi', 'spots': 'Shirdi Sai Baba VIP Sheeghra Darshan, Dwarkamai sacred Dhuni, Chavadi, Gurusthan, Shani Shingnapur open-sky tailabhishekam'},
            {'day': 3, 'title': 'Grishneshwar Jyotirlinga & UNESCO Ellora Caves Marvel', 'route': 'Shirdi to Aurangabad / Ellora', 'halt': 'Aurangabad / Shirdi', 'spots': 'Grishneshwar Jyotirlinga (12th Jyotirlinga), UNESCO World Heritage Ellora Rock-cut Caves, Kailasa Temple monolithic wonder'},
            {'day': 4, 'title': 'Pandharpur Vitthal Rukmini Temple & Return Flight', 'route': 'Shirdi to Pandharpur to Pune to Chennai', 'halt': 'Chennai Return', 'spots': 'Holy town Pandharpur Chandrabhaga River snanam, Lord Vitthal & Goddess Rukmini Darshan, Pune Airport flight to Chennai'}
        ]
    },
    {
        'code': 'SGT-SBLT-AHOBILAM-SRISAILAM-5D',
        'name': '4 NIGHTS 5 DAYS SRISAILAM JYOTIRLINGA, AHOBILAM 9 NARASIMHA & MANTRALAYAM',
        'destination': 'Srisailam, Mahanandi, Ahobilam, Mantralayam',
        'category': 'devotional',
        'nights': 4, 'days': 5,
        'ap': 9900, 'ep': 7600,
        'is_devotional': True,
        'darshan_info': 'Mallikarjuna Jyotirlinga & Bhramaramba Shaktipeeth, All 9 Nava Narasimha Shrines of Ahobilam, Raghavendra Swamy Brindavan.',
        'days_plan': [
            {'day': 1, 'title': 'Chennai to Srisailam Mallikarjuna Swamy Jyotirlinga', 'route': 'Chennai to Srisailam', 'halt': 'Srisailam', 'spots': 'Sri Bhramaramba Mallikarjuna Swamy Jyotirlinga (dual Jyotirlinga + Shaktipeeth), Patala Ganga ropeway, Krishna River'},
            {'day': 2, 'title': 'Srisailam Shikharam to Mahanandi Mineral Springs', 'route': 'Srisailam to Mahanandi to Nandyal', 'halt': 'Nandyal', 'spots': 'Shikhareswara Swamy hill view, Mahanandiswara Swamy Temple perpetual natural freshwater spring pool snanam'},
            {'day': 3, 'title': 'Nallamala Hills Ahobilam 9 Narasimha Sacred Shrines Trek', 'route': 'Nandyal to Ahobilam Circuit', 'halt': 'Ahobilam', 'spots': 'Lower Ahobilam (Bhargava, Yogananda, Chatravata) and Upper Ahobilam (Ahobila, Varaha, Malola, Jwala Narasimha where pillar cracked open)'},
            {'day': 4, 'title': 'Ahobilam to Mantralayam Raghavendra Swamy Mutt', 'route': 'Ahobilam to Mantralayam', 'halt': 'Mantralayam', 'spots': 'Sri Raghavendra Swamy Brindavana Moola Darshan, Tungabhadra River snanam, Annadhanam Mahaprasadam'},
            {'day': 5, 'title': 'Panchamukhi Anjaneya Swamy Temple & Safe Return', 'route': 'Mantralayam to Chennai', 'halt': 'Chennai Return', 'spots': 'Panchamukhi Anjaneya Swamy rock cave temple, Final blessing darshan, Return highway travel to Chennai'}
        ]
    },
    {
        'code': 'SGT-SBLT-AMARNATH-9D',
        'name': '8 NIGHTS 9 DAYS AMARNATH YATRA (BALTAL HELICOPTER), GULMARG & VAISHNO DEVI',
        'destination': 'Srinagar, Baltal, Holy Amarnath Cave, Gulmarg, Pahalgam, Katra, Vaishno Devi',
        'category': 'devotional',
        'nights': 8, 'days': 9,
        'ap': 85000, 'ep': 72000,
        'flight': True,
        'is_devotional': True,
        'darshan_info': 'Official Amarnath Yatra Helicopter passes from Baltal to Panjtarni, Holy Ice Shiva Lingam, Mata Vaishno Devi Bhawan.',
        'days_plan': [
            {'day': 1, 'title': 'Flight Chennai to Srinagar & Dal Lake Shikara Ride', 'route': 'Chennai to Srinagar', 'halt': 'Srinagar Deluxe Houseboat', 'spots': 'Flight to Srinagar, Traditional luxury wooden houseboat check-in, Evening romantic Shikara ride on Dal Lake, Floating markets'},
            {'day': 2, 'title': 'Srinagar to Sonmarg Meadow of Gold & Baltal Camp', 'route': 'Srinagar to Sonmarg to Baltal', 'halt': 'Baltal / Sonmarg', 'spots': 'Scenic Sindh river valley drive, Thajiwas Glacier pony ride, Yatra medical check and Baltal camp preparation'},
            {'day': 3, 'title': 'Helicopter Flight to Panjtarni & Holy Amarnath Ice Lingam Darshan', 'route': 'Baltal to Panjtarni to Holy Cave to Baltal', 'halt': 'Sonmarg / Baltal', 'spots': 'VIP Helicopter flight Baltal to Panjtarni, Holy Amarnath Cave (3,888m) sacred Ice Shiva Lingam Darshan & Amar Katha pigeons, Return flight to Baltal'},
            {'day': 4, 'title': 'Sonmarg to Gulmarg High Altitude Gondola Ride', 'route': 'Baltal to Gulmarg', 'halt': 'Gulmarg', 'spots': 'Gulmarg world-highest Gondola Phase 1 (Kongdoori) & Phase 2 (Apharwat Peak 4,390m snowline view), Golf Course'},
            {'day': 5, 'title': 'Gulmarg to Pahalgam Valley of Shepherds', 'route': 'Gulmarg to Pahalgam', 'halt': 'Pahalgam', 'spots': 'Pampore Saffron fields, Avantipur ancient ruins, Lidder River rafting point, Betaab Valley & Aru Valley'},
            {'day': 6, 'title': 'Pahalgam to Katra Foothills of Trikuta Mountains', 'route': 'Pahalgam to Katra', 'halt': 'Katra', 'spots': 'Scenic Jammu-Srinagar highway through Chenani-Nashri Tunnel, Arrival in Katra base camp for Vaishno Devi Yatra registration'},
            {'day': 7, 'title': 'Mata Vaishno Devi Holy Bhawan Darshan', 'route': 'Katra to Bhawan to Katra', 'halt': 'Katra', 'spots': '14km pilgrimage trek / Battery Car / Ropeway to Mata Vaishno Devi Bhawan, Holy Cave darshan of Maha Kali, Maha Lakshmi & Maha Saraswati Pindis, Bhairon Temple'},
            {'day': 8, 'title': 'Katra Rest & Jammu City Historical Temples', 'route': 'Katra to Jammu', 'halt': 'Jammu', 'spots': 'Relaxing Ayurvedic leg massage, Raghunath Temple Jammu, Bahu Fort & Bagh-e-Bahu garden view'},
            {'day': 9, 'title': 'Jammu Airport to Chennai Return Flight', 'route': 'Jammu to Chennai', 'halt': 'Chennai Return', 'spots': 'Dry fruit & Kashmiri saffron shopping, Transfer to Jammu Civil Airport for return flight to Chennai'}
        ]
    },
    {
        'code': 'SGT-SBLT-SHIRDI-2D',
        'name': '1 NIGHT 2 DAYS SHIRDI SAI BABA VIP SHEEGHRA DARSHAN (FLIGHT INCLUSIVE)',
        'destination': 'Shirdi, Dwarkamai, Chavadi, Shani Shingnapur',
        'category': 'devotional',
        'nights': 1, 'days': 2,
        'ap': 17500, 'ep': 14500,
        'flight': True,
        'is_devotional': True,
        'darshan_info': 'Direct flight to Shirdi Airport, VIP Sheeghra Darshan pass, Shani Shingnapur tailabhishekam.',
        'days_plan': [
            {'day': 1, 'title': 'Flight Chennai to Shirdi & VIP Samadhi Darshan', 'route': 'Chennai to Shirdi', 'halt': 'Shirdi', 'spots': 'Morning direct flight to Shirdi Airport, Hotel check-in, VIP Sheeghra Darshan of Sai Baba Samadhi Mandir, Dwarkamai sacred stone & Dhuni, Chavadi, Gurusthan neem tree, Evening Dhoop Aarti'},
            {'day': 2, 'title': 'Early Kakad Aarti, Shani Shingnapur & Return Flight', 'route': 'Shirdi to Shani Shingnapur to Shirdi to Chennai', 'halt': 'Chennai Return', 'spots': 'Morning Kakad Aarti blessing, drive to Shani Shingnapur open-air Shani Dev black stone pillar tailabhishekam, transfer to Shirdi Airport for return flight'}
        ]
    },
    {
        'code': 'SGT-SBLT-GAYA-KASHI-AYODHYA-6D',
        'name': '5 NIGHTS 6 DAYS GAYA, KASHI VISHWANATH, PRAYAGRAJ & AYODHYA RAM MANDIR',
        'destination': 'Gaya, Bodh Gaya, Varanasi, Prayagraj, Ayodhya',
        'category': 'devotional',
        'nights': 5, 'days': 6,
        'ap': 37500, 'ep': 31000,
        'flight': True,
        'is_devotional': True,
        'darshan_info': 'Gaya Vishnupad Pind Daan, Kashi Vishwanath Corridor, Triveni Sangam Snanam, Ayodhya Ram Lalla VIP Darshan.',
        'days_plan': [
            {'day': 1, 'title': 'Flight Chennai to Varanasi & Ganga Maha Aarti Private Boat', 'route': 'Chennai to Varanasi', 'halt': 'Varanasi', 'spots': 'Morning flight to Varanasi, Hotel check-in, Evening private Bajra boat cruise on Holy Ganges river watching majestic Ganga Maha Aarti at Dashashwamedh Ghat'},
            {'day': 2, 'title': 'Kashi Vishwanath Corridor, Annapurna & Sarnath Stupa', 'route': 'Varanasi Sightseeing', 'halt': 'Varanasi', 'spots': 'Subah-e-Banaras, Kashi Vishwanath Golden Temple Darshan via corridor, Annapurna Mandir, Vishalakshi Shaktipeeth, Kaal Bhairav Mandir, Sarnath Dhamek Stupa'},
            {'day': 3, 'title': 'Varanasi to Gaya Pind Daan & Mahabodhi Temple', 'route': 'Varanasi to Gaya to Bodh Gaya', 'halt': 'Bodh Gaya / Varanasi', 'spots': 'Gaya Vishnupad Temple ancestral Pind Daan rituals, Phalgu River holy bath, Bodh Gaya Mahabodhi Temple & sacred Bodhi Tree where Buddha attained enlightenment'},
            {'day': 4, 'title': 'Varanasi to Prayagraj Triveni Sangam Snanam to Ayodhya', 'route': 'Varanasi to Prayagraj to Ayodhya', 'halt': 'Ayodhya', 'spots': 'Prayagraj Triveni Sangam (Ganga-Yamuna-Saraswati) holy snanam by motor boat, Bade Hanumanji reclining temple, Anand Bhavan, Evening drive to sacred Ayodhya'},
            {'day': 5, 'title': 'Ayodhya Sri Ram Janmabhoomi VIP Darshan & Saryu Aarti', 'route': 'Ayodhya Pilgrimage Circuit', 'halt': 'Ayodhya', 'spots': 'Sri Ram Janmabhoomi Mandir VIP Darshan of Ram Lalla, Hanuman Garhi, Kanak Bhavan, Dashrath Mahal, Evening Saryu River Maha Aarti'},
            {'day': 6, 'title': 'Ayodhya / Lucknow Airport Return Flight to Chennai', 'route': 'Ayodhya/Lucknow to Chennai', 'halt': 'Chennai Return', 'spots': 'Morning final prayer blessings, transfer to Ayodhya Maharishi Valmiki Airport / Lucknow Airport for flight to Chennai'}
        ]
    },
    {
        'code': 'SGT-SBLT-YERCAUD-2D',
        'name': '1 NIGHT 2 DAYS YERCAUD JEWEL OF THE SOUTH HILL STATION TOUR',
        'destination': 'Chennai, Salem, Yercaud',
        'category': 'hill_station',
        'nights': 1, 'days': 2,
        'ap': 6000, 'ep': 4500,
        'is_devotional': False,
        'days_plan': [
            {'day': 1, 'title': 'Chennai to Yercaud Ghat Road & Lake Boating', 'route': 'Chennai to Yercaud', 'halt': 'Yercaud', 'spots': 'Scenic 20 hairpin bends drive, Emerald Lake pedal boating, Deer Park, Anna Park, Pagoda Point panoramic sunset view'},
            {'day': 2, 'title': 'Lady’s Seat, Rose Garden & Shevaroy Temple Return', 'route': 'Yercaud to Chennai', 'halt': 'Chennai Return', 'spots': 'Lady’s Seat & Gent’s Seat valley viewpoint, Government Rose Garden, Shevaroy Cave Temple at 5,326 ft, Kiliyur Falls, Return to Chennai'}
        ]
    }
]

def main():
    print(f"Importing {len(SBLT_PACKAGES)} comprehensive packages from SBLT source...")

    # Clear previous SGT-SBLT- records if any
    deleted = Package.objects.filter(package_code__startswith='SGT-SBLT-').delete()
    print(f"Cleared previous SGT-SBLT records: {deleted}")

    imported_count = 0

    for pkg_data in SBLT_PACKAGES:
        code = pkg_data['code']
        name = pkg_data['name']
        dest = pkg_data['destination']
        cat = pkg_data['category']
        nights = pkg_data['nights']
        days = pkg_data['days']
        ap_price = Decimal(str(pkg_data['ap']))
        ep_price = Decimal(str(pkg_data['ep']))
        is_dev = pkg_data.get('is_devotional', False)
        is_flight = pkg_data.get('flight', False)
        is_intl = pkg_data.get('is_intl', False)
        country = pkg_data.get('country', 'India')

        inclusions_text = (
            ("Round-trip flights / Volvo luxury AC transport as per itinerary.\n" if is_flight else "Dedicated AC tourist vehicle with professional chauffeur.\n")
            + "Deluxe hotel accommodation on twin / triple sharing basis.\n"
            + ("100% Satvik Pure Vegetarian South Indian meals (Breakfast, Lunch & Dinner).\n" if is_dev else "Daily breakfast and chef-crafted dinner included.\n")
            + "All fuel charges, interstate permits, highway tolls, and driver allowances.\n"
            + ("Amarnath Yatra helicopter passes and registration.\n" if 'AMARNATH' in code else "")
            + ("Special Entry Darshan tokens / VIP coordination.\n" if is_dev else "")
            + "24x7 Siva Gayathri Tours & Travels emergency support and dispatch."
        )

        exclusions_text = (
            "Monument entrance tickets, optional rides, and camera fees.\n"
            "Personal laundry, phone calls, room service, and extra snacks.\n"
            "Special individual pooja / homam sankalpam fees.\n"
            "Any delay or expense caused by unexpected weather conditions or flight delays."
        )

        terms_text = (
            "50% advance payable upon booking confirmation, balance before journey commences.\n"
            "Traditional Indian pilgrimage dress code is mandatory for sanctum darshan.\n"
            "Siva Gayathri Tours & Travels reserves right to alter route order for passenger safety and crowd management."
        )

        pkg = Package.objects.create(
            package_code=code,
            name=name,
            destination=dest,
            category=cat,
            duration_nights=nights,
            duration_days=days,
            base_price=ap_price,
            price_with_food=ap_price,
            price_without_food=ep_price,
            pricing_type='per_person',
            meal_plan='AP',
            room_sharing_type='twin_sharing',
            min_pax=2 if is_flight else 4,
            is_devotional=is_dev,
            satvik_pure_veg_meals=is_dev,
            senior_citizen_friendly=is_dev,
            temple_dress_code="Mandatory Traditional Dress: Dhoti/Kurta for Men, Saree/Chudidar for Women" if is_dev else "",
            temple_darshan_info=pkg_data.get('darshan_info', ''),
            flight_inclusive=is_flight,
            is_international=is_intl,
            destination_country=country,
            currency_code='INR',
            inclusions=inclusions_text,
            exclusions=exclusions_text,
            terms_and_conditions=terms_text,
            contact_persons_footer="Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131)",
            is_active=True,
        )

        # Attach Itinerary Days
        ItineraryDay.objects.filter(package=pkg).delete()
        for d in pkg_data['days_plan']:
            ItineraryDay.objects.create(
                package=pkg,
                day_number=d['day'],
                title=d['title'],
                route_segment=d.get('route', dest),
                night_stay_location=d.get('halt', dest),
                meals_included="Satvik Breakfast, Lunch & Dinner" if is_dev else "Breakfast & Dinner",
                sightseeing_spots=d['spots'],
                activities=f"Coordinated visits to {d['spots']}."
            )

        # Attach Tariffs
        attach_tariffs(pkg)

        # Attach Darshan Slots if devotional
        if is_dev:
            TempleDarshanSlot.objects.filter(package=pkg).delete()
            for d in pkg_data['days_plan']:
                spots = d['spots']
                t_names = re.findall(r'([A-Za-z0-9\s]+(?:Temple|Mutt|Kovil|Koil|Sannidhi|Amman|Swamy|Darshan|Jyotirlinga|Cave))', spots, re.IGNORECASE)
                for t in t_names[:2]:
                    TempleDarshanSlot.objects.create(
                        package=pkg,
                        temple_name=clean_rebrand(t.strip()),
                        deity_or_circuit=dest,
                        darshan_type='special_entry',
                        reporting_location='Sanctum Main Entrance',
                        dress_code_notes=pkg.temple_dress_code or 'Traditional Dhoti / Saree',
                        senior_citizen_support=True
                    )

        imported_count += 1
        print(f"  [IMPORTED] #{pkg.id} {pkg.package_code}: {pkg.name[:50]}... ({pkg.duration_nights}N/{pkg.duration_days}D | Rs.{pkg.price_with_food:,})")

    print("\n" + "=" * 80)
    print(f"  SUCCESSFULLY IMPORTED {imported_count} PACKAGES FROM SBLT!")
    print(f"  Total Packages in DB:   {Package.objects.count()}")
    print(f"  Total Itinerary Days:   {ItineraryDay.objects.count()}")
    print(f"  Total Vehicle Tariffs:  {PackageVehicleTariff.objects.count()}")
    print("=" * 80)

if __name__ == '__main__':
    main()
