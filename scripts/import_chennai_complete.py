import os
import sys
import re
import json
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

sys.stdout.reconfigure(encoding='utf-8')

print("=" * 80)
print("  SIVA GAYATHRI TOURS & TRAVELS — COMPLETE CHENNAI CATALOG IMPORTER")
print("=" * 80)

# Fetch Vehicle Types
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
        (re.compile(r'Chennai\s+Tours\s*(?:&|and)\s*Travels', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Chennai\s+Travels', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'chennaitravels\.in', re.IGNORECASE), 'sivagayathritravels.com'),
        (re.compile(r'booking@chennaitravels\.in', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'info@chennaitravels\.in', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'\+91[\s\d-]{9,15}'), '+91 98425 33777'),
    ]
    cleaned = text
    for pattern, repl in replacements:
        cleaned = pattern.sub(repl, cleaned)
    return cleaned.strip()

def determine_category(title, days):
    t_lower = title.lower()
    if any(k in t_lower for k in ['temple', 'navagraha', 'sabarimala', 'pilgrimage', 'darshan', 'murugan', 'shiva', 'amman', 'divya desam', 'narasimhar', 'tirupati', 'kumbakonam', 'kasi', 'varanasi', 'kalahasti', 'srisailam', 'church', 'christian', 'shrine']):
        return 'devotional'
    if any(k in t_lower for k in ['ooty', 'kodaikanal', 'coorg', 'munnar', 'wayanad', 'yercaud', 'valparai', 'kolli', 'yelagiri', 'vagamon']):
        return 'hill_station'
    if 'honeymoon' in t_lower or 'family' in t_lower:
        return 'family_vacation'
    if days == 1 or '1-day' in t_lower or 'one day' in t_lower:
        return 'local_tour'
    return 'holiday'

def attach_tariffs(pkg, item):
    PackageVehicleTariff.objects.filter(package=pkg).delete()
    days = pkg.duration_days
    is_local = (pkg.category == 'local_tour' or days <= 1)

    sedan_p = item.get('sedan_price')
    innova_p = item.get('innova_price')

    for vt, tier, km_rate, bata, local_km, default_local_rate in TARIFF_CONFIGS:
        if not vt:
            continue
        if is_local:
            if tier == '4_sedan' and sedan_p:
                rate = float(sedan_p)
            elif tier == '7_crysta' and innova_p:
                rate = float(innova_p)
            elif tier == '17_tt_urbania':
                base_ref = innova_p if innova_p else default_local_rate
                rate = float(base_ref) * 1.55
            elif tier == '36_mini_bus':
                base_ref = innova_p if innova_p else default_local_rate
                rate = float(base_ref) * 2.25
            elif tier == '54_luxury_coach':
                base_ref = innova_p if innova_p else default_local_rate
                rate = float(base_ref) * 3.10
            else:
                rate = default_local_rate

            PackageVehicleTariff.objects.create(
                package=pkg,
                vehicle_type=vt,
                seating_tier=tier,
                rate_type='local_1day',
                package_rate=Decimal(str(round(rate, 2))),
                per_day_rate=Decimal(str(round(rate, 2))),
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
                package_rate=Decimal(str(round(pkg_rate, 2))),
                per_day_rate=Decimal(str(round(per_day, 2))),
                included_km=total_km,
                extra_km_rate=Decimal(str(km_rate)),
                driver_bata_per_day=Decimal(str(bata)),
                driver_bata_included=True,
                toll_parking_included=True,
                interstate_permit_included=True if any(s in dest_lower for s in ['kerala', 'karnataka', 'goa', 'tirupati', 'andhra', 'pondicherry', 'puducherry']) else False,
            )

def main():
    json_path = os.path.join(WORKSPACE_ROOT, 'scripts', 'scraped_chennai_packages_complete.json')
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found!")
        return

    with open(json_path, encoding='utf-8') as f:
        tours = json.load(f)

    print(f"Loaded {len(tours)} complete tour packages to import.")

    # Clear previous SGT-CT records
    deleted = Package.objects.filter(package_code__startswith='SGT-CT-').delete()
    print(f"Cleared previous SGT-CT records: {deleted}")

    imported_count = 0

    for idx, item in enumerate(tours, 1):
        name = item.get('title', '').strip()
        days = max(1, item.get('days', 1))
        nights = item.get('nights', max(0, days - 1))
        scraped_price = item.get('price', 0)
        days_plan = item.get('days_plan', [])

        category = determine_category(name, days)
        is_dev = (category == 'devotional')

        # Generate unique code
        url_part = item['url'].split('#')[-1] if '#' in item['url'] else item['url'].rstrip('.html').split('/')[-1]
        slug_clean = re.sub(r'[^A-Z0-9]+', '-', url_part.upper()).strip('-')[:18]
        pkg_code = f"SGT-CT-{slug_clean}-{days}D"
        if Package.objects.filter(package_code=pkg_code).exists():
            pkg_code = f"SGT-CT-{slug_clean}-{days}D-{idx}"

        # Destination derived from title
        dest_clean = name.replace('1-DAY', '').replace('TOUR', '').replace('PACKAGE', '').replace('YATRA', '').replace('CIRCUIT', '').strip()
        dest_clean = clean_rebrand(dest_clean).title()

        # Pricing
        if days == 1 or category == 'local_tour':
            pricing_type = 'vehicle_rate'
            ep_price = Decimal(str(item.get('sedan_price', 3000)))
            ap_price = Decimal(str(item.get('innova_price', 4500)))
            base_price = ep_price
            meal_plan = 'EP'
        elif scraped_price and 1500 <= scraped_price <= 150000:
            pricing_type = 'per_person'
            ap_price = Decimal(str(scraped_price))
            ep_price = Decimal(str(int(scraped_price * 0.78)))
            base_price = ap_price
            meal_plan = 'AP'
        elif is_dev:
            pricing_type = 'per_person'
            ep_price = Decimal(str(days * 1500))
            ap_price = Decimal(str(days * 2100))
            base_price = ap_price
            meal_plan = 'AP'
        elif category == 'family_vacation':
            pricing_type = 'per_person'
            ep_price = Decimal(str(days * 2200))
            ap_price = Decimal(str(days * 3100))
            base_price = ap_price
            meal_plan = 'MAP'
        else:
            pricing_type = 'per_person'
            ep_price = Decimal(str(days * 1400))
            ap_price = Decimal(str(days * 1950))
            base_price = ap_price
            meal_plan = 'AP'

        inclusions_text = (
            "Well-maintained, sanitized tourist vehicle with professional route chauffeur.\n"
            "All fuel charges, interstate permit fees, highway tolls, and parking taxes.\n"
            f"Comprehensive sightseeing covering key attractions along {dest_clean}.\n"
            + ("100% Satvik Pure Vegetarian South Indian meals.\n" if is_dev else "")
            + ("Daily breakfast & chef dinner included.\n" if meal_plan in ['AP', 'MAP'] else "")
            + "24x7 Siva Gayathri Tours & Travels dispatch and guest support."
        )

        exclusions_text = (
            "Monument entrance tickets, boating charges, camera tokens, and personal expenses.\n"
            "Special darshan passes / personal pooja archana tickets.\n"
            "Any unforeseen expense arising from road traffic, natural diversions, or flight delays."
        )

        terms_text = (
            "50% advance upon tour confirmation, remaining balance payable before trip departure.\n"
            "Vehicle will strictly adhere to designated routes and tourist safety regulations.\n"
            "AC will be switched off on ghat hairpin bends for engine power and safety.\n"
            "Siva Gayathri Tours & Travels guarantees polite drivers and timely assistance."
        )

        pkg = Package.objects.create(
            package_code=pkg_code,
            name=name,
            destination=dest_clean,
            category=category,
            duration_nights=nights,
            duration_days=days,
            base_price=base_price,
            price_with_food=ap_price,
            price_without_food=ep_price,
            pricing_type=pricing_type,
            meal_plan=meal_plan,
            room_sharing_type='twin_sharing',
            min_pax=4 if days == 1 else 15,
            is_devotional=is_dev,
            satvik_pure_veg_meals=is_dev,
            senior_citizen_friendly=is_dev,
            temple_dress_code="Mandatory Traditional Dress: Dhoti/Kurta for Men, Saree/Chudidar for Women" if is_dev else "",
            inclusions=inclusions_text,
            exclusions=exclusions_text,
            terms_and_conditions=terms_text,
            contact_persons_footer="Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131)",
            is_active=True,
        )

        # Create Itinerary Days
        for d_info in days_plan:
            d_num = d_info.get('day', 1)
            d_title = d_info.get('title', f"Day {d_num}: Sightseeing & Travel")
            d_spots = d_info.get('spots', name)
            ItineraryDay.objects.create(
                package=pkg,
                day_number=d_num,
                title=d_title[:250],
                route_segment=f"{dest_clean} Circuit"[:250],
                activities=d_spots,
                sightseeing_spots=d_spots[:500],
                meals_included="Breakfast, Lunch, Dinner" if meal_plan == 'AP' else ("Breakfast & Dinner" if meal_plan == 'MAP' else "Not Included"),
                night_stay_location=dest_clean.split()[0] if days > 1 and d_num < days else "Return Journey",
            )

        # Attach Tariffs
        attach_tariffs(pkg, item)

        # Devotional Temple Slots
        if is_dev:
            dest_lower = name.lower()
            if 'tirupati' in dest_lower:
                TempleDarshanSlot.objects.create(
                    package=pkg,
                    temple_name="Tirumala Sri Venkateswara Temple",
                    deity_or_circuit="Lord Venkateswara (Balaji)",
                    darshan_type="special_entry_300",
                    booked_slot_time="09:00 AM - 11:00 AM",
                    reporting_location="Vaikuntam Queue Complex 1",
                    dress_code_notes="Strict Traditional: Dhoti/Kurta for Men, Saree/Chudidar for Women",
                    prasad_details="Tirupati Laddu Prasadam Included",
                    senior_citizen_support=True
                )
            if 'rameshwaram' in dest_lower or 'rameswaram' in dest_lower:
                TempleDarshanSlot.objects.create(
                    package=pkg,
                    temple_name="Ramanathaswamy Temple",
                    deity_or_circuit="Lord Shiva (Ramanathaswamy)",
                    darshan_type="special_entry_300",
                    booked_slot_time="06:00 AM - 08:00 AM",
                    reporting_location="East Gopuram Entrance",
                    dress_code_notes="Traditional Attire (Post 22 Theertham holy bath change)",
                    prasad_details="Holy Theertham & Prasadam",
                    senior_citizen_support=True
                )
            if 'madurai' in dest_lower:
                TempleDarshanSlot.objects.create(
                    package=pkg,
                    temple_name="Madurai Meenakshi Amman Temple",
                    deity_or_circuit="Goddess Meenakshi & Sundareswarar",
                    darshan_type="vip_break",
                    booked_slot_time="08:30 AM - 10:30 AM",
                    reporting_location="South Tower Entrance",
                    dress_code_notes="Strict Traditional Attire",
                    prasad_details="Meenakshi Amman Vibhuti & Kumkum Prasadam",
                    senior_citizen_support=True
                )

        imported_count += 1
        if imported_count % 20 == 0 or imported_count == len(tours):
            print(f"  Imported {imported_count}/{len(tours)}: {name[:50]} ({nights}N/{days}D)")

    print("=" * 80)
    print(f"SUCCESS! Imported {imported_count} comprehensive packages with full day itineraries & vehicle tariffs.")
    print("=" * 80)

if __name__ == '__main__':
    main()
