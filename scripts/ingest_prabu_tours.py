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
)
from core.models import VehicleType

def clean_rebrand(text: str) -> str:
    if not text:
        return ""
    s = text
    s = s.replace('\u2013', ' - ').replace('\u2014', ' - ').replace('\u00a0', ' ').replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    s = re.sub(r'https?://(?:www\.)?prabutourstravels\.com\S*', '', s, flags=re.I)
    s = re.sub(r'wa\.me/\+?91\d+', 'wa.me/919842533777', s, flags=re.I)
    s = re.sub(r'\b(?:www\.)?prabutourstravels\.com\b', 'sivagayathritravels.com', s, flags=re.I)
    s = re.sub(r'\b(?:www\.)?besttempotravellerrental\.com\b', 'sivagayathritravels.com', s, flags=re.I)
    s = re.sub(r'\bPrabu(?:\s+Tours(?:\s+and(?:\s+Travels)?)?|\s+Travels)?\b', 'Siva Gayathri Tours & Travels', s, flags=re.I)
    s = re.sub(r'\bMr\.Prabu\b', 'Mr. Rithik CA', s, flags=re.I)
    s = re.sub(r'\+91-?9840108069|98401-?08069|9840108069', '+91 98425 33777', s)
    s = re.sub(r'\+91-?8220202056|82202-?02056|8220202056', '+91 94381 7131', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def slugify(text: str) -> str:
    s = re.sub(r'[^a-zA-Z0-9]+', '-', text).strip('-').upper()
    return s[:25]

def main():
    t0 = time.time()
    print("=" * 70, flush=True)
    print("SIVA GAYATHRI TOURS & TRAVELS — PRABU TOURS INGESTION (39 PACKAGES)", flush=True)
    print("=" * 70, flush=True)

    with connection.cursor() as cursor:
        cursor.execute("PRAGMA synchronous = OFF;")
        cursor.execute("PRAGMA journal_mode = MEMORY;")

    # Vehicle types setup
    vtypes = list(VehicleType.objects.all())
    sedan_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['sedan', 'dzire', 'etios'])), vtypes[0] if vtypes else None)
    crysta_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['crysta', 'innova'])), vtypes[1] if len(vtypes) > 1 else sedan_vt)
    urbania_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['urbania', 'tempo', '17'])), vtypes[2] if len(vtypes) > 2 else sedan_vt)
    bus36_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['36', 'mini', '40'])), vtypes[3] if len(vtypes) > 3 else sedan_vt)
    coach54_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['54', 'coach', '52', 'volvo'])), vtypes[4] if len(vtypes) > 4 else sedan_vt)

    with open('scripts/prabu_crawled_packages.json', 'r', encoding='utf-8') as f:
        crawled_pkgs = json.load(f)

    print(f"Loaded {len(crawled_pkgs)} crawled packages from cache.", flush=True)

    print("\nPurging previous SGT-PTT- records if any...", flush=True)
    with transaction.atomic():
        deleted_count, _ = Package.objects.filter(package_code__startswith='SGT-PTT-').delete()
    print(f"Purged {deleted_count} previous records.", flush=True)

    packages_to_create = []
    meta_records = []
    cats_counter = Counter()

    for idx, p in enumerate(crawled_pkgs, 1):
        days = p['duration_days']
        nights = p['duration_nights']
        raw_title = p['title']
        title = clean_rebrand(raw_title)
        # Format title cleanly
        title = re.sub(r'\s+', ' ', title).strip().upper()
        if not any(title.endswith(suf) for suf in ['TOUR PACKAGE', 'PACKAGE', 'SPECIAL', 'TRIP']):
            title = f"{title} TOUR PACKAGE"

        dest = clean_rebrand(p['destination'])
        if not dest or len(dest) > 150:
            dest = title.replace('TOUR PACKAGE', '').replace('TOUR FROM COIMBATORE', '').replace('FROM COIMBATORE', '').strip()

        category = p['category']
        cats_counter[category] += 1

        # Base fare based on days
        base_fare = max(4200.0, days * 3600.0)
        base_price = Decimal(str(round(base_fare, 2)))
        price_with_food = (base_price * Decimal('1.25')).quantize(Decimal('1.00'))
        price_without_food = base_price.quantize(Decimal('1.00'))

        slug = slugify(p['filename'].replace('.php', ''))
        pkg_code = f"SGT-PTT-{idx:02d}-{slug}"

        packages_to_create.append(Package(
            package_code=pkg_code,
            name=title[:255],
            destination=dest[:255],
            category=category,
            duration_days=days,
            duration_nights=nights,
            pricing_type='per_person',
            base_price=base_price,
            price_with_food=price_with_food,
            price_without_food=price_without_food,
            transit_mode='road_coach',
            flight_estimate_per_pax=Decimal('0.00'),
            train_estimate_per_pax=Decimal('0.00'),
        ))

        meta_records.append({
            'pkg_code': pkg_code,
            'days': days,
            'dest': dest,
            'category': category,
            'base_price': base_price,
            'itinerary': p['itinerary']
        })

    print(f"\nBulk inserting {len(packages_to_create)} Package models into database...", flush=True)
    with transaction.atomic():
        Package.objects.bulk_create(packages_to_create, batch_size=100)
    print("Packages created!", flush=True)

    pkg_map = {p.package_code: p for p in Package.objects.filter(package_code__startswith='SGT-PTT-')}
    print(f"Mapped {len(pkg_map)} packages for child relations.", flush=True)

    days_to_create = []
    tariffs_to_create = []
    darshan_to_create = []

    for meta in meta_records:
        pkg_code = meta['pkg_code']
        p_obj = pkg_map[pkg_code]
        days = meta['days']
        dest = meta['dest']
        cat = meta['category']
        base_price = meta['base_price']
        itin = meta['itinerary']

        # 1. Itinerary Days
        for d_idx, item in enumerate(itin, 1):
            day_label = item['day']
            day_text = clean_rebrand(item['text'])
            day_title = f"{day_label}: {dest} Sightseeing & Circuit" if len(dest) < 40 else f"{day_label}: Sightseeing Tour"
            activities = (
                f"{day_text} Seamless transfers in private AC vehicle with dedicated driver "
                f"and round-the-clock coordination by Siva Gayathri Tours & Travels."
            )
            days_to_create.append(ItineraryDay(
                package=p_obj,
                day_number=d_idx,
                title=day_title[:250],
                route_segment=f"{dest} Day {d_idx}"[:250],
                activities=activities,
                sightseeing_spots=f"{dest} Highlights & Attractions"[:500],
                night_stay_location=dest[:250] if days > 1 else "Coimbatore Return",
                meals_included="Breakfast Included" if d_idx > 1 else "Refreshments on route",
                hotel_info=f"{dest} Verified 2/3-Star Stay" if days > 1 else "Day Return Tour",
                transport_info="Dedicated AC Tourist Vehicle"
            ))

        # 2. 5-Tier Tariffs
        sedan_rate = base_price
        crysta_rate = (base_price * Decimal('1.35')).quantize(Decimal('1.00'))
        urbania_rate = (base_price * Decimal('1.80')).quantize(Decimal('1.00'))
        bus36_rate = (base_price * Decimal('2.50')).quantize(Decimal('1.00'))
        coach54_rate = (base_price * Decimal('3.40')).quantize(Decimal('1.00'))
        km_limit = days * 300

        tariffs_to_create.extend([
            PackageVehicleTariff(package=p_obj, vehicle_type=sedan_vt, seating_tier='4_sedan', rate_type='outstation_multiday' if days > 1 else 'outstation_day', package_rate=sedan_rate, per_day_rate=sedan_rate/days, included_km=km_limit, extra_km_rate=Decimal('12.00'), extra_hour_rate=Decimal('150.00'), driver_bata_per_day=Decimal('400.00'), driver_bata_included=True, toll_parking_included=True, interstate_permit_included=True),
            PackageVehicleTariff(package=p_obj, vehicle_type=crysta_vt, seating_tier='7_crysta', rate_type='outstation_multiday' if days > 1 else 'outstation_day', package_rate=crysta_rate, per_day_rate=crysta_rate/days, included_km=km_limit, extra_km_rate=Decimal('19.00'), extra_hour_rate=Decimal('250.00'), driver_bata_per_day=Decimal('500.00'), driver_bata_included=True, toll_parking_included=True, interstate_permit_included=True),
            PackageVehicleTariff(package=p_obj, vehicle_type=urbania_vt, seating_tier='17_tt_urbania', rate_type='outstation_multiday' if days > 1 else 'outstation_day', package_rate=urbania_rate, per_day_rate=urbania_rate/days, included_km=km_limit, extra_km_rate=Decimal('26.00'), extra_hour_rate=Decimal('300.00'), driver_bata_per_day=Decimal('600.00'), driver_bata_included=True, toll_parking_included=True, interstate_permit_included=True),
            PackageVehicleTariff(package=p_obj, vehicle_type=bus36_vt, seating_tier='36_mini_bus', rate_type='outstation_multiday' if days > 1 else 'outstation_day', package_rate=bus36_rate, per_day_rate=bus36_rate/days, included_km=km_limit, extra_km_rate=Decimal('42.00'), extra_hour_rate=Decimal('450.00'), driver_bata_per_day=Decimal('800.00'), driver_bata_included=True, toll_parking_included=True, interstate_permit_included=True),
            PackageVehicleTariff(package=p_obj, vehicle_type=coach54_vt, seating_tier='54_luxury_coach', rate_type='outstation_multiday' if days > 1 else 'outstation_day', package_rate=coach54_rate, per_day_rate=coach54_rate/days, included_km=km_limit, extra_km_rate=Decimal('55.00'), extra_hour_rate=Decimal('600.00'), driver_bata_per_day=Decimal('1000.00'), driver_bata_included=True, toll_parking_included=True, interstate_permit_included=True),
        ])

        # 3. Temple Darshan Slots
        if cat == 'devotional':
            darshan_to_create.append(TempleDarshanSlot(
                package=p_obj,
                temple_name=f"{dest} Holy Darshan"[:200],
                deity_or_circuit="Sacred Deity / Spiritual Circuit"[:150],
                darshan_type='special_entry_300',
                booked_slot_time="08:30 AM - 11:30 AM",
                reporting_location="Main Temple Entrance / Q Complex",
                dress_code_notes="Strict Traditional: Dhoti/Kurta for Men, Saree/Chudidar for Women",
                prasad_details="Special Darshan Prasadam Included",
                senior_citizen_support=True
            ))

    print(f"\nBulk inserting child models...", flush=True)
    with transaction.atomic():
        print(f"  • Inserting {len(days_to_create)} Itinerary Days...", flush=True)
        ItineraryDay.objects.bulk_create(days_to_create, batch_size=500)
        print(f"  • Inserting {len(tariffs_to_create)} Vehicle Tariffs...", flush=True)
        PackageVehicleTariff.objects.bulk_create(tariffs_to_create, batch_size=500)
        print(f"  • Inserting {len(darshan_to_create)} Temple Darshan Slots...", flush=True)
        TempleDarshanSlot.objects.bulk_create(darshan_to_create, batch_size=200)

    # Restore normal sqlite pragma
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA synchronous = NORMAL;")

    elapsed = time.time() - t0
    print("\n" + "=" * 70, flush=True)
    print(f"PRABU TOURS INGESTION COMPLETE IN {elapsed:.2f} SECONDS!", flush=True)
    print(f"  • Total SGT-PTT- Packages Ingested : {len(packages_to_create)}", flush=True)
    print(f"  • Total Itinerary Days Created     : {len(days_to_create)}", flush=True)
    print(f"  • Total 5-Tier Tariffs Created     : {len(tariffs_to_create)}", flush=True)
    print(f"  • Total Temple Darshan Slots       : {len(darshan_to_create)}", flush=True)
    print("\nCategory Breakdown:", flush=True)
    for cat, count in cats_counter.most_common():
        print(f"  • {cat:<20}: {count:>5} packages", flush=True)
    print("=" * 70, flush=True)

if __name__ == '__main__':
    main()
