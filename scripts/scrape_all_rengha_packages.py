import os
import sys
import re
import json
import time
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

CACHE_FILE = os.path.join(os.path.dirname(__file__), 'scraped_rengha_full_catalog.json')
URLS_FILE = os.path.join(os.path.dirname(__file__), 'all_rengha_package_urls.json')

def clean_rebrand(text):
    if not text:
        return ""
    # Normalize unicode punctuation and hyphens
    text = text.replace('\u2013', ' - ').replace('\u2014', ' - ').replace('\u2015', ' - ')
    text = text.replace('\u00a0', ' ').replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    
    # Strip URLs, wa.link, and web domains
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'wa\.link/\S+', '', text)
    text = re.sub(r'(?:www\.)?[a-zA-Z0-9-]+\.(?:com|in|org|net)/\S*', '', text)

    replacements = [
        (re.compile(r'Rengha\s+Holidays\s+(?:and|&)\s+Tourism\s+(?:Pvt\s+Ltd|Private\s+Limited)?', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Rengha\s+Holidays\s+(?:Pvt\s+Ltd|Private\s+Limited)?', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Rengha\s+Tourism', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Rengha', re.IGNORECASE), 'Siva Gayathri'),
        (re.compile(r'(?:Siva\s+)?Gayathriholidays(?:\.com)?', re.IGNORECASE), 'sivagayathritravels.com'),
        (re.compile(r'\+91[\s\d-]{9,15}'), '+91 98425 33777'),
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

def parse_duration_from_title(title, default_days=4):
    m = re.search(r'(\d+)\s*N(?:ights?)?\s*[/&]?\s*(\d+)\s*D(?:ays?)?', title, re.IGNORECASE)
    if m:
        nights = int(m.group(1))
        days = int(m.group(2))
        return days, nights
    m2 = re.search(r'(\d+)\s*D(?:ays?)?\s*[/&]?\s*(\d+)\s*N(?:ights?)?', title, re.IGNORECASE)
    if m2:
        days = int(m2.group(1))
        nights = int(m2.group(2))
        return days, nights
    m3 = re.search(r'(\d+)\s*Days?', title, re.IGNORECASE)
    if m3:
        days = int(m3.group(1))
        return days, max(1, days - 1)
    m4 = re.search(r'(\d+)\s*Nights?', title, re.IGNORECASE)
    if m4:
        nights = int(m4.group(1))
        return nights + 1, nights
    return default_days, max(1, default_days - 1)

def detect_category(title, dest, overview, is_intl=False):
    combined = f"{title} {dest}".lower()
    
    # 1. International check first
    intl_regex = re.compile(r'\b(thailand|bangkok|pattaya|phuket|krabi|singapore|malaysia|europe|netherlands|vietnam|hanoi|phu quoc|maldives|sri lanka|dubai|abu dhabi|bali|indonesia|seychelles|mauritius|philippines|fiji|switzerland|france|italy|paris|rome|venice|zurich|germany|austria|london|uk|bhutan|nepal|alaska|antarctica|egypt|baku|azerbaijan|turkey|istanbul)\b', re.IGNORECASE)
    if is_intl or intl_regex.search(combined):
        return 'international'
        
    # 2. Devotional check (Authentic pilgrimage circuits)
    dev_regex = re.compile(r'\b(temple|shiva|sthalangal|divya\s+desam|jyotirlinga|darshan|yatra|puri|jaganath|shirdi|kashi|prayagraj|ayodhya|char dham|do dham|kedarnath|badrinath|guruvayur|guruvayoor|kanyakumari|madurai|rameswaram|rameshwaram|thiruchendur|thiruvannamalai|chidambaram|navagraha|palani|tirupati|somnath|dwarka|dwaraka|sabarimala)\b|\bgaya\b', re.IGNORECASE)
    if dev_regex.search(combined):
        return 'devotional'
        
    # 3. Hill Station check
    hill_regex = re.compile(r'\b(ooty|munnar|thekkady|vagamon|sikkim|darjeeling|shimla|manali|kashmir|srinagar|gulmarg|tawang|araku|mussoorie|auli|wayanad|dalhousie|dharamshala|shillong|assam|meghalaya|coorg|kodaikanal|chikmagalur)\b', re.IGNORECASE)
    if hill_regex.search(combined):
        return 'hill_station'
        
    # 4. Family / Honeymoon check
    fam_regex = re.compile(r'\b(goa|andaman|pondicherry|cruise|high seas|alleppey|houseboat|backwater|beach|resort|safari)\b|honeymoon', re.IGNORECASE)
    if fam_regex.search(combined):
        return 'family_vacation'
        
    return 'holiday'

def detect_country_and_currency(title, dest):
    c = f"{title} {dest}".lower()
    if any(k in c for k in ['thailand', 'bangkok', 'pattaya', 'phuket', 'krabi']):
        return 'Thailand', 'THB'
    if 'singapore' in c and 'malaysia' in c:
        return 'Singapore & Malaysia', 'SGD'
    if 'singapore' in c:
        return 'Singapore', 'SGD'
    if 'malaysia' in c:
        return 'Malaysia', 'MYR'
    if any(k in c for k in ['dubai', 'abu dhabi', 'uae', 'sharjah']):
        return 'United Arab Emirates', 'AED'
    if any(k in c for k in ['bali', 'indonesia', 'jakarta']):
        return 'Indonesia', 'IDR'
    if 'maldives' in c:
        return 'Maldives', 'USD'
    if 'sri lanka' in c:
        return 'Sri Lanka', 'LKR'
    if any(k in c for k in ['vietnam', 'hanoi', 'da nang', 'phu quoc', 'ho chi minh']):
        return 'Vietnam', 'VND'
    if any(k in c for k in ['switzerland', 'france', 'italy', 'paris', 'rome', 'venice', 'zurich', 'europe', 'germany', 'austria', 'amsterdam', 'netherlands']):
        return 'Europe', 'EUR'
    if any(k in c for k in ['london', 'uk', 'england', 'scotland']):
        return 'United Kingdom', 'GBP'
    if 'bhutan' in c or 'thimphu' in c or 'paro' in c:
        return 'Bhutan', 'INR'
    if 'nepal' in c or 'kathmandu' in c or 'pokhara' in c:
        return 'Nepal', 'NPR'
    if 'seychelles' in c:
        return 'Seychelles', 'USD'
    if 'mauritius' in c:
        return 'Mauritius', 'USD'
    if 'philippines' in c:
        return 'Philippines', 'USD'
    if 'fiji' in c:
        return 'Fiji', 'FJD'
    if 'egypt' in c or 'cairo' in c:
        return 'Egypt', 'USD'
    if 'turkey' in c or 'istanbul' in c:
        return 'Turkey', 'USD'
    if 'antarctica' in c or 'alaska' in c:
        return 'International', 'USD'
    return 'India', 'INR'

def format_package_description(title, destination, days, nights, category, overview=""):
    cleaned_ov = clean_rebrand(overview or '').strip()
    cleaned_ov = re.sub(r'Duration:\s*\d+[^.]*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'From City:[^.]*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'To City:[^.]*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'Place Covered:[^.]*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'Tour Info[^.]*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'About Temple:\s*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'[\?]+', '', cleaned_ov)
    cleaned_ov = re.sub(r'^(?:Best|best)\s+[^:]*:\s*', '', cleaned_ov)
    cleaned_ov = re.sub(r'\s+', ' ', cleaned_ov).strip()
    
    if len(cleaned_ov) < 80:
        cat_desc = {
            'international': f"Embark on an unforgettable international journey with our {title} ({nights} Nights / {days} Days). Discover iconic landmarks, scenic vistas, and rich culture across {destination}. Features verified hotel accommodation, private transfers, daily meals, and comprehensive 24/7 assistance from Siva Gayathri Tours & Travels.",
            'devotional': f"Attain divine blessings and peace of mind on our sacred {title} ({nights} Nights / {days} Days). Experience seamless darshan at venerated temples across {destination}, complemented by Satvik vegetarian meals, comfortable accommodations, senior citizen support, and dedicated chauffeur service.",
            'hill_station': f"Relax amidst scenic mountain vistas and misty valleys on our {title} ({nights} Nights / {days} Days). Explore famous tea gardens, viewpoints, waterfalls, and natural wonders across {destination} with private tourist vehicle logistics and verified star hotel stays.",
            'family_vacation': f"Create cherished memories with your loved ones on our {title} ({nights} Nights / {days} Days). Enjoy an ideal blend of sightseeing, backwaters, relaxation, and memorable activities across {destination}, thoughtfully curated by Siva Gayathri Tours & Travels.",
            'holiday': f"Experience the captivating sights, heritage, and landscapes of {destination} on our {title} ({nights} Nights / {days} Days). Complete with chauffeur-driven tourist vehicle, hotel accommodation, and personalized itinerary management."
        }.get(category, f"Experience {title} covering {destination} with Siva Gayathri Tours & Travels.")
        return cat_desc
    return cleaned_ov

def parse_package_html(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    
    # Title
    h1 = soup.find('h1')
    raw_title = h1.get_text(strip=True) if h1 else ''
    if not raw_title:
        raw_title = url.split('/')[-1].replace('-', ' ').title()
    raw_title = raw_title.split('|')[0].strip()
    title = clean_rebrand(raw_title).upper()
    if not any(title.endswith(suf) for suf in ['TOUR', 'PACKAGE', 'YATRA', 'EXPEDITION', 'CRUISE', 'SPECIAL', 'ESCAPE']):
        title = f"{title} TOUR PACKAGE"

    # Overview
    overview = ''
    for h3 in soup.find_all('h3'):
        if 'overview' in h3.get_text().lower():
            card = h3.find_parent('div', class_='card')
            if card:
                cb = card.find('div', class_='card-body')
                if cb:
                    overview = cb.get_text(' ', strip=True)
            break

    # Itinerary
    itinerary = []
    for h3 in soup.find_all('h3'):
        if 'itinerary' in h3.get_text().lower():
            card = h3.find_parent('div', class_='card')
            if card:
                for item in card.find_all('div', class_='accordion-item'):
                    btn = item.find('button')
                    hdr_text = btn.get_text(' ', strip=True) if btn else ''
                    body = item.find('div', class_='accordion-body')
                    body_text = body.get_text(' ', strip=True) if body else ''
                    img = body.find('img') if body else None
                    img_src = img.get('src', '') if img else ''
                    
                    hdr_clean = clean_rebrand(hdr_text)
                    body_clean = clean_rebrand(body_text)
                    if hdr_clean or body_clean:
                        itinerary.append({
                            'header': hdr_clean,
                            'content': body_clean,
                            'image': img_src
                        })
            break

    # Inclusions & Exclusions
    inclusions = []
    exclusions = []
    for h3 in soup.find_all('h3'):
        if 'inclusion' in h3.get_text().lower():
            card = h3.find_parent('div', class_='card')
            if card:
                for li in card.find_all('li'):
                    txt = clean_rebrand(li.get_text(' ', strip=True))
                    img = li.find('img')
                    if img and 'tick' in img.get('src', ''):
                        inclusions.append(txt)
                    elif img and 'cross' in img.get('src', ''):
                        exclusions.append(txt)
                    else:
                        inclusions.append(txt)
            break

    # Hero image
    hero_img = ''
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if any(w in src.lower() for w in ['tour', 'package', 'upload', 'single']):
            if not any(ex in src.lower() for ex in ['icon', 'avatar', 'logo', 'payment', 'paypal', 'visa', 'happy']):
                hero_img = src
                break

    # Duration
    days, nights = parse_duration_from_title(raw_title, default_days=len(itinerary) if itinerary else 4)
    if len(itinerary) > days:
        days = len(itinerary)
        nights = max(1, days - 1)

    # Destination & Category
    dest = clean_rebrand(raw_title.split('–')[0].split('-')[0].split('|')[0].split('(')[0]).strip()
    country, currency = detect_country_and_currency(title, dest)
    cat = detect_category(title, dest, overview, is_intl=(country != 'India'))

    return {
        'url': url,
        'title': title,
        'destination': dest,
        'category': cat,
        'days': days,
        'nights': nights,
        'is_international': (cat == 'international'),
        'destination_country': country,
        'currency_code': currency,
        'overview': overview,
        'itinerary': itinerary,
        'inclusions': inclusions,
        'exclusions': exclusions,
        'hero_img': hero_img
    }

def scrape_all_rengha_urls():
    from playwright.sync_api import sync_playwright

    with open(URLS_FILE, 'r', encoding='utf-8') as f:
        all_urls = json.load(f)

    # Load cache if available, or initialize from existing scraped packages
    catalog = {}
    PREV_FILE = os.path.join(os.path.dirname(__file__), 'scraped_rengha_packages.json')
    
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                for item in cached_data:
                    if item.get('url'):
                        catalog[item['url']] = item
            print(f"Loaded {len(catalog)} packages from cache!")
        except Exception as e:
            print(f"Cache read error: {e}")
    elif os.path.exists(PREV_FILE):
        try:
            with open(PREV_FILE, 'r', encoding='utf-8') as f:
                prev_data = json.load(f)
                for item in prev_data:
                    if item.get('url') and 'honeymoon' not in item.get('url'):
                        catalog[item['url']] = item
            print(f"Initialized cache with {len(catalog)} previously scraped main packages!")
        except Exception as e:
            print(f"Prev file read error: {e}")

    remaining_urls = [u for u in all_urls if u not in catalog]
    print(f"Total URLs: {len(all_urls)} | Already cached: {len(catalog)} | Remaining to scrape: {len(remaining_urls)}")

    if not remaining_urls:
        print("All URLs already cached!")
        return list(catalog.values())

    CHUNK_SIZE = 8
    with sync_playwright() as p:
        print("Launching Playwright Chrome...")
        browser = p.chromium.launch(channel='chrome', headless=True)
        context = browser.new_context()

        # Session establishment on home
        print("Establishing session on renghaholidays.com...")
        init_p = context.new_page()
        init_p.goto('https://www.renghaholidays.com/', timeout=45000, wait_until='commit')
        init_p.wait_for_timeout(3000)
        init_p.close()
        print("Clearance session established!")

        for chunk_idx in range(0, len(remaining_urls), CHUNK_SIZE):
            chunk = remaining_urls[chunk_idx:chunk_idx + CHUNK_SIZE]
            print(f"\nScraping chunk {chunk_idx + 1} to {min(chunk_idx + CHUNK_SIZE, len(remaining_urls))} of {len(remaining_urls)}...")

            pages = []
            for u in chunk:
                try:
                    pg = context.new_page()
                    pages.append((pg, u))
                except Exception as e:
                    print(f"  Error opening page for {u}: {e}")

            # Navigate all
            for pg, u in pages:
                try:
                    pg.goto(u, wait_until='load', timeout=30000)
                except Exception as e:
                    try:
                        pg.goto(u, wait_until='domcontentloaded', timeout=15000)
                    except:
                        pass

            # Extract content
            for pg, u in pages:
                try:
                    html = pg.content()
                    data = parse_package_html(html, u)
                    catalog[u] = data
                    print(f"  [OK] {data['title'][:45]} ({data['nights']}N/{data['days']}D, {len(data['itinerary'])} days, {len(data['inclusions'])} inc) [{data['category']}]")
                except Exception as e:
                    print(f"  [FAIL] Failed parsing {u}: {e}")
                finally:
                    try:
                        pg.close()
                    except:
                        pass

            # Periodically write cache
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(list(catalog.values()), f, indent=2, ensure_ascii=False)

        browser.close()

    print(f"\nScraping complete! Total in catalog: {len(catalog)}")
    return list(catalog.values())

def attach_tariffs(pkg, days):
    PackageVehicleTariff.objects.filter(package=pkg).delete()
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

    for vt, tier, km_rate, bata in configs:
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
            interstate_permit_included=True if pkg.is_international or any(k in pkg.name.lower() for k in ['kerala', 'karnataka', 'goa', 'delhi', 'agra', 'jaipur', 'mumbai', 'shirdi', 'puri', 'varanasi', 'char dham', 'do dham']) else False,
        )

def import_catalog_to_django(catalog):
    PREV_FILE = os.path.join(os.path.dirname(__file__), 'scraped_rengha_packages.json')
    all_packages = list(catalog)
    existing_urls = set(p.get('url') for p in all_packages if p.get('url'))
    if os.path.exists(PREV_FILE):
        try:
            with open(PREV_FILE, 'r', encoding='utf-8') as f:
                prev_pkgs = json.load(f)
                for p in prev_pkgs:
                    if p.get('url') and p['url'] not in existing_urls:
                        all_packages.append(p)
                        existing_urls.add(p['url'])
        except Exception as e:
            print(f"Error loading prev pkgs: {e}")

    print(f"\n=======================================================")
    print(f"Beginning Database Import for {len(all_packages)} Total Packages...")
    print(f"=======================================================")

    # Clear old SGT-RH packages to ensure clean atomic state
    del_count, _ = Package.objects.filter(package_code__startswith='SGT-RH-').delete()
    print(f"Cleared previous SGT-RH- records: {del_count}")

    imported = 0
    with transaction.atomic():
        for idx, item in enumerate(all_packages, 1):
            days = item.get('days', 4)
            nights = item.get('nights', max(1, days - 1))
            
            # Slug generation
            raw_slug = re.sub(r'[^A-Z0-9]+', '-', item['title'][:22]).strip('-')
            pkg_code = f"SGT-RH-{raw_slug}-{days}D"
            if Package.objects.filter(package_code=pkg_code).exists():
                pkg_code = f"SGT-RH-{raw_slug}-{days}D-{idx}"

            is_intl = item.get('is_international', False)
            is_dev = (item.get('category') == 'devotional')

            # Pricing
            if is_intl:
                base_price = Decimal(str(days * 7500))
            elif is_dev:
                base_price = Decimal(str(days * 2200))
            elif item.get('category') == 'family_vacation':
                base_price = Decimal(str(days * 3400))
            elif item.get('category') == 'hill_station':
                base_price = Decimal(str(days * 2500))
            else:
                base_price = Decimal(str(days * 2400))

            ap_price = base_price
            ep_price = Decimal(str(round(float(base_price) * 0.78, 2)))
            meal_plan = 'MAP' if is_intl or item.get('category') == 'family_vacation' else 'AP'

            inclusions_list = item.get('inclusions', [])
            if inclusions_list:
                inclusions_text = "\n".join([f"• {inc}" for inc in inclusions_list])
            else:
                inclusions_text = (
                    "• Well-maintained tourist vehicle with professional chauffeur throughout the tour.\n"
                    "• All route permit charges, interstate road taxes, highway toll gates, and vehicle parking.\n"
                    "• Hotel accommodation on twin-sharing basis with daily breakfast and dinner.\n"
                    f"• Comprehensive sightseeing covering key attractions along {item['destination']}.\n"
                    + ("• 100% Satvik Pure Vegetarian South Indian meals.\n" if is_dev else "")
                    + "• 24x7 Siva Gayathri Tours & Travels dispatch and customer assistance."
                )

            exclusions_list = item.get('exclusions', [])
            if exclusions_list:
                exclusions_text = "\n".join([f"• {exc}" for exc in exclusions_list])
            else:
                exclusions_text = (
                    "• Monument entrance fees, boating charges, camera tokens, and personal expenses.\n"
                    "• Any airfare or train tickets (can be arranged upon request).\n"
                    "• Optional activities, adventure sports, or excursions not explicitly mentioned.\n"
                    "• Any delay or expenses caused by roadblocks, train delays, or natural calamities."
                )

            terms_text = (
                "50% advance deposit upon tour confirmation, remaining balance payable prior to trip departure.\n"
                "Vehicle will strictly adhere to designated routes, safety rules, and permit schedules.\n"
                "AC will be switched off on steep ghat roads and hairpin bends for engine power and passenger safety.\n"
                "Siva Gayathri Tours & Travels guarantees polite chauffeurs, sanitized coaches, and timely support."
            )

            pkg_name = clean_rebrand(item['title']).upper()
            pkg_dest = clean_rebrand(item['destination'])[:150]
            pkg_desc = format_package_description(pkg_name, pkg_dest, days, nights, item['category'], item.get('overview', ''))

            pkg = Package.objects.create(
                package_code=pkg_code,
                name=pkg_name,
                destination=pkg_dest,
                category=item['category'],
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
                destination_country=item.get('destination_country', 'India'),
                currency_code=item.get('currency_code', 'INR'),
                visa_required=is_intl,
                visa_guidelines=f"Tourist eVisa / Entry Authorization required for {item.get('destination_country')}." if is_intl else "",
                passport_validity_months=6 if is_intl else 0,
                flight_inclusive=False,
                flight_details_note=f"Scheduled flight booking assistance available Ex-Coimbatore (CJB) / Ex-Chennai (MAA) to {item.get('destination_country')}." if is_intl else "",
                overseas_dmc_partner=f"Certified DMC Destination Partner in {item.get('destination_country')}" if is_intl else "",
                is_devotional=is_dev,
                satvik_pure_veg_meals=is_dev,
                senior_citizen_friendly=is_dev,
                temple_dress_code="Mandatory Traditional Dress: Dhoti/Kurta for Men, Saree/Chudidar for Women" if is_dev else "",
                temple_darshan_info=f"Sacred Pilgrimage Circuit covering prominent shrines along {pkg_dest}." if is_dev else "",
                inclusions=inclusions_text,
                exclusions=exclusions_text,
                terms_and_conditions=terms_text,
                contact_persons_footer="Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131)",
                description=pkg_desc,
                is_active=True,
            )

            # Itinerary Days
            raw_itinerary = item.get('itinerary') or item.get('days_plan') or []
            for d_idx in range(1, days + 1):
                if d_idx <= len(raw_itinerary):
                    plan_item = raw_itinerary[d_idx - 1]
                    d_title = plan_item.get('header') or plan_item.get('title') or f"Day {d_idx}: Sightseeing & Exploration"
                    d_desc = plan_item.get('content') or plan_item.get('desc') or f"Sightseeing and activities across {pkg_dest}."
                else:
                    if d_idx == days:
                        d_title = f"Day {d_idx}: Final Sightseeing, Souvenir Shopping & Departure"
                        d_desc = f"Morning leisure, local handicraft shopping, checkout from hotel, and comfortable return journey from {pkg_dest} with pleasant memories."
                    else:
                        d_title = f"Day {d_idx}: In-Depth Exploration of {pkg_dest}"
                        d_desc = f"Guided sightseeing covering major viewpoints, cultural monuments, and scenic landmarks along {pkg_dest}."

                d_title_clean = clean_rebrand(d_title)[:250]
                d_desc_clean = clean_rebrand(d_desc)

                ItineraryDay.objects.create(
                    package=pkg,
                    day_number=d_idx,
                    title=d_title_clean,
                    route_segment=f"{pkg_dest} Circuit"[:250],
                    activities=d_desc_clean,
                    sightseeing_spots=d_desc_clean[:500],
                    meals_included="Breakfast, Lunch, Dinner" if meal_plan == 'AP' else "Breakfast & Dinner",
                    night_stay_location=pkg_dest.split()[0] if days > 1 and d_idx < days else "Return Journey",
                )

            # Attach Tariffs
            attach_tariffs(pkg, days)

            # International Checklist
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

            # Devotional Slots
            if is_dev:
                dest_lower = (item['title'] + " " + item['destination']).lower()
                if 'ramanathaswamy' in dest_lower or 'rameshwaram' in dest_lower or 'rameswaram' in dest_lower:
                    TempleDarshanSlot.objects.create(
                        package=pkg,
                        temple_name="Arulmigu Ramanathaswamy Temple (22 Theertham & Spatika Lingam)",
                        deity_or_circuit="Lord Ramanathaswamy & Parvathavarthini Amman",
                        darshan_type="special_entry_300",
                        booked_slot_time="05:30 AM - 08:30 AM (Spatika Linga Pooja)",
                        reporting_location="East Gopuram Gate 1",
                        dress_code_notes="Strict Traditional: Dhoti/Kurta (Men), Saree (Women)",
                        prasad_details="Holy 22 Theertha Snanam & Temple Prasadam",
                        senior_citizen_support=True
                    )
                elif 'puri' in dest_lower or 'jaganath' in dest_lower:
                    TempleDarshanSlot.objects.create(
                        package=pkg,
                        temple_name="Puri Jagannath Temple & Konark Sun Temple",
                        deity_or_circuit="Lord Jagannath, Balabhadra & Subhadra",
                        darshan_type="special_entry_300",
                        booked_slot_time="06:30 AM - 09:30 AM",
                        reporting_location="Singhadwara (Lion's Gate)",
                        dress_code_notes="Strict Traditional: Dhoti/Kurta (Men), Saree (Women)",
                        prasad_details="Holy Mahaprasad (Khaja & Bhog)",
                        senior_citizen_support=True
                    )
                elif 'char dham' in dest_lower or 'do dham' in dest_lower or 'kedarnath' in dest_lower or 'badrinath' in dest_lower:
                    TempleDarshanSlot.objects.create(
                        package=pkg,
                        temple_name="Kedarnath Jyotirlinga & Badrinath Vishal Sannidhi",
                        deity_or_circuit="Lord Badri Vishal & Kedarnath Jyotirlinga",
                        darshan_type="special_entry_300",
                        booked_slot_time="06:00 AM - 09:00 AM",
                        reporting_location="Main Temple Complex",
                        dress_code_notes="Strict Traditional Attire (Warm Woolens)",
                        prasad_details="Badrinath Tulsi & Kedar Bhasma Prasadam",
                        senior_citizen_support=True
                    )
                elif 'shirdi' in dest_lower:
                    TempleDarshanSlot.objects.create(
                        package=pkg,
                        temple_name="Shirdi Sai Baba Samadhi Mandir & Shani Shingnapur",
                        deity_or_circuit="Shirdi Sai Baba & Lord Shani Bhagwan",
                        darshan_type="special_entry_300",
                        booked_slot_time="07:00 AM - 09:30 AM (Kakad Aarti / Darshan)",
                        reporting_location="VIP Gate 1 / Shirdi Sansthan Complex",
                        dress_code_notes="Decent Traditional Attire",
                        prasad_details="Sai Baba Udi & Boondi Ladoo Prasadam",
                        senior_citizen_support=True
                    )
                elif 'kashi' in dest_lower or 'gaya' in dest_lower or 'ayodhya' in dest_lower:
                    TempleDarshanSlot.objects.create(
                        package=pkg,
                        temple_name="Kashi Vishwanath Jyotirlinga & Ram Janmabhoomi Ayodhya",
                        deity_or_circuit="Lord Shiva Vishwanath & Sri Ram Lalla",
                        darshan_type="special_entry_300",
                        booked_slot_time="05:30 AM - 08:30 AM",
                        reporting_location="Kashi Vishwanath Corridor Gate 4",
                        dress_code_notes="Strict Traditional Attire",
                        prasad_details="Holy Ganga Jal & Ayodhya Ram Lalla Prasadam",
                        senior_citizen_support=True
                    )
                elif 'guruvayur' in dest_lower or 'guruvayoor' in dest_lower:
                    TempleDarshanSlot.objects.create(
                        package=pkg,
                        temple_name="Guruvayoor Sri Krishna Temple",
                        deity_or_circuit="Lord Guruvayoorappan (Unnikrishnan)",
                        darshan_type="special_entry_300",
                        booked_slot_time="04:30 AM - 07:30 AM",
                        reporting_location="East Nada Entrance",
                        dress_code_notes="Strict Kerala Traditional: Mundu (Men bare chest), Saree/Set Mundu (Women)",
                        prasad_details="Neyyappam & Palpayasam Prasadam",
                        senior_citizen_support=True
                    )
                elif 'shiva' in dest_lower or 'sthalangal' in dest_lower or 'divya desam' in dest_lower:
                    TempleDarshanSlot.objects.create(
                        package=pkg,
                        temple_name=f"{pkg_name.split('TOUR')[0].strip()[:70]}",
                        deity_or_circuit="Lord Shiva / Maha Vishnu Sacred Circuit",
                        darshan_type="special_entry_300",
                        booked_slot_time="06:30 AM - 09:30 AM (Morning Viswaroopa Darshan)",
                        reporting_location="Main Temple Rajagopuram Entrance",
                        dress_code_notes="Strict Traditional: Dhoti (Men), Saree / Chudidar with Dupatta (Women)",
                        prasad_details="Archana Prasadam, Vibhuti & Kumkum",
                        senior_citizen_support=True
                    )
                else:
                    TempleDarshanSlot.objects.create(
                        package=pkg,
                        temple_name=f"{item['destination']} Sacred Temple Circuit",
                        deity_or_circuit="Presiding Deity",
                        darshan_type="special_entry_300",
                        booked_slot_time="06:30 AM - 09:30 AM",
                        reporting_location="Main Temple Entrance",
                        dress_code_notes="Strict Traditional Attire",
                        prasad_details="Temple Archanai & Theertha Prasadam",
                        senior_citizen_support=True
                    )

            imported += 1
            if imported % 25 == 0 or imported == len(catalog):
                print(f"  [DB] Imported {imported}/{len(catalog)}: {pkg.name[:45]} ({nights}N/{days}D) [{pkg.category}]")

    print(f"\nSuccessfully imported all {imported} packages into database under prefix SGT-RH-!")

def main():
    print("="*80)
    print("STARTING COMPLETE RENGHA HOLIDAYS EXTRACTION & IMPORT")
    print("="*80)
    catalog = scrape_all_rengha_urls()
    import_catalog_to_django(catalog)

if __name__ == '__main__':
    main()
