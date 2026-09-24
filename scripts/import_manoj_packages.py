import os
import sys
import re
import json
from decimal import Decimal

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
)
from core.models import VehicleType

DATA_FILE = os.path.join(os.path.dirname(__file__), 'scraped_manoj_packages.json')

def clean_rebrand(text):
    if not text:
        return ""
    text = text.replace('\u2013', ' - ').replace('\u2014', ' - ').replace('\u2015', ' - ')
    text = text.replace('\u00a0', ' ').replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'wa\.link/\S+', '', text)
    text = re.sub(r'(?:www\.)?[a-zA-Z0-9-]+\.(?:com|in|org|net)/\S*', '', text)

    replacements = [
        (re.compile(r'Manoj\s+Tours\s*(?:&|and)\s*Travels', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Manoj\s+Travels', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Manoj', re.IGNORECASE), 'Siva Gayathri'),
        (re.compile(r'info@manojtravels\.in', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'\+91\s*98650\s*89000'), '+91 98425 33777'),
    ]
    cleaned = text
    for pattern, repl in replacements:
        cleaned = pattern.sub(repl, cleaned)
        
    cleaned = re.sub(r'from\s+chennai', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'(\bTOUR PACKAGE\b\s*)+', 'TOUR PACKAGE', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'(\bPACKAGE\b\s*)+', 'PACKAGE', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*,\s*', ', ', cleaned)
    cleaned = re.sub(r'\s*-\s*', ' - ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def detect_category(title, category_name):
    combined = f"{title} {category_name}".lower()
    if any(k in combined for k in ['temple', 'pilgrimage', 'navagraha', 'sabarimala', 'darshan', 'rameswaram', 'rameshwaram', 'madurai', 'tirupati', 'kumbakonam', 'chambal', 'palani', 'guruvayur']):
        return 'devotional'
    if any(k in combined for k in ['ooty', 'munnar', 'kodaikanal', 'coorg', 'wayanad', 'yercaud', 'hills', 'valley', 'falls']):
        return 'hill_station'
    if any(k in combined for k in ['honey moon', 'honeymoon', 'theme park', 'black thunder', 'beach', 'resort', 'lake']):
        return 'family_vacation'
    return 'holiday'

def format_description(title, destination, days, nights, category):
    cat_desc = {
        'devotional': f"Attain divine blessings on our sacred {title} ({nights} Nights / {days} Days). Experience seamless darshan at venerated temples across {destination}, complemented by pure vegetarian meals, comfortable accommodations, senior citizen support, and dedicated chauffeur service.",
        'hill_station': f"Relax amidst scenic mountain vistas, tea plantations, and cool breezes on our {title} ({nights} Nights / {days} Days). Explore famous viewpoints, botanical gardens, and waterfalls across {destination} with private chauffeur logistics and verified star stays.",
        'family_vacation': f"Create cherished memories with your family on our {title} ({nights} Nights / {days} Days). Enjoy an ideal blend of sightseeing, nature, relaxation, and memorable activities across {destination}, thoughtfully curated by Siva Gayathri Tours & Travels.",
        'holiday': f"Experience the captivating sights, heritage, and landscapes of {destination} on our {title} ({nights} Nights / {days} Days). Complete with chauffeur-driven tourist vehicle, hotel accommodation, and personalized itinerary management."
    }.get(category, f"Experience {title} covering {destination} with Siva Gayathri Tours & Travels.")
    return cat_desc

def main():
    print("="*80, flush=True)
    print("MANOJ TRAVELS COMPLETE EXTRACTION & DATABASE INGESTION", flush=True)
    print("="*80, flush=True)

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    print(f"Loaded {len(catalog)} packages from {DATA_FILE}", flush=True)

    # Clear previous SGT-MT packages if any
    deleted_count, _ = Package.objects.filter(package_code__startswith='SGT-MT-').delete()
    print(f"Cleared previous SGT-MT- records: {deleted_count}", flush=True)

    # Pre-fetch Vehicle Types
    vtypes = list(VehicleType.objects.all())
    sedan_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['sedan', 'dzire', 'etios'])), vtypes[0] if vtypes else None)
    crysta_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['crysta', 'innova'])), vtypes[1] if len(vtypes) > 1 else sedan_vt)
    urbania_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['urbania', 'tempo', '17'])), vtypes[2] if len(vtypes) > 2 else sedan_vt)
    bus36_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['36', 'mini', '40'])), vtypes[3] if len(vtypes) > 3 else sedan_vt)
    coach54_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['54', 'coach', '52', 'volvo'])), vtypes[4] if len(vtypes) > 4 else sedan_vt)

    configs = [
        (sedan_vt, '4_sedan', 14.0, 500.0),
        (crysta_vt, '7_crysta', 20.0, 600.0),
        (urbania_vt, '17_tt_urbania', 26.0, 800.0),
        (bus36_vt, '36_mini_bus', 35.0, 1000.0),
        (coach54_vt, '54_luxury_coach', 45.0, 1200.0),
    ]

    all_itineraries = []
    all_tariffs = []
    all_temple_slots = []
    used_codes = set()

    print("Creating packages and preparing relations in atomic batch...", flush=True)
    with transaction.atomic():
        for idx, item in enumerate(catalog, 1):
            days = item.get('days_count', 1)
            nights = max(0, days - 1)
            
            raw_title = item.get('title', '').replace('-', ' ').strip().title()
            pkg_name = clean_rebrand(raw_title).upper()
            if not any(pkg_name.endswith(suf) for suf in ['TOUR', 'PACKAGE', 'YATRA', 'SPECIAL', 'ESCAPE']):
                pkg_name = f"{pkg_name} TOUR PACKAGE"

            raw_slug = re.sub(r'[^A-Z0-9]+', '-', pkg_name[:20]).strip('-')
            pkg_code = f"SGT-MT-{raw_slug}-{days}D"
            if pkg_code in used_codes:
                pkg_code = f"SGT-MT-{raw_slug}-{days}D-{idx}"
            used_codes.add(pkg_code)

            category = detect_category(pkg_name, item.get('category_name', ''))
            is_dev = (category == 'devotional')

            # Destination
            dest_parts = [p.strip().title() for p in item.get('title', '').split('-') if len(p.strip()) > 2]
            dest = ", ".join(list(dict.fromkeys(dest_parts))[:4]) if dest_parts else "South India"

            # Pricing
            if days == 1:
                base_price = Decimal("2500.00")
            elif is_dev:
                base_price = Decimal(str(days * 2200))
            elif category == 'hill_station':
                base_price = Decimal(str(days * 2500))
            elif category == 'family_vacation':
                base_price = Decimal(str(days * 3000))
            else:
                base_price = Decimal(str(days * 2400))

            ap_price = base_price
            ep_price = Decimal(str(round(float(base_price) * 0.78, 2)))
            meal_plan = 'EP' if days == 1 else ('AP' if is_dev else 'MAP')

            inclusions_text = (
                "• Dedicated AC tourist vehicle with professional chauffeur throughout the tour.\n"
                "• All interstate road taxes, route permit charges, toll gates, and vehicle parking fees.\n"
                + ("• Verified hotel accommodation on twin-sharing basis.\n" if days > 1 else "")
                + ("• 100% Satvik Pure Vegetarian South Indian meals.\n" if is_dev else "")
                + f"• Comprehensive sightseeing covering prominent landmarks along {dest}.\n"
                "• 24x7 Siva Gayathri Tours & Travels dispatch and customer assistance."
            )

            exclusions_text = (
                "• Monument entrance tickets, temple special darshan tickets, boating, and theme park passes.\n"
                "• Personal expenses, shopping, laundry, and camera tokens.\n"
                "• Optional adventure activities not explicitly stated in the itinerary.\n"
                "• Any delays or expenses caused by roadblocks, traffic, or natural calamities."
            )

            terms_text = (
                "50% advance deposit upon tour confirmation, remaining balance payable prior to trip departure.\n"
                "Vehicle will strictly adhere to designated routes, safety rules, and permit schedules.\n"
                "AC will be switched off on steep ghat roads and hairpin bends for engine power and passenger safety.\n"
                "Siva Gayathri Tours & Travels guarantees polite chauffeurs, sanitized coaches, and timely support."
            )

            pkg_desc = format_description(pkg_name, dest, days, nights, category)

            pkg = Package.objects.create(
                package_code=pkg_code,
                name=pkg_name,
                destination=dest,
                category=category,
                duration_nights=nights,
                duration_days=days,
                base_price=base_price,
                price_with_food=ap_price,
                price_without_food=ep_price,
                pricing_type='per_person',
                meal_plan=meal_plan,
                room_sharing_type='twin_sharing',
                min_pax=2 if days <= 2 else 4,
                is_international=False,
                destination_country='India',
                currency_code='INR',
                visa_required=False,
                flight_inclusive=False,
                is_devotional=is_dev,
                satvik_pure_veg_meals=is_dev,
                senior_citizen_friendly=is_dev,
                temple_dress_code="Mandatory Traditional Dress: Dhoti/Kurta for Men, Saree/Chudidar for Women" if is_dev else "",
                temple_darshan_info=f"Sacred Pilgrimage Circuit covering prominent shrines along {dest}." if is_dev else "",
                inclusions=inclusions_text,
                exclusions=exclusions_text,
                terms_and_conditions=terms_text,
                contact_persons_footer="Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131)",
                description=pkg_desc,
                is_active=True,
            )

            # Itinerary Days
            raw_days = item.get('days', [])
            primary_city = dest.split(',')[0].strip()

            for d_idx in range(1, days + 1):
                if d_idx <= len(raw_days):
                    plan_item = raw_days[d_idx - 1]
                    d_title = clean_rebrand(plan_item.get('title', f"Day {d_idx}: Sightseeing & Exploration"))[:250]
                    d_desc = clean_rebrand(plan_item.get('details', f"Sightseeing and activities across {dest}."))
                else:
                    if d_idx == days and days > 1:
                        d_title = f"Day {d_idx}: Final Sightseeing, Souvenir Shopping & Departure"
                        d_desc = f"Morning leisure, local handicraft shopping, checkout from hotel, and comfortable return journey from {dest} with pleasant memories."
                    else:
                        d_title = f"Day {d_idx}: In-Depth Exploration of {dest}"
                        d_desc = f"Guided sightseeing covering major viewpoints, cultural monuments, and scenic landmarks along {dest}."

                all_itineraries.append(ItineraryDay(
                    package=pkg,
                    day_number=d_idx,
                    title=d_title,
                    route_segment=f"{dest} Circuit"[:250],
                    activities=d_desc,
                    sightseeing_spots=d_desc[:500],
                    meals_included="Breakfast, Lunch, Dinner" if meal_plan == 'AP' else ("Breakfast & Dinner" if meal_plan == 'MAP' else "None"),
                    night_stay_location=primary_city if days > 1 and d_idx < days else "Return Journey",
                ))

            # 5-Tier Vehicle Tariffs
            for vt, tier, km_rate, bata in configs:
                if not vt:
                    continue
                daily = (300 * km_rate) + bata
                pkg_rate = days * daily
                all_tariffs.append(PackageVehicleTariff(
                    package=pkg,
                    vehicle_type=vt,
                    seating_tier=tier,
                    rate_type='outstation_multiday' if days > 1 else 'outstation_day',
                    package_rate=Decimal(str(round(pkg_rate, 2))),
                    per_day_rate=Decimal(str(round(daily, 2))),
                    included_km=days * 300,
                    extra_km_rate=Decimal(str(km_rate)),
                    driver_bata_per_day=Decimal(str(bata)),
                    driver_bata_included=True,
                    toll_parking_included=True,
                    interstate_permit_included=any(k in dest.lower() for k in ['kerala', 'karnataka', 'mysore', 'bangalore', 'coorg', 'munnar', 'cochin', 'wayanad', 'athirappilly']),
                ))

            # Devotional Slots
            if is_dev:
                if 'navagraha' in pkg_name.lower():
                    all_temple_slots.append(TempleDarshanSlot(
                        package=pkg,
                        temple_name="Kumbakonam Navagraha 9 Temple Parikrama Circuit",
                        deity_or_circuit="Navagraha Sannidhi Circuit (Suriyan, Chandran, Chevvai, Budhan, Guru, Sukran, Sani, Rahu, Kethu)",
                        darshan_type="special_entry_300",
                        booked_slot_time="06:30 AM - 09:30 AM & 04:30 PM - 07:30 PM",
                        reporting_location="Suriyanar Koil / Thingalur / Alangudi",
                        dress_code_notes="Strict Traditional: Dhoti (Men), Saree (Women)",
                        prasad_details="Holy Navagraha Vibhuti & Archana Prasadam",
                        senior_citizen_support=True
                    ))
                elif 'sabarimala' in pkg_name.lower():
                    all_temple_slots.append(TempleDarshanSlot(
                        package=pkg,
                        temple_name="Sabarimala Sri Dharma Sastha Sannidhanam",
                        deity_or_circuit="Lord Ayyappa Swamy (Mandala / Makaravilakku)",
                        darshan_type="special_entry_300",
                        booked_slot_time="04:00 AM - 07:00 AM (Neyyabhishekam)",
                        reporting_location="Pampa River Base & Nadapanthal",
                        dress_code_notes="Traditional Black / Blue Vesti with Irumudi Kattu",
                        prasad_details="Holy Aravana Payasam & Appam Prasadam",
                        senior_citizen_support=True
                    ))
                else:
                    all_temple_slots.append(TempleDarshanSlot(
                        package=pkg,
                        temple_name=f"{dest} Sacred Temple Pilgrimage",
                        deity_or_circuit="Presiding Deities",
                        darshan_type="special_entry_300",
                        booked_slot_time="06:30 AM - 09:30 AM",
                        reporting_location="Main Temple Entrance",
                        dress_code_notes="Strict Traditional Attire",
                        prasad_details="Temple Archanai & Theertha Prasadam",
                        senior_citizen_support=True
                    ))

            if idx % 50 == 0 or idx == len(catalog):
                print(f"  Prepared {idx}/{len(catalog)} packages...", flush=True)

        print(f"Bulk creating {len(all_itineraries)} Itinerary Days...", flush=True)
        ItineraryDay.objects.bulk_create(all_itineraries, batch_size=500)

        print(f"Bulk creating {len(all_tariffs)} Vehicle Tariffs...", flush=True)
        PackageVehicleTariff.objects.bulk_create(all_tariffs, batch_size=500)

        if all_temple_slots:
            print(f"Bulk creating {len(all_temple_slots)} Temple Darshan Slots...", flush=True)
            TempleDarshanSlot.objects.bulk_create(all_temple_slots, batch_size=500)

    print("="*80, flush=True)
    print(f"SUCCESS! Fully imported {len(catalog)} packages under prefix SGT-MT-!", flush=True)
    print("="*80, flush=True)

if __name__ == '__main__':
    main()
