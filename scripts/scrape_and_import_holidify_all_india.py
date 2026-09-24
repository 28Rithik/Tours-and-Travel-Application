import os
import sys
import re
import json
import html
import urllib.request
from decimal import Decimal
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

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

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

# ==============================================================================
# 1. TEXT CLEANING & REBRANDING UTILITIES
# ==============================================================================

def clean_rebrand(text):
    if not text:
        return ""
    text = html.unescape(text)
    text = text.replace('\u2192', ' - ').replace('\u2013', ' - ').replace('\u2014', ' - ').replace('\u2015', ' - ')
    text = text.replace('\u00a0', ' ').replace('\xa0', ' ').replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'wa\.link/\S+', '', text)
    text = re.sub(r'(?:www\.)?[a-zA-Z0-9-]+\.(?:com|in|org|net)/\S*', '', text)

    replacements = [
        (re.compile(r'Holidify\s+(?:Travels?|Packages?|Holidays?|Team)?', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'holidify\.com', re.IGNORECASE), 'sivagayathritravels.com'),
        (re.compile(r'\bHolidify\b', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Compare quotes from \d+ agents.*', re.IGNORECASE), ''),
        (re.compile(r'Get (?:Customized )?Offers.*', re.IGNORECASE), ''),
        (re.compile(r'\+91[\s\d-]{9,15}'), '+91 98425 33777'),
    ]
    cleaned = text
    for pattern, repl in replacements:
        cleaned = pattern.sub(repl, cleaned)

    cleaned = re.sub(r'\s*,\s*', ', ', cleaned)
    cleaned = re.sub(r'\s*-\s*', ' - ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

# ==============================================================================
# 2. PACKAGE PARSER
# ==============================================================================

def parse_holidify_package_detail(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html_content = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html_content, 'html.parser')

        id_match = re.search(r'-(\d+)\.html', url)
        pkg_id = id_match.group(1) if id_match else str(abs(hash(url)) % 100000)

        h1 = soup.find('h1')
        raw_title = h1.text.strip() if h1 else 'India Tour Package'
        title = clean_rebrand(raw_title)

        highlights = soup.find(class_=re.compile(r'atf-top-highlights', re.I))
        duration_str = ''
        theme_tag = ''
        if highlights:
            for pt in [p.text.strip() for p in highlights.find_all('p') if p.text.strip()]:
                if re.search(r'\d+\s*N\s*/\s*\d+\s*D', pt, re.I):
                    duration_str = pt
                elif not theme_tag and not re.search(r'^\d', pt):
                    theme_tag = pt

        days = 4
        nights = 3
        if duration_str:
            dn_match = re.search(r'(\d+)\s*N\s*/\s*(\d+)\s*D', duration_str, re.I)
            if dn_match:
                nights = int(dn_match.group(1))
                days = int(dn_match.group(2))
        else:
            dn_match = re.search(r'(\d+)\s*(?:Nights?|N)\s*[/&, -]*\s*(\d+)\s*(?:Days?|D)', title, re.I)
            if dn_match:
                nights = int(dn_match.group(1))
                days = int(dn_match.group(2))
            else:
                d_only = re.search(r'(\d+)\s*(?:Days?|Day)', title, re.I)
                if d_only:
                    days = int(d_only.group(1))
                    nights = max(1, days - 1)

        days = max(1, min(days, 30))
        nights = max(0, min(nights, days))

        price = 0
        final_p = soup.find(class_=re.compile(r'final-price', re.I))
        if final_p:
            pm = re.search(r'[\d,]+', final_p.text.replace('₹', ''))
            if pm:
                try:
                    price = float(pm.group(0).replace(',', ''))
                except:
                    pass
        if not price:
            all_prices = re.findall(r'₹\s*([\d,]+)', soup.text)
            if all_prices:
                for p_str in all_prices:
                    val = float(p_str.replace(',', ''))
                    if 2500 <= val <= 250000:
                        price = val
                        break
        if not price:
            price = days * 4000

        stay_info = '3-Star Premium Hotel & Luxury Resort'
        for tag in soup.find_all(string=re.compile(r'STAY', re.I)):
            parent_txt = tag.parent.text.strip().replace('\n', ' ')
            if any(k in parent_txt.lower() for k in ['hotels', 'resort', 'stay', 'camp', 'beach']):
                stay_info = clean_rebrand(parent_txt.replace('STAY', '').strip())
                if stay_info:
                    break

        hero_image = ''
        swipe_img = soup.find('div', class_='swipe-image')
        if swipe_img and swipe_img.get('style') and 'url(' in swipe_img.get('style'):
            m = re.search(r"url\(['\"]?(.*?)['\"]?\)", swipe_img.get('style'))
            if m and 'patt.png' not in m.group(1):
                hero_image = m.group(1)
        if not hero_image:
            for lbg in soup.find_all('div', class_='lazyBG'):
                orig = lbg.get('data-original')
                if orig and 'patt.png' not in orig:
                    hero_image = orig
                    break

        itinerary = []
        h2 = soup.find('h2', id='itinerary')
        sec = h2.find_next_sibling('div') if h2 else None
        if sec:
            day_blocks = sec.find_all('div', class_=lambda c: c and 'accordion' in c.lower())
            if not day_blocks:
                day_blocks = sec.find_all('div', class_=lambda c: c and 'day' in c.lower())
            if not day_blocks:
                day_blocks = sec.find_all(recursive=False)

            seen_days = set()
            for blk in day_blocks:
                header = blk.find(['button', 'h3', 'h4', 'h5', 'a', 'div'], class_=lambda c: c and any(k in c.lower() for k in ['header', 'title', 'heading', 'btn']))
                htxt = header.text.strip() if header else blk.text.strip()[:60]
                dm = re.search(r'Day\s*(\d+)\b[:\s-]*(.*)', htxt, re.I)
                if dm:
                    d_num = int(dm.group(1))
                    d_title = dm.group(2).strip() or f"Sightseeing & Excursion - Day {d_num}"
                    if d_num in seen_days:
                        continue
                    seen_days.add(d_num)

                    body = blk.find(class_=lambda c: c and any(k in c.lower() for k in ['collapse', 'body', 'content', 'desc']))
                    b_text = body.text.strip() if body else blk.text.strip()
                    b_text = b_text.replace(htxt, '').strip()

                    itinerary.append({
                        'day': d_num,
                        'title': clean_rebrand(d_title),
                        'activities': clean_rebrand(b_text)
                    })

        inclusions = []
        exclusions = []
        inc_div = soup.find('div', class_=lambda c: c and 'inclusions' in c.lower())
        if inc_div:
            for li in inc_div.find_all(['li', 'p', 'div']):
                t = clean_rebrand(li.text.strip())
                if t and len(t) > 3 and t not in inclusions:
                    inclusions.append(t)
        exc_div = soup.find('div', class_=lambda c: c and 'exclusions' in c.lower())
        if exc_div:
            for li in exc_div.find_all(['li', 'p', 'div']):
                t = clean_rebrand(li.text.strip())
                if t and len(t) > 3 and t not in exclusions:
                    exclusions.append(t)

        return {
            'url': url,
            'pkg_id': pkg_id,
            'title': title,
            'days': days,
            'nights': nights,
            'theme': theme_tag,
            'price': price,
            'stay_info': stay_info,
            'hero_image': hero_image,
            'itinerary': itinerary,
            'inclusions': inclusions,
            'exclusions': exclusions,
        }
    except Exception as e:
        return None

# ==============================================================================
# 3. DESTINATION & REGION RESOLVER FOR PAN-INDIA
# ==============================================================================

def detect_all_india_destination(title):
    combined = title.lower()
    if any(k in combined for k in ['goa', 'calangute', 'baga', 'panaji']):
        return 'Goa Beach Paradise, India'
    if any(k in combined for k in ['andaman', 'port blair', 'havelock', 'neil island', 'radhanagar']):
        return 'Andaman & Nicobar Islands, India'
    if any(k in combined for k in ['sikkim', 'gangtok', 'darjeeling', 'meghalaya', 'shillong', 'cherrapunji', 'kaziranga', 'assam', 'guwahati', 'north east', 'tawang']):
        return 'Northeast & Himalayan Vistas, India'
    if any(k in combined for k in ['mumbai', 'lonavala', 'mahabaleshwar', 'alibaug', 'shirdi', 'panchgani', 'maharashtra', 'khandala', 'matheran']):
        return 'Maharashtra & Western Ghats, India'
    if any(k in combined for k in ['gujarat', 'rann of kutch', 'kutch', 'gir', 'somnath', 'dwarka', 'statue of unity', 'ahmedabad']):
        return 'Gujarat Heritage & Wildlife, India'
    if any(k in combined for k in ['madhya pradesh', 'khajuraho', 'kanha', 'bandhavgarh', 'pachmarhi', 'ujjain', 'omkareshwar', 'gwalior', 'bhopal']):
        return 'Madhya Pradesh Heart of India, India'
    if any(k in combined for k in ['puri', 'odisha', 'bhubaneswar', 'konark']):
        return 'Odisha Temple & Golden Beach, India'
    return 'Incredible India Pan-Tour Circuit'

def detect_all_india_category(title, theme):
    combined = f"{title} {theme}".lower()
    if any(k in combined for k in ['shirdi', 'somnath', 'dwarka', 'ujjain', 'omkareshwar', 'puri', 'jagannath', 'temple', 'pilgrim']):
        return 'devotional'
    if any(k in combined for k in ['sikkim', 'darjeeling', 'shillong', 'meghalaya', 'lonavala', 'mahabaleshwar', 'pachmarhi', 'hill']):
        return 'hill_station'
    if any(k in combined for k in ['honeymoon', 'couple', 'romantic']):
        return 'holiday'
    if any(k in combined for k in ['family', 'vacation', 'getaway']):
        return 'family_vacation'
    return 'holiday'

# ==============================================================================
# 4. MAIN SCRAPE AND IMPORT PIPELINE (PHASE 3)
# ==============================================================================

def run_phase3_all_india_import():
    urls_file = os.path.join(WORKSPACE_ROOT, 'scripts', 'holidify_all_india_urls.json')
    if not os.path.exists(urls_file):
        print(f"Error: {urls_file} not found! Please run discover_holidify_all_india.py first.")
        return

    all_india_urls = json.load(open(urls_file, encoding='utf-8'))
    print(f"================================================================================")
    print(f"PHASE 3: FILTERING & IMPORTING REMAINING ALL-INDIA PACKAGES FROM HOLIDIFY")
    print(f"================================================================================")
    print(f"Total crawled All-India URLs: {len(all_india_urls)}")

    # Get already imported package IDs from Phase 1 and Phase 2
    existing_codes = set(Package.objects.filter(
        package_code__startswith='SGT-HOL-'
    ).values_list('package_code', flat=True))

    existing_ids = set()
    for code in existing_codes:
        parts = code.split('-')
        if len(parts) >= 4:
            existing_ids.add(parts[-1])

    print(f"Found {len(existing_ids)} existing Holidify package IDs in database from previous phases.")

    # Filter out already imported packages
    remaining_urls = []
    for u in all_india_urls:
        m = re.search(r'-(\d+)\.html', u)
        if m:
            pid = m.group(1)
            if pid not in existing_ids:
                remaining_urls.append(u)
        else:
            remaining_urls.append(u)

    print(f"Total net new All-India packages to scrape: {len(remaining_urls)}")

    print(f"Starting concurrent scraping with 14 workers...")
    scraped_data = []
    with ThreadPoolExecutor(max_workers=14) as executor:
        for item in executor.map(parse_holidify_package_detail, remaining_urls):
            if item:
                scraped_data.append(item)

    print(f"\nSuccessfully scraped {len(scraped_data)} new packages from Holidify All-India!")

    cache_path = os.path.join(WORKSPACE_ROOT, 'scripts', 'scraped_holidify_all_india_cache.json')
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(scraped_data, f, indent=2, ensure_ascii=False)
    print(f"Saved raw cache to {cache_path}")

    v_sedan = VehicleType.objects.filter(name__icontains='sedan').first()
    v_crysta = VehicleType.objects.filter(name__icontains='crysta').first() or VehicleType.objects.filter(name__icontains='innova').first()
    v_urbania = VehicleType.objects.filter(name__icontains='urbania').first() or VehicleType.objects.filter(name__icontains='tempo').first()
    v_minibus = VehicleType.objects.filter(name__icontains='36').first() or VehicleType.objects.filter(name__icontains='bus').first()
    v_coach = VehicleType.objects.filter(name__icontains='54').first() or VehicleType.objects.filter(name__icontains='coach').first()

    tariff_configs = [
        (v_sedan, '4_sedan', 14.0, 500),
        (v_crysta, '7_crysta', 20.0, 600),
        (v_urbania, '17_tt_urbania', 26.0, 800),
        (v_minibus, '36_mini_bus', 40.0, 1000),
        (v_coach, '54_luxury_coach', 55.0, 1200),
    ]

    print("\nStarting atomic database transaction for Phase 3...")
    with transaction.atomic():
        deleted_cnt, _ = Package.objects.filter(package_code__startswith='SGT-HOL-IN-').delete()
        if deleted_cnt > 0:
            print(f"Cleaned up {deleted_cnt} previous SGT-HOL-IN- records for clean refresh.")

        packages_created = 0
        all_itinerary_records = []
        all_tariff_records = []
        all_darshan_records = []

        for p_data in scraped_data:
            pkg_id = p_data['pkg_id']
            pkg_code = f"SGT-HOL-IN-{pkg_id}"
            title = p_data['title']
            days = p_data['days']
            nights = p_data['nights']
            base_price = Decimal(str(round(p_data['price'], 2)))
            price_with_food = Decimal(str(round(float(base_price) * 1.25, 2)))
            price_without_food = base_price

            dest = detect_all_india_destination(title)
            cat = detect_all_india_category(title, p_data.get('theme', ''))
            is_devo = (cat == 'devotional')

            overview = (
                f"Embark on an unforgettable vacation to {dest} with Siva Gayathri Tours & Travels. "
                f"This {nights} Nights / {days} Days itinerary is designed for maximum comfort and immersive exploration, "
                f"featuring hotel and resort accommodation ({p_data['stay_info']}), private AC vehicle transportation, "
                f"sightseeing excursions, and 24x7 tour coordination. "
                f"Ideal for families, holidaymakers, and group travelers."
            )

            inc_list = p_data['inclusions']
            if not inc_list:
                inc_list = [
                    f"Accommodation on twin/triple sharing in {p_data['stay_info']}.",
                    "Daily complimentary breakfast at all hotels/resorts.",
                    "All transfers and sightseeing by private air-conditioned vehicle as per itinerary.",
                    "Professional driver allowance, toll charges, interstate green permits, and parking fees.",
                    "Dedicated 24x7 tour manager coordination by Siva Gayathri Tours & Travels."
                ]
            else:
                inc_list.append("Dedicated 24x7 tour manager coordination by Siva Gayathri Tours & Travels.")
            if is_devo:
                inc_list.append("100% Satvik pure vegetarian meal coordination.")
                inc_list.append("Special senior citizen assistance and temple queue assistance.")

            exc_list = p_data['exclusions']
            if not exc_list:
                exc_list = [
                    "Airfare or train tickets to/from destination.",
                    "Entry tickets for monuments, camera permits, water sports, or boat cruise tickets.",
                    "Special temple pooja/archanai tickets or VIP darshan passes.",
                    "Personal expenses such as laundry, telephone calls, tips, and optional beverages.",
                    "GST (5%) as applicable."
                ]

            terms = (
                "1. 50% advance payment required upon booking confirmation; remaining balance due before tour commencement.\n"
                "2. Standard hotel check-in time is 12:00 PM and check-out is 10:00 AM.\n"
                "3. Water sports and boat cruises are subject to local port and weather conditions.\n"
                "4. All our vehicles are driven by verified, experienced chauffeurs ensuring safety and punctuality.\n"
                "5. Cancellation policy applies as per standard Siva Gayathri Tours & Travels terms."
            )

            pkg = Package.objects.create(
                package_code=pkg_code,
                name=title,
                destination=dest,
                category=cat,
                transit_mode='road_coach',
                duration_days=days,
                duration_nights=nights,
                pricing_type='per_person',
                base_price=base_price,
                price_with_food=price_with_food,
                price_without_food=price_without_food,
                min_pax=2,
                hotel_star_category=p_data['stay_info'],
                room_sharing_type='twin_sharing',
                meal_plan='MAP' if is_devo else 'CP',
                default_vehicle_type=v_sedan if days <= 4 else v_crysta,
                vehicle_seating_desc="Private Air-Conditioned Sedan / Crysta / Urbania Coach",
                bus_amenities_desc="AC, Clean Pushback Seats, First Aid Kit, Chauffeur Guide, Sound System",
                has_campfire_dj=True if 'hill_station' in cat else False,
                has_jeep_safari=True if any(k in title.lower() for k in ['safari', 'wildlife', 'kutch', 'kaziranga', 'gir']) else False,
                has_boating=True if any(k in title.lower() for k in ['goa', 'andaman', 'cruise', 'boat', 'island']) else False,
                has_industrial_visit=False,
                is_devotional=is_devo,
                satvik_pure_veg_meals=is_devo,
                senior_citizen_friendly=is_devo,
                temple_dress_code="Traditional Dhoti/Kurta for Men, Saree/Salwar for Women" if is_devo else "",
                is_international=False,
                destination_country="India",
                currency_code="INR",
                inclusions='\n'.join(f"- {item}" for item in inc_list),
                exclusions='\n'.join(f"- {item}" for item in exc_list),
                terms_and_conditions=terms,
                contact_persons_footer="Rithik CA (+91 98425 33777), Anandh C (+91 94381 7131)",
                description=overview,
                is_active=True
            )
            packages_created += 1

            itinerary_items = p_data.get('itinerary', [])
            if not itinerary_items:
                for d_idx in range(1, days + 1):
                    itinerary_items.append({
                        'day': d_idx,
                        'title': f"Day {d_idx} - {dest} Sightseeing & Local Exploration",
                        'activities': f"Morning breakfast at hotel. Proceed for full-day guided sightseeing across premier attractions in {dest}. Evening leisure and overnight stay."
                    })

            existing_day_nums = [it['day'] for it in itinerary_items]
            for d_idx in range(1, days + 1):
                if d_idx not in existing_day_nums:
                    itinerary_items.append({
                        'day': d_idx,
                        'title': f"Day {d_idx} - Sightseeing & Coastal / Mountain Leisure",
                        'activities': f"Enjoy morning breakfast. Proceed for scenic sightseeing, photography, and local market exploration. Overnight stay at hotel."
                    })
            itinerary_items = sorted(itinerary_items, key=lambda x: x['day'])

            for item in itinerary_items:
                d_num = item['day']
                d_title = item['title']
                d_desc = item['activities']
                if not d_desc:
                    d_desc = f"Guided sightseeing and transfers for Day {d_num} covering key highlights of {dest}."

                all_itinerary_records.append(ItineraryDay(
                    package=pkg,
                    day_number=d_num,
                    title=f"Day {d_num}: {d_title}"[:250],
                    route_segment=f"{dest} Circuit"[:250],
                    activities=d_desc,
                    morning_activity=d_desc[:300],
                    sightseeing_spots=d_desc[:400],
                    evening_night_activity="Evening at leisure, dining, and overnight stay.",
                    meals_included="Complimentary Breakfast & Dinner",
                    night_stay_location=f"Hotel / Resort in {dest.split(',')[0]}",
                    transport_info="Private AC Vehicle for all transfers & sightseeing"
                ))

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
                    interstate_permit_included=True,
                ))

            if is_devo:
                detected_temples = []
                lower_text = f"{title} {overview}".lower()
                if 'shirdi' in lower_text:
                    detected_temples.append(('Shirdi Sai Baba Samadhi Mandir', 'Shri Sai Baba', '06:00 AM - 09:00 AM', 'Gate No 1 / Kakad Aarti Queue'))
                if 'somnath' in lower_text:
                    detected_temples.append(('Somnath Jyotirlinga Temple', 'Lord Shiva Somnath', '06:30 AM - 09:30 AM', 'Main Shore Temple Gateway'))
                if 'dwarka' in lower_text:
                    detected_temples.append(('Dwarkadhish Temple (Jagat Mandir)', 'Lord Krishna Dwarkadhish', '07:00 AM - 10:00 AM', 'Moksha Dwar / Swarg Dwar'))
                if 'ujjain' in lower_text or 'mahakal' in lower_text:
                    detected_temples.append(('Mahakaleshwar Jyotirlinga Temple, Ujjain', 'Lord Shiva Mahakal Bhasma Aarti', '04:00 AM - 07:00 AM', 'Nandi Hall VIP Entry'))
                if 'omkareshwar' in lower_text:
                    detected_temples.append(('Omkareshwar Jyotirlinga & Mamleshwar', 'Lord Shiva Omkareshwar', '07:30 AM - 10:00 AM', 'Narmada River Bridge Entry'))
                if 'puri' in lower_text or 'jagannath' in lower_text:
                    detected_temples.append(('Jagannath Temple, Puri', 'Lord Jagannath, Balabhadra & Subhadra', '06:00 AM - 09:00 AM', 'Singhadwara (Lion Gate)'))

                if not detected_temples:
                    detected_temples.append(('Prominent Spiritual Temple Circuit', 'Presiding Deities', '07:00 AM - 09:30 AM', 'Main Mandir Complex Gate'))

                for t_name, deity, slot_time, rep_loc in detected_temples:
                    all_darshan_records.append(TempleDarshanSlot(
                        package=pkg,
                        temple_name=t_name,
                        deity_or_circuit=deity,
                        darshan_type='special_entry_300',
                        booked_slot_time=slot_time,
                        token_ticket_number=f"SGT-DARSHAN-IN-{pkg_id}-{abs(hash(t_name)) % 10000}",
                        reporting_location=rep_loc,
                        dress_code_notes="Strict Traditional Dhoti/Kurta for Men, Saree/Salwar for Women",
                        prasad_details="Special Holy Prasadam Included",
                        senior_citizen_support=True
                    ))

        print(f"Bulk inserting {len(all_itinerary_records)} ItineraryDay records...")
        ItineraryDay.objects.bulk_create(all_itinerary_records, batch_size=500)

        print(f"Bulk inserting {len(all_tariff_records)} PackageVehicleTariff records...")
        PackageVehicleTariff.objects.bulk_create(all_tariff_records, batch_size=500)

        if all_darshan_records:
            print(f"Bulk inserting {len(all_darshan_records)} TempleDarshanSlot records...")
            TempleDarshanSlot.objects.bulk_create(all_darshan_records, batch_size=500)

    print("\n================================================================================")
    print(f"PHASE 3 COMPLETE: Successfully imported {packages_created} All-India packages!")
    print(f"Itinerary Days: {len(all_itinerary_records)}")
    print(f"Vehicle Tariffs: {len(all_tariff_records)}")
    print(f"Temple Darshan Slots: {len(all_darshan_records)}")
    print(f"================================================================================")

if __name__ == '__main__':
    run_phase3_all_india_import()
