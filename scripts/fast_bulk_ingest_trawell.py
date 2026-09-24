import os
import sys
import re
import json
import time
from decimal import Decimal
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from django.db import connection, transaction
from packages.models import (
    Package,
    ItineraryDay,
    PackageVehicleTariff,
    TempleDarshanSlot,
    InternationalDocumentChecklist,
)
from core.models import VehicleType

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

INTL_REGEX = re.compile(r'\b(thailand|sri lanka|bali|dubai|singapore|maldives|malaysia|mauritius|international|bangkok|phuket|pattaya|colombo|kandy|bentota|sigiriya|nuwara eliya)\b', re.I)
DEVOTIONAL_REGEX = re.compile(r'\b(temple|pilgrimage|darshan|jyotirlinga|sthalang|divya|shiva|rameshwaram|madurai|tirupati|kanchipuram|shirdi|kashi|varanasi|puri|ayodhya|somnath|murudeshwar|srisailam|mahabalipuram)\b', re.I)
HILL_REGEX = re.compile(r'\b(ooty|munnar|coorg|kodaikanal|chikmagalur|wayanad|yercaud|yelagiri|shimla|manali|kashmir|nainital|mussoorie|darjeeling|hill station|panchgani|mahabaleshwar)\b', re.I)

def map_category(title: str, dest: str, hub: str, days: int) -> str:
    combined = f"{title} {dest} {hub}".lower()
    if INTL_REGEX.search(combined):
        return 'international'
    if days == 1 or 'one day' in combined or '1 day' in combined:
        return 'local_tour'
    if DEVOTIONAL_REGEX.search(combined):
        return 'devotional'
    if HILL_REGEX.search(combined):
        return 'hill_station'
    if any(k in combined for k in ['honeymoon', 'family', 'resort', 'leisure', 'beach', 'goa', 'andamans']):
        return 'family_vacation'
    return 'holiday'

def parse_stay_plan(stay_str: str, duration: int, default_dest: str):
    plan = []
    if stay_str and ':' in stay_str:
        parts = stay_str.split(';')
        for p in parts:
            if ':' in p:
                city, nights_s = p.split(':', 1)
                try:
                    nights = int(nights_s.strip())
                    plan.append((city.strip(), nights))
                except ValueError:
                    pass
    if not plan:
        plan = [(default_dest if default_dest else "Destination Hotel", max(1, duration - 1))]
    return plan

def main():
    t0 = time.time()
    print("=" * 70, flush=True)
    print("SIVA GAYATHRI TOURS & TRAVELS — ULTRA-FAST BULK INGESTION (1,369 TOURS)", flush=True)
    print("=" * 70, flush=True)

    # Enable fast sqlite writes
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA synchronous = OFF;")
        cursor.execute("PRAGMA journal_mode = MEMORY;")

    with open('scripts/trawell_all_api_tours.json', 'r', encoding='utf-8') as f:
        tours = json.load(f)

    with open('scripts/trawell_all_details_cache.json', 'r', encoding='utf-8') as f:
        details = json.load(f)

    print(f"Loaded {len(tours)} master tours and {len(details)} details.", flush=True)

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

    print("\nPurging previous SGT-TRW- records for clean state...", flush=True)
    with transaction.atomic():
        deleted_count, _ = Package.objects.filter(package_code__startswith='SGT-TRW-').delete()
    print(f"Purged previous records ({deleted_count} items cascade removed).", flush=True)

    print("\nPreparing package models in memory...", flush=True)
    packages_to_create = []
    meta_by_code = {}
    cats_counter = Counter()

    for code, t_info in tours.items():
        d_info = details.get(code, {})

        raw_title = t_info.get('it_title') or d_info.get('it_title') or f"{code} Tour"
        title = clean_rebrand(raw_title).upper()
        if not any(title.endswith(suf) for suf in ['TOUR', 'PACKAGE', 'TRIP', 'GETAWAY', 'SPECIAL', 'CIRCUIT']):
            title = f"{title} TOUR PACKAGE"

        hub = t_info.get('source_hub', '')
        dest = d_info.get('destinations') or t_info.get('it_fromdest') or hub.replace('-', ' ').title()
        dest = clean_rebrand(dest)

        duration = 3
        if d_info.get('duration'):
            try:
                duration = int(d_info['duration'])
            except (ValueError, TypeError):
                pass
        elif t_info.get('it_duration'):
            try:
                duration = int(t_info['it_duration'])
            except (ValueError, TypeError):
                pass

        nights = max(1, duration - 1) if duration > 1 else 0

        fare = 0.0
        if d_info.get('base_fare'):
            try:
                fare = float(d_info['base_fare'])
            except (ValueError, TypeError):
                pass
        if fare <= 0 and d_info.get('orig_fare'):
            try:
                fare = float(d_info['orig_fare'])
            except (ValueError, TypeError):
                pass
        if fare <= 0 and t_info.get('base_fare'):
            try:
                fare = float(t_info['base_fare'])
            except (ValueError, TypeError):
                pass
        if fare <= 0:
            fare = max(4500.0, duration * 2400.0)

        category = map_category(title, dest, hub, duration)
        cats_counter[category] += 1

        hotels = d_info.get('hotels', [])
        hotel_names = []
        for h in hotels:
            hname = clean_rebrand(h.get('name', ''))
            hstar = h.get('star_rating', '')
            if hname:
                hotel_names.append(f"{hname} ({hstar}★)" if hstar else hname)
        hotel_str = ", ".join(hotel_names[:3]) if hotel_names else f"{dest} Verified Tourist Hotel"

        base_price = Decimal(str(round(fare, 2)))
        price_with_food = (base_price * Decimal('1.25')).quantize(Decimal('1.00'))
        price_without_food = base_price.quantize(Decimal('1.00'))

        pkg_code = f"SGT-TRW-{code}"
        packages_to_create.append(Package(
            package_code=pkg_code,
            name=title[:255],
            destination=dest[:255],
            category=category,
            duration_days=duration,
            duration_nights=nights,
            pricing_type='per_person',
            base_price=base_price,
            price_with_food=price_with_food,
            price_without_food=price_without_food,
            transit_mode='flight_coach' if category == 'international' else 'road_coach',
            flight_estimate_per_pax=Decimal('18000.00') if category == 'international' else Decimal('0.00'),
            train_estimate_per_pax=Decimal('0.00'),
        ))

        meta_by_code[pkg_code] = {
            'code': code,
            'dest': dest,
            'category': category,
            'duration': duration,
            'hotel_str': hotel_str,
            'stay_str': d_info.get('stay', ''),
            'base_price': base_price
        }

    print(f"Bulk creating {len(packages_to_create)} Package models...", flush=True)
    with transaction.atomic():
        Package.objects.bulk_create(packages_to_create, batch_size=500)
    print("Packages created in database!", flush=True)

    # Retrieve all created packages to get IDs
    pkg_map = {p.package_code: p for p in Package.objects.filter(package_code__startswith='SGT-TRW-')}
    print(f"Mapped {len(pkg_map)} packages for child relations.", flush=True)

    days_to_create = []
    tariffs_to_create = []
    darshan_to_create = []
    intl_to_create = []

    for pkg_code, p_obj in pkg_map.items():
        meta = meta_by_code[pkg_code]
        dest = meta['dest']
        category = meta['category']
        duration = meta['duration']
        hotel_str = meta['hotel_str']
        base_price = meta['base_price']

        # Itinerary Days
        stay_plan = parse_stay_plan(meta['stay_str'], duration, dest)
        current_day = 1
        for city, n_nights in stay_plan:
            for n in range(n_nights):
                if current_day > duration:
                    break
                day_title = f"Day {current_day}: Arrival & {city} Sightseeing" if current_day == 1 else f"Day {current_day}: {city} Sightseeing & Exploration"
                activities = (
                    f"Full day exploration covering iconic landmarks, cultural attractions, and scenic vistas in and around {city}. "
                    f"Comfortable transfers in chauffeur-driven AC tourist vehicle with premium overnight stay at {hotel_str} "
                    f"arranged and managed exclusively by Siva Gayathri Tours & Travels."
                )
                days_to_create.append(ItineraryDay(
                    package=p_obj,
                    day_number=current_day,
                    title=day_title[:250],
                    route_segment=f"{city} Sightseeing Circuit"[:250],
                    activities=activities,
                    sightseeing_spots=f"{city} Major Attractions & Scenic Viewpoints"[:500],
                    night_stay_location=city[:250],
                    meals_included="Breakfast Included",
                    hotel_info=hotel_str[:250],
                    transport_info="Dedicated AC Tourist Vehicle"
                ))
                current_day += 1

        while current_day <= duration:
            last_city = stay_plan[-1][0] if stay_plan else dest
            days_to_create.append(ItineraryDay(
                package=p_obj,
                day_number=current_day,
                title=f"Day {current_day}: {last_city} Sightseeing & Departure"[:250],
                route_segment=f"{last_city} Circuit"[:250],
                activities=(
                    f"Morning sightseeing and souvenir shopping in {last_city}. "
                    f"Afternoon transfer to airport/railway station with wonderful memories curated by Siva Gayathri Tours & Travels."
                ),
                sightseeing_spots=f"{last_city} Heritage & Commercial Centers"[:500],
                night_stay_location=last_city[:250],
                meals_included="Breakfast Included",
                hotel_info=hotel_str[:250],
                transport_info="Dedicated AC Tourist Vehicle"
            ))
            current_day += 1

        # Vehicle Tariffs (5 tiers)
        for vt, tier, km_rate, extra_hr, bata in tariff_configs:
            if vt:
                daily = (300 * km_rate) + bata
                pkg_rate = max(base_price, duration * daily)
                tariffs_to_create.append(PackageVehicleTariff(
                    package=p_obj,
                    vehicle_type=vt,
                    seating_tier=tier,
                    rate_type='outstation_multiday' if duration > 1 else 'outstation_day',
                    package_rate=Decimal(str(round(pkg_rate, 2))),
                    per_day_rate=Decimal(str(round(daily, 2))),
                    included_km=duration * 300,
                    extra_km_rate=km_rate,
                    extra_hour_rate=extra_hr,
                    driver_bata_per_day=bata,
                    driver_bata_included=True,
                    toll_parking_included=True,
                    interstate_permit_included=True
                ))

        # Devotional darshan
        if category == 'devotional':
            darshan_to_create.append(TempleDarshanSlot(
                package=p_obj,
                temple_name=f"{dest} Sacred Temple Darshan"[:200],
                deity_or_circuit="Sacred Deity / Spiritual Circuit"[:150],
                darshan_type='special_entry_300',
                booked_slot_time="09:00 AM - 11:30 AM",
                reporting_location="Main Temple Entrance / Q Complex",
                dress_code_notes="Strict Traditional: Dhoti/Kurta for Men, Saree/Chudidar for Women",
                prasad_details="Special Darshan Prasadam Included",
                senior_citizen_support=True
            ))

        # International documents
        if category == 'international':
            intl_to_create.append(InternationalDocumentChecklist(
                package=p_obj,
                document_name="Original Passport (min 6 months validity)",
                is_mandatory=True,
                submission_deadline_days=7,
                notes="Original Passport with at least 2 blank pages"
            ))
            intl_to_create.append(InternationalDocumentChecklist(
                package=p_obj,
                document_name="Tourist Visa & Travel Insurance",
                is_mandatory=True,
                submission_deadline_days=5,
                notes=f"Approved Tourist Visa and valid travel insurance for {dest}"
            ))

    print(f"\nBulk inserting child models...", flush=True)
    with transaction.atomic():
        print(f"  • Inserting {len(days_to_create)} Itinerary Days...", flush=True)
        ItineraryDay.objects.bulk_create(days_to_create, batch_size=1000)
        print(f"  • Inserting {len(tariffs_to_create)} Vehicle Tariffs...", flush=True)
        PackageVehicleTariff.objects.bulk_create(tariffs_to_create, batch_size=1000)
        print(f"  • Inserting {len(darshan_to_create)} Temple Darshan Slots...", flush=True)
        TempleDarshanSlot.objects.bulk_create(darshan_to_create, batch_size=500)
        print(f"  • Inserting {len(intl_to_create)} Intl Document Checklists...", flush=True)
        InternationalDocumentChecklist.objects.bulk_create(intl_to_create, batch_size=500)

    # Restore normal sqlite pragma
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA synchronous = NORMAL;")

    elapsed = time.time() - t0
    print("\n" + "=" * 70, flush=True)
    print(f"INGESTION COMPLETE IN {elapsed:.2f} SECONDS!", flush=True)
    print(f"  • Total SGT-TRW- Packages Ingested : {len(packages_to_create)}", flush=True)
    print(f"  • Total Itinerary Days Created     : {len(days_to_create)}", flush=True)
    print(f"  • Total 5-Tier Tariffs Created     : {len(tariffs_to_create)}", flush=True)
    print(f"  • Total Temple Darshan Slots       : {len(darshan_to_create)}", flush=True)
    print(f"  • Total Intl Checklists Created    : {len(intl_to_create)}", flush=True)
    print("\nCategory Breakdown:", flush=True)
    for cat, count in cats_counter.most_common():
        print(f"  • {cat:<20}: {count:>5} packages", flush=True)
    print("=" * 70, flush=True)

if __name__ == '__main__':
    main()
