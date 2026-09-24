import os
import sys
import re
import json
import ssl
import html
import urllib.request
from decimal import Decimal
from bs4 import BeautifulSoup

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

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
}

# ==============================================================================
# CLEANING, REBRANDING & NORMALIZATION UTILITIES
# ==============================================================================

def clean_html_text(text):
    if not text:
        return ""
    text = html.unescape(text)
    soup = BeautifulSoup(text, 'html.parser')
    for li in soup.find_all('li'):
        li.insert_before('\n- ')
    for br in soup.find_all('br'):
        br.replace_with('\n')
    cleaned = soup.get_text()
    cleaned = cleaned.replace('\xa0', ' ').replace('\u2013', ' - ').replace('\u2014', ' - ').replace('\u2015', ' - ')
    cleaned = cleaned.replace('\u00a0', ' ').replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    lines = [line.strip() for line in cleaned.split('\n') if line.strip()]
    return '\n'.join(lines)

def clean_rebrand(text):
    if not text:
        return ""
    # Normalize unicode punctuation and hyphens
    text = text.replace('\u2013', ' - ').replace('\u2014', ' - ').replace('\u2015', ' - ')
    text = text.replace('\u00a0', ' ').replace('\xa0', ' ').replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    
    # Strip any external links
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'wa\.link/\S+', '', text)
    text = re.sub(r'(?:www\.)?[a-zA-Z0-9-]+\.(?:com|in|org|net)/\S*', '', text)

    replacements = [
        (re.compile(r'Aspire\s+Holidays\s+(?:Pvt\s+Ltd|Private\s+Limited)?', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Aspire\s+Holiday\s+(?:Pvt\s+Ltd|Private\s+Limited)?', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Aspire\s+Tours\s+(?:and|&)\s+Travels', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Aspire\s+Travels?', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'\bAspire\b', re.IGNORECASE), 'Siva Gayathri'),
        (re.compile(r'aspireholidays\.in', re.IGNORECASE), 'sivagayathritravels.com'),
        (re.compile(r'info@aspireholidays\.in', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'\+91[\s\d-]{9,15}'), '+91 98425 33777'),
    ]
    cleaned = text
    for pattern, repl in replacements:
        cleaned = pattern.sub(repl, cleaned)

    # Clean double package tags or unwanted repetitive suffixes
    cleaned = re.sub(r'(\bTOUR PACKAGE\b\s*)+', 'TOUR PACKAGE', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'(\bPACKAGE\b\s*)+', 'PACKAGE', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*,\s*', ', ', cleaned)
    cleaned = re.sub(r'\s*-\s*', ' - ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def detect_country_currency(country_name, title):
    combined = f"{country_name} {title}".lower()
    mapping = [
        (('thailand', 'bangkok', 'pattaya', 'phuket', 'krabi'), 'Thailand', 'THB'),
        (('singapore',), 'Singapore', 'SGD'),
        (('malaysia', 'kuala lumpur', 'langkawi', 'penang'), 'Malaysia', 'MYR'),
        (('dubai', 'abu dhabi', 'uae', 'sharjah'), 'United Arab Emirates', 'AED'),
        (('indonesia', 'bali', 'jakarta'), 'Indonesia', 'IDR'),
        (('vietnam', 'hanoi', 'da nang', 'phu quoc', 'ho chi minh'), 'Vietnam', 'VND'),
        (('maldives',), 'Maldives', 'USD'),
        (('sri lanka', 'colombo', 'kandy', 'bentota'), 'Sri Lanka', 'LKR'),
        (('switzerland', 'swiss', 'zurich', 'lucerne', 'interlaken'), 'Switzerland', 'CHF'),
        (('france', 'paris'), 'France', 'EUR'),
        (('italy', 'rome', 'venice', 'florence', 'milan'), 'Italy', 'EUR'),
        (('spain', 'barcelona', 'madrid'), 'Spain', 'EUR'),
        (('germany', 'berlin', 'munich', 'frankfurt'), 'Germany', 'EUR'),
        (('netherlands', 'amsterdam'), 'Netherlands', 'EUR'),
        (('austria', 'vienna', 'salzburg'), 'Austria', 'EUR'),
        (('greece', 'athens', 'santorini'), 'Greece', 'EUR'),
        (('turkey', 'istanbul', 'cappadocia'), 'Turkey', 'EUR'),
        (('united kingdom', 'london', 'scotland', 'uk', 'england'), 'United Kingdom', 'GBP'),
        (('united states', 'usa', 'america', 'new york', 'california', 'alaska'), 'United States', 'USD'),
        (('australia', 'sydney', 'melbourne', 'cairns'), 'Australia', 'AUD'),
        (('new zealand', 'auckland', 'queenstown'), 'New Zealand', 'NZD'),
        (('japan', 'tokyo', 'kyoto', 'osaka'), 'Japan', 'JPY'),
        (('south korea', 'seoul', 'busan', 'jeju'), 'South Korea', 'KRW'),
        (('mauritius',), 'Mauritius', 'USD'),
        (('seychelles',), 'Seychelles', 'USD'),
        (('egypt', 'cairo', 'nile'), 'Egypt', 'USD'),
        (('south africa', 'cape town', 'johannesburg'), 'South Africa', 'ZAR'),
        (('kenya', 'nairobi', 'masai mara'), 'Kenya', 'USD'),
        (('tanzania', 'zanzibar', 'serengeti'), 'Tanzania', 'USD'),
        (('nepal', 'kathmandu', 'pokhara'), 'Nepal', 'INR'),
        (('bhutan', 'thimphu', 'paro'), 'Bhutan', 'INR'),
        (('azerbaijan', 'baku'), 'Azerbaijan', 'USD'),
        (('georgia', 'tbilisi'), 'Georgia', 'USD'),
        (('kazakhstan', 'almaty'), 'Kazakhstan', 'USD'),
        (('uzbekistan', 'tashkent'), 'Uzbekistan', 'USD'),
        (('qatar', 'doha'), 'Qatar', 'QAR'),
        (('oman', 'muscat'), 'Oman', 'OMR'),
        (('saudi arabia', 'riyadh', 'jeddah'), 'Saudi Arabia', 'SAR'),
        (('philippines', 'manila', 'boracay'), 'Philippines', 'USD'),
        (('fiji',), 'Fiji', 'FJD'),
        (('cambodia', 'siem reap', 'angkor'), 'Cambodia', 'USD'),
    ]
    for keywords, c_name, curr in mapping:
        if any(k in combined for k in keywords):
            return c_name, curr
    if country_name and country_name.lower() != 'india':
        return country_name.title(), 'USD'
    return 'India', 'INR'

def format_package_description(title, destination, days, nights, category, raw_content="", highlights=""):
    cleaned_ov = clean_rebrand(clean_html_text(raw_content)).strip()
    cleaned_hl = clean_rebrand(clean_html_text(highlights)).strip()
    
    cleaned_ov = re.sub(r'Duration:\s*\d+[^.]*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'From City:[^.]*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'To City:[^.]*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'[\?]+', '', cleaned_ov)
    cleaned_ov = re.sub(r'\s+', ' ', cleaned_ov).strip()
    
    if len(cleaned_ov) < 60:
        cat_desc = {
            'international': f"Embark on an unforgettable international vacation with our {title} ({nights} Nights / {days} Days). Discover iconic landmarks, world-class attractions, and rich cultural heritage across {destination}. Includes verified hotel accommodation, private transfers, daily meals, and comprehensive assistance from Siva Gayathri Tours & Travels.",
            'devotional': f"Attain divine blessings and inner peace on our sacred {title} ({nights} Nights / {days} Days). Experience seamless darshan at venerated temples across {destination}, complemented by Satvik vegetarian meals, comfortable accommodations, senior citizen priority support, and dedicated chauffeur service.",
            'hill_station': f"Relax amidst scenic mountain vistas, lush plantations, and misty valleys on our {title} ({nights} Nights / {days} Days). Explore famous viewpoints, waterfalls, and nature trails across {destination} with private tourist vehicle logistics and premium star hotel stays.",
            'family_vacation': f"Create cherished memories with your family on our {title} ({nights} Nights / {days} Days). Enjoy an ideal blend of sightseeing, relaxation, and memorable activities across {destination}, thoughtfully curated by Siva Gayathri Tours & Travels.",
            'holiday': f"Experience the captivating sights, heritage, and landscapes of {destination} on our {title} ({nights} Nights / {days} Days). Complete with chauffeur-driven tourist vehicle, comfortable hotel accommodation, and personalized itinerary management."
        }.get(category, f"Experience {title} covering {destination} with Siva Gayathri Tours & Travels.")
        if cleaned_hl:
            return f"{cat_desc}\n\nKey Highlights:\n{cleaned_hl}"
        return cat_desc
        
    if cleaned_hl and cleaned_hl not in cleaned_ov:
        return f"{cleaned_ov}\n\nKey Highlights:\n{cleaned_hl}"
    return cleaned_ov

# ==============================================================================
# MAIN INGESTION AND IMPORT ENGINE
# ==============================================================================

def main():
    print("=" * 80)
    print("  SIVA GAYATHRI TOURS & TRAVELS — ASPIRE HOLIDAYS COMPLETE EXTRACTOR A TO Z")
    print("=" * 80)

    out_file = os.path.join(WORKSPACE_ROOT, 'scripts', 'scraped_aspire_packages.json')
    if os.path.exists(out_file) and '--force-scrape' not in sys.argv:
        print(f"Loading cached dataset from {out_file}...")
        with open(out_file, 'r', encoding='utf-8') as f:
            all_packages = json.load(f)
        print(f"Loaded {len(all_packages)} packages from cache!")
    else:
        print("Fetching complete tour package catalog from https://aspireholidays.in/api/package...")
        url = "https://aspireholidays.in/api/package"
        req = urllib.request.Request(url, headers=HEADERS)
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        data = json.loads(resp.read().decode('utf-8'))
        all_packages = data.get('data', [])
        print(f"Successfully retrieved {len(all_packages)} packages from Aspire Holidays REST API!")
        
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(all_packages, f, indent=2, ensure_ascii=False)
        print(f"Saved complete raw dataset to {out_file} ({os.path.getsize(out_file):,} bytes)!")

    # Database Import
    print(f"\nImporting all {len(all_packages)} packages into database with prefix SGT-AH-...")
    with transaction.atomic():
        deleted = Package.objects.filter(package_code__startswith='SGT-AH-').delete()
        print(f"Cleared previous SGT-AH- records: {deleted}")

        imported_count = 0
        all_days_records = []
        all_doc_records = []
        all_darshan_records = []
        all_pkg_records = []
        existing_codes = set(Package.objects.values_list('package_code', flat=True))

        # Step 1: Pre-process & Create Package objects
        for idx, item in enumerate(all_packages, 1):
            raw_title = item.get('name', 'Tour Package').strip()
            pkg_name = clean_rebrand(raw_title).upper()
            if not any(pkg_name.endswith(suf) for suf in ['TOUR', 'PACKAGE', 'YATRA', 'EXPEDITION', 'CRUISE', 'HOLIDAYS']):
                pkg_name = f"{pkg_name} TOUR PACKAGE"

            # Resolve Country & State
            c_data = item.get('country')
            raw_country = c_data.get('country') if isinstance(c_data, dict) else str(c_data or '')
            raw_state = item.get('state') or ''
            
            # Category Resolution
            cat_obj = item.get('category')
            cat_title = (cat_obj.get('title') if isinstance(cat_obj, dict) else str(cat_obj or '')).lower()
            sub_obj = item.get('sub')
            sub_title = (sub_obj.get('title') if isinstance(sub_obj, dict) else str(sub_obj or '')).lower()

            is_intl = ('international' in cat_title) or (raw_country and raw_country.lower() not in ['india', 'none', ''])
            is_dev = ('pilgrim' in sub_title) or any(k in pkg_name.lower() for k in ['temple', 'darshan', 'jyotirlinga', 'yatra', 'kashi', 'shirdi', 'tirupati', 'chardham', 'rameshwaram', 'puri', 'divine'])
            is_hill = any(k in f"{pkg_name} {raw_state}".lower() for k in ['ooty', 'munnar', 'kodaikanal', 'manali', 'shimla', 'kashmir', 'srinagar', 'gulmarg', 'sikkim', 'darjeeling', 'coorg', 'wayanad', 'ladakh', 'meghalaya', 'shillong', 'arunachal', 'himachal', 'uttarakhand', 'mussoorie', 'nainital'])
            is_honeymoon = ('honeymoon' in sub_title) or ('honeymoon' in pkg_name.lower()) or any(k in pkg_name.lower() for k in ['goa', 'andaman', 'cruise', 'island'])

            if is_intl:
                category = 'international'
            elif is_dev:
                category = 'devotional'
            elif is_hill:
                category = 'hill_station'
            elif is_honeymoon:
                category = 'family_vacation'
            else:
                category = 'holiday'

            country_name, currency_code = detect_country_currency(raw_country, pkg_name)
            destination = clean_rebrand(raw_state if (raw_state and not is_intl) else country_name) or "Scenic Destination"

            # Duration calculation
            raw_tdays = item.get('tdays')
            days_list = item.get('days', [])
            if raw_tdays and isinstance(raw_tdays, int) and raw_tdays > 0:
                days = raw_tdays
            elif days_list and len(days_list) > 0:
                days = len(days_list)
            else:
                days = 3
            nights = max(1, days - 1) if days > 1 else 0

            # Build clean unique slug
            raw_slug = re.sub(r'[^A-Z0-9]+', '-', pkg_name[:20]).strip('-')
            pkg_code = f"SGT-AH-{raw_slug}-{days}D"
            if pkg_code in existing_codes:
                pkg_code = f"SGT-AH-{raw_slug}-{days}D-{idx}"
            existing_codes.add(pkg_code)

            # Pricing
            raw_amount = item.get('amount')
            if raw_amount and isinstance(raw_amount, (int, float)) and raw_amount > 500:
                base_price = Decimal(str(raw_amount))
            else:
                if is_intl:
                    base_price = Decimal(str(days * 7500))
                elif is_dev:
                    base_price = Decimal(str(days * 2200))
                elif category == 'family_vacation':
                    base_price = Decimal(str(days * 3400))
                elif category == 'hill_station':
                    base_price = Decimal(str(days * 2500))
                else:
                    base_price = Decimal(str(days * 2400))

            ap_price = base_price
            ep_price = Decimal(str(round(float(base_price) * 0.78, 2)))
            meal_plan = 'MAP' if is_intl or category == 'family_vacation' else 'AP'

            # Inclusions from item flags
            inc_items = []
            if item.get('hotel'):
                inc_items.append(f"Hotel Accommodation: {clean_rebrand(item.get('hotel_title', 'Verified Star Hotel Twin-Sharing'))}")
            else:
                inc_items.append("Comfortable hotel accommodation on twin-sharing basis.")
            
            if item.get('transport'):
                inc_items.append(f"Fleet Logistics: {clean_rebrand(item.get('transport_title', 'Chauffeur-driven tourist vehicle for full itinerary'))}")
            else:
                inc_items.append("Chauffeur-driven well-maintained tourist vehicle with fuel, toll, and parking included.")
            
            if item.get('ticket'):
                inc_items.append(f"Sightseeing & Admissions: {clean_rebrand(item.get('ticket_title', 'Included as per itinerary'))}")
            else:
                inc_items.append(f"Guided sightseeing covering major viewpoints and attractions across {destination}.")

            if is_dev:
                inc_items.append("100% Satvik Pure Vegetarian South Indian meals during transit and stay.")
                inc_items.append("Priority Temple Darshan coordination and senior citizen assistance.")
            elif is_intl:
                inc_items.append(f"Daily international buffet breakfast and Indian/Local dinner.")
                inc_items.append("English-speaking local representative and airport arrival/departure transfers.")
            else:
                inc_items.append("Daily breakfast and dinner at hotel.")

            inc_items.append("24x7 Siva Gayathri Tours & Travels dispatch and customer assistance.")
            inclusions_text = "\n".join(f"• {line}" for line in inc_items)

            exclusions_text = (
                "• Personal expenses such as laundry, telephone calls, room service, and beverages.\n"
                "• Optional adventure sports, boating, camera tokens, and activities not specified.\n"
                "• Scheduled flight or train tickets (available upon request at actual fare).\n"
                "• Expenses arising from unforeseen events, roadblocks, or natural calamities."
            )

            terms_text = (
                "• 50% advance deposit upon confirmation, remaining balance payable prior to trip start.\n"
                "• AC will be switched off on steep ghat roads and hairpin bends for passenger safety.\n"
                "• Vehicle will strictly adhere to designated routes and permitted itineraries.\n"
                "• Siva Gayathri Tours & Travels guarantees verified vehicles and polite chauffeurs."
            )

            pkg_desc = format_package_description(
                pkg_name, destination, days, nights, category,
                item.get('content', ''), item.get('highlights', '')
            )

            pkg = Package(
                package_code=pkg_code,
                name=pkg_name,
                destination=destination[:150],
                category=category,
                duration_nights=nights,
                duration_days=days,
                base_price=base_price,
                price_with_food=ap_price,
                price_without_food=ep_price,
                pricing_type='per_person',
                meal_plan=meal_plan,
                room_sharing_type='twin_sharing',
                min_pax=2 if is_intl else 4,
                is_international=is_intl,
                destination_country=country_name,
                currency_code=currency_code,
                visa_required=is_intl,
                visa_guidelines=f"Tourist eVisa / Entry Authorization required for {country_name}." if is_intl else "",
                passport_validity_months=6 if is_intl else 0,
                flight_inclusive=False,
                flight_details_note=f"Scheduled flight booking assistance available Ex-Coimbatore (CJB) / Ex-Chennai (MAA) / Ex-Bangalore (BLR) to {country_name}." if is_intl else "",
                overseas_dmc_partner=f"Certified DMC Destination Partner in {country_name}" if is_intl else "",
                is_devotional=is_dev,
                satvik_pure_veg_meals=is_dev,
                senior_citizen_friendly=is_dev,
                temple_dress_code="Mandatory Traditional Dress: Dhoti/Kurta for Men, Saree/Chudidar for Women" if is_dev else "",
                temple_darshan_info=f"Sacred Pilgrimage Circuit covering prominent shrines along {destination}." if is_dev else "",
                inclusions=inclusions_text,
                exclusions=exclusions_text,
                terms_and_conditions=terms_text,
                contact_persons_footer="Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131)",
                description=pkg_desc,
                is_active=True,
            )
            all_pkg_records.append((pkg, days_list, is_intl, is_dev, country_name, destination, days, meal_plan))

        # Bulk save packages
        created_packages = Package.objects.bulk_create([p[0] for p in all_pkg_records])
        print(f"Created {len(created_packages)} Package records in database!")

        # Step 2: Create Itinerary Days, Tariffs, Devotional Slots, & Checklists
        print("Creating Day-by-Day Itineraries, Tariffs, and Specialized Records...")
        vtypes = list(VehicleType.objects.all())
        sedan_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['sedan', 'dzire', 'etios'])), vtypes[0] if vtypes else None)
        crysta_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['crysta', 'innova'])), vtypes[1] if len(vtypes) > 1 else sedan_vt)
        urbania_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['urbania', 'tempo', '17'])), vtypes[2] if len(vtypes) > 2 else sedan_vt)
        bus36_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['36', 'mini', '40'])), vtypes[3] if len(vtypes) > 3 else sedan_vt)
        coach54_vt = next((vt for vt in vtypes if any(k in vt.name.lower() for k in ['54', 'coach', '52', 'volvo'])), vtypes[4] if len(vtypes) > 4 else sedan_vt)

        tariff_configs = [
            (sedan_vt, '4_sedan', 14.0, 500.0),
            (crysta_vt, '7_crysta', 20.0, 600.0),
            (urbania_vt, '17_tt_urbania', 26.0, 800.0),
            (bus36_vt, '36_mini_bus', 35.0, 1000.0),
            (coach54_vt, '54_luxury_coach', 45.0, 1200.0),
        ]
        all_tariff_records = []

        for pkg, (_, days_list, is_intl, is_dev, country_name, destination, days, meal_plan) in zip(created_packages, all_pkg_records):
            # Itinerary Days
            for d_idx in range(1, days + 1):
                if d_idx <= len(days_list):
                    d_raw = days_list[d_idx - 1]
                    raw_d_title = d_raw.get('title') or d_raw.get('name') or f"Day {d_idx}: Sightseeing"
                    raw_d_content = d_raw.get('content') or f"Sightseeing and exploration across {destination}."
                    d_title = clean_rebrand(raw_d_title.strip())
                    d_desc = clean_rebrand(clean_html_text(raw_d_content))
                else:
                    if d_idx == days:
                        d_title = f"Day {d_idx}: Departure & Return Journey"
                        d_desc = f"Morning breakfast at hotel, leisure shopping for local souvenirs, checkout, and return journey from {destination} with sweet memories."
                    else:
                        d_title = f"Day {d_idx}: Exploration of {destination}"
                        d_desc = f"Guided sightseeing covering major scenic viewpoints, heritage landmarks, and cultural spots across {destination}."

                all_days_records.append(ItineraryDay(
                    package=pkg,
                    day_number=d_idx,
                    title=d_title[:250],
                    route_segment=f"{destination} Circuit"[:250],
                    activities=d_desc,
                    sightseeing_spots=d_desc[:500],
                    meals_included="Breakfast, Lunch, Dinner" if meal_plan == 'AP' else "Breakfast & Dinner",
                    night_stay_location=destination.split()[0] if days > 1 and d_idx < days else "Return Journey",
                ))

            # Fleet Tariffs
            for vt, tier, km_rate, bata in tariff_configs:
                if not vt:
                    continue
                daily = (300 * km_rate) + bata
                pkg_rate = days * daily
                all_tariff_records.append(PackageVehicleTariff(
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
                    interstate_permit_included=True if is_intl or any(k in pkg.name.lower() for k in ['kerala', 'karnataka', 'goa', 'delhi', 'agra', 'jaipur', 'mumbai', 'shirdi', 'puri', 'varanasi', 'char dham', 'do dham']) else False,
                ))

            # International Document Checklist
            if is_intl:
                docs = [
                    ("Original Passport (Min 6 months validity from return date)", True, 15, "Clear color scan of front and back bio-pages"),
                    ("Passport Size Photographs (35x45mm, White background)", True, 10, "Matte finish, 80% facial coverage without border"),
                    (f"Tourist eVisa / Entry Authorization for {country_name}", True, 7, "Online processing assistance by Siva Gayathri Tours"),
                    ("Confirmed Round-Trip Flight Tickets & Accommodation Vouchers", True, 5, "Issued and managed by Siva Gayathri Tours & Travels"),
                    ("Comprehensive Overseas Travel & Health Insurance Certificate", True, 5, "Mandatory minimum coverage as per embassy guidelines"),
                ]
                for dname, mand, dline, note in docs:
                    all_doc_records.append(InternationalDocumentChecklist(
                        package=pkg,
                        document_name=dname,
                        is_mandatory=mand,
                        submission_deadline_days=dline,
                        notes=note
                    ))

            # Temple Darshan Slot
            if is_dev:
                dest_lower = destination.lower()
                all_darshan_records.append(TempleDarshanSlot(
                    package=pkg,
                    temple_name=f"{destination} Sacred Pilgrimage Circuit",
                    deity_or_circuit="Presiding Deities & Sacred Sanctums",
                    darshan_type="special_entry_300",
                    booked_slot_time="06:00 AM - 09:30 AM",
                    reporting_location=f"Main Sanctum Complex, {destination}",
                    dress_code_notes="Strict Traditional Attire: Dhoti/Kurta for Men, Saree/Chudidar for Women",
                    prasad_details="Holy Temple Theertham & Prasadam",
                    senior_citizen_support=True
                ))

            imported_count += 1
            if imported_count % 100 == 0 or imported_count == len(all_pkg_records):
                print(f"  Processed {imported_count}/{len(all_pkg_records)} packages (Tariffs, Days & Enrichment attached)...")

        # Bulk save days, tariffs, docs, darshan
        ItineraryDay.objects.bulk_create(all_days_records, batch_size=500)
        print(f"Saved {len(all_days_records)} ItineraryDay records!")

        PackageVehicleTariff.objects.bulk_create(all_tariff_records, batch_size=500)
        print(f"Saved {len(all_tariff_records)} PackageVehicleTariff records!")

        if all_doc_records:
            InternationalDocumentChecklist.objects.bulk_create(all_doc_records, batch_size=500)
            print(f"Saved {len(all_doc_records)} InternationalDocumentChecklist records!")

        if all_darshan_records:
            TempleDarshanSlot.objects.bulk_create(all_darshan_records, batch_size=500)
            print(f"Saved {len(all_darshan_records)} TempleDarshanSlot records!")

    print("=" * 80)
    print(f"SUCCESS! Scraped & Imported all {imported_count} packages from aspireholidays.in under prefix SGT-AH-!")
    print("=" * 80)

if __name__ == '__main__':
    main()
