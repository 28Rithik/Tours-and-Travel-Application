import os
import sys
import re
import json
import html
import urllib.request
from decimal import Decimal
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding='utf-8')

# Setup Django environment
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from django.db import transaction
from packages.models import (
    Package,
    ItineraryDay,
    PackageVehicleTariff,
    TempleDarshanSlot,
    InternationalDocumentChecklist,
)
from core.models import VehicleType

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

# ==============================================================================
# 1. TEXT CLEANING & REBRANDING UTILITIES
# ==============================================================================

def clean_rebrand(text):
    if not text:
        return ""
    text = html.unescape(text)
    text = text.replace('\u2192', ' - ').replace('\u2013', ' - ').replace('\u2014', ' - ').replace('\u2015', ' - ')
    text = text.replace('\u00a0', ' ').replace('\xa0', ' ').replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'wa\.link/\S+', '', text)
    text = re.sub(r'(?:www\.)?[a-zA-Z0-9-]+\.(?:com|in|org|net)/\S*', '', text)

    replacements = [
        (re.compile(r'Sri\s+Murugan\s+Travel\s+Agency\s*\(SMTA\)?', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Sri\s+Murugan\s+Travel\s+Agency', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Sri\s+Murugan\s+Travels?', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Sri\s+Murugan', re.IGNORECASE), 'Siva Gayathri'),
        (re.compile(r'\bSMTA\b', re.IGNORECASE), 'Siva Gayathri Tours'),
        (re.compile(r'srimurugantravel\.com', re.IGNORECASE), 'sivagayathritravels.com'),
        (re.compile(r'info@srimurugantravel\.com', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'\+91\s*-\s*97918\s*48265', re.IGNORECASE), '+91 98425 33777'),
        (re.compile(r'\+91[\s\d-]{9,15}'), '+91 98425 33777'),
    ]
    cleaned = text
    for pattern, repl in replacements:
        cleaned = pattern.sub(repl, cleaned)

    cleaned = re.sub(r'\s*,\s*', ', ', cleaned)
    cleaned = re.sub(r'\s*-\s*', ' - ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

# ==============================================================================
# 2. SRI MURUGAN PACKAGE PARSER
# ==============================================================================

def parse_srimurugan_package_detail(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html_content = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. JSON-LD data
        ld_trip = None
        for s in soup.find_all('script', type='application/ld+json'):
            try:
                d = json.loads(s.string)
                if d.get('@type') == 'TouristTrip':
                    ld_trip = d
                    break
            except:
                pass

        # 2. Slug and Code
        slug = url.rstrip('/').split('/')[-1]
        tour_type = 'DOM'
        if '/international/' in url:
            tour_type = 'INT'
        elif '/train/' in url:
            tour_type = 'TRN'
        elif any(k in url for k in ['rameshwaram', 'sabarimala']):
            tour_type = 'DEV'

        pkg_code = f"SGT-SMT-{tour_type}-{slug}"[:50]

        # 3. Title
        raw_title = ''
        if ld_trip and ld_trip.get('name'):
            raw_title = ld_trip['name']
        if not raw_title:
            raw_title = soup.title.string.strip() if soup.title else slug.replace('-', ' ')
        raw_title = re.sub(r'Sri Murugan.*', '', raw_title, flags=re.I).strip()
        title = clean_rebrand(raw_title).title()

        # 4. Hero Banner Image
        hero_image = ''
        for tag in soup.find_all(lambda t: t.has_attr('style') and 'background' in t['style']):
            m = re.search(r"url\(['\"]?(https?://.*?/cms/.*?\.(?:jpg|png|jpeg))['\"]?\)", tag['style'])
            if m:
                hero_image = m.group(1)
                break
        if not hero_image and ld_trip and ld_trip.get('image'):
            hero_image = ld_trip['image']

        # 5. Itinerary Extraction
        itinerary = []
        # On-page H4 tags
        for h in soup.find_all(['h4', 'h5', 'h3']):
            dm = re.search(r'DAY\s*(\d+)', h.text.strip(), re.I)
            if dm:
                d_num = int(dm.group(1))
                p = h.find_next_sibling(['p', 'div', 'ul'])
                p_text = p.text.strip() if p else ''
                p_text = clean_rebrand(re.sub(r'\s+', ' ', p_text).strip())
                if p_text:
                    d_title = f"Day {d_num}: Sightseeing & Tour Excursions"
                    if '-' in p_text:
                        parts = p_text.split('-', 1)
                        if len(parts[0].strip()) > 3 and len(parts[0].strip()) < 60:
                            d_title = f"Day {d_num}: {parts[0].strip().title()}"
                    itinerary.append({
                        'day': d_num,
                        'title': d_title,
                        'description': p_text
                    })

        # Fallback to JSON-LD if on-page had no H4
        if not itinerary and ld_trip and 'itinerary' in ld_trip:
            elements = ld_trip['itinerary'].get('itemListElement', [])
            for el in elements:
                item = el.get('item', {})
                name = item.get('name', '')
                desc = clean_rebrand(item.get('description', ''))
                dm = re.search(r'Day\s*(\d+)', name, re.I)
                d_num = int(dm.group(1)) if dm else el.get('position', len(itinerary)+1)
                if desc:
                    itinerary.append({
                        'day': d_num,
                        'title': f"Day {d_num}: {desc.split('-')[0].strip().title() if '-' in desc else name}",
                        'description': desc
                    })

        # 6. Duration Days & Nights
        days = len(itinerary)
        if days == 0:
            # Check for "X Days" in text
            d_match = re.search(r'(?:[A-Z0-9]+\s*)?(\d+)\s*Days?', soup.text, re.I)
            if d_match:
                days = int(d_match.group(1))
            else:
                days = 4
        days = max(1, min(days, 30))
        nights = max(1, days - 1)

        # Ensure every day 1..days has an itinerary item
        existing_days = {it['day']: it for it in itinerary}
        full_itinerary = []
        for d_idx in range(1, days + 1):
            if d_idx in existing_days:
                full_itinerary.append(existing_days[d_idx])
            else:
                full_itinerary.append({
                    'day': d_idx,
                    'title': f"Day {d_idx}: Sightseeing & Travel Leisure",
                    'description': f"Morning breakfast. Proceed for guided sightseeing excursions, cultural exploration, scenic viewpoints, and overnight stay."
                })

        # 7. Price
        price = 0
        pm = re.search(r'Rs\.?\s*(?:From\s*)?([\d,]+)', soup.text, re.I)
        if pm:
            try:
                price = float(pm.group(1).replace(',', ''))
            except:
                pass
        if not price:
            pm2 = re.search(r'₹\s*([\d,]+)', soup.text)
            if pm2:
                try:
                    price = float(pm2.group(1).replace(',', ''))
                except:
                    pass
        if not price:
            price = days * 4500 if tour_type != 'INT' else days * 12000

        # 8. Inclusions
        inclusions = []
        inc_header = soup.find(string=re.compile(r'Package Inclusion|Inclusion', re.I))
        if inc_header:
            container = inc_header.find_parent(['div', 'section', 'li', 'td'])
            if container:
                for line in container.get_text(separator='\n').splitlines():
                    l = clean_rebrand(line.strip())
                    if l and len(l) > 3 and not any(k in l.lower() for k in ['package inclusion', 'inclusion']):
                        inclusions.append(l)

        # 9. Visiting places / route
        visiting = ''
        vp = soup.find(string=re.compile(r'Visting Places|Visiting Places', re.I))
        if vp:
            p_cont = vp.find_parent()
            if p_cont:
                visiting = clean_rebrand(p_cont.text.replace('Visting Places', '').replace('Visiting Places', '').replace(':', '').strip())

        return {
            'url': url,
            'pkg_code': pkg_code,
            'tour_type': tour_type,
            'title': title,
            'days': days,
            'nights': nights,
            'price': price,
            'hero_image': hero_image,
            'itinerary': full_itinerary,
            'inclusions': inclusions,
            'visiting': visiting
        }
    except Exception as e:
        print(f"Error parsing {url}: {e}")
        return None

# ==============================================================================
# 3. DESTINATION, TRANSIT & COUNTRY RESOLVER
# ==============================================================================

INTL_COUNTRIES = [
    (('dubai', 'abudhabi', 'uae', 'emirates'), 'United Arab Emirates', 'AED'),
    (('singapore',), 'Singapore', 'SGD'),
    (('malaysia', 'kuala lumpur'), 'Malaysia', 'MYR'),
    (('thailand', 'bangkok', 'pattaya', 'phuket', 'karabi', 'krabi'), 'Thailand', 'THB'),
    (('bali', 'indonesia'), 'Indonesia', 'IDR'),
    (('america', 'usa'), 'United States of America', 'USD'),
    (('australia', 'newzealand', 'new zealand'), 'Australia & New Zealand', 'USD'),
    (('baku', 'azerbaijan'), 'Azerbaijan', 'USD'),
    (('china', 'beijing', 'shanghai', 'hong kong', 'macau'), 'China', 'USD'),
    (('egypt', 'nile'), 'Egypt', 'USD'),
    (('europe', 'france', 'swiss', 'switzerland', 'italy'), 'Europe', 'EUR'),
    (('japan',), 'Japan', 'USD'),
    (('almaty', 'kazakhstan'), 'Kazakhstan', 'USD'),
    (('kenya',), 'Kenya', 'USD'),
    (('maldives',), 'Maldives', 'USD'),
    (('russia',), 'Russia', 'USD'),
    (('korea', 'south korea'), 'South Korea', 'USD'),
    (('srilanka', 'sri lanka'), 'Sri Lanka', 'USD'),
    (('turkey',), 'Turkey', 'USD'),
    (('uzbekistan',), 'Uzbekistan', 'USD'),
    (('vietnam', 'veitnam', 'cambodia'), 'Vietnam & Cambodia', 'USD'),
]

DEVOTIONAL_KEYWORDS = [
    'ayodhya', 'ram mandir', 'kasi', 'varanasi', 'gaya', 'buddhagaya', 'allahabad', 'prayagraj',
    'badrinath', 'kedarnath', 'kedharnath', 'gangotri', 'yamunotri', 'amarnath', 'vaishnodevi',
    'vaishnavidevi', 'vaishnavdevi', 'shirdi', 'pandaripuram', 'pandharpur', 'mantralayam',
    'shani shingnapur', 'dwarka', 'dwaraka', 'dwaraga', 'somnath', 'kadarkovil', 'jyotirlinga',
    'udupi', 'murudeswarar', 'kollur', 'dharmasthala', 'kukke', 'puri', 'rameshwaram', 'sabarimala',
    'naimisaranyam', 'naimisharanya', 'mukthinath', 'arunachala', 'mathura'
]

HILL_KEYWORDS = [
    'kashmir', 'gulmarg', 'pahalgam', 'ladak', 'ladakh', 'leh', 'shimla', 'simla', 'manali',
    'kulu', 'kullu', 'kufri', 'darjeeling', 'dargeeling', 'gangtok', 'gangktok', 'nainital',
    'mussoorie', 'corbett', 'arunachal', 'northeast', 'north east', 'bhutan', 'ooty', 'kodaikanal', 'munnar'
]

def resolve_package_metadata(item):
    tour_type = item['tour_type']
    title = item['title']
    title_lower = title.lower()
    url_lower = item['url'].lower()
    combined = f"{title_lower} {url_lower}"

    # International check
    if tour_type == 'INT':
        is_intl = True
        country = 'International'
        currency = 'USD'
        for keys, c_name, curr in INTL_COUNTRIES:
            if any(k in combined for k in keys):
                country = c_name
                currency = curr
                break
        cat = 'international'
        transit = 'flight_coach'
        dest = f"{country} Premier Tour Circuit"
        return is_intl, country, currency, cat, transit, dest

    # Domestic / Train / Devotional
    is_intl = False
    country = 'India'
    currency = 'INR'

    # Transit mode
    if tour_type == 'TRN':
        transit = 'train_coach'
    elif any(k in combined for k in ['flight', 'air', 'ex : chennai']):
        transit = 'flight_coach'
    else:
        transit = 'road_coach'

    # Category
    if any(k in combined for k in DEVOTIONAL_KEYWORDS) or tour_type == 'DEV':
        cat = 'devotional'
    elif any(k in combined for k in HILL_KEYWORDS):
        cat = 'hill_station'
    elif 'train' in combined:
        cat = 'fixed_departure'
    else:
        cat = 'family_vacation'

    # Destination name
    if item.get('visiting'):
        dest = f"{item['visiting'].title()}, India"
    else:
        dest = f"{title}, India"

    return is_intl, country, currency, cat, transit, dest

# ==============================================================================
# 4. MAIN SCRAPE AND IMPORT PIPELINE
# ==============================================================================

def run_srimurugan_import():
    urls_file = os.path.join(WORKSPACE_ROOT, 'scripts', 'srimurugan_package_urls.json')
    if not os.path.exists(urls_file):
        print(f"Error: {urls_file} not found!")
        return

    package_urls = json.load(open(urls_file, encoding='utf-8'))
    print("="*80)
    print(f"SCRAPING & IMPORTING {len(package_urls)} PACKAGES FROM SRI MURUGAN TRAVELS")
    print("="*80)

    # 1. Fetch details in parallel
    print("Starting multi-threaded scrape with 10 workers...")
    scraped_data = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        for item in executor.map(parse_srimurugan_package_detail, package_urls):
            if item:
                scraped_data.append(item)

    print(f"\nSuccessfully scraped {len(scraped_data)} packages from Sri Murugan Travels!")
    
    # Save cache
    cache_path = os.path.join(WORKSPACE_ROOT, 'scripts', 'scraped_srimurugan_cache.json')
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(scraped_data, f, indent=2, ensure_ascii=False)
    print(f"Saved raw cache to {cache_path}")

    # 2. Vehicle Types
    v_sedan = VehicleType.objects.filter(name__icontains='sedan').first()
    v_crysta = VehicleType.objects.filter(name__icontains='crysta').first() or VehicleType.objects.filter(name__icontains='innova').first()
    v_urbania = VehicleType.objects.filter(name__icontains='urbania').first() or VehicleType.objects.filter(name__icontains='tempo').first()
    v_minibus = VehicleType.objects.filter(name__icontains='36').first() or VehicleType.objects.filter(name__icontains='bus').first()
    v_coach = VehicleType.objects.filter(name__icontains='54').first() or VehicleType.objects.filter(name__icontains='coach').first()

    tariff_configs = [
        (v_sedan, '4_sedan', 14.0, 500),
        (v_crysta, '7_crysta', 20.0, 600),
        (v_urbania, '17_tt_urbania', 26.0, 800),
        (v_minibus, '36_mini_bus', 40.0, 1000),
        (v_coach, '54_luxury_coach', 55.0, 1200),
    ]

    print("\nStarting atomic database transaction for Sri Murugan ingestion...")
    with transaction.atomic():
        deleted_cnt, _ = Package.objects.filter(package_code__startswith='SGT-SMT-').delete()
        if deleted_cnt > 0:
            print(f"Cleaned up {deleted_cnt} previous SGT-SMT- records for clean refresh.")

        packages_created = 0
        all_itinerary_records = []
        all_tariff_records = []
        all_darshan_records = []
        all_doc_records = []

        for p_data in scraped_data:
            code = p_data['pkg_code']
            title = p_data['title']
            days = p_data['days']
            nights = p_data['nights']
            base_price = Decimal(str(round(p_data['price'], 2)))
            price_with_food = Decimal(str(round(float(base_price) * 1.25, 2)))
            price_without_food = Decimal(str(round(float(base_price) * 0.85, 2)))

            is_intl, country_name, currency, cat, transit, dest = resolve_package_metadata(p_data)
            is_devo = (cat == 'devotional')

            # Overview
            overview = (
                f"Welcome to an extraordinary journey with Siva Gayathri Tours & Travels. "
                f"The '{title}' is an all-inclusive {nights} Nights / {days} Days package "
                f"carefully designed with premium hotel accommodation, confirmed {transit.replace('_', ' ').title()} transit, "
                f"air-conditioned local sightseeing, verified chauffeurs, and 24x7 tour manager assistance. "
                f"Departing comfortably from Tamil Nadu (Chennai / Madurai / Coimbatore) to {dest}."
            )

            # Inclusions
            inc_list = p_data['inclusions']
            if not inc_list:
                inc_list = [
                    "Confirmed round-trip transit (Flight / Train / AC Coach as applicable).",
                    "Star category hotel accommodation on twin / triple sharing basis.",
                    "Daily complimentary breakfast and dinner.",
                    "Local sightseeing in private air-conditioned vehicle as per schedule.",
                    "Professional chauffeur allowance, toll charges, interstate permits, and parking fees.",
                    "Dedicated 24x7 tour coordinator assistance by Siva Gayathri Tours & Travels."
                ]
            else:
                inc_list.append("Dedicated 24x7 tour manager coordination by Siva Gayathri Tours & Travels.")
            if is_devo:
                inc_list.append("100% Satvik pure vegetarian South Indian meals guaranteed.")
                inc_list.append("Special senior citizen darshan guidance and battery car assistance.")

            # Exclusions
            exc_list = [
                "Monument entry tickets, camera permits, and optional boating / safari fees.",
                "Special personal temple pooja tickets or VIP queue passes.",
                "Personal expenses such as laundry, telephone calls, tips, and extra beverages.",
                "GST (5%) as applicable."
            ]

            terms = (
                "1. 50% advance deposit upon booking confirmation; remaining balance payable prior to trip departure.\n"
                "2. Standard hotel check-in time is 12:00 PM and check-out is 10:00 AM.\n"
                "3. Sightseeing order may be rearranged based on local temple darshan timings or flight/train schedules.\n"
                "4. All passenger details and ID proofs (Aadhaar / Passport) must be submitted at the time of booking.\n"
                "5. Standard cancellation and refund policy of Siva Gayathri Tours & Travels applies."
            )

            pkg = Package.objects.create(
                package_code=code,
                name=title,
                destination=dest[:250],
                category=cat,
                transit_mode=transit,
                flight_estimate_per_pax=Decimal('8500.00') if transit == 'flight_coach' else Decimal('0.00'),
                train_estimate_per_pax=Decimal('2200.00') if transit == 'train_coach' else Decimal('0.00'),
                duration_days=days,
                duration_nights=nights,
                pricing_type='per_person',
                base_price=base_price,
                price_with_food=price_with_food,
                price_without_food=price_without_food,
                min_pax=2,
                hotel_star_category="Star Category Hotel & Resort",
                room_sharing_type='twin_sharing',
                meal_plan='MAP' if is_devo else 'CP',
                default_vehicle_type=v_sedan if days <= 4 else v_crysta,
                vehicle_seating_desc="Private Air-Conditioned Sedan / Crysta / Urbania Coach",
                bus_amenities_desc="AC, Clean Pushback Seats, First Aid Kit, Audio System, Chauffeur Guide",
                has_campfire_dj=True if 'hill_station' in cat else False,
                has_jeep_safari=True if any(k in title.lower() for k in ['safari', 'desert', 'kullu', 'corbett']) else False,
                has_boating=True if any(k in title.lower() for k in ['boat', 'cruise', 'alappuzha', 'dhow', 'nile', 'havelock']) else False,
                has_industrial_visit=False,
                is_devotional=is_devo,
                satvik_pure_veg_meals=is_devo,
                senior_citizen_friendly=is_devo,
                temple_dress_code="Traditional Dhoti/Kurta for Men, Saree/Chudidar for Women" if is_devo else "",
                is_international=is_intl,
                destination_country=country_name,
                visa_required=True if is_intl and country_name not in ['Nepal', 'Bhutan'] else False,
                visa_guidelines="Tourist eVisa application and documentation handled by Siva Gayathri Tours & Travels." if is_intl else "",
                passport_validity_months=6 if is_intl else 0,
                currency_code=currency,
                inclusions='\n'.join(f"- {item}" for item in inc_list),
                exclusions='\n'.join(f"- {item}" for item in exc_list),
                terms_and_conditions=terms,
                contact_persons_footer="Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131)",
                description=overview,
                is_active=True
            )
            packages_created += 1

            # Itinerary Days
            for it in p_data.get('itinerary', []):
                d_num = it['day']
                d_title = it['title']
                d_desc = it['description']
                if not d_desc:
                    d_desc = f"Guided sightseeing and transfers for Day {d_num} covering key landmarks of {dest}."

                all_itinerary_records.append(ItineraryDay(
                    package=pkg,
                    day_number=d_num,
                    title=f"Day {d_num}: {d_title}"[:250],
                    route_segment=f"{dest} Circuit"[:250],
                    activities=d_desc,
                    morning_activity=d_desc[:300],
                    sightseeing_spots=d_desc[:400],
                    evening_night_activity="Evening at leisure, shopping, and overnight hotel stay.",
                    meals_included="Breakfast & Dinner Included",
                    night_stay_location=f"Star Hotel in {dest.split(',')[0]}",
                    transport_info=f"AC Vehicle Transfer as per itinerary ({transit.replace('_', ' ').title()})"
                ))

            # 5-Tier Vehicle Tariffs
            for vt, tier, km_rate, bata in tariff_configs:
                if not vt:
                    continue
                daily = (300 * km_rate) + bata
                pkg_rate = days * daily
                all_tariff_records.append(PackageVehicleTariff(
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
                    interstate_permit_included=True if any(k in dest.lower() for k in ['kerala', 'karnataka', 'north', 'delhi', 'agra', 'jaipur']) else False,
                ))

            # Devotional Slots
            if is_devo:
                detected_temples = []
                lower_text = f"{title} {overview}".lower()
                if 'ayodhya' in lower_text:
                    detected_temples.append(('Shri Ram Janmabhoomi Teerth Kshetra, Ayodhya', 'Lord Shri Ram Lalla', '08:00 AM - 11:00 AM', 'Ram Mandir Complex Gate 1'))
                if 'kasi' in lower_text or 'varanasi' in lower_text:
                    detected_temples.append(('Kashi Vishwanath Jyotirlinga & Ganga Aarti', 'Lord Shiva Vishwanath & Ganga Aarti', '05:30 AM - 08:30 AM', 'Gate No 4 / Dashashwamedh Ghat'))
                if 'badrinath' in lower_text:
                    detected_temples.append(('Badrinath Dham Temple', 'Lord Badri Vishal', '06:30 AM - 10:30 AM', 'Simha Dwar Entrance'))
                if 'kedarnath' in lower_text or 'kedharnath' in lower_text:
                    detected_temples.append(('Kedarnath Jyotirlinga Temple', 'Lord Shiva Kedarnath', '06:00 AM - 11:00 AM', 'Main Mandir Precincts'))
                if 'amarnath' in lower_text:
                    detected_temples.append(('Shri Amarnath Cave Shrine', 'Baba Barfani Holy Ice Lingam', '07:00 AM - 12:00 PM', 'Holy Cave Sanctum'))
                if 'vaishnodevi' in lower_text or 'vaishnavidevi' in lower_text or 'vaishnavdevi' in lower_text:
                    detected_temples.append(('Maa Vaishno Devi Shrine, Katra', 'Maa Vaishno Devi Pindies', '06:00 AM - 10:00 AM', 'Bhawan Sanctum Gate'))
                if 'shirdi' in lower_text:
                    detected_temples.append(('Shirdi Sai Baba Samadhi Mandir', 'Shri Sai Baba', '06:00 AM - 09:00 AM', 'Gate No 1 / Kakad Aarti Queue'))
                if 'udupi' in lower_text:
                    detected_temples.append(('Udupi Sri Krishna Matha & Kanakana Kindi', 'Lord Sri Krishna', '07:00 AM - 09:30 AM', 'Gopura Entrance'))
                if 'murudeswarar' in lower_text or 'murudeshwar' in lower_text:
                    detected_temples.append(('Murudeshwar Shiva Temple & Rajagopura', 'Lord Shiva Murudeshwara', '08:00 AM - 10:00 AM', '20-Storey Raja Gopuram Gate'))
                if 'kollur' in lower_text:
                    detected_temples.append(('Kollur Mookambika Temple', 'Goddess Mookambika', '07:30 AM - 10:00 AM', 'Eastern Entrance'))
                if 'dharmasthala' in lower_text:
                    detected_temples.append(('Sri Manjunatha Swamy Temple, Dharmasthala', 'Lord Manjunatha', '08:00 AM - 11:00 AM', 'Main Sanctum Queue'))
                if 'kukke' in lower_text:
                    detected_temples.append(('Kukke Shri Subrahmanya Temple', 'Lord Subrahmanya', '07:00 AM - 09:30 AM', 'Main Temple Gopuram'))
                if 'rameshwaram' in lower_text or 'rameswaram' in lower_text:
                    detected_temples.append(('Sri Ramanathaswamy Temple, Rameswaram', 'Lord Shiva & 22 Theerthams', '06:00 AM - 08:30 AM', 'East Gopuram Gate'))
                if 'sabarimala' in lower_text:
                    detected_temples.append(('Sabarimala Sree Dharma Sastha Temple', 'Lord Ayyappa', '05:00 AM - 09:00 AM', 'Pathinettampadi (18 Holy Steps)'))
                if 'dwaraka' in lower_text or 'dwarka' in lower_text:
                    detected_temples.append(('Dwarkadhish Temple, Gujarat', 'Lord Dwarkadhish', '07:00 AM - 10:00 AM', 'Swarg Dwar Entrance'))
                if 'somnath' in lower_text:
                    detected_temples.append(('Somnath Jyotirlinga Shore Temple', 'Lord Shiva Somnath', '06:30 AM - 09:30 AM', 'Main Gateway'))

                if not detected_temples:
                    detected_temples.append(('Sacred Pilgrimage Temple Darshan', 'Presiding Deities', '07:00 AM - 09:30 AM', 'Main Temple Complex Entry'))

                for t_name, deity, slot_time, rep_loc in detected_temples:
                    all_darshan_records.append(TempleDarshanSlot(
                        package=pkg,
                        temple_name=t_name,
                        deity_or_circuit=deity,
                        darshan_type='special_entry_300',
                        booked_slot_time=slot_time,
                        token_ticket_number=f"SGT-SMT-DARSHAN-{abs(hash(t_name+title)) % 100000}",
                        reporting_location=rep_loc,
                        dress_code_notes="Strict Traditional Dhoti/Kurta for Men, Saree/Chudidar for Women",
                        prasad_details="Special Temple Prasadam and Holy Water Included",
                        senior_citizen_support=True
                    ))

            # International Document Checklists
            if is_intl:
                docs = [
                    ("Original Passport (Min 6 months validity from return date)", True, 15, "Clear color scan of front and back bio-pages"),
                    ("Passport Size Photographs (35x45mm, White background)", True, 10, "Matte finish, 80% facial coverage without border"),
                    (f"Tourist eVisa / Entry Authorization for {country_name}", True, 7, "Online processing assistance by Siva Gayathri Tours"),
                    ("Confirmed Round-Trip Flight Tickets & Hotel Vouchers", True, 5, "Issued and managed by Siva Gayathri Tours & Travels"),
                    ("Comprehensive Overseas Travel & Health Insurance Certificate", True, 5, "Mandatory minimum coverage as per embassy guidelines"),
                ]
                for dname, mand, dline, note in docs:
                    all_doc_records.append(InternationalDocumentChecklist(
                        package=pkg,
                        document_name=dname,
                        is_mandatory=mand,
                        submission_deadline_days=dline,
                        notes=note
                    ))

        # Bulk insertions
        print(f"Bulk inserting {len(all_itinerary_records)} ItineraryDay records...")
        ItineraryDay.objects.bulk_create(all_itinerary_records, batch_size=500)

        print(f"Bulk inserting {len(all_tariff_records)} PackageVehicleTariff records...")
        PackageVehicleTariff.objects.bulk_create(all_tariff_records, batch_size=500)

        if all_darshan_records:
            print(f"Bulk inserting {len(all_darshan_records)} TempleDarshanSlot records...")
            TempleDarshanSlot.objects.bulk_create(all_darshan_records, batch_size=500)

        if all_doc_records:
            print(f"Bulk inserting {len(all_doc_records)} InternationalDocumentChecklist records...")
            InternationalDocumentChecklist.objects.bulk_create(all_doc_records, batch_size=500)

    print("\n" + "="*80)
    print(f"SRI MURUGAN INGESTION COMPLETE: Successfully imported {packages_created} packages!")
    print(f"Itinerary Days: {len(all_itinerary_records)}")
    print(f"Vehicle Tariffs: {len(all_tariff_records)}")
    print(f"Temple Darshan Slots: {len(all_darshan_records)}")
    print(f"International Document Checklists: {len(all_doc_records)}")
    print("="*80)

if __name__ == '__main__':
    run_srimurugan_import()
