import os
import sys
import re
import json
import urllib.request
from decimal import Decimal
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')

# Setup Django
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
    InternationalDocumentChecklist,
)
from core.models import VehicleType

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

INTL_SPECS = [
    ('australia.html', 'Australia', 'Sydney, Melbourne & Gold Coast', 'AUD', 6, 5, 115000),
    ('bali.html', 'Indonesia (Bali)', 'Seminyak, Ubud & Nusa Penida', 'INR', 5, 4, 38000),
    ('bhutan.html', 'Bhutan', 'Thimphu, Paro & Punakha', 'INR', 4, 3, 29000),
    ('cambodia.html', 'Cambodia', 'Siem Reap, Angkor Wat & Phnom Penh', 'USD', 7, 6, 42000),
    ('china.html', 'China', 'Beijing, Shanghai & Xi\'an', 'USD', 13, 12, 125000),
    ('denmark.html', 'Denmark', 'Copenhagen & Castles', 'EUR', 7, 6, 110000),
    ('dubai.html', 'Dubai, UAE', 'Dubai City, Desert Safari & Abu Dhabi', 'AED', 8, 7, 46000),
    ('europe.html', 'Europe Grand Tour', 'Paris, Swiss Alps, Rome & Venice', 'EUR', 15, 14, 185000),
    ('france.html', 'France', 'Paris, Versailles & Loire Valley', 'EUR', 7, 6, 120000),
    ('georgia.html', 'Georgia', 'Tbilisi, Kazbegi & Batumi', 'USD', 7, 6, 55000),
    ('hong-kong.html', 'Hong Kong & Macau', 'Victoria Peak, Disneyland & Macau', 'HKD', 10, 9, 88000),
    ('israel.html', 'Israel (Holy Land)', 'Jerusalem, Bethlehem, Nazareth & Dead Sea', 'USD', 7, 6, 95000),
    ('japan.html', 'Japan', 'Tokyo, Mount Fuji & Kyoto', 'USD', 10, 9, 145000),
    ('kenya.html', 'Kenya', 'Nairobi, Masai Mara & Lake Nakuru', 'USD', 7, 6, 135000),
    ('malaysia.html', 'Malaysia', 'Kuala Lumpur, Genting & Batu Caves', 'MYR', 5, 4, 32000),
    ('maldives.html', 'Maldives', 'Private Water Villa Resort', 'USD', 6, 5, 68000),
    ('mauritius.html', 'Mauritius', 'Port Louis, Chamarel & Ile Aux Cerfs', 'USD', 5, 4, 52000),
    ('nepal.html', 'Nepal', 'Kathmandu, Pokhara & Chitwan', 'INR', 6, 5, 34000),
    ('norway.html', 'Norway', 'Oslo, Bergen, Fjords & Arctic Circle', 'EUR', 8, 7, 140000),
    ('singapore.html', 'Singapore', 'Marina Bay, Sentosa & Universal Studios', 'SGD', 6, 5, 45000),
    ('south-korea.html', 'South Korea', 'Seoul, Nami Island & Busan', 'USD', 11, 10, 115000),
    ('sri-lanka.html', 'Sri Lanka', 'Colombo, Kandy, Nuwara Eliya & Bentota', 'INR', 8, 7, 44000),
    ('sweden.html', 'Sweden', 'Stockholm, Drottningholm & Archipelago', 'EUR', 9, 8, 135000),
    ('switzerland.html', 'Switzerland', 'Zurich, Lucerne, Interlaken & Titlis', 'EUR', 11, 10, 165000),
    ('thailand.html', 'Thailand', 'Bangkok, Pattaya & Coral Island', 'THB', 6, 5, 35000),
    ('turkey.html', 'Turkey', 'Istanbul, Cappadocia & Bosphorus', 'USD', 6, 5, 78000),
    ('united-kingdom.html', 'United Kingdom', 'London, Oxford & Scottish Highlands', 'GBP', 8, 7, 135000),
    ('usa.html', 'United States of America', 'New York, Washington DC, Niagara & Orlando', 'USD', 16, 15, 235000),
    ('vietnam.html', 'Vietnam', 'Hanoi, Halong Bay Cruise & Da Nang', 'USD', 7, 6, 48000),
]

DEV_SPECS = [
    (
        'kanyakumari.html',
        'KANYAKUMARI & RAMESHWARAM MAHA THEERTHAM PILGRIMAGE YATRA',
        'Kanyakumari & Rameshwaram',
        3, 2, 16500,
        "Holy southern seaside pilgrimage covering the confluence of three seas at Cape Comorin and Ramanathaswamy 22 sacred well theerthams.",
        [
            {'day': 1, 'title': 'Day 1: Arrival & Kanyakumari Sacred Darshan', 'spots': 'Confluence of Triveni Sangam, Kanyakumari Amman Temple, Vivekananda Rock Memorial, and breathtaking Sunset View.'},
            {'day': 2, 'title': 'Day 2: Kanyakumari to Rameshwaram Island Transit', 'spots': 'Sunrise at Cape Comorin, Padmanabhapuram Palace, travel across iconic Pamban Sea Bridge to holy Rameshwaram island.'},
            {'day': 3, 'title': 'Day 3: Ramanathaswamy 22 Wells Snanam & Dhanushkodi', 'spots': 'Agni Theertham sea bath, 22 sacred Theertham well bath inside temple, Spatika Linga darshan, Kothandaramaswamy temple, Dhanushkodi ruins, return journey.'},
        ],
        ['Ramanathaswamy Temple', 'Kanyakumari Amman Temple']
    ),
    (
        'madurai.html',
        'MADURAI MEENAKSHI AMMAN & ALAGAR HILLS TEMPLE HERITAGE YATRA',
        'Madurai',
        2, 1, 9500,
        "Spiritual exploration of Tamil Nadu's Athens of the East, honoring Goddess Meenakshi and Lord Sundareswarar with historic architectural gems.",
        [
            {'day': 1, 'title': 'Day 1: Madurai Meenakshi Amman Temple & Palace', 'spots': 'Arrival, sacred darshan of Madurai Meenakshi Sundareswarar Temple, 1000-pillar hall, Thirumalai Nayakar Mahal sound & light show, vibrant night bazaar.'},
            {'day': 2, 'title': 'Day 2: Alagar Koil, Pazhamudircholai & Return', 'spots': 'Early morning visit to Lord Kallalagar Temple in Alagar Hills, Pazhamudircholai Murugan Arupadai Veedu, holy Rakkayi Theertham, return transit.'},
        ],
        ['Madurai Meenakshi Amman Temple', 'Pazhamudircholai Murugan Temple']
    ),
    (
        'tanjore.html',
        'THANJAVUR BRIHADEESWARAR BIG TEMPLE & CHOLA HERITAGE YATRA',
        'Thanjavur',
        2, 1, 14100,
        "Architectural pilgrimage exploring the world-famous UNESCO Chola living temple of Rajaraja Chola and ancient arts.",
        [
            {'day': 1, 'title': 'Day 1: Thanjavur Brihadeeswarar Big Temple Exploration', 'spots': 'Arrival in Thanjavur, darshan at magnificent 1000-year-old Brihadeeswarar Temple (Peruvudaiyar Kovil), monolithic Nandi, Sivaganga Park.'},
            {'day': 2, 'title': 'Day 2: Maratha Palace, Art Gallery & Saraswathi Mahal', 'spots': 'Visit Thanjavur Royal Palace, Saraswathi Mahal Library ancient palm-leaf manuscripts, Tanjore bronze gallery, authentic Tanjore painting workshops, return journey.'},
        ],
        ['Brihadeeswarar Temple (Big Temple)']
    ),
    (
        'mahabalipuram.html',
        'MAHABALIPURAM UNESCO SHORE TEMPLE & ROCK-CUT SHRINES TOUR',
        'Mahabalipuram',
        2, 1, 14100,
        "Coastal heritage exploration featuring 7th-century Pallava dynasty rock architecture and Shore Temple facing the Bay of Bengal.",
        [
            {'day': 1, 'title': 'Day 1: Shore Temple, Pancha Rathas & Arjuna\'s Penance', 'spots': 'Arrival along scenic East Coast Road, UNESCO Shore Temple, monolithic Five Rathas, Arjuna\'s Penance bas-relief, Krishna\'s Butterball.'},
            {'day': 2, 'title': 'Day 2: Mahabalipuram Beach, Lighthouse & Return', 'spots': 'Sunrise at seashore, Mahabalipuram heritage lighthouse, local granite sculpture artisans market, seaside cafes, comfortable return transit.'},
        ],
        ['Mahabalipuram Shore Temple']
    ),
    (
        'velankanni.html',
        'VELANKANNI BASILICA OF OUR LADY OF GOOD HEALTH PILGRIMAGE',
        'Velankanni & Nagapattinam',
        2, 1, 14100,
        "Sacred Marian shrine on the Coromandel Coast renowned for divine healing and historic Portuguese-Gothic basilica.",
        [
            {'day': 1, 'title': 'Day 1: Arrival & Basilica Sacred Mass & Holy Flagstaff', 'spots': 'Arrival in Velankanni, holy prayers at Basilica of Our Lady of Good Health, church museum, lighting prayer candles, holy water tank, evening Rosary procession.'},
            {'day': 2, 'title': 'Day 2: Morning Mass, Beach Sanctuary & Return', 'spots': 'Early morning Holy Mass, serene walk along Velankanni beach, souvenir shopping, Nagore Dargah visit nearby (optional), return transit.'},
        ],
        ['Basilica of Our Lady of Good Health']
    ),
    (
        'devotion.html',
        'SABARIMALA & SRIRANGAM MAHA DIVYA DESAM PILGRIMAGE CIRCUIT',
        'Sabarimala & Srirangam',
        3, 2, 10900,
        "Sacred spiritual circuit combining Lord Ayyappa Swami darshan in Kerala and Lord Ranganatha reclining Vishnu temple in Srirangam.",
        [
            {'day': 1, 'title': 'Day 1: Departure towards Pamba & Sabarimala Ascent', 'spots': 'Journey from Coimbatore/Chennai to Pamba base camp. Holy dip in Pamba river, trek to Sannidhanam, traditional Irumudi offerings.'},
            {'day': 2, 'title': 'Day 2: Sabarimala Ayyappa Darshan & Transit to Srirangam', 'spots': 'Nirmalya darshan, Harivarasanam chanting, descent to Pamba, travel towards Srirangam, evening relaxation.'},
            {'day': 3, 'title': 'Day 3: Srirangam Sri Ranganatha Swamy & Srivilliputhur Andal', 'spots': 'Darshan at Srirangam 21 gopuram temple complex, proceed to Srivilliputhur Andal temple tower, return journey with sacred prasadham.'},
        ],
        ['Sabarimala Sree Dharma Sastha Temple', 'Srirangam Sri Ranganathaswamy Temple']
    ),
    (
        'devotional-packages.html',
        'TIRUPATI BALAJI & SRI KALAHASTI RAHU-KETU DIVYA DARSHAN YATRA',
        'Tirupati & Kalahasti',
        2, 1, 12500,
        "Exclusive two-day holy pilgrimage covering Lord Venkateswara Balaji Special Entry Darshan on Tirumala Hills and Kalahasti Sarpa Dosha Nivarana.",
        [
            {'day': 1, 'title': 'Day 1: Arrival Tirupati & Sri Kalahasteeswara Darshan', 'spots': 'Arrival at Tirupati, proceed to Sri Kalahasti Temple for Rahu-Ketu Sarpa Dosha Nivarana Pooja, evening visit to Tiruchanur Padmavathi Ammavari Temple.'},
            {'day': 2, 'title': 'Day 2: Tirumala Hill Ascent & Lord Balaji Special Entry Darshan', 'spots': 'Early morning ghat road ascent to Tirumala, Vaikuntam Queue Complex Special Entry ₹300 Darshan, Laddu Prasadam collection, Varahaswamy temple, return journey.'},
        ],
        ['Tirumala Sri Venkateswara Temple', 'Sri Kalahasteeswara Temple']
    )
]

def clean_rebrand(text):
    if not text:
        return ""
    replacements = [
        (re.compile(r'Kandhan\s+Travels', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'kandhantravels\.com', re.IGNORECASE), 'sivagayathritravels.com'),
        (re.compile(r'booking@kandhantravels\.com', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'info@kandhantravels\.com', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'\+91[\s\d-]{9,15}'), '+91 98425 33777'),
        (re.compile(r'9500076953'), '9842533777'),
        (re.compile(r'Mettupalayam', re.IGNORECASE), 'Coimbatore & Chennai'),
    ]
    cleaned = text
    for pattern, repl in replacements:
        cleaned = pattern.sub(repl, cleaned)
    return cleaned.strip()

def scrape_intl_package(spec):
    filename, country, dest, curr, exp_days, exp_nights, price = spec
    url = f'https://www.kandhantravels.com/{filename}'
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=12).read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        for el in soup.find_all(['header', 'footer', 'nav', 'script', 'style']):
            el.decompose()

        # Title
        h3 = soup.find('h3')
        raw_title = h3.get_text(strip=True) if h3 and len(h3.get_text(strip=True)) > 5 else f"{exp_days}-Day {country} Tour Package"
        if filename == 'thailand.html' and 'turkey' in raw_title.lower():
            raw_title = "6-Day Thailand Extravaganza: Bangkok, Pattaya & Coral Island"

        title = clean_rebrand(raw_title).upper()

        # Days Plan
        days_plan = []
        seen_days = set()
        for p in soup.find_all('p'):
            txt = p.get_text(strip=True)
            m = re.match(r'^Day\s*(\d+)[\s:–-]+(.*)', txt, re.IGNORECASE)
            if m:
                d_num = int(m.group(1))
                if d_num in seen_days:
                    continue
                seen_days.add(d_num)
                rest = m.group(2).strip()
                parts = re.split(r'[:–-]', rest, maxsplit=1)
                day_title = f"Day {d_num}: {parts[0].strip()}"
                day_spots = parts[1].strip() if len(parts) > 1 else rest
                days_plan.append({
                    'day': d_num,
                    'title': clean_rebrand(day_title),
                    'spots': clean_rebrand(day_spots if len(day_spots) > 10 else day_title)
                })

        days_plan.sort(key=lambda x: x['day'])
        actual_days = max(exp_days, len(days_plan))
        actual_nights = max(exp_nights, actual_days - 1)

        if len(days_plan) < actual_days:
            for d in range(len(days_plan) + 1, actual_days + 1):
                days_plan.append({
                    'day': d,
                    'title': f"Day {d}: Guided Sightseeing & Cultural Leisure in {country}",
                    'spots': f"Explore iconic landmarks, cultural treasures, local cuisine, and shopping across {country}."
                })

        desc_paras = [clean_rebrand(p.get_text(strip=True)) for p in soup.find_all('p') if len(p.get_text(strip=True)) > 40 and not p.get_text(strip=True).startswith('Day ')]
        description = "\n\n".join(desc_paras[:3]) if desc_paras else f"Experience {country} with this exclusive {actual_days} Days / {actual_nights} Nights international holiday package."

        return {
            'type': 'international',
            'filename': filename,
            'url': url,
            'title': title,
            'country': country,
            'destination': dest,
            'currency': curr,
            'days': actual_days,
            'nights': actual_nights,
            'price': price,
            'days_plan': days_plan,
            'description': description,
        }
    except Exception as e:
        print(f"Error scraping intl {filename}: {e}")
        return None

def attach_intl_tariffs(pkg, base_pax_price):
    PackageVehicleTariff.objects.filter(package=pkg).delete()
    vtypes = list(VehicleType.objects.all())
    sedan_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['sedan', 'dzire', 'etios'])), vtypes[0] if vtypes else None)
    crysta_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['crysta', 'innova'])), vtypes[1] if len(vtypes) > 1 else sedan_vt)
    urbania_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['urbania', 'tempo', '17'])), vtypes[2] if len(vtypes) > 2 else sedan_vt)
    bus36_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['36', 'mini', '40'])), vtypes[3] if len(vtypes) > 3 else sedan_vt)
    coach54_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['54', 'coach', '52', 'volvo'])), vtypes[4] if len(vtypes) > 4 else sedan_vt)

    days = pkg.duration_days
    configs = [
        (sedan_vt, '4_sedan', 3500.0),
        (crysta_vt, '7_crysta', 5500.0),
        (urbania_vt, '17_tt_urbania', 8500.0),
        (bus36_vt, '36_mini_bus', 14500.0),
        (coach54_vt, '54_luxury_coach', 19500.0),
    ]

    for vt, tier, daily_rate in configs:
        if not vt:
            continue
        total_p_rate = days * daily_rate
        PackageVehicleTariff.objects.create(
            package=pkg,
            vehicle_type=vt,
            seating_tier=tier,
            rate_type='outstation_multiday',
            package_rate=Decimal(str(round(total_p_rate, 2))),
            per_day_rate=Decimal(str(round(daily_rate, 2))),
            included_km=days * 200,
            extra_km_rate=Decimal("20.00"),
            driver_bata_per_day=Decimal("1000.00"),
            driver_bata_included=True,
            toll_parking_included=True,
            interstate_permit_included=True,
        )

def attach_dev_tariffs(pkg, base_cost):
    PackageVehicleTariff.objects.filter(package=pkg).delete()
    vtypes = list(VehicleType.objects.all())
    sedan_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['sedan', 'dzire', 'etios'])), vtypes[0] if vtypes else None)
    crysta_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['crysta', 'innova'])), vtypes[1] if len(vtypes) > 1 else sedan_vt)
    urbania_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['urbania', 'tempo', '17'])), vtypes[2] if len(vtypes) > 2 else sedan_vt)
    bus36_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['36', 'mini', '40'])), vtypes[3] if len(vtypes) > 3 else sedan_vt)
    coach54_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['54', 'coach', '52', 'volvo'])), vtypes[4] if len(vtypes) > 4 else sedan_vt)

    days = pkg.duration_days
    configs = [
        (sedan_vt, '4_sedan', 14.0, 500.0),
        (crysta_vt, '7_crysta', 20.0, 600.0),
        (urbania_vt, '17_tt_urbania', 26.0, 800.0),
        (bus36_vt, '36_mini_bus', 35.0, 1000.0),
        (coach54_vt, '54_luxury_coach', 45.0, 1200.0),
    ]

    for vt, tier, km_rate, bata in configs:
        if not vt:
            continue
        daily = (300 * km_rate) + bata
        pkg_rate = days * daily
        PackageVehicleTariff.objects.create(
            package=pkg,
            vehicle_type=vt,
            seating_tier=tier,
            rate_type='outstation_multiday',
            package_rate=Decimal(str(round(pkg_rate, 2))),
            per_day_rate=Decimal(str(round(daily, 2))),
            included_km=days * 300,
            extra_km_rate=Decimal(str(km_rate)),
            driver_bata_per_day=Decimal(str(bata)),
            driver_bata_included=True,
            toll_parking_included=True,
            interstate_permit_included=True if 'sabarimala' in pkg.name.lower() or 'tirupati' in pkg.name.lower() else False,
        )

def main():
    print("=" * 80)
    print("  SIVA GAYATHRI TOURS & TRAVELS — KANDHAN TRAVELS SCRAPER & IMPORTER")
    print("=" * 80)

    # 1. Scrape International Packages
    print(f"\n[1/3] Scraping {len(INTL_SPECS)} International Packages from kandhantravels.com...")
    intl_data = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(scrape_intl_package, s) for s in INTL_SPECS]
        for f in as_completed(futures):
            res = f.result()
            if res:
                intl_data.append(res)
                print(f"  Scraped: {res['title'][:55]} ({res['nights']}N/{res['days']}D)")

    # 2. Prepare Devotional Packages
    print(f"\n[2/3] Preparing {len(DEV_SPECS)} Devotional Packages...")
    dev_data = []
    for fn, title, dest, days, nights, cost, desc, days_plan, temples in DEV_SPECS:
        dev_data.append({
            'type': 'devotional',
            'filename': fn,
            'url': f'https://www.kandhantravels.com/{fn}',
            'title': title,
            'country': 'India',
            'destination': dest,
            'currency': 'INR',
            'days': days,
            'nights': nights,
            'price': cost,
            'description': desc,
            'days_plan': days_plan,
            'temples': temples,
        })
        print(f"  Prepared: {title[:55]} ({nights}N/{days}D)")

    all_kandhan = intl_data + dev_data
    with open('scripts/scraped_kandhan_packages.json', 'w', encoding='utf-8') as f:
        json.dump(all_kandhan, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(all_kandhan)} total packages to scripts/scraped_kandhan_packages.json")

    # 3. Import into Django Database
    print(f"\n[3/3] Importing into Database with prefix SGT-KT-...")
    deleted = Package.objects.filter(package_code__startswith='SGT-KT-').delete()
    print(f"Cleared previous SGT-KT records: {deleted}")

    imported_count = 0

    # A. Import International Packages
    for item in intl_data:
        code_slug = re.sub(r'[^A-Z0-9]+', '-', item['country'].upper()).strip('-')[:14]
        pkg_code = f"SGT-KT-INTL-{code_slug}-{item['days']}D"
        if Package.objects.filter(package_code=pkg_code).exists():
            pkg_code = f"{pkg_code}-{imported_count+1}"

        price_val = Decimal(str(item['price']))
        inclusions_text = (
            f"Airport meet-and-greet and round-trip transfers in {item['country']}.\n"
            f"Star Category Hotel accommodation on twin-sharing basis.\n"
            "Daily international buffet breakfast and Indian chef dinners.\n"
            f"Comprehensive sightseeing tours in air-conditioned luxury tourist coach.\n"
            f"All state entrance permits, highway tolls, city taxes, and driver gratuities.\n"
            "Official tourist visa assistance & travel insurance documentation guidance.\n"
            "24x7 Siva Gayathri Tours & Travels International Concierge & Guest Support."
        )

        exclusions_text = (
            "International flight tickets (airfare can be booked upon request ex-Chennai / Coimbatore).\n"
            "Personal expenses, room service, laundry, mini bar, telephone charges.\n"
            "Optional adventure activities, water sports, and special entrance passes not stated.\n"
            "Any surcharge during festive peaks, trade fairs, or local holidays."
        )

        terms_text = (
            "Valid Passport with minimum 6 months validity from return date is strictly mandatory.\n"
            "50% advance deposit required for international land booking confirmation.\n"
            "Balance payment must be settled at least 15 days prior to international departure.\n"
            "Visa grant is at the sole discretion of the respective embassy/consulate."
        )

        pkg = Package.objects.create(
            package_code=pkg_code,
            name=item['title'],
            destination=item['destination'],
            category='holiday',
            duration_nights=item['nights'],
            duration_days=item['days'],
            base_price=price_val,
            price_with_food=price_val,
            price_without_food=Decimal(str(int(item['price'] * 0.85))),
            pricing_type='per_person',
            meal_plan='MAP',
            room_sharing_type='twin_sharing',
            min_pax=2,
            is_international=True,
            destination_country=item['country'],
            currency_code=item['currency'] if item['currency'] in ['INR', 'AED', 'SGD', 'MYR', 'THB', 'USD', 'EUR'] else 'USD',
            visa_required=True,
            visa_guidelines=f"Tourist eVisa / Visa on Arrival for {item['country']}. Passport must be valid for at least 6 months with 2 blank pages.",
            passport_validity_months=6,
            flight_inclusive=False,
            flight_details_note=f"Scheduled flights available Ex-Chennai (MAA) / Ex-Coimbatore (CJB) to {item['country']}.",
            overseas_dmc_partner=f"Certified Destination Partner in {item['country']}",
            inclusions=inclusions_text,
            exclusions=exclusions_text,
            terms_and_conditions=terms_text,
            contact_persons_footer="Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131)",
            is_active=True,
        )

        # Create Itinerary Days
        for d in item['days_plan']:
            ItineraryDay.objects.create(
                package=pkg,
                day_number=d['day'],
                title=d['title'][:250],
                route_segment=f"{item['country']} Tourist Circuit"[:250],
                activities=d['spots'],
                sightseeing_spots=d['spots'][:500],
                meals_included="Breakfast & Dinner",
                night_stay_location=item['destination'].split(',')[0],
            )

        # Attach Tariffs
        attach_intl_tariffs(pkg, item['price'])

        # Attach International Document Checklist
        docs = [
            ("Original Passport (Min 6 months validity)", True, 15, "Scan of front & back bio-pages"),
            ("Passport Size Photograph (35x45mm, White background)", True, 10, "Matte finish, 80% face close up"),
            ("Tourist eVisa / Entry Authorization Form", True, 7, "Processed via embassy portal"),
            ("Confirmed Return Air Tickets & Hotel Vouchers", True, 5, "Provided by Siva Gayathri Travels"),
            ("Overseas Medical & Travel Insurance Policy", True, 5, "Minimum $50,000 coverage"),
        ]
        for dname, mand, dline, note in docs:
            InternationalDocumentChecklist.objects.create(
                package=pkg,
                document_name=dname,
                is_mandatory=mand,
                submission_deadline_days=dline,
                notes=note
            )

        imported_count += 1

    # B. Import Devotional Packages
    for item in dev_data:
        code_slug = re.sub(r'[^A-Z0-9]+', '-', item['destination'].upper()).strip('-')[:14]
        pkg_code = f"SGT-KT-DEV-{code_slug}-{item['days']}D"
        if Package.objects.filter(package_code=pkg_code).exists():
            pkg_code = f"{pkg_code}-{imported_count+1}"

        price_val = Decimal(str(item['price']))
        inclusions_text = (
            "Well-maintained, sanitized tourist vehicle with experienced pilgrimage chauffeur.\n"
            "All fuel charges, interstate permit taxes, highway tolls, and parking fees.\n"
            f"Comprehensive temple darshan circuit covering {item['destination']}.\n"
            "100% Satvik Pure Vegetarian South Indian meals.\n"
            "Senior citizen assistance with low-step boarding and wheelchair coordination.\n"
            "24x7 Siva Gayathri Tours & Travels dispatch and guest support."
        )

        exclusions_text = (
            "Special darshan passes / Archanai & Abhishekam personal pooja tickets.\n"
            "Camera fees, head tonsure charges, and personal offerings to temple priests.\n"
            "Any expense incurred due to temple crowd delays or road diversions."
        )

        terms_text = (
            "Strict Traditional Temple Dress Code must be followed by all pilgrims.\n"
            "50% advance payable upon booking confirmation, balance before departure.\n"
            "Vehicle will strictly adhere to spiritual circuit timings and safety guidelines.\n"
            "Polite and devout drivers ensuring serene and divine travel experience."
        )

        pkg = Package.objects.create(
            package_code=pkg_code,
            name=item['title'],
            destination=item['destination'],
            category='devotional',
            duration_nights=item['nights'],
            duration_days=item['days'],
            base_price=price_val,
            price_with_food=price_val,
            price_without_food=Decimal(str(int(item['price'] * 0.78))),
            pricing_type='per_person',
            meal_plan='AP',
            room_sharing_type='twin_sharing',
            min_pax=4,
            is_devotional=True,
            satvik_pure_veg_meals=True,
            senior_citizen_friendly=True,
            temple_dress_code="Mandatory Traditional Dress: Dhoti/Kurta for Men, Saree/Chudidar for Women",
            temple_darshan_info=f"Sacred Pilgrimage covering major shrines along {item['destination']}.",
            inclusions=inclusions_text,
            exclusions=exclusions_text,
            terms_and_conditions=terms_text,
            contact_persons_footer="Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131)",
            is_active=True,
        )

        # Create Itinerary Days
        for d in item['days_plan']:
            ItineraryDay.objects.create(
                package=pkg,
                day_number=d['day'],
                title=d['title'][:250],
                route_segment=f"{item['destination']} Circuit"[:250],
                activities=d['spots'],
                sightseeing_spots=d['spots'][:500],
                meals_included="Breakfast, Lunch, Dinner",
                night_stay_location=item['destination'].split()[0],
            )

        # Attach Tariffs
        attach_dev_tariffs(pkg, item['price'])

        # Attach Temple Slots
        for tname in item.get('temples', []):
            TempleDarshanSlot.objects.create(
                package=pkg,
                temple_name=tname,
                deity_or_circuit=f"{tname} Sacred Sannidhi",
                darshan_type='special_entry_300',
                booked_slot_time="08:00 AM - 11:00 AM",
                reporting_location="East Gopuram / Main Entrance Queue",
                dress_code_notes="Strict Traditional: Dhoti/Kurta (Men), Saree/Chudidar (Women)",
                prasad_details="Holy Theertham & Prasadam Included",
                senior_citizen_support=True
            )

        imported_count += 1

    print("=" * 80)
    print(f"SUCCESS! Scraped & Imported {imported_count} packages from kandhantravels.com:")
    print(f"  - {len(intl_data)} International Packages (29 Countries)")
    print(f"  - {len(dev_data)} Devotional Packages (Tamil Nadu & Kerala Shrines)")
    print("=" * 80)

if __name__ == '__main__':
    main()
