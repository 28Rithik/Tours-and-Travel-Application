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
    InternationalDocumentChecklist,
)
from core.models import VehicleType

sys.stdout.reconfigure(encoding='utf-8')

print("=" * 80)
print("  SIVA GAYATHRI TOURS & TRAVELS — JAISUN TOURISM CATALOG IMPORTER")
print("=" * 80)

# Fetch Vehicle Types
vtypes = list(VehicleType.objects.all())
sedan_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['sedan', 'dzire', 'etios'])), vtypes[0] if vtypes else None)
crysta_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['crysta', 'innova'])), vtypes[1] if len(vtypes) > 1 else sedan_vt)
urbania_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['urbania', 'tempo', '17'])), vtypes[2] if len(vtypes) > 2 else sedan_vt)
bus36_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['36', 'mini', '40'])), vtypes[3] if len(vtypes) > 3 else sedan_vt)
coach54_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['54', 'coach', '52', 'volvo'])), vtypes[4] if len(vtypes) > 4 else sedan_vt)

TARIFF_CONFIGS = [
    (sedan_vt, '4_sedan', 14.0, 500.0),
    (crysta_vt, '7_crysta', 20.0, 600.0),
    (urbania_vt, '17_tt_urbania', 26.0, 800.0),
    (bus36_vt, '36_mini_bus', 35.0, 1000.0),
    (coach54_vt, '54_luxury_coach', 45.0, 1200.0),
]

INTL_KEYWORDS = [
    'dubai', 'singapore', 'malaysia', 'thailand', 'bangkok', 'pattaya', 'bali',
    'switzerland', 'europe', 'uk', 'united kingdom', 'london', 'usa', 'america',
    'australia', 'japan', 'korea', 'china', 'russia', 'turkey', 'philippines',
    'cambodia', 'vietnam', 'south africa', 'georgia', 'armenia', 'canada',
    'ireland', 'kazakhstan', 'ukraine', 'egypt', 'greece', 'azerbaijan',
    'tashkent', 'uzbekistan', 'kyrgyzstan', 'kenya', 'tanzania', 'new zealand',
    'maldives', 'mauritius', 'sri lanka', 'colombo', 'nepal', 'kathmandu',
    'bhutan', 'thimphu', 'glaciers', 'hong kong', 'alaska'
]

DEV_KEYWORDS = [
    'yatra', 'dham', 'pilgrimage', 'darshan', 'temple', 'shirdi', 'varanasi',
    'amarnath', 'nava graha', 'navagraha', 'muktinath', 'rameshwaram', 'kailash',
    'vaishno', 'somnath', 'dwarka'
]

HILL_KEYWORDS = [
    'ooty', 'kodaikanal', 'munnar', 'wayanad', 'coorg', 'darjeeling', 'shimla',
    'manali', 'mussoorie', 'nainital', 'kullu'
]

def clean_rebrand(text):
    if not text:
        return ""
    replacements = [
        (re.compile(r'Jaisun\s+Tourism', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Jaisun', re.IGNORECASE), 'Siva Gayathri'),
        (re.compile(r'jaisuntourism\.com', re.IGNORECASE), 'sivagayathritravels.com'),
        (re.compile(r'booking@jaisuntourism\.com', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'info@jaisuntourism\.com', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'\+91[\s\d-]{9,15}'), '+91 98425 33777'),
    ]
    cleaned = text
    for pattern, repl in replacements:
        cleaned = pattern.sub(repl, cleaned)
    return cleaned.strip()

def determine_intl(title, url):
    combo = (title + ' ' + url).lower()
    return any(k in combo for k in INTL_KEYWORDS)

def determine_category(title, url, is_intl):
    combo = (title + ' ' + url).lower()
    if any(k in combo for k in DEV_KEYWORDS):
        return 'devotional'
    if any(k in combo for k in HILL_KEYWORDS):
        return 'hill_station'
    if 'honeymoon' in combo:
        return 'family_vacation'
    if 'academic' in combo or 'college' in combo:
        return 'college_iv'
    return 'holiday'

def determine_currency(title, url):
    combo = (title + ' ' + url).lower()
    if any(k in combo for k in ['europe', 'switzerland', 'france', 'denmark', 'sweden', 'norway', 'ireland', 'greece']):
        return 'EUR'
    if any(k in combo for k in ['uk', 'united kingdom', 'london', 'scotland']):
        return 'GBP'
    if 'dubai' in combo:
        return 'AED'
    if 'singapore' in combo:
        return 'SGD'
    if 'malaysia' in combo:
        return 'MYR'
    if 'thailand' in combo or 'bangkok' in combo or 'pattaya' in combo:
        return 'THB'
    if any(k in combo for k in ['usa', 'america', 'canada', 'australia', 'japan', 'korea', 'maldives', 'mauritius', 'vietnam', 'cambodia', 'turkey', 'kenya', 'tanzania', 'egypt', 'south africa', 'china', 'philippines']):
        return 'USD'
    return 'INR'

def attach_tariffs(pkg, days):
    PackageVehicleTariff.objects.filter(package=pkg).delete()
    for vt, tier, km_rate, bata in TARIFF_CONFIGS:
        if not vt:
            continue
        daily = (300 * km_rate) + bata
        pkg_rate = days * daily
        PackageVehicleTariff.objects.create(
            package=pkg,
            vehicle_type=vt,
            seating_tier=tier,
            rate_type='outstation_multiday',
            package_rate=Decimal(str(round(pkg_rate, 2))),
            per_day_rate=Decimal(str(round(daily, 2))),
            included_km=days * 300,
            extra_km_rate=Decimal(str(km_rate)),
            driver_bata_per_day=Decimal(str(bata)),
            driver_bata_included=True,
            toll_parking_included=True,
            interstate_permit_included=True if pkg.is_international or any(k in pkg.name.lower() for k in ['kerala', 'karnataka', 'tirupati', 'andhra', 'goa', 'delhi', 'rajasthan', 'himachal', 'kashmir']) else False,
        )

def main():
    json_path = os.path.join(WORKSPACE_ROOT, 'scripts', 'scraped_jaisun_packages.json')
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found!")
        return

    with open(json_path, encoding='utf-8') as f:
        packages = json.load(f)

    print(f"Loaded {len(packages)} packages from scraped Jaisun catalog.")

    # Clear previous SGT-JT records
    deleted = Package.objects.filter(package_code__startswith='SGT-JT-').delete()
    print(f"Cleared previous SGT-JT records: {deleted}")

    imported_count = 0

    for idx, item in enumerate(packages, 1):
        raw_title = item.get('title', '')
        url = item.get('url', '')
        days = max(1, item.get('days', 1))
        nights = item.get('nights', max(0, days - 1))
        days_plan = item.get('days_plan', [])

        name = clean_rebrand(raw_title)
        if not name.endswith('TOUR') and not name.endswith('PACKAGE') and not name.endswith('YATRA') and not name.endswith('CRUISE'):
            name = f"{name} TOUR PACKAGE"

        is_intl = determine_intl(name, url)
        category = determine_category(name, url, is_intl)
        is_dev = (category == 'devotional')

        # Code slug
        url_slug = url.rstrip('/').split('/')[-1]
        slug_clean = re.sub(r'[^A-Z0-9]+', '-', url_slug.upper()).strip('-')[:18]
        pkg_code = f"SGT-JT-{slug_clean}-{days}D"
        if Package.objects.filter(package_code=pkg_code).exists():
            pkg_code = f"SGT-JT-{slug_clean}-{days}D-{idx}"

        # Destination derived from title
        dest_clean = name.replace('TOUR', '').replace('PACKAGE', '').replace('YATRA', '').replace('CRUISE', '').replace('GROUP', '').replace('INBOUND', '').strip()
        dest_clean = clean_rebrand(dest_clean).title()
        if not dest_clean:
            dest_clean = "Scenic Circuit"

        # Pricing
        if is_intl:
            pricing_type = 'per_person'
            ap_price = Decimal(str(days * 7500))
            ep_price = Decimal(str(days * 5800))
            base_price = ap_price
            meal_plan = 'MAP'
        elif is_dev:
            pricing_type = 'per_person'
            ap_price = Decimal(str(days * 2200))
            ep_price = Decimal(str(days * 1600))
            base_price = ap_price
            meal_plan = 'AP'
        elif category == 'family_vacation':
            pricing_type = 'per_person'
            ap_price = Decimal(str(days * 3500))
            ep_price = Decimal(str(days * 2700))
            base_price = ap_price
            meal_plan = 'MAP'
        elif category == 'hill_station':
            pricing_type = 'per_person'
            ap_price = Decimal(str(days * 2400))
            ep_price = Decimal(str(days * 1800))
            base_price = ap_price
            meal_plan = 'AP'
        else:
            pricing_type = 'per_person'
            ap_price = Decimal(str(days * 2600))
            ep_price = Decimal(str(days * 1950))
            base_price = ap_price
            meal_plan = 'AP'

        # Build Inclusions / Exclusions
        inc_list = item.get('inclusions', [])
        inclusions_text = "\n".join(inc_list) if inc_list else (
            "Well-maintained, sanitized tourist vehicle with professional route chauffeur.\n"
            "All fuel charges, interstate permit taxes, highway tolls, and parking fees.\n"
            f"Comprehensive sightseeing covering key attractions along {dest_clean}.\n"
            + ("100% Satvik Pure Vegetarian South Indian meals.\n" if is_dev else "")
            + ("Daily breakfast & dinner included.\n" if meal_plan in ['AP', 'MAP'] else "")
            + "24x7 Siva Gayathri Tours & Travels dispatch and guest support."
        )

        exc_list = item.get('exclusions', [])
        exclusions_text = "\n".join(exc_list) if exc_list else (
            "Monument entrance tickets, boating charges, camera tokens, and personal expenses.\n"
            + ("International / domestic airfare & visa fees (available on request).\n" if is_intl else "Personal temple archana and pooja expenses.\n")
            + "Any unforeseen expense arising from road traffic, natural diversions, or flight delays."
        )

        terms_text = (
            "50% advance deposit upon tour confirmation, remaining balance payable prior to trip departure.\n"
            "Vehicle will strictly adhere to designated routes, safety rules, and permit schedules.\n"
            "AC will be switched off on steep ghat roads and hairpin bends for engine power and passenger safety.\n"
            "Siva Gayathri Tours & Travels guarantees polite chauffeurs, sanitized coaches, and timely support."
        )

        currency_val = determine_currency(name, url)

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
            min_pax=2 if is_intl else (4 if days <= 2 else 15),
            is_international=is_intl,
            destination_country=dest_clean.split(',')[0] if is_intl else "India",
            currency_code=currency_val,
            visa_required=is_intl,
            visa_guidelines=f"Tourist eVisa / Entry Authorization required for {dest_clean}. Valid passport with min 6 months validity mandatory." if is_intl else "",
            passport_validity_months=6 if is_intl else 0,
            flight_inclusive=False,
            flight_details_note=f"Scheduled flight booking assistance available Ex-Coimbatore (CJB) / Ex-Chennai (MAA) to {dest_clean}." if is_intl else "",
            overseas_dmc_partner=f"Certified DMC Destination Partner in {dest_clean}" if is_intl else "",
            is_devotional=is_dev,
            satvik_pure_veg_meals=is_dev,
            senior_citizen_friendly=is_dev,
            temple_dress_code="Mandatory Traditional Dress: Dhoti/Kurta for Men, Saree/Chudidar for Women" if is_dev else "",
            temple_darshan_info=f"Sacred Pilgrimage Circuit covering prominent shrines of {dest_clean}." if is_dev else "",
            inclusions=inclusions_text,
            exclusions=exclusions_text,
            terms_and_conditions=terms_text,
            contact_persons_footer="Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131)",
            is_active=True,
        )

        # Create Itinerary Days
        for d in days_plan:
            d_num = d.get('day', 1)
            d_title = d.get('title', f"Day {d_num}: Sightseeing & Exploration")
            d_spots = d.get('spots', dest_clean)
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
        attach_tariffs(pkg, days)

        # Attach International Document Checklist
        if is_intl:
            docs = [
                ("Original Passport (Min 6 months validity from return date)", True, 15, "Scan of front & back bio-pages"),
                ("Passport Size Photograph (35x45mm, White background)", True, 10, "Matte finish, 80% face close up"),
                ("Tourist eVisa / Entry Authorization Form", True, 7, "Processed via embassy portal"),
                ("Confirmed Return Air Tickets & Hotel Vouchers", True, 5, "Issued by Siva Gayathri Tours"),
                ("Overseas Travel & Medical Insurance Certificate", True, 5, "Minimum $50,000 coverage"),
            ]
            for dname, mand, dline, note in docs:
                InternationalDocumentChecklist.objects.create(
                    package=pkg,
                    document_name=dname,
                    is_mandatory=mand,
                    submission_deadline_days=dline,
                    notes=note
                )

        # Devotional Temple Slots
        if is_dev:
            dest_lower = name.lower()
            if 'char dham' in dest_lower or 'dham' in dest_lower:
                TempleDarshanSlot.objects.create(
                    package=pkg,
                    temple_name="Badrinath & Kedarnath Sacred Dhams",
                    deity_or_circuit="Lord Badri Vishal & Lord Shiva Jyotirlinga",
                    darshan_type="special_entry_300",
                    booked_slot_time="06:00 AM - 09:00 AM",
                    reporting_location="Temple Gate Queue Complex",
                    dress_code_notes="Strict Traditional Attire (Warm woolen spiritual clothes)",
                    prasad_details="Holy Tulsi & Badrinath Mahaprasad Included",
                    senior_citizen_support=True
                )
            elif 'varanasi' in dest_lower or 'kashi' in dest_lower:
                TempleDarshanSlot.objects.create(
                    package=pkg,
                    temple_name="Kashi Vishwanath Jyotirlinga & Ganga Aarti",
                    deity_or_circuit="Lord Shiva (Vishwanath)",
                    darshan_type="special_entry_300",
                    booked_slot_time="05:30 AM - 08:30 AM",
                    reporting_location="Kashi Vishwanath Corridor Gate 4",
                    dress_code_notes="Strict Traditional Dhoti/Kurta (Men), Saree (Women)",
                    prasad_details="Holy Ganga Jal & Rudraksha Prasadam Included",
                    senior_citizen_support=True
                )
            elif 'shirdi' in dest_lower:
                TempleDarshanSlot.objects.create(
                    package=pkg,
                    temple_name="Shirdi Sai Baba Samadhi Mandir",
                    deity_or_circuit="Sri Sai Baba",
                    darshan_type="special_entry_300",
                    booked_slot_time="07:00 AM - 09:30 AM",
                    reporting_location="Gate Number 2 VIP / Special Entry",
                    dress_code_notes="Decent Traditional Attire",
                    prasad_details="Sai Baba Udi & Boondi Ladoo Prasadam",
                    senior_citizen_support=True
                )
            elif 'navagraha' in dest_lower:
                TempleDarshanSlot.objects.create(
                    package=pkg,
                    temple_name="Kumbakonam Navagraha Sthalam Sannidhis",
                    deity_or_circuit="Navagraha 9 Planetary Deities",
                    darshan_type="special_entry_300",
                    booked_slot_time="08:00 AM - 12:00 PM",
                    reporting_location="Navagraha Temple Sannidhis",
                    dress_code_notes="Strict Traditional Dhoti / Saree",
                    prasad_details="Navadhanya Prasadam & Holy Rakshai",
                    senior_citizen_support=True
                )

        imported_count += 1
        if imported_count % 20 == 0 or imported_count == len(packages):
            print(f"  Imported {imported_count}/{len(packages)}: {name[:45]} ({nights}N/{days}D) [Category: {category}]")

    print("=" * 80)
    print(f"SUCCESS! Imported all {imported_count} Jaisun Tourism packages into database under prefix SGT-JT-!")
    print("=" * 80)

if __name__ == '__main__':
    main()
