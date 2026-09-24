import os
import sys
import re
import json
import ssl
import urllib.request
from decimal import Decimal
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')

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

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

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
    # Remove awkward leftovers & duplicate suffixes
    cleaned = re.sub(r'from\s+chennai', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'(\bTOUR PACKAGE\b\s*)+', 'TOUR PACKAGE', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'(\bPACKAGE\b\s*)+', 'PACKAGE', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*,\s*', ', ', cleaned)
    cleaned = re.sub(r'\s*-\s*', ' - ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def format_package_description(title, destination, days, nights, category, overview=""):
    cleaned_ov = clean_rebrand(overview or '').strip()
    cleaned_ov = re.sub(r'Duration:\s*\d+[^.]*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'From City:[^.]*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'To City:[^.]*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'Place Covered:[^.]*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'Tour Info[^.]*', '', cleaned_ov, flags=re.IGNORECASE)
    cleaned_ov = re.sub(r'[\?]+', '', cleaned_ov)
    cleaned_ov = re.sub(r'^(?:Best|best)\s+[^:]*:\s*', '', cleaned_ov)
    cleaned_ov = re.sub(r'\s+', ' ', cleaned_ov).strip()
    
    if len(cleaned_ov) < 80:
        cat_desc = {
            'international': f"Embark on an unforgettable overseas journey with our {title} ({nights} Nights / {days} Days). Discover iconic landmarks, world-class attractions, and unique cultural experiences across {destination}. Features premium hotel accommodation, private transfers, daily meals, and comprehensive assistance from Siva Gayathri Tours & Travels.",
            'devotional': f"Attain divine blessings and peace of mind on our sacred {title} ({nights} Nights / {days} Days). Experience seamless darshan at venerated temples across {destination}, complemented by Satvik vegetarian meals, comfortable accommodations, senior citizen support, and dedicated chauffeur service.",
            'hill_station': f"Relax amidst scenic mountain vistas and misty valleys on our {title} ({nights} Nights / {days} Days). Explore famous tea gardens, viewpoints, waterfalls, and natural wonders across {destination} with private tourist vehicle logistics and verified star hotel stays.",
            'family_vacation': f"Create cherished memories with your family on our {title} ({nights} Nights / {days} Days). Enjoy an ideal blend of sightseeing, relaxation, and memorable activities across {destination}, thoughtfully curated by Siva Gayathri Tours & Travels.",
            'holiday': f"Experience the captivating sights, heritage, and landscapes of {destination} on our {title} ({nights} Nights / {days} Days). Complete with chauffeur-driven tourist vehicle, hotel accommodation, and personalized itinerary management."
        }.get(category, f"Experience {title} covering {destination} with Siva Gayathri Tours & Travels.")
        return cat_desc
    return cleaned_ov

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

def detect_category(title, dest, overview, is_intl=False, source=''):
    combined = f"{title} {dest}".lower()
    
    # 1. International check first
    intl_regex = re.compile(r'\b(thailand|bangkok|pattaya|phuket|krabi|singapore|malaysia|europe|netherlands|vietnam|hanoi|phu quoc|maldives|sri lanka|dubai|abu dhabi|bali|indonesia|seychelles|mauritius|philippines|fiji|switzerland)\b', re.IGNORECASE)
    if is_intl or intl_regex.search(combined):
        return 'international'
        
    # 2. Devotional check (Authentic pilgrimage circuits with word boundaries)
    dev_regex = re.compile(r'\b(puri|jaganath|shirdi|kashi|prayagraj|ayodhya|char dham|do dham|kedarnath|badrinath|jyotirlinga|shani shingnapur|guruvayur|guruvayoor|sacred south india)\b|\bgaya\b', re.IGNORECASE)
    if dev_regex.search(combined):
        return 'devotional'
        
    # 3. Hill Station check
    hill_regex = re.compile(r'\b(ooty|munnar|thekkady|vagamon|sikkim|darjeeling|shimla|manali|kashmir|srinagar|gulmarg|tawang|araku|mussoorie|auli|wayanad|dalhousie|dharamshala|shillong|assam|meghalaya|coorg)\b', re.IGNORECASE)
    if hill_regex.search(combined):
        return 'hill_station'
        
    # 4. Honeymoon / Family check
    fam_regex = re.compile(r'\b(goa|andaman|pondicherry|cruise|high seas)\b|honeymoon', re.IGNORECASE)
    if fam_regex.search(combined) or source == 'honeymoon':
        return 'family_vacation'
        
    return 'holiday'

def detect_country_and_currency(title, dest):
    c = f"{title} {dest}".lower()
    if 'thailand' in c or 'bangkok' in c or 'pattaya' in c or 'phuket' in c or 'krabi' in c:
        return 'Thailand', 'THB'
    if 'singapore' in c and 'malaysia' in c:
        return 'Singapore & Malaysia', 'SGD'
    if 'singapore' in c:
        return 'Singapore', 'SGD'
    if 'malaysia' in c:
        return 'Malaysia', 'MYR'
    if 'dubai' in c or 'abu dhabi' in c:
        return 'Dubai, UAE', 'AED'
    if 'bali' in c:
        return 'Bali, Indonesia', 'IDR'
    if 'maldives' in c:
        return 'Maldives', 'USD'
    if 'sri lanka' in c:
        return 'Sri Lanka', 'INR'
    if 'vietnam' in c or 'hanoi' in c or 'phu quoc' in c:
        return 'Vietnam', 'VND'
    if 'europe' in c or 'netherlands' in c or 'switzerland' in c:
        return 'Europe', 'EUR'
    if 'seychelles' in c:
        return 'Seychelles', 'USD'
    if 'mauritius' in c:
        return 'Mauritius', 'USD'
    if 'philippines' in c:
        return 'Philippines', 'USD'
    if 'fiji' in c:
        return 'Fiji', 'FJD'
    return 'India', 'INR'

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

# ==============================================================================
# SCRAPER FOR MAIN RENGHA CATALOG (40 packages + 7 landing pages) VIA PLAYWRIGHT
# ==============================================================================

def scrape_main_packages_playwright():
    print("\n--- Scraping Main Catalog & Special Landing Pages via Playwright ---")
    from playwright.sync_api import sync_playwright
    
    main_urls = [
        'https://www.renghaholidays.com/packages/amazing-europe-special-6n-7d',
        'https://www.renghaholidays.com/packages/awesome-malaysia-3n-4d',
        'https://www.renghaholidays.com/packages/bangkok-to-pattaya-experience-thailand-in-just-4n5d',
        'https://www.renghaholidays.com/packages/beat-the-heat-2026-luxury-vizag-araku-valley-summer-tour-packages',
        'https://www.renghaholidays.com/packages/bhubaneswar-puri-jaganath-tour-package-2n3d',
        'https://www.renghaholidays.com/packages/blissful-goa-3n-4d',
        'https://www.renghaholidays.com/packages/dazzling-phukat-krabi-escape-5n-6d',
        'https://www.renghaholidays.com/packages/exciting-thailand-escape-4n-5d',
        'https://www.renghaholidays.com/packages/golden-triangle-tour-package-from-chennai-4-nights-5-days',
        'https://www.renghaholidays.com/packages/kanyakumari-the-lands-end-spiritual-journey-2026-edition',
        'https://www.renghaholidays.com/packages/kedarnath-badrinath-yatra-do-dham-helicopter-yatra',
        'https://www.renghaholidays.com/packages/kerala-divine-serene-2026-guruvayur-to-kochi',
        'https://www.renghaholidays.com/packages/kolkata-the-cultural-heart-spiritual-sojourn-2026-edition',
        'https://www.renghaholidays.com/packages/luxury-weekend-cruise-chennai-to-high-seas',
        'https://www.renghaholidays.com/packages/madhya-pradesh-jyotirlinga-spiritual-yatra-3-days-2-nights',
        'https://www.renghaholidays.com/packages/magical-golden-triangle-4n-5d',
        'https://www.renghaholidays.com/packages/magical-ooty-tour-package-2n-3d',
        'https://www.renghaholidays.com/packages/marvels-of-malaysia-and-singapore-holiday-package-6n-7d',
        'https://www.renghaholidays.com/packages/munnar-thekkady-vagamon-meadows-escape',
        'https://www.renghaholidays.com/packages/mysore-2026-luxury-tour-packages-experience-royal-heritage-in-force-urbania-with-rengha-holidays-book-your-tension-free-trip',
        'https://www.renghaholidays.com/packages/mystical-sikkim-darjeeling-alpine-retreat-4n-5d',
        'https://www.renghaholidays.com/packages/ooty-the-queen-of-hills-luxury-escape-2026-edition',
        'https://www.renghaholidays.com/packages/paradise-of-kashmir-srinagar-gulmarg-4n-5d',
        'https://www.renghaholidays.com/packages/phu-quoc-island-tropical-escape-4n-5d',
        'https://www.renghaholidays.com/packages/premium-char-dham-helicopter-yatra-5-nights-6-days',
        'https://www.renghaholidays.com/packages/premium-do-dham-same-day-heliyatra-1n-2d',
        'https://www.renghaholidays.com/packages/rajasthan-tour-package-from-chennai-2026',
        'https://www.renghaholidays.com/packages/scenic-shimla-manali-alpine-retreat-5n-6d',
        'https://www.renghaholidays.com/packages/shirdi-sai-divine-darshan-yatra-2n-3d',
        'https://www.renghaholidays.com/packages/shirdi-shani-shingnapur-2n3d-2026',
        'https://www.renghaholidays.com/packages/simply-bali-fully-loaded-6n-7d',
        'https://www.renghaholidays.com/packages/singapore-malaysia-tour-package-from-chennai',
        'https://www.renghaholidays.com/packages/spiritual-kashi-gaya-prayagraj-ayodhya-tour-4n-5d',
        'https://www.renghaholidays.com/packages/sri-lanka-the-wonder-of-asia-fully-loaded',
        'https://www.renghaholidays.com/packages/tawang-the-himalayan-spiritual-retreat-2026-edition',
        'https://www.renghaholidays.com/packages/vizag-araku-valley-tour-2026-the-ultimate-coastal-hill-station-guide-rengha-holidays',
        'https://www.renghaholidays.com/packages/wonder-of-vietnam-4n-5d',
        'https://www.renghaholidays.com/packages/wonderful-maldives-escape-3n-4d',
        'https://www.renghaholidays.com/packages/wonders-of-assam-meghalaya-4n-5d',
        'https://www.renghaholidays.com/packages/wonders-of-dubai'
    ]
    
    special_urls = [
        'https://www.renghaholidays.com/page/delhi-agra-jaipur-tour-package-from-chennai',
        'https://www.renghaholidays.com/page/thailand-tour-package-from-chennai',
        'https://www.renghaholidays.com/page/chennai-to-singapore-tour-package',
        'https://www.renghaholidays.com/page/best-malaysia-tour-package-from-chennai-2026-flight-visa-hotel-sightseeing-rengha-holidays',
        'https://www.renghaholidays.com/page/best-dubai-tour-package-from-chennai-2026',
        'https://www.renghaholidays.com/page/bali-tour-package-from-chennai',
        'https://www.renghaholidays.com/page/Sri-lanka-tour-package-from-chennai'
    ]

    all_target_urls = main_urls
    scraped_packages = []

    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Establish session on homepage
        print("Establishing clearance session on homepage...")
        page.goto('https://www.renghaholidays.com/', timeout=35000, wait_until='commit')
        for _ in range(15):
            page.wait_for_timeout(1000)
            try:
                if 'checking your browser' not in page.title().lower():
                    break
            except:
                pass
        print(f"Session established! Page title: {page.title()[:40]}")

        for idx, u in enumerate(all_target_urls, 1):
            try:
                page.goto(u, timeout=20000, wait_until='domcontentloaded')
                page.wait_for_timeout(1200)
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Title
                h1 = soup.find('h1')
                raw_title = h1.get_text(strip=True) if h1 else page.title()
                raw_title = raw_title.split('|')[0].strip()
                title = clean_rebrand(raw_title).upper()
                if not any(title.endswith(suf) for suf in ['TOUR', 'PACKAGE', 'YATRA', 'EXPEDITION', 'CRUISE']):
                    title = f"{title} TOUR PACKAGE"

                # Overview
                overview = ""
                ov_h3 = soup.find(lambda t: t.name in ['h2', 'h3', 'h4'] and 'overview' in t.text.lower())
                if ov_h3:
                    p_tag = ov_h3.find_next(['p', 'div'])
                    if p_tag:
                        overview = clean_rebrand(p_tag.get_text(strip=True))

                # Itinerary
                itinerary = []
                it_h3 = soup.find(lambda t: t.name in ['h2', 'h3', 'h4'] and 'itinerary' in t.text.lower())
                if it_h3:
                    for h in it_h3.find_all_next(['h4', 'h5', 'strong']):
                        prev_h3 = h.find_previous(['h2', 'h3'])
                        if prev_h3 != it_h3:
                            break
                        h_text = clean_rebrand(h.get_text(strip=True))
                        if len(h_text) > 3 and not any(ex in h_text.lower() for ex in ['inclusions', 'policy', 'help', 'overview', 'info']):
                            nxt_p = h.find_next(['p', 'div'])
                            desc = clean_rebrand(nxt_p.get_text(strip=True)) if nxt_p else ""
                            itinerary.append({'title': h_text, 'desc': desc})

                # Inclusions
                inclusions = []
                inc_h3 = soup.find(lambda t: t.name in ['h2', 'h3', 'h4'] and 'inclusion' in t.text.lower())
                if inc_h3:
                    for li in inc_h3.find_all_next('li')[:20]:
                        prev_h3 = li.find_previous(['h2', 'h3'])
                        if prev_h3 != inc_h3:
                            break
                        item_t = clean_rebrand(li.get_text(strip=True))
                        if len(item_t) > 3:
                            inclusions.append(item_t)

                # Duration
                days, nights = parse_duration_from_title(raw_title, default_days=len(itinerary) if itinerary else 4)
                if len(itinerary) > days:
                    days = len(itinerary)
                    nights = max(1, days - 1)

                # Category & Destination
                dest = clean_rebrand(raw_title.split('–')[0].split('-')[0].split('|')[0]).strip()
                country, currency = detect_country_and_currency(title, dest)
                cat = detect_category(title, dest, overview, is_intl=(country != 'India'), source='main')

                scraped_packages.append({
                    'source': 'main',
                    'url': u,
                    'title': title,
                    'destination': dest,
                    'category': cat,
                    'days': days,
                    'nights': nights,
                    'is_international': (cat == 'international'),
                    'destination_country': country,
                    'currency_code': currency,
                    'overview': overview,
                    'days_plan': itinerary,
                    'inclusions': inclusions
                })
                print(f"  [{idx:2d}/{len(all_target_urls)}] Scraped: {title[:45]} ({nights}N/{days}D, {len(itinerary)} days plan) [{cat}]")

            except Exception as e:
                print(f"  [ERR] Failed scraping {u}: {e}")

        browser.close()
    return scraped_packages

# ==============================================================================
# SCRAPER FOR HONEYMOON SUBDOMAIN (40 packages) VIA URLLIB / BS4
# ==============================================================================

def scrape_single_honeymoon_package(pid, card_title):
    url = f'https://honeymoon.renghaholidays.com/packages/{pid}/{pid}'
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=12, context=ctx).read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
    except Exception as e:
        return None, f"Error {pid}: {e}"

    raw_title = card_title if card_title else f"Honeymoon Tour Package {pid}"
    title = clean_rebrand(raw_title).upper()
    if not any(title.endswith(suf) for suf in ['TOUR', 'PACKAGE', 'SPECIAL', 'ESCAPE', 'ODYSSEY', 'ITINERARY']):
        title = f"{title} TOUR PACKAGE"

    # Overview
    overview = ""
    for p in soup.find_all('p'):
        t = clean_rebrand(p.get_text(strip=True))
        if len(t) > 60 and not any(ex in t.lower() for ex in ['copyright', 'reserved', 'your rating']):
            overview = t
            break

    # Itinerary days from accordion
    days_plan = []
    for idx, item in enumerate(soup.find_all('div', class_='accordion-title'), 1):
        title_text = clean_rebrand(item.get_text(strip=True))
        content_div = item.find_next_sibling('div')
        content_text = clean_rebrand(content_div.get_text(strip=True)) if content_div else ''
        if not title_text.lower().startswith('day'):
            title_text = f"Day {idx}: {title_text}"
        days_plan.append({
            'title': title_text,
            'desc': content_text[:600]
        })

    # Inclusions
    inclusions = []
    for li in soup.find_all('li'):
        t = clean_rebrand(li.get_text(strip=True))
        if any(t.startswith(prefix) for prefix in ['?', '•', '✔', '-']) or any(k in t.lower() for k in ['breakfast', 'dinner', 'transfer', 'sightseeing', 'hotel', 'accommodation']):
            clean_item = re.sub(r'^[?•✔\-\s]+', '', t).strip()
            if len(clean_item) > 8 and clean_item not in inclusions:
                inclusions.append(clean_item)

    # Durations
    days, nights = parse_duration_from_title(raw_title, default_days=len(days_plan) if days_plan else 5)
    if len(days_plan) > days:
        days = len(days_plan)
        nights = max(1, days - 1)

    dest = clean_rebrand(raw_title.split(':')[0].split('|')[0].split('–')[0]).strip()
    country, currency = detect_country_and_currency(title, dest)
    cat = detect_category(title, dest, overview, is_intl=(country != 'India'), source='honeymoon')

    return {
        'source': 'honeymoon',
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
        'days_plan': days_plan,
        'inclusions': inclusions[:8]
    }, None

def scrape_honeymoon_packages():
    print("\n--- Scraping 40 Honeymoon Packages from honeymoon.renghaholidays.com ---")
    index_url = 'https://honeymoon.renghaholidays.com/packages'
    req = urllib.request.Request(index_url, headers=HEADERS)
    html = urllib.request.urlopen(req, timeout=12, context=ctx).read().decode('utf-8', errors='ignore')
    soup = BeautifulSoup(html, 'html.parser')

    cards = []
    for a in soup.find_all('a', href=True):
        h = a['href'].strip()
        m = re.search(r'packages/(\d+)/\d+', h)
        if m:
            pid = m.group(1)
            card_text = a.get_text(strip=True)
            if len(card_text) > 5 and not any(c['pid'] == pid for c in cards):
                cards.append({'pid': pid, 'title': card_text})

    print(f"Found {len(cards)} honeymoon package entries on index page.")
    results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(scrape_single_honeymoon_package, c['pid'], c['title']): c for c in cards}
        for future in as_completed(futures):
            data, err = future.result()
            if data:
                results.append(data)
                print(f"  [{len(results):2d}/{len(cards)}] Scraped: {data['title'][:45]} ({data['nights']}N/{data['days']}D, {len(data['days_plan'])} days plan)")
            else:
                print(f"  [ERR] {err}")
    return results

# ==============================================================================
# MAIN DATABASE IMPORT & ENRICHMENT PIPELINE
# ==============================================================================

def main():
    print("=" * 80)
    print("  SIVA GAYATHRI TOURS & TRAVELS — RENGHA HOLIDAYS COMPLETE EXTRACTOR A TO Z")
    print("=" * 80)

    out_file = 'scripts/scraped_rengha_packages.json'
    if os.path.exists(out_file) and '--force-scrape' not in sys.argv:
        print(f"Loading cached {out_file} directly for database import...")
        with open(out_file, 'r', encoding='utf-8') as f:
            all_packages = json.load(f)
        print(f"Loaded {len(all_packages)} packages from {out_file}!")
    else:
        # 1. Scrape Main & Landing Packages
        main_scraped = scrape_main_packages_playwright()
        
        # 2. Scrape Honeymoon Packages
        honeymoon_scraped = scrape_honeymoon_packages()

        all_packages = main_scraped + honeymoon_scraped
        print(f"\nScraping complete: Total {len(all_packages)} packages extracted ({len(main_scraped)} main + {len(honeymoon_scraped)} honeymoon)!")

        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(all_packages, f, indent=2, ensure_ascii=False)
        print(f"Saved complete raw dataset to {out_file}!")

    # 3. Database Import
    print(f"\nImporting all {len(all_packages)} packages into database with prefix SGT-RH-...")
    deleted = Package.objects.filter(package_code__startswith='SGT-RH-').delete()
    print(f"Cleared previous SGT-RH- records: {deleted}")

    imported_count = 0
    for idx, item in enumerate(all_packages, 1):
        days = item['days']
        nights = item['nights']
        
        # Build clean unique slug
        raw_slug = re.sub(r'[^A-Z0-9]+', '-', item['title'][:20]).strip('-')
        pkg_code = f"SGT-RH-{raw_slug}-{days}D"
        if Package.objects.filter(package_code=pkg_code).exists():
            pkg_code = f"SGT-RH-{raw_slug}-{days}D-{idx}"

        # Pricing
        is_intl = item['is_international']
        is_dev = (item['category'] == 'devotional')
        if is_intl:
            base_price = Decimal(str(days * 7500))
        elif is_dev:
            base_price = Decimal(str(days * 2200))
        elif item['category'] == 'family_vacation':
            base_price = Decimal(str(days * 3400))
        elif item['category'] == 'hill_station':
            base_price = Decimal(str(days * 2500))
        else:
            base_price = Decimal(str(days * 2400))

        ap_price = base_price
        ep_price = Decimal(str(round(float(base_price) * 0.78, 2)))

        meal_plan = 'MAP' if is_intl or item['category'] == 'family_vacation' else 'AP'

        inclusions_text = "\n".join(item['inclusions']) if item['inclusions'] else (
            "Well-maintained tourist vehicle with professional chauffeur throughout the tour.\n"
            "All route permit charges, interstate road taxes, highway toll gates, and vehicle parking.\n"
            "Hotel accommodation on twin-sharing basis with daily breakfast and dinner.\n"
            f"Comprehensive sightseeing covering key attractions along {item['destination']}.\n"
            + ("100% Satvik Pure Vegetarian South Indian meals.\n" if is_dev else "")
            + "24x7 Siva Gayathri Tours & Travels dispatch and customer assistance."
        )

        exclusions_text = (
            "Monument entrance fees, boating charges, camera tokens, and personal expenses.\n"
            "Any airfare or train tickets (can be arranged upon request).\n"
            "Optional activities, adventure sports, or excursions not explicitly mentioned.\n"
            "Any delay or expenses caused by roadblocks, train delays, or natural calamities."
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
            destination_country=item['destination_country'],
            currency_code=item['currency_code'],
            visa_required=is_intl,
            visa_guidelines=f"Tourist eVisa / Entry Authorization required for {item['destination_country']}." if is_intl else "",
            passport_validity_months=6 if is_intl else 0,
            flight_inclusive=False,
            flight_details_note=f"Scheduled flight booking assistance available Ex-Coimbatore (CJB) / Ex-Chennai (MAA) to {item['destination_country']}." if is_intl else "",
            overseas_dmc_partner=f"Certified DMC Destination Partner in {item['destination_country']}" if is_intl else "",
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

        # Create Day-by-Day Itinerary
        raw_days = item['days_plan']
        for d_idx in range(1, days + 1):
            if d_idx <= len(raw_days):
                plan_item = raw_days[d_idx - 1]
                d_title = plan_item.get('title', f"Day {d_idx}: Sightseeing & Exploration")
                d_desc = plan_item.get('desc', f"Sightseeing and activities across {pkg_dest}.")
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
            if 'puri' in dest_lower or 'jaganath' in dest_lower:
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
            elif 'char dham' in dest_lower or 'do dham' in dest_lower:
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

        imported_count += 1
        if imported_count % 15 == 0 or imported_count == len(all_packages):
            print(f"  Imported {imported_count}/{len(all_packages)}: {pkg.name[:45]} ({nights}N/{days}D) [{pkg.category}]")

    print("=" * 80)
    print(f"SUCCESS! Scraped & Imported all {imported_count} packages from renghaholidays.com under prefix SGT-RH-!")
    print("=" * 80)

if __name__ == '__main__':
    main()
