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
print("  SIVA GAYATHRI TOURS & TRAVELS — CHENNAI TRAVELS IMPORTER")
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

def clean_title(title):
    t = clean_rebrand(title)
    # Remove SEO suffixes
    t = re.sub(r'[\u2013\u2014\-–|:].*?(?:Secrets|No Driving|No Rush|Limited|Offer|Expect|Made Easy|Do It Right|Must Read|Book Now|Wonders|Bliss|Unveil|Explore Now|Revealed|Everlasting|Package Before|Simple Steps|Hidden Gems).*$', '', t, flags=re.IGNORECASE)
    t = re.sub(r'^(?:Exclusive|Explore|Discover|Unveil)\s+', '', t, flags=re.IGNORECASE)
    t = re.sub(r'from\s*(?:₹|Rs\.?)\s*[\d,]+', '', t, flags=re.IGNORECASE)
    t = re.sub(r'Starts\s*@.*', '', t, flags=re.IGNORECASE)
    t = re.sub(r'-\s*Siva\s+Gayathri\s+Tours\s*(?:&|and)?\s*Travels', '', t, flags=re.IGNORECASE)
    t = re.sub(r'[\u2013\u2014–]+', '-', t)
    t = ' '.join(t.split()).strip(' -:')
    return t.upper()

def determine_category(title, days):
    t_lower = title.lower()
    if any(k in t_lower for k in ['temple', 'navagraha', 'sabarimala', 'pilgrimage', 'darshan', 'murugan', 'shiva', 'amman', 'divya desam', 'narasimhar', 'tirupati', 'kumbakonam', 'kasi', 'varanasi', 'kalahasti', 'srisailam', 'church', 'christian']):
        return 'devotional'
    if any(k in t_lower for k in ['ooty', 'kodaikanal', 'coorg', 'munnar', 'wayanad', 'yercaud', 'valparai', 'kolli', 'yelagiri', 'vagamon']):
        return 'hill_station'
    if 'honeymoon' in t_lower:
        return 'family_vacation'
    if days == 1 or 'one day' in t_lower:
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
                interstate_permit_included=True if any(s in dest_lower for s in ['kerala', 'karnataka', 'goa', 'tirupati', 'andhra', 'pondicherry', 'puducherry']) else False,
            )

def main():
    json_path = os.path.join(WORKSPACE_ROOT, 'scripts', 'scraped_chennai_packages.json')
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found!")
        return

    with open(json_path, encoding='utf-8') as f:
        scraped_data = json.load(f)

    # Filter out non-tours
    tours = [p for p in scraped_data if not any(k in p['title'].lower() for k in ['job', 'ticket', 'tariff', 'policy', 'attach'])]
    print(f"Loaded {len(tours)} valid tour packages to import.")

    # Clear previous SGT-CT records if re-running
    deleted = Package.objects.filter(package_code__startswith='SGT-CT-').delete()
    print(f"Cleared previous SGT-CT records: {deleted}")

    imported_count = 0

    for idx, item in enumerate(tours, 1):
        raw_title = item.get('title', '')
        days = max(1, item.get('days', 1))
        nights = item.get('nights', max(0, days - 1))
        scraped_price = item.get('price', 0)
        days_plan = item.get('days_plan', [])

        name = clean_title(raw_title)
        if not name.endswith('TOUR') and not name.endswith('PACKAGE') and not name.endswith('YATRA'):
            name = f"{name} TOUR PACKAGE"

        category = determine_category(name, days)
        is_dev = (category == 'devotional')

        # Generate unique code
        # Slug from URL or title
        url_slug = item['url'].rstrip('.html').split('/')[-1]
        slug_clean = re.sub(r'[^A-Z0-9]+', '-', url_slug.upper()).strip('-')[:18]
        pkg_code = f"SGT-CT-{slug_clean}-{days}D"
        if Package.objects.filter(package_code=pkg_code).exists():
            pkg_code = f"SGT-CT-{slug_clean}-{days}D-{idx}"

        # Destination derived from title
        dest_clean = name.replace('TOUR', '').replace('PACKAGE', '').replace('YATRA', '').strip()
        dest_clean = clean_rebrand(dest_clean).title()

        # Pricing
        if days == 1 or category == 'local_tour':
            pricing_type = 'vehicle_rate'
            ep_price = Decimal("2200.00")
            ap_price = Decimal("2800.00")
            base_price = Decimal("2200.00")
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

        # Attach Itinerary Days
        ItineraryDay.objects.filter(package=pkg).delete()
        if days_plan:
            for d in days_plan:
                d_num = d.get('day', 1)
                spots = clean_rebrand(d.get('spots', dest_clean))
                d_title = clean_rebrand(d.get('title', f"Day {d_num}: Sightseeing"))
                
                ItineraryDay.objects.create(
                    package=pkg,
                    day_number=d_num,
                    title=d_title,
                    route_segment=f"Segment {d_num}: {dest_clean}",
                    night_stay_location="Same Day Return" if days == 1 else dest_clean.split(',')[min(d_num-1, len(dest_clean.split(','))-1)].strip(),
                    meals_included="Satvik Meals" if is_dev else ("Breakfast Included" if days > 1 else "On Own"),
                    sightseeing_spots=spots,
                    activities=f"Coordinated visits to {spots}."
                )
        else:
            ItineraryDay.objects.create(
                package=pkg,
                day_number=1,
                title=f"Day 1: Full Day Sightseeing & Shrines",
                route_segment=dest_clean,
                night_stay_location="Same Day Return" if days == 1 else dest_clean,
                meals_included="On Own",
                sightseeing_spots=dest_clean,
                activities=f"Guided tour covering prominent landmarks along {dest_clean}."
            )

        # Attach Tariffs
        attach_tariffs(pkg)

        # Attach Temple Darshan Slots if devotional
        if is_dev:
            TempleDarshanSlot.objects.filter(package=pkg).delete()
            for d in days_plan:
                spots = d.get('spots', '')
                t_names = re.findall(r'([A-Za-z0-9\s]+(?:Temple|Mutt|Kovil|Koil|Sannidhi|Amman|Swamy|Jyotirlinga|Darshan))', spots, re.IGNORECASE)
                for t in t_names[:2]:
                    TempleDarshanSlot.objects.create(
                        package=pkg,
                        temple_name=clean_rebrand(t.strip()),
                        deity_or_circuit=dest_clean,
                        darshan_type='special_entry',
                        reporting_location='Temple Main Entrance',
                        dress_code_notes='Traditional Dhoti / Saree',
                        senior_citizen_support=True
                    )

        imported_count += 1
        if idx % 20 == 0 or idx == len(tours):
            print(f"  Processed {idx}/{len(tours)} packages... (Imported: {imported_count})")

    print("\n" + "=" * 80)
    print(f"  IMPORT COMPLETE!")
    print(f"  Newly Created Packages: {imported_count}")
    print(f"  Total Packages in DB:   {Package.objects.count()}")
    print(f"  Total Itinerary Days:   {ItineraryDay.objects.count()}")
    print(f"  Total Vehicle Tariffs:  {PackageVehicleTariff.objects.count()}")
    print("=" * 80)

if __name__ == '__main__':
    main()
