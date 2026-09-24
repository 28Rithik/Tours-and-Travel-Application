import os
import sys
import re
import json
from decimal import Decimal
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

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

def map_category(title: str, dest: str, hub: str, days: int) -> str:
    combined = f"{title} {dest} {hub}".lower()
    if any(k in combined for k in ['thailand', 'sri lanka', 'bali', 'dubai', 'singapore', 'maldives', 'malaysia', 'mauritius', 'international', 'bangkok', 'phuket', 'pattaya', 'colombo', 'kandy', 'bentota']):
        return 'international'
    if days == 1 or 'one day' in combined or '1 day' in combined:
        return 'local_tour'
    if any(k in combined for k in ['temple', 'pilgrimage', 'darshan', 'jyotirlinga', 'sthalang', 'divya', 'shiva', 'rameshwaram', 'madurai', 'tirupati', 'kanchipuram', 'shirdi', 'kashi', 'varanasi', 'puri', 'ayodhya', 'somnath', 'murudeshwar', 'srisailam']):
        return 'devotional'
    if any(k in combined for k in ['ooty', 'munnar', 'coorg', 'kodaikanal', 'chikmagalur', 'wayanad', 'yercaud', 'yelagiri', 'shimla', 'manali', 'kashmir', 'nainital', 'mussoorie', 'darjeeling', 'hill station', 'panchgani', 'mahabaleshwar']):
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
    print("=" * 70, flush=True)
    print("SIVA GAYATHRI TOURS & TRAVELS — COMPLETE TRAWELL INGESTION & UPDATE", flush=True)
    print("=" * 70, flush=True)

    with open('scripts/trawell_all_api_tours.json', 'r', encoding='utf-8') as f:
        tours = json.load(f)

    with open('scripts/trawell_all_details_cache.json', 'r', encoding='utf-8') as f:
        details = json.load(f)

    print(f"Loaded {len(tours)} master tours and {len(details)} tour detail records.", flush=True)

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

    total_pkgs = 0
    created_pkgs = 0
    updated_pkgs = 0
    total_days = 0
    total_tariffs = 0
    total_darshan = 0
    total_intl = 0

    cats_counter = Counter()

    # Process in chunks of 200 within atomic transactions
    all_codes = list(tours.keys())
    chunk_size = 200

    for i in range(0, len(all_codes), chunk_size):
        chunk = all_codes[i:i + chunk_size]
        with transaction.atomic():
            for code in chunk:
                t_info = tours[code]
                d_info = details.get(code, {})

                raw_title = t_info.get('it_title') or d_info.get('it_title') or f"{code} Tour"
                title = clean_rebrand(raw_title).upper()
                if not any(title.endswith(suf) for suf in ['TOUR', 'PACKAGE', 'TRIP', 'GETAWAY', 'SPECIAL', 'CIRCUIT']):
                    title = f"{title} TOUR PACKAGE"

                hub = t_info.get('source_hub', '')
                dest = d_info.get('destinations') or t_info.get('it_fromdest') or hub.replace('-', ' ').title()
                dest = clean_rebrand(dest)

                # Duration
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

                # Fare
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

                # Hotels
                hotels = d_info.get('hotels', [])
                hotel_names = []
                for h in hotels:
                    hname = clean_rebrand(h.get('name', ''))
                    hstar = h.get('star_rating', '')
                    if hname:
                        hotel_names.append(f"{hname} ({hstar}★)" if hstar else hname)
                hotel_str = ", ".join(hotel_names[:3]) if hotel_names else f"{dest} Verified Tourist Hotel"

                # Inclusions / Exclusions
                inclusions = [
                    "Chauffeur-driven sanitized tourist vehicle for the entire sightseeing circuit",
                    f"Star-rated verified hotel accommodation ({hotel_str}) on twin/triple sharing",
                    "Daily complimentary hotel breakfast",
                    "All interstate permits, highway toll charges, and vehicle parking fees included",
                    "Driver day & night bata allowances included",
                    "Applicable tourist taxes & GST included with zero hidden extras",
                    "Dedicated 24/7 round-the-clock trip coordination by Siva Gayathri Tours & Travels"
                ]

                exclusions = [
                    "Airfare, train tickets, or intercity transit to the tour starting city",
                    "Lunch, dinner, snacks, and personal beverages",
                    "Monument entry tickets, special temple darshan passes, and local guides",
                    "Optional adventure activities, safaris, boat rides, and water sports",
                    "Early check-in / late check-out beyond hotel standard timings",
                    "Personal laundry, room service, or tips"
                ]

                base_price = Decimal(str(round(fare, 2)))
                price_with_food = (base_price * Decimal('1.25')).quantize(Decimal('1.00'))
                price_without_food = base_price.quantize(Decimal('1.00'))

                pkg_code = f"SGT-TRW-{code}"
                pkg, created = Package.objects.update_or_create(
                    package_code=pkg_code,
                    defaults={
                        'name': title[:255],
                        'destination': dest[:255],
                        'category': category,
                        'duration_days': duration,
                        'duration_nights': nights,
                        'pricing_type': 'per_person',
                        'base_price': base_price,
                        'price_with_food': price_with_food,
                        'price_without_food': price_without_food,
                        'transit_mode': 'flight_coach' if category == 'international' else 'road_coach',
                        'flight_estimate_per_pax': Decimal('18000.00') if category == 'international' else Decimal('0.00'),
                        'train_estimate_per_pax': Decimal('0.00'),
                    }
                )

                if created:
                    created_pkgs += 1
                else:
                    updated_pkgs += 1
                total_pkgs += 1

                # Clear and re-populate child relations
                pkg.itinerary_days.all().delete()
                pkg.vehicle_tariffs.all().delete()
                pkg.temple_slots.all().delete()
                pkg.intl_documents.all().delete()

                # Itinerary Days based on stay plan
                stay_plan = parse_stay_plan(d_info.get('stay', ''), duration, dest)
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
                        ItineraryDay.objects.create(
                            package=pkg,
                            day_number=current_day,
                            title=day_title[:250],
                            route_segment=f"{city} Sightseeing Circuit"[:250],
                            activities=activities,
                            sightseeing_spots=f"{city} Major Attractions & Scenic Viewpoints"[:500],
                            night_stay_location=city[:250],
                            meals_included="Breakfast Included",
                            hotel_info=hotel_str[:250],
                            transport_info="Dedicated AC Tourist Vehicle"
                        )
                        total_days += 1
                        current_day += 1

                # Remaining days if any
                while current_day <= duration:
                    last_city = stay_plan[-1][0] if stay_plan else dest
                    ItineraryDay.objects.create(
                        package=pkg,
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
                    )
                    total_days += 1
                    current_day += 1

                # Vehicle Tariffs (5 tiers)
                for vt, tier, km_rate, extra_hr, bata in tariff_configs:
                    if vt:
                        daily = (300 * km_rate) + bata
                        pkg_rate = max(base_price, duration * daily)
                        PackageVehicleTariff.objects.create(
                            package=pkg,
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
                        )
                        total_tariffs += 1

                # Devotional darshan slots
                if category == 'devotional':
                    TempleDarshanSlot.objects.create(
                        package=pkg,
                        temple_name=f"{dest} Sacred Temple Darshan"[:200],
                        deity_or_circuit="Sacred Deity / Spiritual Circuit"[:150],
                        darshan_type='special_entry_300',
                        booked_slot_time="09:00 AM - 11:30 AM",
                        reporting_location="Main Temple Entrance / Q Complex",
                        dress_code_notes="Strict Traditional: Dhoti/Kurta for Men, Saree/Chudidar for Women",
                        prasad_details="Special Darshan Prasadam Included",
                        senior_citizen_support=True
                    )
                    total_darshan += 1

                # International documents checklist
                if category == 'international':
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
                        notes=f"Approved Tourist Visa and valid travel insurance for {dest}"
                    )
                    total_intl += 2

        print(f"Committed batch up to {min(i + chunk_size, len(all_codes))}/{len(all_codes)} packages...", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("INGESTION & ENRICHMENT COMPLETE FOR ALL TRAWELL PACKAGES!", flush=True)
    print(f"  • Total SGT-TRW- Packages Processed : {total_pkgs}", flush=True)
    print(f"  • New Packages Created             : {created_pkgs}", flush=True)
    print(f"  • Existing Packages Updated        : {updated_pkgs}", flush=True)
    print(f"  • Itinerary Days Ingested          : {total_days}", flush=True)
    print(f"  • 5-Tier Tariffs Ingested          : {total_tariffs}", flush=True)
    print(f"  • Temple Darshan Slots Ingested    : {total_darshan}", flush=True)
    print(f"  • Intl Document Checklists Ingested: {total_intl}", flush=True)
    print("\nCategory Breakdown:", flush=True)
    for cat, count in cats_counter.most_common():
        print(f"  • {cat:<20}: {count:>5} packages", flush=True)
    print("=" * 70, flush=True)

if __name__ == '__main__':
    main()
