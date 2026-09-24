import os
import sys
import json
import re
from decimal import Decimal

# Setup Django environment
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
)
from core.models import VehicleType

print("=" * 80)
print("  SIVA GAYATHRI TOURS & TRAVELS — SCRAPED PACKAGE IMPORTER")
print("=" * 80)

# 1. Fetch Vehicle Types
vtypes = list(VehicleType.objects.all())
sedan_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['sedan', 'dzire', 'etios'])), vtypes[0] if vtypes else None)
crysta_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['crysta', 'innova'])), vtypes[1] if len(vtypes) > 1 else sedan_vt)
urbania_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['urbania', 'tempo', '17'])), vtypes[2] if len(vtypes) > 2 else sedan_vt)
bus36_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['36', 'mini', '40'])), vtypes[3] if len(vtypes) > 3 else sedan_vt)
coach54_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['54', 'coach', '52', 'volvo'])), vtypes[4] if len(vtypes) > 4 else sedan_vt)

TARIFF_CONFIGS = [
    (sedan_vt, '4_sedan', 14.0, 500.0, 80, 2200.0),
    (crysta_vt, '7_crysta', 20.0, 600.0, 80, 3500.0),
    (urbania_vt, '17_tt_urbania', 26.0, 800.0, 80, 5500.0),
    (bus36_vt, '36_mini_bus', 35.0, 1000.0, 80, 8500.0),
    (coach54_vt, '54_luxury_coach', 45.0, 1200.0, 80, 12000.0),
]

def clean_rebrand(text):
    if not text:
        return ""
    replacements = [
        (re.compile(r'Manoj\s+Tours\s*(?:&|and)\s*Travels', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Manoj\s+Travels', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Manoj', re.IGNORECASE), 'Siva Gayathri'),
        (re.compile(r'info@manojtravels\.in', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'\+91\s*98650\s*89000'), '+91 98425 33777'),
        (re.compile(r'manojtravels\.in', re.IGNORECASE), 'sivagayathritravels.com'),
    ]
    cleaned = text
    for pattern, repl in replacements:
        cleaned = pattern.sub(repl, cleaned)
    return cleaned.strip()

def format_clean_title(raw_title, days_count):
    # Remove ellipsis and trailing artifacts
    t = re.sub(r'\.{2,}', '', raw_title).strip(' -_')
    t = clean_rebrand(t)
    
    compounds = [
        ('Black-Thunder-Water-Theme-Park', 'Black Thunder Theme Park'),
        ('Athirappilly-Water-Falls', 'Athirappilly Waterfalls'),
        ('Malampuzha-Dam', 'Malampuzha Dam'),
        ('Hogennakal-Falls', 'Hogenakkal Falls'),
        ('Parambikulam-Topslip', 'Parambikulam & Topslip'),
        ('Navagraha-Temple-Package', 'Navagraha 9 Temples Pilgrimage'),
        ('Coimbatore-Temple-Tour(North)', 'Coimbatore North Sacred Temples Tour'),
        ('Coimbatore-Temple-Tour(South)', 'Coimbatore South Sacred Temples Tour'),
    ]
    for orig, rep in compounds:
        t = re.sub(re.escape(orig), rep, t, flags=re.IGNORECASE)
        t = re.sub(re.escape(orig.replace('-', ' ')), rep, t, flags=re.IGNORECASE)

    parts = [p.strip().title() for p in t.split('-') if p.strip()]
    if not parts:
        parts = [t.title()]

    route_name = " - ".join(parts)
    nights = max(0, days_count - 1)
    if days_count == 1:
        return f"1-DAY {route_name.upper()} SIGHTSEEING TOUR"
    else:
        return f"{nights}N/{days_count}D {route_name.upper()} TOUR PACKAGE"

def determine_category(raw_cat, title):
    t_lower = (raw_cat + " " + title).lower()
    if any(k in t_lower for k in ['temple', 'navagraha', 'sabarimala', 'pilgrimage', 'darshan', 'murugan', 'shiva', 'amman']):
        return 'devotional'
    if 'honey moon' in t_lower or 'honeymoon' in t_lower:
        return 'family_vacation'
    if any(k in t_lower for k in ['ooty', 'kodaikanal', 'coorg', 'munnar', 'wayanad', 'yercaud', 'valparai']):
        return 'hill_station'
    if 'one day' in t_lower:
        return 'local_tour'
    return 'holiday'

def attach_tariffs(pkg):
    PackageVehicleTariff.objects.filter(package=pkg).delete()
    days = pkg.duration_days
    is_local = (pkg.category == 'local_tour' or days <= 1)

    for vt, tier, km_rate, bata, local_km, local_rate in TARIFF_CONFIGS:
        if not vt:
            continue
        if is_local:
            PackageVehicleTariff.objects.create(
                package=pkg,
                vehicle_type=vt,
                seating_tier=tier,
                rate_type='local_1day',
                package_rate=Decimal(str(local_rate)),
                per_day_rate=Decimal(str(local_rate)),
                included_km=local_km,
                extra_km_rate=Decimal(str(km_rate)),
                driver_bata_per_day=Decimal(str(bata)),
                driver_bata_included=True,
                toll_parking_included=True,
                interstate_permit_included=False,
            )
        else:
            per_day = (300 * km_rate) + bata
            pkg_rate = days * per_day
            total_km = days * 300
            dest_lower = pkg.destination.lower()
            PackageVehicleTariff.objects.create(
                package=pkg,
                vehicle_type=vt,
                seating_tier=tier,
                rate_type='outstation_multiday',
                package_rate=Decimal(str(pkg_rate)),
                per_day_rate=Decimal(str(per_day)),
                included_km=total_km,
                extra_km_rate=Decimal(str(km_rate)),
                driver_bata_per_day=Decimal(str(bata)),
                driver_bata_included=True,
                toll_parking_included=True,
                interstate_permit_included=True if any(s in dest_lower for s in ['kerala', 'karnataka', 'coorg', 'munnar', 'wayanad', 'mysore', 'bangalore']) else False,
            )

def main():
    json_path = os.path.join(WORKSPACE_ROOT, 'scripts', 'scraped_manoj_packages.json')
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found!")
        return

    with open(json_path, encoding='utf-8') as f:
        scraped_data = json.load(f)

    print(f"Loaded {len(scraped_data)} packages from scraped JSON.")

    # Clean existing SGT- packages to avoid stale artifacts
    deleted_old = Package.objects.filter(package_code__startswith='SGT-').delete()
    print(f"Cleared previous SGT scraped packages: {deleted_old}")

    # Deduplicate based on normalized (title, days_count)
    unique_packages = {}
    for item in scraped_data:
        raw_title = item.get('title', '').strip()
        days_count = max(1, item.get('days_count', 1))
        norm_key = re.sub(r'[^a-z0-9]+', ' ', raw_title.lower()).strip()
        norm_key = ' '.join(norm_key.split())
        key = (norm_key, days_count)
        if key not in unique_packages:
            unique_packages[key] = item

    print(f"Deduplicated to {len(unique_packages)} unique pristine packages.")

    imported_count = 0
    updated_count = 0

    for idx, ((norm_key, days_count), item) in enumerate(unique_packages.items(), 1):
        raw_title = item.get('title', '')
        raw_cat = item.get('category_name', '')
        days_list = item.get('days', [])
        actual_days = max(1, len(days_list) if days_list else days_count)
        nights_count = max(0, actual_days - 1)

        category = determine_category(raw_cat, raw_title)
        package_name = format_clean_title(raw_title, actual_days)
        destinations = clean_rebrand(raw_title).replace('-', ', ').replace('  ', ' ').strip(', ')

        # Generate unique package code
        # Slugify title prefix
        slug_prefix = re.sub(r'[^A-Z0-9]+', '-', raw_title.upper()).strip('-')[:18]
        pkg_code = f"SGT-{slug_prefix}-{actual_days}D"
        
        # Ensure code uniqueness if clash
        existing = Package.objects.filter(package_code=pkg_code).first()
        if existing and existing.name != package_name:
            pkg_code = f"SGT-{slug_prefix}-{actual_days}D-{idx}"

        # Calculate standard pricing
        if actual_days == 1 or category == 'local_tour':
            pricing_type = 'vehicle_rate'
            ep_price = Decimal("2200.00")
            ap_price = Decimal("2800.00")
            base_price = Decimal("2200.00")
            meal_plan = 'EP'
        elif category == 'devotional':
            pricing_type = 'per_person'
            ep_price = Decimal(str(actual_days * 1500))
            ap_price = Decimal(str(actual_days * 2100))
            base_price = ap_price
            meal_plan = 'AP'
        elif category == 'family_vacation':
            pricing_type = 'per_person'
            ep_price = Decimal(str(actual_days * 2200))
            ap_price = Decimal(str(actual_days * 3100))
            base_price = ap_price
            meal_plan = 'MAP'
        else:
            pricing_type = 'per_person'
            ep_price = Decimal(str(actual_days * 1400))
            ap_price = Decimal(str(actual_days * 1950))
            base_price = ap_price
            meal_plan = 'AP'

        # Standard clean inclusions & terms for Siva Gayathri
        inclusions_text = (
            "Dedicated AC vehicle with experienced tourist driver as per itinerary.\n"
            "All fuel charges, driver bata, interstate toll, and vehicle parking charges.\n"
            f"Comprehensive sightseeing as detailed in the day-by-day itinerary.\n"
            + ("100% Satvik pure vegetarian South Indian meals.\n" if category == 'devotional' else "")
            + ("Daily breakfast & chef dinner included.\n" if meal_plan in ['AP', 'MAP'] else "")
            + "24x7 Siva Gayathri Tours on-trip support and dispatch control."
        )

        exclusions_text = (
            "Entry tickets to monuments, palaces, botanical gardens, and amusement parks.\n"
            "Personal boating charges, elephant safari, camera passes, and tips.\n"
            "Personal laundry, phone calls, and food items ordered outside the meal plan.\n"
            "Any unforeseen expenses due to road blocks, strikes, or natural conditions."
        )

        terms_text = (
            "50% advance upon confirmation and remaining 50% payable prior to departure.\n"
            "Vehicle will strictly run according to the agreed itinerary and designated routes.\n"
            "AC will be switched off on steep ghat roads and during prolonged halts as per standard safety rules.\n"
            "Siva Gayathri Tours & Travels guarantees verified, polite chauffeurs and sanitized vehicles."
        )

        is_dev = (category == 'devotional')

        pkg, created = Package.objects.get_or_create(
            package_code=pkg_code,
            defaults={
                'name': package_name,
                'destination': destinations,
                'category': category,
                'duration_nights': nights_count,
                'duration_days': actual_days,
                'base_price': base_price,
                'price_with_food': ap_price,
                'price_without_food': ep_price,
                'pricing_type': pricing_type,
                'meal_plan': meal_plan,
                'room_sharing_type': 'twin_sharing',
                'min_pax': 4 if actual_days == 1 else 15,
                'is_devotional': is_dev,
                'satvik_pure_veg_meals': is_dev,
                'senior_citizen_friendly': is_dev,
                'temple_dress_code': 'Strict Traditional Attire (Dhoti / Saree) mandatory for sanctum darshan.' if is_dev else '',
                'inclusions': inclusions_text,
                'exclusions': exclusions_text,
                'terms_and_conditions': terms_text,
                'contact_persons_footer': "Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131)",
                'is_active': True,
            }
        )

        if not created:
            pkg.name = package_name
            pkg.destination = destinations
            pkg.category = category
            pkg.duration_nights = nights_count
            pkg.duration_days = actual_days
            pkg.price_with_food = ap_price
            pkg.price_without_food = ep_price
            pkg.pricing_type = pricing_type
            pkg.meal_plan = meal_plan
            pkg.is_devotional = is_dev
            pkg.satvik_pure_veg_meals = is_dev
            pkg.senior_citizen_friendly = is_dev
            pkg.inclusions = inclusions_text
            pkg.exclusions = exclusions_text
            pkg.terms_and_conditions = terms_text
            pkg.save()
            updated_count += 1
        else:
            imported_count += 1

        # Attach Day-by-Day Itinerary
        ItineraryDay.objects.filter(package=pkg).delete()
        if days_list:
            for d in days_list:
                d_num = d.get('day', 1)
                spots_clean = clean_rebrand(d.get('details', ''))
                
                # Derive night stay if mentioned
                halt_loc = ""
                stay_match = re.search(r'(?:Stay|Halt at)\s+([A-Za-z]+)', spots_clean, re.IGNORECASE)
                if stay_match:
                    halt_loc = stay_match.group(1)
                elif actual_days == 1:
                    halt_loc = "Same Day Return"
                else:
                    halt_loc = destinations.split(',')[min(d_num - 1, len(destinations.split(',')) - 1)].strip()

                ItineraryDay.objects.create(
                    package=pkg,
                    day_number=d_num,
                    title=f"Day {d_num}: {package_name.replace('TOUR', '').strip().title()}",
                    route_segment=f"Segment {d_num}: {destinations}",
                    night_stay_location=halt_loc,
                    meals_included="Satvik Breakfast & Dinner" if is_dev else ("Breakfast Included" if actual_days > 1 else "On Own"),
                    sightseeing_spots=spots_clean,
                    activities=f"Guided sightseeing across {halt_loc or 'designated destination spots'}."
                )
        else:
            # Fallback 1 day
            ItineraryDay.objects.create(
                package=pkg,
                day_number=1,
                title=f"Day 1: Full Day Sightseeing",
                route_segment=destinations,
                night_stay_location="Same Day Return" if actual_days == 1 else destinations,
                meals_included="On Own",
                sightseeing_spots=destinations,
                activities=f"Complete tour covering key attractions along {destinations}."
            )

        # Attach 5-Tier Tariffs
        attach_tariffs(pkg)

        # Attach Darshan Slots if devotional
        if is_dev:
            TempleDarshanSlot.objects.filter(package=pkg).delete()
            for d in days_list:
                spots = d.get('details', '')
                temple_names = re.findall(r'([A-Za-z0-9\s]+(?:Temple|Kovil|Koil|Sannidhi|Amman|Swamy|Murugan|Shiva))', spots, re.IGNORECASE)
                for t_name in temple_names[:3]:
                    TempleDarshanSlot.objects.create(
                        package=pkg,
                        temple_name=clean_rebrand(t_name.strip()),
                        deity_or_circuit=destinations,
                        darshan_type='special_entry',
                        reporting_location='Temple Main Entrance Tower',
                        dress_code_notes='Traditional Dhoti / Saree',
                        senior_citizen_support=True
                    )

        if idx % 20 == 0 or idx == len(unique_packages):
            print(f"  Processed {idx}/{len(unique_packages)} packages... (Imported: {imported_count}, Updated: {updated_count})")

    print("\n" + "=" * 80)
    print(f"  IMPORT COMPLETE!")
    print(f"  Newly Created Packages: {imported_count}")
    print(f"  Updated Packages:       {updated_count}")
    print(f"  Total Packages in DB:   {Package.objects.count()}")
    print(f"  Total Itinerary Days:   {ItineraryDay.objects.count()}")
    print(f"  Total Vehicle Tariffs:  {PackageVehicleTariff.objects.count()}")
    print("=" * 80)

if __name__ == '__main__':
    main()
