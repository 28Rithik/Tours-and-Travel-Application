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
    s = re.sub(r'https?://(?:www\.)?bharathiyartravels\.com\S*', '', s, flags=re.I)
    s = re.sub(r'wa\.me/\d+', 'wa.me/919842533777', s, flags=re.I)
    s = re.sub(r'\b(?:www\.)?bharathiyartravels\.com\b', 'sivagayathritravels.com', s, flags=re.I)
    s = re.sub(r'\bBharathiyar(?:\s+Tours(?:\s+and(?:\s+Travels)?)?|\s+Travels)?\b', 'Siva Gayathri Tours & Travels', s, flags=re.I)
    s = re.sub(r'\+91-?9629808833|919629808833|96298-?08833|9629808833', '+91 98425 33777', s)
    s = re.sub(r'bharathiyartravels\.cbe@gmail\.com', 'info@sivagayathritravels.com', s, flags=re.I)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def map_category(title: str, dest: str, days: int) -> str:
    combined = f"{title} {dest}".lower()
    if any(k in combined for k in ['thailand', 'sri lanka', 'bali', 'dubai', 'singapore', 'malaysia', 'mauritius', 'international']):
        return 'international'
    if days == 1 or 'hourly' in combined or 'one way' in combined or 'drop taxi' in combined:
        return 'local_tour'
    if any(k in combined for k in ['temple', 'marudhamalai', 'isha', 'palani', 'guruvayur', 'sabarimalai', 'rameshwaram', 'thiruchendur', 'thiruvannamalai', 'navagraha', 'darshan', 'masani amman']):
        return 'devotional'
    if any(k in combined for k in ['ooty', 'munnar', 'kodaikanal', 'valparai', 'coorg', 'wayanad', 'chikmagalur', 'yercaud', 'hill station']):
        return 'hill_station'
    if any(k in combined for k in ['mysore', 'athirapally', 'alleppey', 'varkala', 'kovalam', 'trivandrum', 'top slip', 'family', 'holiday']):
        return 'family_vacation'
    return 'holiday'

def slugify(text: str) -> str:
    s = re.sub(r'[^a-zA-Z0-9]+', '-', text).strip('-').upper()
    return s[:30]

def main():
    t0 = time.time()
    print("=" * 70, flush=True)
    print("SIVA GAYATHRI TOURS & TRAVELS — BHARATHIYAR TRAVELS INGESTION (65 PACKAGES)", flush=True)
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

    # 1. Load 45 multi-day tour packages
    with open('scripts/bharathiyar_packages.json', 'r', encoding='utf-8') as f:
        multi_day_pkgs = json.load(f)
    print(f"Loaded {len(multi_day_pkgs)} multi-day tour packages.", flush=True)

    # 2. Define 4 Weekend Group Tours
    group_tours = [
        {
            'slug': 'TIRUCHENDUR',
            'title': 'COIMBATORE TO TIRUCHENDUR WEEKEND GROUP TOUR',
            'destination': 'Coimbatore - Tiruchendur - Coimbatore',
            'duration_days': 2,
            'duration_nights': 1,
            'per_pax_fare': 2500.0,
            'category': 'devotional',
            'itinerary': [
                {'day': 'Day 1', 'text': 'Coimbatore departure (Morning / Night slot), scenic drive through Tamil Nadu spiritual corridor, arrival at Tiruchendur, hotel check-in and beach temple visit.'},
                {'day': 'Day 2', 'text': 'Early morning Lord Subramanya Swamy Sea Shore Darshan, special abhishekam viewing, Nazhikkinaru sacred well snanam, return journey to Coimbatore.'}
            ]
        },
        {
            'slug': 'SABARIMALA',
            'title': 'COIMBATORE TO SABARIMALA MANDALA YATRA GROUP TOUR',
            'destination': 'Coimbatore - Pamba - Sabarimala - Coimbatore',
            'duration_days': 2,
            'duration_nights': 1,
            'per_pax_fare': 2500.0,
            'category': 'devotional',
            'itinerary': [
                {'day': 'Day 1', 'text': 'Coimbatore departure, highway transfer via Palakkad and Thrissur to Nilakkal/Pamba base camp. Trek to Sannidhanam.'},
                {'day': 'Day 2', 'text': 'Holy 18 steps ascent, Lord Ayyappa Sannidhanam Darshan, Neyyabhishekam, Harivarasanam prayers, trek down to Pamba and return to Coimbatore.'}
            ]
        },
        {
            'slug': 'TIRUVANNAMALAI',
            'title': 'COIMBATORE TO TIRUVANNAMALAI GIRIVALAM GROUP TOUR',
            'destination': 'Coimbatore - Tiruvannamalai - Coimbatore',
            'duration_days': 2,
            'duration_nights': 1,
            'per_pax_fare': 2500.0,
            'category': 'devotional',
            'itinerary': [
                {'day': 'Day 1', 'text': 'Coimbatore departure, travel via Salem to sacred Tiruvannamalai. Evening 14km sacred Girivalam circumambulation around Annamalai Hill.'},
                {'day': 'Day 2', 'text': 'Early morning Sri Arunachaleswarar Temple Darshan, Sri Ramana Ashram meditation hall visit, afternoon return transfer to Coimbatore.'}
            ]
        },
        {
            'slug': 'RAMESWARAM',
            'title': 'COIMBATORE TO RAMESWARAM & DHANUSHKODI GROUP TOUR',
            'destination': 'Coimbatore - Rameswaram - Dhanushkodi - Coimbatore',
            'duration_days': 2,
            'duration_nights': 1,
            'per_pax_fare': 2500.0,
            'category': 'devotional',
            'itinerary': [
                {'day': 'Day 1', 'text': 'Coimbatore departure via Madurai to Rameswaram Island crossing historic Pamban Bridge. Evening Ramanathaswamy Temple darshan and hotel stay.'},
                {'day': 'Day 2', 'text': 'Sacred 22 Theertham holy bath, Dhanushkodi ghost town and Arichal Munai border visit, APJ Abdul Kalam National Memorial, return to Coimbatore.'}
            ]
        }
    ]

    # 3. Define 6 Local Hourly Packages
    hourly_pkgs = [
        {'code': '5H-50KM', 'title': 'COIMBATORE LOCAL 5 HOURS / 50 KM HIRE PACKAGE', 'dest': 'Coimbatore Local City', 'hours': 5, 'km': 50, 'rates': {'sedan': 1500, 'ertiga': 2000, 'innova': 2500, 'crysta': 3000}},
        {'code': '8H-80KM', 'title': 'COIMBATORE LOCAL 8 HOURS / 80 KM HIRE PACKAGE', 'dest': 'Coimbatore Local City', 'hours': 8, 'km': 80, 'rates': {'sedan': 2500, 'ertiga': 3350, 'innova': 3500, 'crysta': 4300}},
        {'code': '10H-100KM', 'title': 'COIMBATORE LOCAL 10 HOURS / 100 KM HIRE PACKAGE', 'dest': 'Coimbatore Local City', 'hours': 10, 'km': 100, 'rates': {'sedan': 3000, 'ertiga': 3800, 'innova': 4000, 'crysta': 4700}},
        {'code': '12H-120KM', 'title': 'COIMBATORE LOCAL 12 HOURS / 120 KM HIRE PACKAGE', 'dest': 'Coimbatore Local City', 'hours': 12, 'km': 120, 'rates': {'sedan': 3500, 'ertiga': 4300, 'innova': 4500, 'crysta': 5400}},
        {'code': '14H-140KM', 'title': 'COIMBATORE LOCAL 14 HOURS / 140 KM HIRE PACKAGE', 'dest': 'Coimbatore Local City', 'hours': 14, 'km': 140, 'rates': {'sedan': 4000, 'ertiga': 4900, 'innova': 5200, 'crysta': 6200}},
        {'code': '16H-160KM', 'title': 'COIMBATORE LOCAL 16 HOURS / 160 KM HIRE PACKAGE', 'dest': 'Coimbatore Local City', 'hours': 16, 'km': 160, 'rates': {'sedan': 4500, 'ertiga': 5500, 'innova': 5900, 'crysta': 7000}},
    ]

    # 4. Define 10 One-Way Drop Taxi Routes
    oneway_routes = [
        {'code': 'BLR-CITY', 'dest': 'Bangalore City', 'title': 'COIMBATORE TO BANGALORE CITY ONE WAY DROP TAXI', 'km': 370, 'rates': {'sedan': 11500, 'innova': 16000, 'crysta': 18000, 'tt': 24500}},
        {'code': 'BLR-AIRPORT', 'dest': 'Bangalore Airport (BLR)', 'title': 'COIMBATORE TO BANGALORE AIRPORT ONE WAY DROP TAXI', 'km': 410, 'rates': {'sedan': 12500, 'innova': 17500, 'crysta': 20000, 'tt': 27000}},
        {'code': 'CALICUT', 'dest': 'Calicut (Kozhikode)', 'title': 'COIMBATORE TO CALICUT ONE WAY DROP TAXI', 'km': 180, 'rates': {'sedan': 6500, 'innova': 7500, 'crysta': 8500, 'tt': 11500}},
        {'code': 'CHENNAI', 'dest': 'Chennai Metropolitan', 'title': 'COIMBATORE TO CHENNAI ONE WAY DROP TAXI', 'km': 510, 'rates': {'sedan': 15000, 'innova': 20000, 'crysta': 22500, 'tt': 27500}},
        {'code': 'COCHIN', 'dest': 'Cochin (Kochi Airport/City)', 'title': 'COIMBATORE TO COCHIN ONE WAY DROP TAXI', 'km': 190, 'rates': {'sedan': 6500, 'innova': 7500, 'crysta': 8500, 'tt': 11500}},
        {'code': 'KODAIKANAL', 'dest': 'Kodaikanal Hill Station', 'title': 'COIMBATORE TO KODAIKANAL ONE WAY DROP TAXI', 'km': 175, 'rates': {'sedan': 6700, 'innova': 8500, 'crysta': 10000, 'tt': 13000}},
        {'code': 'MADURAI', 'dest': 'Madurai City', 'title': 'COIMBATORE TO MADURAI ONE WAY DROP TAXI', 'km': 215, 'rates': {'sedan': 7000, 'innova': 9000, 'crysta': 11000, 'tt': 13000}},
        {'code': 'MUNNAR', 'dest': 'Munnar Hill Station', 'title': 'COIMBATORE TO MUNNAR ONE WAY DROP TAXI', 'km': 160, 'rates': {'sedan': 7200, 'innova': 9000, 'crysta': 10500, 'tt': 13500}},
        {'code': 'SALEM', 'dest': 'Salem City', 'title': 'COIMBATORE TO SALEM ONE WAY DROP TAXI', 'km': 170, 'rates': {'sedan': 5500, 'innova': 7000, 'crysta': 8000, 'tt': 11000}},
        {'code': 'TIRUPPUR', 'dest': 'Tiruppur City', 'title': 'COIMBATORE TO TIRUPPUR ONE WAY DROP TAXI', 'km': 55, 'rates': {'sedan': 2500, 'innova': 3800, 'crysta': 4800, 'tt': 6000}},
    ]

    print("\nPurging previous SGT-BTT- records if any...", flush=True)
    with transaction.atomic():
        deleted_count, _ = Package.objects.filter(package_code__startswith='SGT-BTT-').delete()
    print(f"Purged {deleted_count} previous SGT-BTT- records.", flush=True)

    packages_to_create = []
    meta_records = []
    cats_counter = Counter()

    # --- PROCESS A: 45 Multi-Day Tours ---
    for p in multi_day_pkgs:
        d_tier = p['duration_tier']
        days = p['duration_days']
        nights = p['duration_nights']
        d_name = p['destination_name']
        v_prices = p['vehicle_prices']

        # Base price calculation
        base_fare = v_prices.get('sedan') or (days * 3500)
        base_price = Decimal(str(base_fare))

        title = f"{d_name.upper()} {days} DAYS TOUR PACKAGE" if f"{days} DAY" not in d_name.upper() else f"{d_name.upper()} TOUR PACKAGE"
        dest = d_name
        category = map_category(title, dest, days)
        cats_counter[category] += 1

        code_suffix = slugify(f"{d_tier}-{d_name}")
        pkg_code = f"SGT-BTT-MD-{code_suffix}"

        price_with_food = (base_price * Decimal('1.25')).quantize(Decimal('1.00'))
        price_without_food = base_price.quantize(Decimal('1.00'))

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
            'type': 'multiday',
            'days': days,
            'dest': dest,
            'category': category,
            'base_price': base_price,
            'km_limit': p['km_limit'],
            'v_prices': v_prices,
            'itinerary': p['itinerary']
        })

    # --- PROCESS B: 4 Weekend Group Tours ---
    for g in group_tours:
        pkg_code = f"SGT-BTT-GRP-{g['slug']}"
        base_price = Decimal(str(g['per_pax_fare']))
        price_with_food = (base_price * Decimal('1.25')).quantize(Decimal('1.00'))
        price_without_food = base_price.quantize(Decimal('1.00'))
        category = g['category']
        cats_counter[category] += 1

        packages_to_create.append(Package(
            package_code=pkg_code,
            name=g['title'][:255],
            destination=g['destination'][:255],
            category=category,
            duration_days=g['duration_days'],
            duration_nights=g['duration_nights'],
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
            'type': 'group',
            'days': g['duration_days'],
            'dest': g['destination'],
            'category': category,
            'base_price': base_price,
            'km_limit': 600,
            'itinerary': g['itinerary']
        })

    # --- PROCESS C: 6 Hourly Packages ---
    for h in hourly_pkgs:
        pkg_code = f"SGT-BTT-HRL-{h['code']}"
        base_fare = h['rates']['sedan']
        base_price = Decimal(str(base_fare))
        price_with_food = (base_price * Decimal('1.25')).quantize(Decimal('1.00'))
        price_without_food = base_price.quantize(Decimal('1.00'))
        category = 'local_tour'
        cats_counter[category] += 1

        packages_to_create.append(Package(
            package_code=pkg_code,
            name=h['title'][:255],
            destination=h['dest'][:255],
            category=category,
            duration_days=1,
            duration_nights=0,
            pricing_type='per_vehicle',
            base_price=base_price,
            price_with_food=price_with_food,
            price_without_food=price_without_food,
            transit_mode='road_coach',
            flight_estimate_per_pax=Decimal('0.00'),
            train_estimate_per_pax=Decimal('0.00'),
        ))

        meta_records.append({
            'pkg_code': pkg_code,
            'type': 'hourly',
            'days': 1,
            'dest': h['dest'],
            'category': category,
            'base_price': base_price,
            'km_limit': h['km'],
            'hours': h['hours'],
            'rates': h['rates']
        })

    # --- PROCESS D: 10 One-Way Drop Taxi Routes ---
    for d in oneway_routes:
        pkg_code = f"SGT-BTT-OWD-{d['code']}"
        base_fare = d['rates']['sedan']
        base_price = Decimal(str(base_fare))
        price_with_food = (base_price * Decimal('1.25')).quantize(Decimal('1.00'))
        price_without_food = base_price.quantize(Decimal('1.00'))
        category = 'local_tour'
        cats_counter[category] += 1

        packages_to_create.append(Package(
            package_code=pkg_code,
            name=d['title'][:255],
            destination=d['dest'][:255],
            category=category,
            duration_days=1,
            duration_nights=0,
            pricing_type='per_vehicle',
            base_price=base_price,
            price_with_food=price_with_food,
            price_without_food=price_without_food,
            transit_mode='road_coach',
            flight_estimate_per_pax=Decimal('0.00'),
            train_estimate_per_pax=Decimal('0.00'),
        ))

        meta_records.append({
            'pkg_code': pkg_code,
            'type': 'oneway',
            'days': 1,
            'dest': d['dest'],
            'category': category,
            'base_price': base_price,
            'km_limit': d['km'],
            'rates': d['rates']
        })

    print(f"\nBulk inserting {len(packages_to_create)} Package models into database...", flush=True)
    with transaction.atomic():
        Package.objects.bulk_create(packages_to_create, batch_size=200)
    print("Packages created!", flush=True)

    pkg_map = {p.package_code: p for p in Package.objects.filter(package_code__startswith='SGT-BTT-')}
    print(f"Mapped {len(pkg_map)} packages for child relations.", flush=True)

    days_to_create = []
    tariffs_to_create = []
    darshan_to_create = []

    for meta in meta_records:
        pkg_code = meta['pkg_code']
        p_obj = pkg_map[pkg_code]
        p_type = meta['type']
        days = meta['days']
        dest = meta['dest']
        cat = meta['category']
        base_price = meta['base_price']
        km_limit = meta['km_limit']

        # 1. Itinerary Days
        if p_type in ['multiday', 'group']:
            for idx, item in enumerate(meta['itinerary'], 1):
                day_title = f"{item['day']}: Sightseeing & Travel Circuit"
                activities = (
                    f"{clean_rebrand(item['text'])} Seamless transfers in private AC vehicle "
                    f"with full tour coordination by Siva Gayathri Tours & Travels."
                )
                days_to_create.append(ItineraryDay(
                    package=p_obj,
                    day_number=idx,
                    title=day_title[:250],
                    route_segment=f"{dest} Day {idx}"[:250],
                    activities=activities,
                    sightseeing_spots=f"{dest} Attractions & Landmarks"[:500],
                    night_stay_location=dest[:250],
                    meals_included="Breakfast Included" if idx > 1 else "Refreshments Provided",
                    hotel_info=f"{dest} Verified 2/3-Star Stay" if days > 1 else "Day Return Trip",
                    transport_info="Dedicated Sanitized Tourist Vehicle"
                ))
        elif p_type == 'hourly':
            days_to_create.append(ItineraryDay(
                package=p_obj,
                day_number=1,
                title=f"Coimbatore City Hire ({meta['hours']} Hours / {km_limit} KM)",
                route_segment="Coimbatore City & Suburbs Round Trip",
                activities=(
                    f"Point-to-point local city travel, commercial visits, family functions, or shopping across Coimbatore. "
                    f"Includes {km_limit} km limit and {meta['hours']} hours duration with professional chauffeur."
                ),
                sightseeing_spots="Coimbatore City Centers, Shopping Hubs, Industrial Areas",
                night_stay_location="Coimbatore",
                meals_included="As per personal preference",
                hotel_info="Local Day Package",
                transport_info="Dedicated AC Taxi"
            ))
        elif p_type == 'oneway':
            days_to_create.append(ItineraryDay(
                package=p_obj,
                day_number=1,
                title=f"Coimbatore to {dest} One Way Drop",
                route_segment=f"Coimbatore -> {dest} Direct Highway Route",
                activities=(
                    f"Direct door-to-door one way outstation taxi service from anywhere in Coimbatore to {dest}. "
                    f"Chauffeur-driven AC vehicle with all highway tolls and interstate permits coordinated."
                ),
                sightseeing_spots=f"En-route highlights on way to {dest}",
                night_stay_location=dest[:250],
                meals_included="On road refreshments as needed",
                hotel_info="One Way Drop Service",
                transport_info="Dedicated AC Outstation Cab"
            ))

        # 2. 5-Tier Tariffs
        if p_type == 'multiday':
            v_prices = meta['v_prices']
            sedan_rate = Decimal(str(v_prices.get('sedan') or base_price))
            crysta_rate = Decimal(str(v_prices.get('crysta') or (sedan_rate * Decimal('1.40'))))
            urbania_rate = Decimal(str(v_prices.get('tt18') or v_prices.get('tt14') or (sedan_rate * Decimal('1.90'))))
            bus36_rate = (sedan_rate * Decimal('2.60')).quantize(Decimal('1.00'))
            coach54_rate = (sedan_rate * Decimal('3.50')).quantize(Decimal('1.00'))

            tariffs_to_create.extend([
                PackageVehicleTariff(package=p_obj, vehicle_type=sedan_vt, seating_tier='4_sedan', rate_type='outstation_multiday' if days > 1 else 'outstation_day', package_rate=sedan_rate, per_day_rate=sedan_rate/days, included_km=km_limit, extra_km_rate=Decimal('12.00'), extra_hour_rate=Decimal('150.00'), driver_bata_per_day=Decimal('400.00'), driver_bata_included=True, toll_parking_included=True, interstate_permit_included=True),
                PackageVehicleTariff(package=p_obj, vehicle_type=crysta_vt, seating_tier='7_crysta', rate_type='outstation_multiday' if days > 1 else 'outstation_day', package_rate=crysta_rate, per_day_rate=crysta_rate/days, included_km=km_limit, extra_km_rate=Decimal('19.00'), extra_hour_rate=Decimal('250.00'), driver_bata_per_day=Decimal('500.00'), driver_bata_included=True, toll_parking_included=True, interstate_permit_included=True),
                PackageVehicleTariff(package=p_obj, vehicle_type=urbania_vt, seating_tier='17_tt_urbania', rate_type='outstation_multiday' if days > 1 else 'outstation_day', package_rate=urbania_rate, per_day_rate=urbania_rate/days, included_km=km_limit, extra_km_rate=Decimal('26.00'), extra_hour_rate=Decimal('300.00'), driver_bata_per_day=Decimal('600.00'), driver_bata_included=True, toll_parking_included=True, interstate_permit_included=True),
                PackageVehicleTariff(package=p_obj, vehicle_type=bus36_vt, seating_tier='36_mini_bus', rate_type='outstation_multiday' if days > 1 else 'outstation_day', package_rate=bus36_rate, per_day_rate=bus36_rate/days, included_km=km_limit, extra_km_rate=Decimal('42.00'), extra_hour_rate=Decimal('450.00'), driver_bata_per_day=Decimal('800.00'), driver_bata_included=True, toll_parking_included=True, interstate_permit_included=True),
                PackageVehicleTariff(package=p_obj, vehicle_type=coach54_vt, seating_tier='54_luxury_coach', rate_type='outstation_multiday' if days > 1 else 'outstation_day', package_rate=coach54_rate, per_day_rate=coach54_rate/days, included_km=km_limit, extra_km_rate=Decimal('55.00'), extra_hour_rate=Decimal('600.00'), driver_bata_per_day=Decimal('1000.00'), driver_bata_included=True, toll_parking_included=True, interstate_permit_included=True),
            ])
        elif p_type in ['hourly', 'oneway', 'group']:
            sedan_rate = base_price
            crysta_rate = (base_price * Decimal('1.35')).quantize(Decimal('1.00'))
            urbania_rate = (base_price * Decimal('1.80')).quantize(Decimal('1.00'))
            bus36_rate = (base_price * Decimal('2.50')).quantize(Decimal('1.00'))
            coach54_rate = (base_price * Decimal('3.40')).quantize(Decimal('1.00'))

            tariffs_to_create.extend([
                PackageVehicleTariff(package=p_obj, vehicle_type=sedan_vt, seating_tier='4_sedan', rate_type='local_hourly' if p_type=='hourly' else ('one_way_drop' if p_type=='oneway' else 'outstation_multiday'), package_rate=sedan_rate, per_day_rate=sedan_rate, included_km=km_limit, extra_km_rate=Decimal('12.00'), extra_hour_rate=Decimal('200.00'), driver_bata_per_day=Decimal('400.00'), driver_bata_included=True, toll_parking_included=True, interstate_permit_included=True),
                PackageVehicleTariff(package=p_obj, vehicle_type=crysta_vt, seating_tier='7_crysta', rate_type='local_hourly' if p_type=='hourly' else ('one_way_drop' if p_type=='oneway' else 'outstation_multiday'), package_rate=crysta_rate, per_day_rate=crysta_rate, included_km=km_limit, extra_km_rate=Decimal('19.00'), extra_hour_rate=Decimal('300.00'), driver_bata_per_day=Decimal('500.00'), driver_bata_included=True, toll_parking_included=True, interstate_permit_included=True),
                PackageVehicleTariff(package=p_obj, vehicle_type=urbania_vt, seating_tier='17_tt_urbania', rate_type='local_hourly' if p_type=='hourly' else ('one_way_drop' if p_type=='oneway' else 'outstation_multiday'), package_rate=urbania_rate, per_day_rate=urbania_rate, included_km=km_limit, extra_km_rate=Decimal('26.00'), extra_hour_rate=Decimal('400.00'), driver_bata_per_day=Decimal('600.00'), driver_bata_included=True, toll_parking_included=True, interstate_permit_included=True),
                PackageVehicleTariff(package=p_obj, vehicle_type=bus36_vt, seating_tier='36_mini_bus', rate_type='local_hourly' if p_type=='hourly' else ('one_way_drop' if p_type=='oneway' else 'outstation_multiday'), package_rate=bus36_rate, per_day_rate=bus36_rate, included_km=km_limit, extra_km_rate=Decimal('42.00'), extra_hour_rate=Decimal('500.00'), driver_bata_per_day=Decimal('800.00'), driver_bata_included=True, toll_parking_included=True, interstate_permit_included=True),
                PackageVehicleTariff(package=p_obj, vehicle_type=coach54_vt, seating_tier='54_luxury_coach', rate_type='local_hourly' if p_type=='hourly' else ('one_way_drop' if p_type=='oneway' else 'outstation_multiday'), package_rate=coach54_rate, per_day_rate=coach54_rate, included_km=km_limit, extra_km_rate=Decimal('55.00'), extra_hour_rate=Decimal('600.00'), driver_bata_per_day=Decimal('1000.00'), driver_bata_included=True, toll_parking_included=True, interstate_permit_included=True),
            ])

        # 3. Temple Darshan Slots
        if cat == 'devotional':
            darshan_to_create.append(TempleDarshanSlot(
                package=p_obj,
                temple_name=f"{dest} Temple Darshan Circuit"[:200],
                deity_or_circuit="Sacred Murugan / Shiva / Perumal Yatra"[:150],
                darshan_type='special_entry_300',
                booked_slot_time="08:00 AM - 11:30 AM",
                reporting_location="Main Temple Rajagopuram Entrance",
                dress_code_notes="Strict Traditional: Dhoti/Kurta for Men, Saree/Salwar for Women",
                prasad_details="Special Darshan Prasadam Kit Included",
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
    print(f"BHARATHIYAR TRAVELS INGESTION COMPLETE IN {elapsed:.2f} SECONDS!", flush=True)
    print(f"  • Total SGT-BTT- Packages Ingested : {len(packages_to_create)}", flush=True)
    print(f"  • Total Itinerary Days Created     : {len(days_to_create)}", flush=True)
    print(f"  • Total 5-Tier Tariffs Created     : {len(tariffs_to_create)}", flush=True)
    print(f"  • Total Temple Darshan Slots       : {len(darshan_to_create)}", flush=True)
    print("\nCategory Breakdown:", flush=True)
    for cat, count in cats_counter.most_common():
        print(f"  • {cat:<20}: {count:>5} packages", flush=True)
    print("=" * 70, flush=True)

if __name__ == '__main__':
    main()
