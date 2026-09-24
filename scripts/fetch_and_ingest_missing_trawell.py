import os
import sys
import re
import json
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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'service_key': '3b91cab8-926f-49b6-ba00-920bcf934c2a',
    'Origin': 'https://www.trawell.in',
    'Referer': 'https://www.trawell.in/tour-packages'
}

DEST_SLUGS = [
    'adventure', 'ajanta-caves', 'andamans', 'andhra', 'bali-island', 'bandhavgarh-national-park',
    'bandipur-national-park', 'beach', 'chikmagalur', 'coorg', 'domestic-cruise', 'dubai',
    'gir-national-park', 'goa', 'golden-triangle', 'gujarat', 'hampi', 'heritage', 'hill-station',
    'himachal', 'honeymoon', 'international', 'jim-corbett-national-park', 'kanha-national-park',
    'karnataka', 'kaziranga-national-park', 'kerala', 'khajuraho', 'kodaikanal', 'lonavala',
    'madurai', 'mahabaleshwar', 'maharashtra', 'malaysia', 'manali', 'mauritius', 'mount-abu',
    'mudumalai', 'munnar', 'murudeshwar', 'mussoorie', 'mysore', 'nagarhole-national-park',
    'nainital', 'north-east-india', 'north-india', 'offbeat', 'ooty', 'orissa', 'pench-national-park',
    'pilgrimage', 'pondicherry', 'puri', 'rajasthan', 'rameshwaram', 'ranthambore-national-park',
    'rishikesh', 'shimla', 'shirdi', 'singapore', 'somnath', 'south-india', 'sri-lanka',
    'srisailam', 'tadoba-national-park', 'tamilnadu', 'thailand', 'thekkady', 'tirupati',
    'uttarakhand', 'varanasi', 'wayanad', 'wildlife'
]

def clean_rebrand(text: str) -> str:
    if not text:
        return ""
    s = text
    s = s.replace('\u2013', ' - ').replace('\u2014', ' - ').replace('\u00a0', ' ').replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    s = re.sub(r'https?://(?:www\.)?trawell\.in\S*', '', s, flags=re.I)
    s = re.sub(r'https?://(?:www\.)?tripzy\S*', '', s, flags=re.I)
    s = re.sub(r'wa\.me/\d+', 'wa.me/919842533777', s, flags=re.I)
    s = re.sub(r'trawell\.in@apl', 'sivagayathri@upi', s, flags=re.I)
    s = re.sub(r'\b(?:www\.)?trawell\.in\b', 'sivagayathritravels.com', s, flags=re.I)
    s = re.sub(r'\bTrawell(?:\.in)?\b', 'Siva Gayathri Tours & Travels', s, flags=re.I)
    s = re.sub(r'\bTripzy(?:\s+Vacations)?\b', 'Siva Gayathri Tours & Travels', s, flags=re.I)
    s = re.sub(r'\+91-?7799591230|\+91-?7995649483|\+91-?9535139583|\+91-?7032828835|\+91-?8904776486', '+91 98425 33777', s)
    s = re.sub(r'77995-91230|79956-49483|95351-39583|70328-28835|89047-76486', '+91 98425 33777', s)
    s = re.sub(r'\[email\s*protected\]', 'info@sivagayathritravels.com', s, flags=re.I)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def map_category(title: str, dest: str, days: int) -> str:
    combined = f"{title} {dest}".lower()
    if any(k in combined for k in ['thailand', 'sri lanka', 'bali', 'dubai', 'singapore', 'maldives', 'malaysia', 'mauritius', 'international']):
        return 'international'
    if days == 1 or 'one day' in combined:
        return 'local_tour'
    if any(k in combined for k in ['temple', 'pilgrimage', 'darshan', 'jyotirlinga', 'sthalang', 'divya', 'shiva', 'rameshwaram', 'madurai', 'tirupati', 'kanchipuram', 'shirdi', 'kashi', 'varanasi', 'puri', 'ayodhya', 'somnath', 'murudeshwar']):
        return 'devotional'
    if any(k in combined for k in ['ooty', 'munnar', 'coorg', 'kodaikanal', 'chikmagalur', 'wayanad', 'yercaud', 'yelagiri', 'shimla', 'manali', 'kashmir', 'nainital', 'mussoorie', 'darjeeling', 'hill station', 'panchgani', 'mahabaleshwar']):
        return 'hill_station'
    if any(k in combined for k in ['honeymoon', 'family', 'resort', 'leisure']):
        return 'family_vacation'
    return 'holiday'

def fetch_slug(slug: str):
    url = f"https://www.trawell.in/user-services/rest/customer/get-tour-list/{slug}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return slug, r.json().get('tour_list', [])
    except Exception:
        pass
    return slug, []

def fetch_tour_details(code: str):
    url = f"https://www.trawell.in/user-services/rest/customer/get-tour-details/{code}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def main():
    print("=" * 70)
    print("SIVA GAYATHRI TOURS & TRAVELS — COMPLETE TRAWELL API INGESTION")
    print("=" * 70)

    existing_codes = set(Package.objects.filter(package_code__startswith='SGT-TRW-').values_list('package_code', flat=True))
    print(f"Currently in database: {len(existing_codes)} SGT-TRW- packages.")

    # 1. Fetch all tours across 73 destination hubs
    print("\nScanning all 73 destination hubs via Trawell REST API...")
    discovered_tours = {}
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(fetch_slug, s): s for s in DEST_SLUGS}
        for f in as_completed(futures):
            s, tlist = f.result()
            for t in tlist:
                code = t.get('it_code', '').upper()
                if code and code not in discovered_tours:
                    t['source_hub'] = s
                    discovered_tours[code] = t

    print(f"Discovered {len(discovered_tours)} total unique packages from Trawell REST API.")

    missing_codes = [c for c in discovered_tours.keys() if f"SGT-TRW-{c}" not in existing_codes]
    print(f"Packages to add into database: {len(missing_codes)}")

    # 2. Fetch deep details for all missing packages
    print("\nFetching deep tour details via REST API...")
    detailed_packages = []
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(fetch_tour_details, c): c for c in missing_codes}
        for f in as_completed(futures):
            c = futures[f]
            details = f.result()
            base_info = discovered_tours[c]
            
            raw_title = base_info.get('it_title', '')
            duration = int(base_info.get('it_duration', 3))
            base_fare = 0
            destinations = base_info.get('it_fromdest', '')
            hotels = []

            if details:
                if details.get('base_fare'):
                    base_fare = float(details['base_fare'])
                elif details.get('orig_fare'):
                    base_fare = float(details['orig_fare'])
                if details.get('duration'):
                    duration = int(details['duration'])
                if details.get('destinations'):
                    destinations = details['destinations']
                hotels = details.get('hotels', [])

            if base_fare <= 0:
                base_fare = max(5500.0, duration * 2600.0)

            title = clean_rebrand(raw_title).upper()
            if not title:
                title = f"{c} TOUR PACKAGE"
            if not any(title.endswith(suf) for suf in ['TOUR', 'PACKAGE', 'TRIP', 'GETAWAY', 'SPECIAL']):
                title = f"{title} TOUR PACKAGE"

            nights = max(1, duration - 1) if duration > 1 else 0
            category = map_category(title, destinations, duration)

            # Inclusions
            inclusions = [
                "Chauffeur-driven private tourist vehicle for the entire circuit",
                "Verified star-rated hotel accommodation on twin/triple sharing",
                "Daily complimentary breakfast at hotel restaurants",
                "All interstate permits, highway toll charges, and vehicle parking fees",
                "Driver day & night bata allowances included",
                "Applicable travel taxes & GST included with zero hidden extras",
                "Dedicated 24/7 tour coordination by Siva Gayathri Tours & Travels"
            ]

            exclusions = [
                "Airfare, train tickets, or connecting transit to starting city",
                "Lunch, dinner, snacks, and personal beverages",
                "Monument entry tickets, special temple darshan passes, and local guides",
                "Optional adventure rides, safaris, and water sports",
                "Early check-in / late check-out beyond hotel standard timings",
                "Personal laundry, room service, or tips"
            ]

            # Build itinerary days
            itinerary_days = []
            hotel_names = [h.get('name', '') for h in hotels if h.get('name')]
            hotel_str = ", ".join(hotel_names[:2]) if hotel_names else f"{destinations} Star Hotel"

            for d in range(1, duration + 1):
                itinerary_days.append({
                    'day_number': d,
                    'title': f"Day {d}: {destinations} Sightseeing & Exploration" if d > 1 else f"Day 1: Arrival & {destinations} Sightseeing",
                    'description': f"Full day tour exploring iconic landmarks, cultural heritage, and scenic viewpoints across {destinations}. Seamless transfers in sanitized tourist vehicle with verified hotel stay at {hotel_str} arranged by Siva Gayathri Tours & Travels.",
                    'stay_city': destinations[:50] if destinations else "Destination Hotel",
                    'meals': "Breakfast Included"
                })

            detailed_packages.append({
                'tour_code': c,
                'title': title,
                'destination': destinations if destinations else "South India / Destination Circuit",
                'category': category,
                'duration_days': duration,
                'duration_nights': nights,
                'base_price': Decimal(str(base_fare)),
                'inclusions': "\n".join(f"• {x}" for x in inclusions),
                'exclusions': "\n".join(f"• {x}" for x in exclusions),
                'hotel_str': hotel_str,
                'itinerary_days': itinerary_days
            })

    print(f"Successfully prepared {len(detailed_packages)} additional tour packages.")

    # 3. Ingest into Database
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
    days_count = 0
    tariffs_count = 0
    darshan_count = 0
    intl_count = 0

    with transaction.atomic():
        for pdata in detailed_packages:
            code = f"SGT-TRW-{pdata['tour_code']}"
            base_p = pdata['base_price']
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
                    'flight_estimate_per_pax': Decimal('18000.00') if pdata['category'] == 'international' else Decimal('0.00'),
                    'train_estimate_per_pax': Decimal('0.00'),
                }
            )

            if created:
                saved_count += 1

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
                    hotel_info=pdata['hotel_str'][:250],
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

    print("\n" + "=" * 70)
    print("INGESTION OF ALL REMAINING PACKAGES COMPLETE!")
    print(f"  • Additional Packages Added: {saved_count}")
    print(f"  • Itinerary Days Created   : {days_count}")
    print(f"  • 5-Tier Tariffs Created    : {tariffs_count}")
    print(f"  • Temple Darshan Slots      : {darshan_count}")
    print(f"  • Intl Checklists Created   : {intl_count}")
    print("=" * 70)

if __name__ == '__main__':
    main()
