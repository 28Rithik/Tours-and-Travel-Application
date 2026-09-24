import os
import sys
import re
import json
import time
from decimal import Decimal
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

METADATA_FILE = os.path.join(os.path.dirname(__file__), 'trawell_catalog_metadata.json')
CACHE_FILE = os.path.join(os.path.dirname(__file__), 'scraped_trawell_cache.json')

# ==============================================================================
# Rebranding & Sanitization Engine
# ==============================================================================
def clean_rebrand(text: str) -> str:
    if not text:
        return ""
    s = text
    s = s.replace('\u2013', ' - ').replace('\u2014', ' - ').replace('\u00a0', ' ').replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    
    # Strip external URLs and links
    s = re.sub(r'https?://(?:www\.)?trawell\.in\S*', '', s, flags=re.I)
    s = re.sub(r'https?://(?:www\.)?tripzy\S*', '', s, flags=re.I)
    s = re.sub(r'wa\.me/\d+', 'wa.me/919842533777', s, flags=re.I)
    s = re.sub(r'trawell\.in@apl', 'sivagayathri@upi', s, flags=re.I)
    s = re.sub(r'\b(?:www\.)?trawell\.in\b', 'sivagayathritravels.com', s, flags=re.I)
    s = re.sub(r'\bTrawell(?:\.in)?\b', 'Siva Gayathri Tours & Travels', s, flags=re.I)
    s = re.sub(r'\bTripzy(?:\s+Vacations)?\b', 'Siva Gayathri Tours & Travels', s, flags=re.I)
    
    # Replace external numbers with official Siva Gayathri Contacts
    s = re.sub(r'\+91-?7799591230|\+91-?7995649483|\+91-?9535139583|\+91-?7032828835|\+91-?8904776486', '+91 98425 33777', s)
    s = re.sub(r'77995-91230|79956-49483|95351-39583|70328-28835|89047-76486', '+91 98425 33777', s)
    s = re.sub(r'\[email\s*protected\]', 'info@sivagayathritravels.com', s, flags=re.I)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def map_category(title: str, tags: list, dest: str, days: int) -> str:
    combined = f"{title} {' '.join(tags)} {dest}".lower()
    
    if any(k in combined for k in ['thailand', 'sri lanka', 'bali', 'dubai', 'singapore', 'maldives', 'malaysia', 'international']):
        return 'international'
    if days == 1 or 'one day' in combined or 'day tour' in combined:
        return 'local_tour'
    if any(k in combined for k in ['temple', 'pilgrimage', 'darshan', 'jyotirlinga', 'sthalang', 'divya', 'shiva', 'rameshwaram', 'madurai', 'tirupati', 'kanchipuram', 'shirdi', 'kashi', 'varanasi', 'puri', 'ayodhya', 'somnath', 'murudeshwar']):
        return 'devotional'
    if any(k in combined for k in ['ooty', 'munnar', 'coorg', 'kodaikanal', 'chikmagalur', 'wayanad', 'yercaud', 'yelagiri', 'shimla', 'manali', 'kashmir', 'nainital', 'mussoorie', 'darjeeling', 'hill station', 'panchgani', 'mahabaleshwar']):
        return 'hill_station'
    if any(k in combined for k in ['honeymoon', 'family', 'resort', 'leisure']):
        return 'family_vacation'
    return 'holiday'

# Worker session pool
def get_page(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return ""

def parse_trawell_tour(card_meta: dict) -> dict:
    tour_url = card_meta['tour_url']
    t_code = card_meta['tour_code']
    html = get_page(tour_url)
    
    raw_title = card_meta.get('title', '')
    inclusions = []
    itin_url = card_meta.get('itinerary_url')

    if html:
        soup = BeautifulSoup(html, 'html.parser')
        h1 = soup.find('h1')
        if h1 and h1.get_text(strip=True):
            raw_title = h1.get_text(strip=True)

        inc_header = soup.find(lambda tag: tag.name in ['h2', 'h3', 'h4', 'strong'] and 'inclusions' in tag.get_text().lower())
        if inc_header:
            ul = inc_header.find_next('ul')
            if ul:
                for li in ul.find_all('li'):
                    txt = clean_rebrand(li.get_text(strip=True))
                    if txt and len(txt) > 3:
                        inclusions.append(txt)

        if not itin_url:
            for a in soup.find_all('a', href=True):
                if '/itineraries/' in a['href'] and ('trip' in a['href'] or 'tour' in a['href'] or 'days' in a['href']):
                    href = a['href'].strip()
                    if href.startswith('/'):
                        href = 'https://www.trawell.in' + href
                    itin_url = href
                    break

    title = clean_rebrand(raw_title).upper()
    if not title:
        title = f"{t_code} TOUR PACKAGE"
    if not any(title.endswith(suf) for suf in ['TOUR', 'PACKAGE', 'TRIP', 'GETAWAY', 'EXPEDITION', 'SPECIAL']):
        title = f"{title} TOUR PACKAGE"

    if not inclusions:
        inclusions = [
            "Chauffeur-driven private tourist vehicle for the entire circuit",
            "Verified premium star hotel accommodation on twin/triple sharing",
            "Complimentary daily breakfast at hotel dining halls",
            "Interstate passenger permits, highway toll charges, and vehicle parking fees",
            "Driver allowance, night bata, and fuel expenses included",
            "All applicable travel taxes & GST included with zero hidden charges",
            "Dedicated 24/7 tour manager support from Siva Gayathri Tours & Travels"
        ]

    exclusions = [
        "Airfare, train tickets, or transit to the tour starting city",
        "Lunch, dinner, snacks, and bottled mineral beverages",
        "Monument entry fees, special temple darshan tickets, and local guide fees",
        "Boating, jeep safari, adventure activities, and optional sightseeing rides",
        "Hotel early check-in or late check-out beyond hotel standard timings",
        "Personal expenses, room service, laundry, and tips"
    ]

    duration_str = card_meta.get('duration_str', '')
    days = 3
    nights = 2
    m_dur = re.search(r'(\d+)\s*D(?:ays?)?\s*/\s*(\d+)\s*N(?:ights?)?', duration_str, re.I)
    if m_dur:
        days = int(m_dur.group(1))
        nights = int(m_dur.group(2))
    else:
        m_dur2 = re.search(r'(\d+)\s*Days?', title, re.I)
        if m_dur2:
            days = int(m_dur2.group(1))
            nights = max(1, days - 1) if days > 1 else 0

    offer_price = card_meta.get('offer_price')
    if not offer_price or offer_price <= 0:
        offer_price = max(4500, days * 2400)
    base_price = float(offer_price)

    # Detailed Itinerary Days
    itinerary_days = []
    destination = "South India"
    if itin_url:
        itin_html = get_page(itin_url)
        if itin_html:
            itin_soup = BeautifulSoup(itin_html, 'html.parser')
            
            # Extract day navigation titles
            day_nav_titles = []
            for h in itin_soup.find_all(['h2', 'h3', 'h4']):
                ht = h.get_text(' ', strip=True)
                if 'DAY 1 :' in ht and 'DAY 2 :' in ht:
                    parts = re.split(r'(DAY\s*\d+\s*:)', ht, flags=re.I)
                    for i in range(1, len(parts), 2):
                        full_d_title = (parts[i] + parts[i+1]).strip()
                        day_nav_titles.append(clean_rebrand(full_d_title))
                    break

            # Extract numbered sights
            numbered_sights = []
            for h in itin_soup.find_all(['h2', 'h3', 'h4']):
                ht = h.get_text(strip=True)
                if re.match(r'^\d+\.\s+[A-Za-z]', ht):
                    # Sibling description
                    desc_p = []
                    curr = h.find_next_sibling()
                    while curr and curr.name in ['p', 'div', 'span'] and not re.match(r'^\d+\.\s+[A-Za-z]', curr.get_text(strip=True)):
                        t = curr.get_text(' ', strip=True)
                        if len(t) > 20 and not any(k in t.lower() for k in ['reviews', 'contact our', 'request quote']):
                            desc_p.append(clean_rebrand(t))
                        curr = curr.find_next_sibling()
                        if len(desc_p) >= 2:
                            break
                    sight_desc = " ".join(desc_p)
                    numbered_sights.append({
                        'name': clean_rebrand(ht),
                        'desc': sight_desc
                    })

            # Formulate Day Itineraries
            total_days_target = max(len(day_nav_titles), days)
            sights_per_day = max(1, len(numbered_sights) // total_days_target) if numbered_sights else 0

            for d in range(1, total_days_target + 1):
                d_title = day_nav_titles[d-1] if d <= len(day_nav_titles) else f"Day {d}: Sightseeing & Leisure Circuit"
                
                # Assign sights
                start_s = (d - 1) * sights_per_day
                end_s = start_s + sights_per_day if d < total_days_target else len(numbered_sights)
                day_sights = numbered_sights[start_s:end_s] if numbered_sights else []

                sight_text_blocks = []
                for s in day_sights:
                    if s['desc']:
                        sight_text_blocks.append(f"• {s['name']}: {s['desc']}")
                    else:
                        sight_text_blocks.append(f"• {s['name']}: Prime sightseeing landmark with scenic views and photo opportunities.")

                if sight_text_blocks:
                    narrative = f"{d_title}. Morning departure for scheduled sightseeing. Points covered:\n" + "\n".join(sight_text_blocks)
                else:
                    narrative = f"{d_title}. Experience scheduled morning and afternoon sightseeing with private tourist vehicle support, scenic viewpoints, photo stops, and evening relaxation arranged by Siva Gayathri Tours & Travels."

                # Stay city
                stay_city = "Destination Hotel"
                if 'to ' in d_title.lower():
                    stay_city = d_title.split('to ')[-1].split('&')[0].strip()
                elif 'in ' in d_title.lower():
                    stay_city = d_title.split('in ')[-1].split('&')[0].strip()

                itinerary_days.append({
                    'day_number': d,
                    'title': d_title[:255],
                    'description': narrative[:2500],
                    'stay_city': stay_city[:50],
                    'meals': 'Breakfast Included'
                })

    # If no itinerary page could be parsed, build standard complete days
    if not itinerary_days:
        for d in range(1, days + 1):
            itinerary_days.append({
                'day_number': d,
                'title': f"Day {d}: Sightseeing & Destination Exploration",
                'description': f"Full day tour covering key destination landmarks, cultural sights, and scenic viewpoints with private chauffeur-driven tourist vehicle. Personalized schedule and comfortable overnight stay arranged by Siva Gayathri Tours & Travels.",
                'stay_city': "Destination Hotel",
                'meals': 'Breakfast Included'
            })

    dest_candidates = [d['stay_city'] for d in itinerary_days if d['stay_city'] and d['stay_city'] != 'Destination Hotel']
    if dest_candidates:
        destination = " - ".join(list(dict.fromkeys(dest_candidates))[:4])
    else:
        destination = card_meta.get('distance_str', 'South India Circuit')

    cat = map_category(title, card_meta.get('category_tags', []), destination, days)

    return {
        'tour_code': t_code,
        'title': title,
        'destination': destination,
        'category': cat,
        'duration_days': days,
        'duration_nights': nights,
        'base_price': base_price,
        'inclusions': "\n".join(f"• {x}" for x in inclusions),
        'exclusions': "\n".join(f"• {x}" for x in exclusions),
        'itinerary_days': itinerary_days
    }

# ==============================================================================
# Ingestion Engine
# ==============================================================================
def ingest_all(parsed_list: list):
    print("\n" + "=" * 70, flush=True)
    print(f"INGESTING {len(parsed_list)} PACKAGES INTO DJANGO DATABASE", flush=True)
    print("=" * 70, flush=True)

    vtypes = list(VehicleType.objects.all())
    sedan_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['sedan', 'dzire', 'etios'])), vtypes[0] if vtypes else None)
    crysta_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['crysta', 'innova'])), vtypes[1] if len(vtypes) > 1 else sedan_vt)
    urbania_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['urbania', 'tempo', '17'])), vtypes[2] if len(vtypes) > 2 else sedan_vt)
    bus36_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['36', 'mini', '40'])), vtypes[3] if len(vtypes) > 3 else sedan_vt)
    coach54_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['54', 'coach', '52', 'volvo'])), vtypes[4] if len(vtypes) > 4 else sedan_vt)

    tariff_configs = [
        (sedan_vt, '4_sedan', Decimal('12.00'), Decimal('150.00'), Decimal('400.00')),
        (crysta_vt, '7_crysta', Decimal('19.00'), Decimal('250.00'), Decimal('500.00')),
        (urbania_vt, '17_tt_urbania', Decimal('26.00'), Decimal('300.00'), Decimal('600.00')),
        (bus36_vt, '36_mini_bus', Decimal('42.00'), Decimal('450.00'), Decimal('800.00')),
        (coach54_vt, '54_luxury_coach', Decimal('55.00'), Decimal('600.00'), Decimal('1000.00')),
    ]

    saved_count = 0
    updated_count = 0
    days_count = 0
    tariffs_count = 0
    darshan_count = 0
    intl_count = 0

    batch_size = 50
    for i in range(0, len(parsed_list), batch_size):
        batch = parsed_list[i:i + batch_size]
        with transaction.atomic():
            for pdata in batch:
                code = f"SGT-TRW-{pdata['tour_code']}"
                base_p = Decimal(str(pdata['base_price']))
                days = pdata['duration_days']
                nights = pdata['duration_nights']

                price_with_food = (base_p * Decimal('1.25')).quantize(Decimal('1.00'))
                price_without_food = base_p.quantize(Decimal('1.00'))

                pkg, created = Package.objects.update_or_create(
                    package_code=code,
                    defaults={
                        'name': pdata['title'][:255],
                        'destination': pdata['destination'][:255],
                        'category': pdata['category'],
                        'duration_days': days,
                        'duration_nights': nights,
                        'pricing_type': 'per_person',
                        'base_price': base_p,
                        'price_with_food': price_with_food,
                        'price_without_food': price_without_food,
                        'transit_mode': 'flight_coach' if pdata['category'] == 'international' else 'road_coach',
                        'flight_estimate_per_pax': Decimal('15000.00') if pdata['category'] == 'international' else Decimal('0.00'),
                        'train_estimate_per_pax': Decimal('0.00'),
                    }
                )

                if created:
                    saved_count += 1
                else:
                    updated_count += 1

                pkg.itinerary_days.all().delete()
                pkg.vehicle_tariffs.all().delete()
                pkg.temple_slots.all().delete()
                pkg.intl_documents.all().delete()

                for d in pdata['itinerary_days']:
                    ItineraryDay.objects.create(
                        package=pkg,
                        day_number=d['day_number'],
                        title=d['title'][:250],
                        route_segment=f"{pdata['destination']} - Day {d['day_number']}"[:250],
                        activities=d['description'],
                        sightseeing_spots=d['title'][:500],
                        night_stay_location=d['stay_city'][:250],
                        meals_included=d['meals'][:250],
                        hotel_info=d['stay_city'][:250],
                        transport_info="Dedicated AC Tourist Vehicle"
                    )
                    days_count += 1

                for vt, tier, km_rate, extra_hr, bata in tariff_configs:
                    if vt:
                        daily = (300 * km_rate) + bata
                        pkg_rate = max(base_p, days * daily)
                        PackageVehicleTariff.objects.create(
                            package=pkg,
                            vehicle_type=vt,
                            seating_tier=tier,
                            rate_type='outstation_multiday' if days > 1 else 'outstation_day',
                            package_rate=Decimal(str(round(pkg_rate, 2))),
                            per_day_rate=Decimal(str(round(daily, 2))),
                            included_km=days * 300,
                            extra_km_rate=km_rate,
                            extra_hour_rate=extra_hr,
                            driver_bata_per_day=bata,
                            driver_bata_included=True,
                            toll_parking_included=True,
                            interstate_permit_included=True
                        )
                        tariffs_count += 1

                if pdata['category'] == 'devotional':
                    TempleDarshanSlot.objects.create(
                        package=pkg,
                        temple_name=f"{pdata['destination']} Sacred Temple Darshan"[:200],
                        deity_or_circuit="Sacred Deity / Spiritual Circuit"[:150],
                        darshan_type='special_entry_300',
                        booked_slot_time="09:00 AM - 11:30 AM",
                        reporting_location="Main Temple Entrance / Q Complex",
                        dress_code_notes="Strict Traditional: Dhoti/Kurta for Men, Saree/Chudidar for Women",
                        prasad_details="Special Darshan Prasadam Included",
                        senior_citizen_support=True
                    )
                    darshan_count += 1

                if pdata['category'] == 'international':
                    InternationalDocumentChecklist.objects.create(
                        package=pkg,
                        document_name="Original Passport (min 6 months validity)",
                        is_mandatory=True,
                        submission_deadline_days=7,
                        notes="Original Passport with at least 2 blank pages"
                    )
                    InternationalDocumentChecklist.objects.create(
                        package=pkg,
                        document_name="Tourist Visa & Travel Insurance",
                        is_mandatory=True,
                        submission_deadline_days=5,
                        notes="Approved Tourist Visa and valid travel insurance"
                    )
                    intl_count += 2

        print(f"  Ingested {min(i + batch_size, len(parsed_list))}/{len(parsed_list)} packages into database...", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("ALL TRAWELL PACKAGES SUCCESSFULLY INGESTED!", flush=True)
    print(f"  • Total Packages Ingested : {saved_count + updated_count} (New: {saved_count}, Updated: {updated_count})", flush=True)
    print(f"  • Itinerary Days Created : {days_count}", flush=True)
    print(f"  • 5-Tier Tariffs Created  : {tariffs_count}", flush=True)
    print(f"  • Temple Darshan Slots    : {darshan_count}", flush=True)
    print(f"  • Intl Checklists Created : {intl_count}", flush=True)
    print("=" * 70, flush=True)

def main():
    print("=" * 70, flush=True)
    print("SIVA GAYATHRI TOURS — HIGH-SPEED PARALLEL TRAWELL SCRAPER & INGESTOR", flush=True)
    print("=" * 70, flush=True)

    if not os.path.exists(METADATA_FILE):
        print(f"Metadata file {METADATA_FILE} not found!", flush=True)
        return

    with open(METADATA_FILE, 'r', encoding='utf-8') as f:
        meta_dict = json.load(f)

    print(f"Loaded {len(meta_dict)} discovered package records.", flush=True)

    # Cache handling
    cached_data = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            print(f"Found {len(cached_data)} existing cached parsed packages.", flush=True)
        except:
            cached_data = {}

    to_scrape = [p for p in meta_dict.values() if p['tour_code'] not in cached_data]
    print(f"Packages to parse from network: {len(to_scrape)} (Already cached: {len(cached_data)})", flush=True)

    # Scrape with ThreadPoolExecutor
    if to_scrape:
        with ThreadPoolExecutor(max_workers=18) as executor:
            future_to_meta = {executor.submit(parse_trawell_tour, p): p for p in to_scrape}
            completed = 0
            for future in as_completed(future_to_meta):
                completed += 1
                try:
                    res = future.result()
                    if res:
                        cached_data[res['tour_code']] = res
                except Exception:
                    pass

                if completed % 50 == 0 or completed == len(to_scrape):
                    print(f"  Parsed {completed}/{len(to_scrape)} packages... (Total cached: {len(cached_data)})", flush=True)
                    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                        json.dump(cached_data, f, indent=2, default=str)

        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cached_data, f, indent=2, default=str)

    parsed_list = list(cached_data.values())
    print(f"\nAll {len(parsed_list)} packages structured and ready for database ingestion.", flush=True)

    # Ingest into Django DB
    ingest_all(parsed_list)

if __name__ == '__main__':
    main()
