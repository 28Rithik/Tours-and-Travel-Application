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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

INTL_FILENAMES = {
    'dubai.html': ('Dubai, UAE', 'AED', 5, 4),
    'singapore.html': ('Singapore', 'SGD', 5, 4),
    'malaysia.html': ('Malaysia', 'MYR', 5, 4),
    'sin-mal.html': ('Singapore & Malaysia', 'SGD', 6, 5),
    'sin-mal-tha.html': ('Singapore, Malaysia & Thailand', 'THB', 8, 7),
    'thailand.html': ('Thailand', 'THB', 5, 4),
    'hon-mac.html': ('Hong Kong & Macau', 'HKD', 5, 4),
    'hon-mac-tha.html': ('Hong Kong, Macau & Thailand', 'HKD', 8, 7),
    'mauritius.html': ('Mauritius', 'USD', 5, 4),
    'maldives.html': ('Maldives', 'USD', 4, 3),
    'srilanka.html': ('Sri Lanka', 'INR', 5, 4),
}

DEV_FILENAMES = {
    'badrinath.html': ('Badrinath Holy Dham Yatra', 'Badrinath & Joshimath', 5, 4, 'Badrinath Temple Complex & Tapt Kund'),
    'kedarnath.html': ('Kedarnath Jyotirlinga Yatra', 'Kedarnath & Guptkashi', 5, 4, 'Kedarnath Jyotirlinga Shrine'),
    'haridwar.html': ('Haridwar Sacred Ganga Aarti Yatra', 'Haridwar & Rishikesh', 3, 2, 'Har Ki Pauri & Mansa Devi Temple'),
    'rishikesh.html': ('Rishikesh Yoga & Spiritual Circuit', 'Rishikesh & Devprayag', 3, 2, 'Triveni Ghat & Neelkanth Mahadev'),
    'varanasi.html': ('Kashi Varanasi Sacred Pilgrimage', 'Varanasi & Sarnath', 4, 3, 'Kashi Vishwanath Jyotirlinga & Ganga Aarti'),
    'rameshwaram.html': ('Rameshwaram Jyotirlinga & 22 Theerthams Yatra', 'Rameshwaram & Dhanushkodi', 3, 2, 'Ramanathaswamy Temple & Agnitheertham'),
    'gur-ath-coc.html': ('Guruvayoor Temple & Athirappilly Tour', 'Guruvayoor & Athirappilly', 3, 2, 'Guruvayoor Sri Krishna Temple'),
    'ala-var-kat.html': ('Prayagraj Varanasi & Vaishno Devi Yatra', 'Prayagraj, Varanasi & Katra', 6, 5, 'Kashi Vishwanath & Mata Vaishno Devi'),
}

def clean_rebrand(text):
    if not text:
        return ""
    replacements = [
        (re.compile(r'ate\.\.\.Routes', re.IGNORECASE), 'at Siva Gayathri Tours & Travels'),
        (re.compile(r'at\s*e\.\.\.Routes', re.IGNORECASE), 'at Siva Gayathri Tours & Travels'),
        (re.compile(r'ate-Routes', re.IGNORECASE), 'at Siva Gayathri Tours & Travels'),
        (re.compile(r'at\s*e-Routes', re.IGNORECASE), 'at Siva Gayathri Tours & Travels'),
        (re.compile(r'e\.\.\.Routes', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'e-Routes', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Eroutes\s+Travel', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Eroutes', re.IGNORECASE), 'Siva Gayathri'),
        (re.compile(r'eroutestravel\.com', re.IGNORECASE), 'sivagayathritravels.com'),
        (re.compile(r'booking@eroutestravel\.com', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'info@eroutestravel\.com', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'\+91[\s\d-]{9,15}'), '+91 98425 33777'),
    ]
    cleaned = text
    for pattern, repl in replacements:
        cleaned = pattern.sub(repl, cleaned)
    return cleaned.strip()

def discover_all_package_urls():
    hub_pages = [
        'http://eroutestravel.com/package.html',
        'http://eroutestravel.com/bhakthi.html',
        'http://eroutestravel.com/honeymoon.html',
        'http://eroutestravel.com/group.html',
        'http://eroutestravel.com/index.html',
        'http://eroutestravel.com/services.html'
    ]
    excludes = {
        'index.html', 'about.html', 'contact.php', 'gallery.html', 'service.html',
        'services.html', 'service_enquiry.php', 'testimonials.html', 'vehicle.html',
        'tariff.html', 'eroutes.pdf', 'package.html', 'bhakthi.html', 'honeymoon.html',
        'group.html', 'audi.html', 'benz.html', 'bmw.html', 'camry.html', 'city.html',
        'coach.html', 'crysta.html', 'dzire.html', 'etios.html', 'fortuner.html',
        'indica.html', 'indigo.html', 'innova.html', 'jaguar.html', 'logan.html',
        'traveller.html', 'travera.html', 'vintage.html'
    }
    found = set()
    for hp in hub_pages:
        try:
            req = urllib.request.Request(hp, headers=HEADERS)
            html = urllib.request.urlopen(req, timeout=10, context=ctx).read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            for a in soup.find_all('a', href=True):
                h = a['href'].strip().split('#')[0].split('?')[0]
                if h.endswith('.html') and h not in excludes and not h.startswith('http'):
                    found.add(h)
        except Exception as e:
            print(f"Error on {hp}: {e}")
    return sorted(found)

def parse_package_page(filename):
    url = f'http://eroutestravel.com/{filename}'
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=12, context=ctx).read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
    except Exception as e:
        return None, f"Fetch error: {e}"

    for el in soup.find_all(['header', 'footer', 'nav', 'script', 'style']):
        el.decompose()

    mt = soup.find('div', class_='main_title')
    cont = mt.find_next_sibling('div') if mt else soup
    if not cont:
        cont = soup

    # 1. Extract Title
    raw_title = ""
    if mt:
        raw_title = mt.get_text(strip=True)
    if not raw_title:
        for h in soup.find_all(['h2', 'h3', 'h4']):
            ht = h.get_text(strip=True)
            if len(ht) > 3 and not any(ex in ht.lower() for ex in ['package', 'client', 'connect', 'contact', 'include', 'exclude', 'trips..']):
                raw_title = ht
                break
    if not raw_title:
        raw_title = filename.rstrip('.html').replace('-', ' ').title()

    title = clean_rebrand(raw_title).upper()
    if not any(title.endswith(suf) for suf in ['TOUR', 'PACKAGE', 'YATRA', 'CRUISE']):
        title = f"{title} TOUR PACKAGE"

    # Identify Destinations / Spots
    destinations = [d.strip() for d in re.split(r'[-–\u2013\u2014&,]+', raw_title) if len(d.strip()) > 1 and not any(ex in d.lower() for ex in ['tour', 'package', 'yatra'])]
    dest_str = " - ".join(destinations) if destinations else title.replace('TOUR', '').replace('PACKAGE', '').strip()

    # Classify Category & Duration
    is_intl = filename in INTL_FILENAMES
    is_dev = filename in DEV_FILENAMES or any(k in title.lower() for k in ['badrinath', 'kedarnath', 'varanasi', 'haridwar', 'rishikesh', 'rameshwaram', 'guruvayoor', 'bhakthi'])

    if is_intl:
        dest_country, curr_code, days, nights = INTL_FILENAMES[filename]
        category = 'international'
    elif is_dev:
        if filename in DEV_FILENAMES:
            _, dest_country, days, nights, _ = DEV_FILENAMES[filename]
        else:
            dest_country = dest_str
            days = max(3, len(destinations))
            nights = max(2, days - 1)
        curr_code = 'INR'
        category = 'devotional'
    elif any(k in title.lower() for k in ['ooty', 'kodaikanal', 'munnar', 'wayanad', 'coorg', 'darjeeling', 'kullu', 'manali', 'shimla', 'yercaud', 'nainital', 'kashmir']):
        category = 'hill_station'
        dest_country = dest_str
        days = max(3, len(destinations) + 1)
        nights = max(2, days - 1)
        curr_code = 'INR'
    elif 'honeymoon' in url.lower() or any(k in title.lower() for k in ['andaman', 'lakshadweep', 'goa']):
        category = 'family_vacation'
        dest_country = dest_str
        days = max(4, len(destinations) + 1)
        nights = max(3, days - 1)
        curr_code = 'INR'
    else:
        category = 'holiday'
        dest_country = dest_str
        days = max(3, len(destinations) + 1)
        nights = max(2, days - 1)
        curr_code = 'INR'

    # 2. Extract Inclusions & Exclusions & Attraction ULs
    inc_items = []
    exc_items = []
    attraction_groups = []

    for ul in cont.find_all('ul'):
        items = [clean_rebrand(li.get_text(strip=True)) for li in ul.find_all('li') if len(li.get_text(strip=True)) > 2]
        if not items:
            continue
        first_lower = items[0].lower()
        if any(tab in first_lower for tab in ['introduction', 'tourist attractions', 'inclusions']):
            continue
        if any('permit' in it.lower() or 'accommodation' in it.lower() or 'toll' in it.lower() or 'guide' in it.lower() for it in items):
            inc_items.extend(items)
        elif any('expenses of personal' in it.lower() or 'tips' in it.lower() or 'excursion' in it.lower() or 'extra' in it.lower() for it in items):
            exc_items.extend(items)
        else:
            prev_h = ul.find_previous(['h3', 'h4', 'strong'])
            h_text = clean_rebrand(prev_h.get_text(strip=True).rstrip(':').strip()) if prev_h else ''
            if not h_text or any(ex in h_text.lower() for ex in ['include', 'exclude', 'client', 'connect', 'disclaimer', 'check us', 'click here']):
                h_text = dest_str
            attraction_groups.append((h_text, items))

    # 3. Extract Narrative Sections (headings + following paragraphs)
    heading_sections = []
    current_heading = None
    current_paras = []
    for el in cont.find_all(['h2', 'h3', 'h4', 'strong', 'p']):
        t = el.get_text(strip=True)
        if not t:
            continue
        if el.name in ['h2', 'h3', 'h4', 'strong'] and len(t) < 45 and not any(ex in t.lower() for ex in ['include', 'exclude', 'client', 'connect', 'disclaimer', 'check us', 'click here', 'package', 'e...routes', 'rate']):
            if current_heading and current_paras:
                heading_sections.append((clean_rebrand(current_heading), clean_rebrand(' '.join(current_paras))))
            current_heading = t.rstrip(':').strip()
            current_paras = []
        elif el.name == 'p':
            if len(t) > 25 and not any(ex in t.lower() for ex in ['copyright', 'reserved', 'click here', 'disclaimer']):
                # Filter out pure title repeater paragraphs
                if t.strip() != raw_title.strip() and t.strip().upper() != title:
                    current_paras.append(t)
    if current_heading and current_paras:
        heading_sections.append((clean_rebrand(current_heading), clean_rebrand(' '.join(current_paras))))

    # All narrative paragraphs for fallback
    all_paras = [clean_rebrand(p.get_text(strip=True)) for p in cont.find_all('p') if len(p.get_text(strip=True)) > 30 and not any(ex in p.get_text(strip=True).lower() for ex in ['copyright', 'reserved', 'click here', 'disclaimer', 'rates & offers'])]

    # 4. Build Days Plan
    days_plan = []

    # Scenario A: We have multi-destination cities (e.g. Agra, Delhi, Jaipur, Kullu, Manali)
    if destinations and len(destinations) >= 2:
        for d_idx, d_name in enumerate(destinations[:days], 1):
            # Find matching attraction items
            matching_attractions = []
            for gh, gi in attraction_groups:
                if d_name.lower() in gh.lower():
                    matching_attractions.extend(gi)
            # Find matching narrative section
            matching_narrative = ""
            for sh, sp in heading_sections:
                if d_name.lower() in sh.lower():
                    matching_narrative = sp
                    break
            if not matching_narrative:
                for p in all_paras:
                    if d_name.lower() in p.lower() and len(p) > 50:
                        matching_narrative = p
                        break

            spots_desc = ""
            if matching_attractions:
                spots_desc = f"Key Sightseeing: {', '.join(matching_attractions)}. "
            if matching_narrative:
                spots_desc += matching_narrative
            if not spots_desc:
                spots_desc = f"Explore scenic beauty, prominent cultural attractions, local bazaars, and architectural wonders of {d_name}."

            days_plan.append({
                'day': d_idx,
                'title': f"Day {d_idx}: Arrival & Sightseeing in {d_name}",
                'spots': spots_desc[:480]
            })

    # Scenario B: We have rich heading sections covering the days (e.g. Badrinath: The Temple Complex, Tapt Kund, Narad Kund...)
    elif heading_sections and len([s for s in heading_sections if s[0].lower() not in raw_title.lower()]) >= (days - 1):
        valid_sections = [s for s in heading_sections if s[0].lower() not in raw_title.lower()]
        for idx, (sh, sp) in enumerate(valid_sections[:days], 1):
            matching_attractions = []
            for gh, gi in attraction_groups:
                matching_attractions.extend(gi)
            att_text = f"Attractions: {', '.join(matching_attractions[:6])}. " if matching_attractions and idx == 1 else ""
            days_plan.append({
                'day': idx,
                'title': f"Day {idx}: {sh} Exploration & Sightseeing",
                'spots': f"{att_text}{sp}"[:480]
            })

    # Scenario C: We have attraction groups (e.g. Singapore, Dubai, Goa with 6+ attraction bullets)
    elif attraction_groups and any(len(gi) >= 2 for _, gi in attraction_groups):
        all_atts = []
        for _, atts in attraction_groups:
            all_atts.extend(atts)
        # Split attractions across days
        chunk_size = max(1, len(all_atts) // max(1, (days - 1)))
        for d_idx in range(1, days):
            start_i = (d_idx - 1) * chunk_size
            end_i = start_i + chunk_size if d_idx < (days - 1) else len(all_atts)
            day_atts = all_atts[start_i:end_i]
            att_str = ", ".join(day_atts) if day_atts else "City Highlights & Landmarks"
            desc = all_paras[d_idx-1] if len(all_paras) >= d_idx else f"Guided sightseeing tour covering {att_str}."
            days_plan.append({
                'day': d_idx,
                'title': f"Day {d_idx}: {dest_str} - {day_atts[0] if day_atts else 'Highlights'}",
                'spots': f"Key Sightseeing: {att_str}. {desc}"[:480]
            })

    # Pad remaining days up to `days`
    while len(days_plan) < days:
        d_idx = len(days_plan) + 1
        if d_idx == days:
            days_plan.append({
                'day': d_idx,
                'title': f"Day {d_idx}: Final Sightseeing, Souvenir Shopping & Departure",
                'spots': f"Morning leisure, local handicraft shopping, checkout from hotel, and comfortable return journey from {dest_str} with pleasant memories."
            })
        else:
            days_plan.append({
                'day': d_idx,
                'title': f"Day {d_idx}: In-Depth Exploration of {dest_str}",
                'spots': f"Full day sightseeing covering natural wonders, heritage monuments, and leisure activities along {dest_str}."
            })

    # 5. Final Inclusions & Exclusions
    inclusions_text = "\n".join(inc_items) if inc_items else (
        "Well-maintained tourist vehicle with professional chauffeur throughout the tour.\n"
        "All route permit charges, interstate road taxes, highway toll gates, and vehicle parking.\n"
        "Hotel accommodation on twin-sharing basis with daily breakfast and dinner.\n"
        f"Comprehensive sightseeing covering key attractions along {dest_str}.\n"
        + ("100% Satvik Pure Vegetarian South Indian meals.\n" if is_dev else "")
        + "24x7 Siva Gayathri Tours & Travels dispatch and customer assistance."
    )

    exclusions_text = "\n".join(exc_items) if exc_items else (
        "Monument entrance fees, boating charges, camera tokens, and personal expenses.\n"
        "Any airfare or train tickets (can be arranged upon request).\n"
        "Optional activities, adventure sports, or excursions not explicitly mentioned.\n"
        "Any delay or expenses caused by roadblocks, train delays, or natural calamities."
    )

    overview_text = "\n\n".join(all_paras[:3]) if all_paras else f"Experience {title} with Siva Gayathri Tours & Travels. Comprehensive {days} Days / {nights} Nights itinerary with full fleet support."

    # Base pricing
    if is_intl:
        base_price = Decimal(str(days * 7200))
    elif is_dev:
        base_price = Decimal(str(days * 2100))
    elif category == 'family_vacation':
        base_price = Decimal(str(days * 3200))
    elif category == 'hill_station':
        base_price = Decimal(str(days * 2400))
    else:
        base_price = Decimal(str(days * 2300))

    return {
        'filename': filename,
        'url': url,
        'title': title,
        'destination': dest_str,
        'category': category,
        'days': days,
        'nights': nights,
        'is_international': is_intl,
        'is_devotional': is_dev,
        'destination_country': dest_country if is_intl else 'India',
        'currency_code': curr_code,
        'base_price': float(base_price),
        'days_plan': days_plan,
        'inclusions': inclusions_text,
        'exclusions': exclusions_text,
        'description': overview_text,
    }, None

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
            interstate_permit_included=True if pkg.is_international or any(k in pkg.name.lower() for k in ['kerala', 'karnataka', 'goa', 'delhi', 'agra', 'jaipur', 'mumbai', 'badrinath', 'kedarnath', 'varanasi']) else False,
        )

def main():
    print("=" * 80)
    print("  SIVA GAYATHRI TOURS & TRAVELS — EROUTES TRAVEL COMPLETE EXTRACTOR A TO Z")
    print("=" * 80)

    # 1. Discover all packages
    pkg_files = discover_all_package_urls()
    print(f"Discovered {len(pkg_files)} distinct package HTML files across eroutestravel.com")

    # 2. Scrape packages concurrently
    results = []
    errors = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_fn = {executor.submit(parse_package_page, fn): fn for fn in pkg_files}
        for future in as_completed(future_to_fn):
            data, err = future.result()
            if data:
                results.append(data)
                print(f"  [{len(results):2d}/{len(pkg_files)}] {data['title'][:50]} ({data['nights']}N/{data['days']}D, {len(data['days_plan'])} days plan)")
            else:
                errors += 1
                print(f"  [ERR] {err}")

    print(f"\nScraping complete: {len(results)} scraped successfully, {errors} errors.")
    out_file = 'scripts/scraped_eroutes_packages.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Saved all scraped packages to {out_file}!")

    # 3. Import into Django Database
    print(f"\nImporting all {len(results)} packages into database with prefix SGT-ER-...")
    deleted = Package.objects.filter(package_code__startswith='SGT-ER-').delete()
    print(f"Cleared previous SGT-ER- records: {deleted}")

    imported_count = 0
    for idx, item in enumerate(results, 1):
        slug = item['filename'].rstrip('.html').upper()
        slug_clean = re.sub(r'[^A-Z0-9]+', '-', slug).strip('-')[:18]
        days = item['days']
        nights = item['nights']
        pkg_code = f"SGT-ER-{slug_clean}-{days}D"
        if Package.objects.filter(package_code=pkg_code).exists():
            pkg_code = f"SGT-ER-{slug_clean}-{days}D-{idx}"

        price_dec = Decimal(str(item['base_price']))
        ap_price = price_dec
        ep_price = Decimal(str(round(float(price_dec) * 0.78, 2)))

        meal_plan = 'MAP' if item['is_international'] or item['category'] == 'family_vacation' else 'AP'

        terms_text = (
            "50% advance deposit upon tour confirmation, remaining balance payable prior to trip departure.\n"
            "Vehicle will strictly adhere to designated routes, safety rules, and permit schedules.\n"
            "AC will be switched off on steep ghat roads and hairpin bends for engine power and passenger safety.\n"
            "Siva Gayathri Tours & Travels guarantees polite chauffeurs, sanitized coaches, and timely support."
        )

        pkg = Package.objects.create(
            package_code=pkg_code,
            name=item['title'],
            destination=item['destination'][:150],
            category=item['category'],
            duration_nights=nights,
            duration_days=days,
            base_price=price_dec,
            price_with_food=ap_price,
            price_without_food=ep_price,
            pricing_type='per_person',
            meal_plan=meal_plan,
            room_sharing_type='twin_sharing',
            min_pax=2 if item['is_international'] else 4,
            is_international=item['is_international'],
            destination_country=item['destination_country'],
            currency_code=item['currency_code'],
            visa_required=item['is_international'],
            visa_guidelines=f"Tourist eVisa / Entry Authorization required for {item['destination_country']}." if item['is_international'] else "",
            passport_validity_months=6 if item['is_international'] else 0,
            flight_inclusive=False,
            flight_details_note=f"Scheduled flight booking assistance available Ex-Coimbatore (CJB) / Ex-Chennai (MAA) to {item['destination_country']}." if item['is_international'] else "",
            overseas_dmc_partner=f"Certified DMC Destination Partner in {item['destination_country']}" if item['is_international'] else "",
            is_devotional=item['is_devotional'],
            satvik_pure_veg_meals=item['is_devotional'],
            senior_citizen_friendly=item['is_devotional'],
            temple_dress_code="Mandatory Traditional Dress: Dhoti/Kurta for Men, Saree/Chudidar for Women" if item['is_devotional'] else "",
            temple_darshan_info=f"Sacred Pilgrimage Circuit covering prominent shrines along {item['destination']}." if item['is_devotional'] else "",
            inclusions=item['inclusions'],
            exclusions=item['exclusions'],
            terms_and_conditions=terms_text,
            contact_persons_footer="Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131)",
            is_active=True,
        )

        # Create Itinerary Days
        for d in item['days_plan']:
            d_num = d.get('day', 1)
            d_title = d.get('title', f"Day {d_num}: Sightseeing & Exploration")
            d_spots = d.get('spots', item['destination'])
            ItineraryDay.objects.create(
                package=pkg,
                day_number=d_num,
                title=d_title[:250],
                route_segment=f"{item['destination']} Circuit"[:250],
                activities=d_spots,
                sightseeing_spots=d_spots[:500],
                meals_included="Breakfast, Lunch, Dinner" if meal_plan == 'AP' else "Breakfast & Dinner",
                night_stay_location=item['destination'].split()[0] if days > 1 and d_num < days else "Return Journey",
            )

        # Attach Tariffs
        attach_tariffs(pkg, days)

        # International Document Checklist
        if item['is_international']:
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
        if item['is_devotional']:
            dest_lower = item['title'].lower()
            if 'badrinath' in dest_lower:
                TempleDarshanSlot.objects.create(
                    package=pkg,
                    temple_name="Badrinath Temple Complex & Tapt Kund",
                    deity_or_circuit="Lord Badri Vishal (Maha Vishnu)",
                    darshan_type="special_entry_300",
                    booked_slot_time="06:30 AM - 09:30 AM",
                    reporting_location="Main Temple Complex",
                    dress_code_notes="Strict Traditional Attire (Warm Woolen Wear)",
                    prasad_details="Holy Tulsi & Badrinath Mahaprasad",
                    senior_citizen_support=True
                )
            if 'kedarnath' in dest_lower:
                TempleDarshanSlot.objects.create(
                    package=pkg,
                    temple_name="Kedarnath Jyotirlinga Shrine",
                    deity_or_circuit="Lord Shiva Jyotirlinga",
                    darshan_type="special_entry_300",
                    booked_slot_time="06:00 AM - 09:00 AM",
                    reporting_location="Kedarnath Sannidhanam",
                    dress_code_notes="Strict Traditional Attire (Warm Woolens)",
                    prasad_details="Holy Bhasma & Bel Patra Prasadam",
                    senior_citizen_support=True
                )
            if 'varanasi' in dest_lower or 'kasi' in dest_lower:
                TempleDarshanSlot.objects.create(
                    package=pkg,
                    temple_name="Kashi Vishwanath Jyotirlinga & Ganga Aarti",
                    deity_or_circuit="Lord Shiva (Vishwanath)",
                    darshan_type="special_entry_300",
                    booked_slot_time="05:30 AM - 08:30 AM",
                    reporting_location="Kashi Vishwanath Corridor Gate 4",
                    dress_code_notes="Strict Traditional Dhoti/Kurta (Men), Saree (Women)",
                    prasad_details="Holy Ganga Jal & Rudraksha Prasadam",
                    senior_citizen_support=True
                )
            if 'rameshwaram' in dest_lower:
                TempleDarshanSlot.objects.create(
                    package=pkg,
                    temple_name="Ramanathaswamy Temple & 22 Theerthams",
                    deity_or_circuit="Lord Shiva (Ramanathaswamy)",
                    darshan_type="special_entry_300",
                    booked_slot_time="06:00 AM - 08:30 AM",
                    reporting_location="East Gopuram Entrance",
                    dress_code_notes="Traditional Attire (Change of clothes post 22 Wells snanam)",
                    prasad_details="Holy Theertham & Prasadam",
                    senior_citizen_support=True
                )
            if 'haridwar' in dest_lower:
                TempleDarshanSlot.objects.create(
                    package=pkg,
                    temple_name="Har Ki Pauri & Mansa Devi Temple",
                    deity_or_circuit="Goddess Mansa Devi & Mother Ganga",
                    darshan_type="special_entry_300",
                    booked_slot_time="06:00 PM - 08:00 PM (Maha Aarti)",
                    reporting_location="Har Ki Pauri Ghat Steps",
                    dress_code_notes="Traditional Dhoti/Kurta or Saree",
                    prasad_details="Holy Ganga Jal & Temple Prasadam",
                    senior_citizen_support=True
                )
            if 'rishikesh' in dest_lower:
                TempleDarshanSlot.objects.create(
                    package=pkg,
                    temple_name="Triveni Ghat & Neelkanth Mahadev",
                    deity_or_circuit="Lord Shiva (Neelkanth)",
                    darshan_type="special_entry_300",
                    booked_slot_time="07:00 AM - 10:00 AM",
                    reporting_location="Triveni Ghat Sannidhi",
                    dress_code_notes="Traditional Attire",
                    prasad_details="Holy Rudraksha & Panchamrutham",
                    senior_citizen_support=True
                )
            if 'guruvayoor' in dest_lower or 'gur-ath' in item['filename']:
                TempleDarshanSlot.objects.create(
                    package=pkg,
                    temple_name="Guruvayoor Sri Krishna Temple",
                    deity_or_circuit="Lord Guruvayoorappan (Unnikrishnan)",
                    darshan_type="special_entry_300",
                    booked_slot_time="04:30 AM - 07:30 AM (Nirmalya Darshanam)",
                    reporting_location="East Nada Entrance",
                    dress_code_notes="Strict Kerala Traditional: Mundu (Men bare chest), Saree/Set Mundu (Women)",
                    prasad_details="Neyyappam & Palpayasam Prasadam",
                    senior_citizen_support=True
                )
            if 'ala-var-kat' in item['filename'] or 'katra' in dest_lower or 'vaishno' in dest_lower:
                TempleDarshanSlot.objects.create(
                    package=pkg,
                    temple_name="Mata Vaishno Devi Bhawan",
                    deity_or_circuit="Mata Vaishno Devi (Maha Kali, Maha Lakshmi, Maha Saraswati)",
                    darshan_type="special_entry_300",
                    booked_slot_time="05:00 AM - 09:00 AM",
                    reporting_location="Bhawan RFID Gate",
                    dress_code_notes="Comfortable Traditional Attire & Warm Clothes",
                    prasad_details="Holy Chunari, Dry Fruits & Bhawan Coins",
                    senior_citizen_support=True
                )

        imported_count += 1
        if imported_count % 15 == 0 or imported_count == len(results):
            print(f"  Imported {imported_count}/{len(results)}: {item['title'][:45]} ({nights}N/{days}D) [Category: {item['category']}]")

    print("=" * 80)
    print(f"SUCCESS! Scraped & Imported all {imported_count} packages from eroutestravel.com under prefix SGT-ER-!")
    print("=" * 80)

if __name__ == '__main__':
    main()
