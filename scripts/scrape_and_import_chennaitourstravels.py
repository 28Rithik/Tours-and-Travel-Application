import os
import sys
import re
import json
import decimal
import django

sys.path.append('c:/Users/rithi/Documents/Documents Project Intership and Course/Projects/Rag chatbot/Travels Trip Managment Application')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import Package, PackageTemplate, ItineraryDay, PackageVehicleTariff, TempleDarshanSlot
from core.models import VehicleType

sys.stdout.reconfigure(encoding='utf-8')

print("="*80)
print("SIVA GAYATHRI TOURS & TRAVELS — COMPLETE CTT CATALOG BUILDER & INGESTOR")
print("="*80)

# Fetch vehicle types
v_sedan = VehicleType.objects.filter(name__icontains='Sedan').first() or VehicleType.objects.get(id=3)
v_crysta = VehicleType.objects.filter(name__icontains='Crysta').first() or VehicleType.objects.get(id=1)
v_tt = VehicleType.objects.filter(name__icontains='Urbania').first() or VehicleType.objects.filter(name__icontains='Tempo').first() or VehicleType.objects.get(id=4)
v_minibus = VehicleType.objects.filter(name__icontains='36').first() or VehicleType.objects.get(id=13)
v_coach = VehicleType.objects.filter(name__icontains='54').first() or VehicleType.objects.filter(name__icontains='52').first() or VehicleType.objects.get(id=8)

def clean_rebrand(text):
    if not text:
        return ""
    text = re.sub(r'Content on this page requires a newer version of Adobe Flash Player\.?', '', text, flags=re.I)
    text = re.sub(r'HAPPY TIME AHEAD WITH (?:OUR )?TRAVEL AHEAD(?:\s*TOURS)?\.?', 'Happy Journey with Siva Gayathri Tours & Travels!', text, flags=re.I)
    text = re.sub(r'Travel Ahead(?:\s*Tours)?', 'Siva Gayathri Tours & Travels', text, flags=re.I)
    text = re.sub(r'Chennai Tours\s*(?:and|&)?\s*Travels(?:\s*-\s*Direct Tour Operators)?', 'Siva Gayathri Tours & Travels', text, flags=re.I)
    text = re.sub(r'chennaitourstravels\.com', 'sivagayathritravels.com', text, flags=re.I)
    text = re.sub(r'travelahead\.[a-z]+', 'sivagayathritravels.com', text, flags=re.I)
    text = re.sub(r'\+?91[\s-]?[0-9]{10}', '+91 98425 33777', text)
    text = re.sub(r'[a-zA-Z0-9_.+-]+@(?:chennaitourstravels|travelahead)\.[a-zA-Z0-9-.]+', 'booking@sivagayathritravels.com', text, flags=re.I)
    text = re.sub(r'Book This Package', '', text, flags=re.I)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# Master package catalog definition list
packages_data = []

# ==============================================================================
# 1. EX-CHENNAI 1-DAY & OUTSTATION SIGHTSEEING PACKAGES
# ==============================================================================

packages_data.append({
    'code': 'SGT-CTT-001',
    'name': 'Chennai to Tirupati Balaji Special Entry Darshan Package',
    'destination': 'Chennai / Tirupati / Tirumala',
    'category': 'devotional',
    'duration_days': 1,
    'duration_nights': 0,
    'base_price': decimal.Decimal('999.00'),
    'price_with_food': decimal.Decimal('1099.00'),
    'price_without_food': decimal.Decimal('799.00'),
    'is_devotional': True,
    'description': clean_rebrand("""
Siva Gayathri Tours & Travels offers daily confirmed Tirupati Balaji Darshan tour packages from Chennai. Includes confirmed ₹300 Special Entry Darshan (Seeghra Darshan), door pickup and drop, breakfast and lunch, AC vehicle transportation, professional tour guide assistance, and Tirupati laddu prasadam.
"""),
    'itinerary': [
        {
            'day': 1,
            'title': 'Chennai to Tirupati Balaji Darshan & Return',
            'route': 'Chennai to Tirupati to Tirumala and Return (320 km round trip)',
            'activities': 'Early morning 04:30 AM pickup from residence in Chennai. Proceed to Tirupati via Tiruvallur highway. Delicious South Indian breakfast enroute. Arrive in Tirupati, transfer to Alipiri / Tirumala Ghat road. Dedicated tour manager assists through ₹300 Special Entry Darshan queue at Lord Venkateswara Temple. Receive special laddu prasadam. Enjoy pure vegetarian Andhra meals for lunch. Visit Sri Padmavathi Ammavari Temple at Tiruchanur and ISKCON Temple. Evening comfortable return drive to Chennai.',
            'morning': '04:30 AM pickup, breakfast enroute, climb Tirumala hills',
            'sightseeing': 'Tirumala Venkateswara Temple, Tiruchanur Padmavathi Ammavari Temple, ISKCON Temple',
            'evening': 'Evening darshan at Padmavathi Temple, return drive to Chennai, drop at residence',
            'night_stay': 'Same Day Return',
            'meals': 'Breakfast, Andhra Meals Lunch'
        }
    ],
    'darshan_slots': [
        {
            'temple_name': 'Tirumala Sri Venkateswara Swamy Temple',
            'deity': 'Lord Venkateswara (Balaji)',
            'darshan_type': 'special_entry_300',
            'slot_time': '10:30 AM - 12:30 PM',
            'location': 'Vaikuntam Queue Complex 1',
            'dress_code': 'Strict Traditional: Dhoti/Kurta or White Pyjama for Men, Saree or Chudidar with Dupatta for Women',
            'prasad': 'TTD Sacred Laddu Prasadam (2 Laddus per ticket included)',
            'senior_citizen': True
        },
        {
            'temple_name': 'Sri Padmavathi Ammavari Temple (Tiruchanur)',
            'deity': 'Goddess Padmavathi',
            'darshan_type': 'special_entry_300',
            'slot_time': '04:00 PM - 05:30 PM',
            'location': 'Tiruchanur Temple Complex',
            'dress_code': 'Traditional Attire',
            'prasad': 'Goddess Kumkum & Laddu Prasadam',
            'senior_citizen': True
        }
    ]
})

packages_data.append({
    'code': 'SGT-CTT-002',
    'name': 'Chennai to Mahabalipuram UNESCO Heritage & Beach Day Tour',
    'destination': 'Chennai / Mahabalipuram (Mamallapuram)',
    'category': 'local_tour',
    'duration_days': 1,
    'duration_nights': 0,
    'base_price': decimal.Decimal('399.00'),
    'price_with_food': decimal.Decimal('799.00'),
    'price_without_food': decimal.Decimal('399.00'),
    'is_devotional': False,
    'description': clean_rebrand("""
Discover the ancient 7th-century Pallava architectural wonders of Mahabalipuram on a leisurely 1-day guided road excursion from Chennai via East Coast Road. Features the Shore Temple, Pancha Rathas monolithic rock shrines, Arjuna Penance, Krishna Butter Ball, and Tiger Cave.
"""),
    'itinerary': [
        {
            'day': 1,
            'title': 'Chennai to Mahabalipuram Heritage Exploration',
            'route': 'Chennai to Mahabalipuram via Scenic ECR (120 km round trip)',
            'activities': 'Morning 08:00 AM pickup from Chennai residence or hotel. Scenic drive along the East Coast Road with Bay of Bengal vistas. Visit Tiger Cave rock sanctuary in Saluvankuppam. Arrive in Mahabalipuram and explore the 7th-century UNESCO World Heritage Shore Temple. Marvel at Arjuna Penance, the world’s largest open-air bas-relief. Inspect Krishna’s miraculous Butter Ball balancing on a 45-degree slope. Visit the monolithic Pancha Rathas (Five Chariots). Lunch at seaside restaurant. Leisure stroll along the beach and stone sculpting workshops. Evening return to Chennai.',
            'morning': '08:00 AM pickup, scenic drive via ECR, Tiger Cave visit',
            'sightseeing': 'Shore Temple, Pancha Rathas, Arjuna Penance, Krishna Butter Ball, Mahabalipuram Lighthouse, Tiger Cave',
            'evening': 'Beach walk, handicraft shopping, return drive to Chennai by 07:00 PM',
            'night_stay': 'Same Day Return',
            'meals': 'Buffet Lunch'
        }
    ]
})

packages_data.append({
    'code': 'SGT-CTT-003',
    'name': 'Chennai to Kanchipuram Ancient Silk & Temple City Day Tour',
    'destination': 'Chennai / Kanchipuram',
    'category': 'devotional',
    'duration_days': 1,
    'duration_nights': 0,
    'base_price': decimal.Decimal('350.00'),
    'price_with_food': decimal.Decimal('650.00'),
    'price_without_food': decimal.Decimal('350.00'),
    'is_devotional': True,
    'description': clean_rebrand("""
Explore the City of Thousand Temples and world-renowned Kanchipuram Silk weaving heritage. Visit Ekambareswarar Temple (Earth Stalam of Pancha Bhoota), Kailasanathar Temple, Kamakshi Amman Shakthi Peetham, and Varadharaja Perumal Divya Desam.
"""),
    'itinerary': [
        {
            'day': 1,
            'title': 'Chennai to Kanchipuram Temple Circuit & Silk Weaving',
            'route': 'Chennai to Kanchipuram (150 km round trip)',
            'activities': 'Morning 07:30 AM departure from Chennai. Arrive in Kanchipuram. Darshan at the monumental Ekambareswarar Temple featuring a 59-meter Raja Gopuram and 3,500-year-old mango tree representing the Earth element. Visit Kamakshi Amman Temple, one of the foremost 51 Shakti Peethas. Savor traditional South Indian vegetarian lunch. Visit Varadharaja Perumal Temple with its 100-pillar stone hall and sacred gold/silver lizard engravings. Visit master handloom silk weavers to observe pure mulberry silk and gold zari craftsmanship. Evening return to Chennai.',
            'morning': '07:30 AM pickup, Ekambareswarar and Kailasanathar temple darshan',
            'sightseeing': 'Ekambareswarar Temple, Kamakshi Amman Temple, Varadharaja Perumal Temple, Kailasanathar Temple, Silk Weaving Centers',
            'evening': 'Silk saree shopping at master weavers, return drive to Chennai by 08:00 PM',
            'night_stay': 'Same Day Return',
            'meals': 'Vegetarian Meals'
        }
    ],
    'darshan_slots': [
        {
            'temple_name': 'Kanchipuram Kamakshi Amman Temple',
            'deity': 'Goddess Kamakshi (Shakti Peetham)',
            'darshan_type': 'special_entry_300',
            'slot_time': '10:00 AM - 11:30 AM',
            'location': 'Inner Sannidhi',
            'dress_code': 'Traditional Indian Dress',
            'prasad': 'Kumkum & Sakkarai Pongal Prasadam',
            'senior_citizen': True
        },
        {
            'temple_name': 'Ekambareswarar Temple (Prithvi / Earth Stalam)',
            'deity': 'Lord Shiva (Ekambareswarar)',
            'darshan_type': 'general',
            'slot_time': '11:30 AM - 12:30 PM',
            'location': 'Prithvi Lingam Sanctum',
            'dress_code': 'Traditional Attire',
            'prasad': 'Vibhuti Prasadam',
            'senior_citizen': True
        }
    ]
})

packages_data.append({
    'code': 'SGT-CTT-004',
    'name': 'Chennai to Pondicherry French Riviera & Auroville Day Tour',
    'destination': 'Chennai / Pondicherry',
    'category': 'holiday',
    'duration_days': 1,
    'duration_nights': 0,
    'base_price': decimal.Decimal('699.00'),
    'price_with_food': decimal.Decimal('1199.00'),
    'price_without_food': decimal.Decimal('699.00'),
    'is_devotional': False,
    'description': clean_rebrand("""
Experience the charming French colonial ambiance of Pondicherry and the universal township of Auroville on a scenic coastal day tour from Chennai. Includes Auroville Matrimandir viewpoint, Sri Aurobindo Ashram, French White Town, Promenade Beach, and French cafes.
"""),
    'itinerary': [
        {
            'day': 1,
            'title': 'Chennai to Pondicherry Day Excursion',
            'route': 'Chennai to Pondicherry via ECR (320 km round trip)',
            'activities': 'Morning 06:30 AM departure from Chennai along East Coast Road. Stop at Auroville Visitor Centre and walk through the green peace zone to view the golden Matrimandir sphere. Drive into Pondicherry town. Visit Sri Aurobindo Ashram and Manakula Vinayagar Temple with its famous temple elephant blessings. Enjoy lunch at a French heritage cafe in White Town. Explore colorful colonial streets, yellow villas, Goubert Avenue Promenade, and the French War Memorial. Evening return to Chennai.',
            'morning': '06:30 AM departure, breakfast enroute, Auroville Matrimandir visit',
            'sightseeing': 'Auroville Matrimandir, Sri Aurobindo Ashram, French White Town, Manakula Vinayagar Temple, Promenade Beach',
            'evening': 'Promenade beach stroll, French bakery refreshments, return drive to Chennai by 09:30 PM',
            'night_stay': 'Same Day Return',
            'meals': 'Lunch at Heritage Cafe'
        }
    ]
})

packages_data.append({
    'code': 'SGT-CTT-005',
    'name': 'Chennai to Vellore Sripuram Golden Temple & Fort Day Tour',
    'destination': 'Chennai / Vellore',
    'category': 'devotional',
    'duration_days': 1,
    'duration_nights': 0,
    'base_price': decimal.Decimal('390.00'),
    'price_with_food': decimal.Decimal('750.00'),
    'price_without_food': decimal.Decimal('390.00'),
    'is_devotional': True,
    'description': clean_rebrand("""
A spiritual day trip to the spectacular Sripuram Golden Temple covered in 1,500 kg of pure gold foil, situated at the foot of green hills in Malaikodi, Vellore. Also covers the historic 16th-century granite Vellore Fort and Jalakandeswarar Temple.
"""),
    'itinerary': [
        {
            'day': 1,
            'title': 'Chennai to Vellore Golden Temple & Jalakandeswarar',
            'route': 'Chennai to Vellore (280 km round trip)',
            'activities': 'Morning 07:00 AM departure from Chennai via Bangalore National Highway. Arrive in Vellore. Visit Sripuram Golden Temple, taking the star-shaped path that leads to the sanctum sanctorum of Sri Lakshmi Narayani. Experience the golden architecture and spiritual messages along the walkway. Traditional vegetarian lunch. Afternoon visit to the grand 16th-century Vellore Fort with its double moats, and the intricately carved Jalakandeswarar Temple. Evening drive back to Chennai.',
            'morning': '07:00 AM pickup, breakfast enroute, Sripuram Golden Temple darshan',
            'sightseeing': 'Sripuram Golden Temple (Maha Lakshmi), Vellore Fort, Jalakandeswarar Temple, Fort Museum',
            'evening': 'Evening tea refreshment, return journey to Chennai arriving by 08:30 PM',
            'night_stay': 'Same Day Return',
            'meals': 'Pure Vegetarian Lunch'
        }
    ],
    'darshan_slots': [
        {
            'temple_name': 'Sripuram Golden Temple (Sri Lakshmi Narayani)',
            'deity': 'Goddess Mahalakshmi (Narayani)',
            'darshan_type': 'special_entry_300',
            'slot_time': '10:30 AM - 01:00 PM',
            'location': 'Star-Shaped Golden Path',
            'dress_code': 'Decent Traditional Dress (No shorts / sleeveless)',
            'prasad': 'Maha Lakshmi Kumkum & Laddu Prasadam',
            'senior_citizen': True
        }
    ]
})

packages_data.append({
    'code': 'SGT-CTT-006',
    'name': 'Chennai to Gingee Fort (Chenji) Heritage Day Tour',
    'destination': 'Chennai / Gingee (Chenji)',
    'category': 'holiday',
    'duration_days': 1,
    'duration_nights': 0,
    'base_price': decimal.Decimal('499.00'),
    'price_with_food': decimal.Decimal('899.00'),
    'price_without_food': decimal.Decimal('499.00'),
    'is_devotional': False,
    'description': clean_rebrand("""
Ascend the majestic citadel dubbed the Troy of the East by Chhatrapati Shivaji Maharaj. Explore Rajagiri Fort, Krishnagiri Fort, the Kalyana Mahal seven-story palace tower, granaries, temple ruins, and Krishnagiri Dam.
"""),
    'itinerary': [
        {
            'day': 1,
            'title': 'Chennai to Gingee Fort Heritage Expedition',
            'route': 'Chennai to Gingee (310 km round trip)',
            'activities': 'Morning 06:30 AM departure from Chennai. Arrive at the foot of Gingee hills. Trek up the Rajagiri Fort to explore the impregnable citadel, arched gateways, Kalyana Mahal, royal granary, and cannon posts overlooking the plains. Visit the lower fort complex and Krishnagiri hill. Lunch at local heritage hotel. Afternoon visit to Krishnagiri Dam and lake before returning to Chennai.',
            'morning': '06:30 AM pickup, trek up Rajagiri Fort citadel',
            'sightseeing': 'Rajagiri Fort, Krishnagiri Fort, Kalyana Mahal, Royal Granaries, Krishnagiri Dam',
            'evening': 'Sunset view, drive back to Chennai arriving by 08:30 PM',
            'night_stay': 'Same Day Return',
            'meals': 'Lunch'
        }
    ]
})

packages_data.append({
    'code': 'SGT-CTT-007',
    'name': 'Chennai to Nagapattinam & Velankanni Shrine Day Pilgrimage',
    'destination': 'Chennai / Nagapattinam / Velankanni',
    'category': 'devotional',
    'duration_days': 1,
    'duration_nights': 0,
    'base_price': decimal.Decimal('1650.00'),
    'price_with_food': decimal.Decimal('2250.00'),
    'price_without_food': decimal.Decimal('1650.00'),
    'is_devotional': True,
    'description': clean_rebrand("""
A dedicated pilgrimage from Chennai to the renowned Basilica of Our Lady of Good Health in Velankanni (Lourdes of the East) and Nagapattinam coastal shrines.
"""),
    'itinerary': [
        {
            'day': 1,
            'title': 'Chennai to Velankanni Pilgrimage & Return',
            'route': 'Chennai to Velankanni via ECR (620 km round trip)',
            'activities': 'Early morning 04:00 AM departure from Chennai by AC vehicle. Drive through the scenic delta highway. Arrive at Velankanni Basilica. Attend holy mass, offer candles, and visit the miraculous spring (Our Lady Tank) and Church museum. Lunch at coastal restaurant. Visit Nagapattinam Soundararaja Perumal Temple and beach. Evening return drive to Chennai.',
            'morning': '04:00 AM early departure, arrival Velankanni by 10:30 AM',
            'sightseeing': 'Basilica of Our Lady of Good Health, Miraculous Tank, Church Museum, Velankanni Beach',
            'evening': 'Return departure, arrival Chennai around 11:30 PM',
            'night_stay': 'Same Day Return',
            'meals': 'Breakfast, Lunch'
        }
    ]
})

packages_data.append({
    'code': 'SGT-CTT-008',
    'name': 'Chennai City Local Heritage & Spiritual Temples Day Tour',
    'destination': 'Chennai Local City Tour',
    'category': 'local_tour',
    'duration_days': 1,
    'duration_nights': 0,
    'base_price': decimal.Decimal('350.00'),
    'price_with_food': decimal.Decimal('650.00'),
    'price_without_food': decimal.Decimal('350.00'),
    'is_devotional': True,
    'description': clean_rebrand("""
A comprehensive local sightseeing tour of Chennai, India’s cultural gateway. Visit Kapaleeshwarar Temple Mylapore, Parthasarathy Temple Triplicane, Santhome Cathedral Basilica, Fort St. George, Government Museum, and the world’s second longest urban beach, Marina Beach.
"""),
    'itinerary': [
        {
            'day': 1,
            'title': 'Chennai Heritage, Temples & Marina Beach',
            'route': 'Chennai City Local (80 km circuit)',
            'activities': 'Morning 08:30 AM pickup from residence. Darshan at the 7th-century Kapaleeshwarar Temple (Lord Shiva) in Mylapore with its colorful 120-foot gopuram. Visit 8th-century Sri Parthasarathy Temple (Lord Krishna as charioteer) in Triplicane. Visit Santhome Cathedral Basilica built over the tomb of Apostle St. Thomas. Drive past Fort St. George, High Court, and Napier Bridge. Lunch break. Afternoon visit to Government Museum Egmore and Bronze Gallery. Evening leisure walk on Marina Beach with sunset views and Chennai street food.',
            'morning': '08:30 AM pickup, Kapaleeshwarar and Parthasarathy temple darshan',
            'sightseeing': 'Kapaleeshwarar Temple, Parthasarathy Temple, Santhome Basilica, Fort St. George, Marina Beach',
            'evening': 'Sunset stroll at Marina Beach, drop at residence by 07:30 PM',
            'night_stay': 'Same Day Tour',
            'meals': 'Traditional South Indian Lunch'
        }
    ]
})

print(f"Created {len(packages_data)} Ex-Chennai Outstation & City tours.")
