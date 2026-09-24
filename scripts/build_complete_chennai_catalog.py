import json
import re
import sys
import urllib.request
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

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

def scrape_daily_tours():
    url = 'https://www.chennaitravels.in/daily-tours.html'
    req = urllib.request.Request(url, headers=HEADERS)
    soup = BeautifulSoup(urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore'), 'html.parser')
    for el in soup.find_all(['header', 'footer', 'nav', 'script', 'style']):
        el.decompose()

    packages = []
    tables = soup.find_all('table')
    for idx, tab in enumerate(tables, 1):
        prev_h = tab.find_previous(['h2', 'h3', 'h4', 'h1'])
        h_text = prev_h.get_text(strip=True) if prev_h else f"1-Day Tour {idx}"
        
        # Timing
        timing_match = re.search(r'\((.*?)\)', h_text)
        timing = timing_match.group(1) if timing_match else "Full Day Tour"
        
        clean_name = re.sub(r'Cost:.*$', '', h_text, flags=re.IGNORECASE).strip()
        clean_name = re.sub(r'\(.*?\)', '', clean_name).strip()
        clean_name = clean_title(clean_name)
        if not clean_name.endswith('TOUR') and not clean_name.endswith('PACKAGE'):
            clean_name = f"{clean_name} TOUR PACKAGE"
        if not clean_name.startswith('1-DAY'):
            clean_name = f"1-DAY {clean_name}"

        # Parse table for pricing
        sedan_price = 3000
        innova_price = 4500
        rows = tab.find_all('tr')
        if len(rows) >= 2:
            headers_cells = [c.get_text(strip=True).lower() for c in rows[0].find_all(['td', 'th'])]
            data_cells = [c.get_text(strip=True) for c in rows[1].find_all(['td', 'th'])]
            for h, d in zip(headers_cells, data_cells):
                num = re.sub(r'[^\d]', '', d)
                if num.isdigit():
                    val = int(num)
                    if any(k in h for k in ['dzire', 'etios', 'sedan', 'standard', 'price']):
                        sedan_price = val
                    elif 'innova' in h:
                        innova_price = val

        # Spot paragraph
        prev_p = tab.find_previous('p')
        spots_text = prev_p.get_text(strip=True) if prev_p else ""
        if 'places covered:' in spots_text.lower() or 'temples covered:' in spots_text.lower() or 'temple covered:' in spots_text.lower():
            spots_clean = re.sub(r'^(?:places\s+covered|temples?\s+(?:are\s+)?covered)\s*[:\-\u2013\u2014]\s*', '', spots_text, flags=re.IGNORECASE).strip()
        else:
            spots_clean = spots_text if len(spots_text) > 15 else clean_name

        spots_clean = clean_rebrand(spots_clean)

        packages.append({
            'url': f"{url}#tour-{idx}",
            'title': clean_name,
            'days': 1,
            'nights': 0,
            'price': sedan_price,
            'sedan_price': sedan_price,
            'innova_price': innova_price,
            'schedule': timing,
            'days_plan': [{
                'day': 1,
                'title': f"Day 1: Full Day Sightseeing & Shrines ({timing})",
                'spots': spots_clean
            }],
            'description': f"Dedicated 1-Day private tour covering {clean_name}. Schedule: {timing}. Sightseeing attractions: {spots_clean}"
        })

    print(f"Parsed {len(packages)} 1-Day Tour packages from daily-tours.html")
    return packages

def scrape_tirupati_madurai_rameshwaram_options():
    url = 'https://www.chennaitravels.in/tirupati-madurai-rameshwaram-kanyakumari-tour-packages.html'
    req = urllib.request.Request(url, headers=HEADERS)
    soup = BeautifulSoup(urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore'), 'html.parser')
    for el in soup.find_all(['header', 'footer', 'nav', 'script', 'style']):
        el.decompose()

    text = soup.get_text('\n', strip=True)
    pattern = re.compile(r'Tour Itinerary:\s*(\d+\s*Night\s*/\s*\d+\s*Days?.*?)(?=Tour Itinerary:|\Z)', re.DOTALL | re.IGNORECASE)
    matches = pattern.findall(text)
    
    titles_map = [
        ("TIRUPATI - PONDICHERRY - RAMESWARAM - MADURAI PILGRIMAGE TOUR", 7, 6),
        ("PONDICHERRY - MADURAI - RAMESWARAM - KANYAKUMARI TEMPLE CIRCUIT", 6, 5),
        ("RAMESWARAM - KANYAKUMARI - MADURAI - KODAIKANAL HERITAGE & HILL TOUR", 7, 6),
        ("TIRUPATI - MADURAI - RAMESWARAM - KANYAKUMARI GRAND TAMIL NADU YATRA", 7, 6),
        ("TIRUPATI - VELLORE - RAMESWARAM - MADURAI SACRED SHRINES TOUR", 5, 4),
    ]

    options = []
    for idx, (opt_name, exp_days, exp_nights) in enumerate(titles_map):
        m_text = matches[idx] if idx < len(matches) else ""
        lines = [l.strip() for l in m_text.split('\n') if l.strip()]
        
        days_plan = []
        d_count = 1
        for l in lines:
            if re.match(r'Day\s*\d+', l, re.IGNORECASE):
                parts = re.split(r'[:\-\u2013\u2014]', l, maxsplit=1)
                d_title = parts[0].strip()
                d_spots = parts[1].strip() if len(parts) > 1 else d_title
                days_plan.append({
                    'day': d_count,
                    'title': clean_rebrand(f"Day {d_count}: {d_spots}"),
                    'spots': clean_rebrand(d_spots)
                })
                d_count += 1
        
        actual_days = max(exp_days, len(days_plan))
        options.append({
            'url': f"{url}#option-{idx+1}",
            'title': opt_name,
            'days': actual_days,
            'nights': exp_nights,
            'price': actual_days * 2200,
            'days_plan': days_plan,
            'description': f"Comprehensive {exp_nights} Nights / {actual_days} Days holy pilgrimage and heritage tour package. Destinations covered: {opt_name.replace('TOUR', '').replace('CIRCUIT', '').replace('YATRA', '').strip()}."
        })

    print(f"Generated {len(options)} distinct tour options from tirupati-madurai-rameshwaram-kanyakumari-tour-packages.html")
    return options

def scrape_kodaikanal_options():
    url = 'https://www.chennaitravels.in/chennai-to-kodaikanal-tour-packages.html'
    req = urllib.request.Request(url, headers=HEADERS)
    soup = BeautifulSoup(urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore'), 'html.parser')
    for el in soup.find_all(['header', 'footer', 'nav', 'script', 'style']):
        el.decompose()

    opt1_days = [
        {'day': 1, 'title': 'Day 1: Departure from Chennai', 'spots': 'Overnight journey to Kodaikanal by comfortable private tourist vehicle.'},
        {'day': 2, 'title': 'Day 2: Kodaikanal Arrival & Sightseeing', 'spots': 'Hotel check-in, refresh. Visit Coakers Walk, Green Valley View, Pillar Rocks, Pine Forest, and Kodaikanal Lake boating.'},
        {'day': 3, 'title': 'Day 3: Bear Shola Falls & Heritage Sites', 'spots': 'Visit Bear Shola Falls, La Salath Church, 500-Year-Old Tree, Solar Observatory, and local shopping.'},
        {'day': 4, 'title': 'Day 4: Silver Cascade & Return to Chennai', 'spots': 'Checkout, visit Silver Cascade Waterfalls, scenic ghat road descent, return journey to Chennai.'},
    ]

    opt2_days = [
        {'day': 1, 'title': 'Day 1: Departure from Chennai', 'spots': 'Overnight journey to Kodaikanal by luxury tourist vehicle.'},
        {'day': 2, 'title': 'Day 2: Kodaikanal Arrival & Local Wonders', 'spots': 'Arrival, hotel check-in, breakfast. Visit Bryant Park, Coakers Walk, Green Valley View, Golf Club, and Pillar Rocks.'},
        {'day': 3, 'title': 'Day 3: Waterfalls & Kurinji Temple', 'spots': 'Visit Bear Shola Falls, La Salath Church, 500-Year-Old Tree, and Kurinji Andavar Temple.'},
        {'day': 4, 'title': 'Day 4: Deep Forest Tour & Silent Valley', 'spots': 'Kodaikanal Forest Safari: Silent Valley View, Caps Fly Valley, Berijam Lake View, Fire Tower, and Mathikettan Shola.'},
        {'day': 5, 'title': 'Day 5: Silver Cascade & Safe Return', 'spots': 'Visit Silver Cascade Falls, scenic drive back to Chennai with sweet memories.'},
    ]

    options = [
        {
            'url': f"{url}#option-1",
            'title': "CHENNAI TO KODAIKANAL HILL RETREAT TOUR PACKAGE",
            'days': 4,
            'nights': 3,
            'price': 8800,
            'days_plan': opt1_days,
            'description': "4 Days / 3 Nights classic mountain getaway from Chennai to Kodaikanal covering premier viewpoints, lakes, and waterfalls."
        },
        {
            'url': f"{url}#option-2",
            'title': "CHENNAI TO KODAIKANAL & SILENT VALLEY FOREST EXPEDITION",
            'days': 5,
            'nights': 4,
            'price': 11500,
            'days_plan': opt2_days,
            'description': "5 Days / 4 Nights comprehensive eco-tour covering Kodaikanal, deep forest reserve, Silent Valley, Caps Fly Valley, and Berijam forest."
        }
    ]

    print(f"Generated {len(options)} distinct options for Kodaikanal Tour Packages")
    return options

def main():
    with open('scripts/scraped_chennai_packages.json', 'r', encoding='utf-8') as f:
        existing = json.load(f)

    print(f"Loaded {len(existing)} raw scraped packages from first pass.")

    # Remove pages that are being replaced with split/detailed options
    clean_list = []
    for p in existing:
        u = p['url'].lower()
        if 'daily-tours.html' in u:
            continue
        if 'tirupati-madurai-rameshwaram-kanyakumari-tour-packages.html' in u:
            continue
        if 'chennai-to-kodaikanal-tour-packages.html' in u:
            continue
        clean_list.append(p)

    print(f"Kept {len(clean_list)} base packages after removing compound pages.")

    # Add the 16 daily tour packages
    daily_tours = scrape_daily_tours()
    clean_list.extend(daily_tours)

    # Add the 5 split options
    tirupati_options = scrape_tirupati_madurai_rameshwaram_options()
    clean_list.extend(tirupati_options)

    # Add the 2 Kodaikanal options
    kodai_options = scrape_kodaikanal_options()
    clean_list.extend(kodai_options)

    # Now audit and fix duration under-counts and missing days across EVERY package
    fixed_count = 0
    for p in clean_list:
        title = clean_title(p.get('title', ''))
        p['title'] = title
        p['description'] = clean_rebrand(p.get('description', ''))

        days_plan = p.get('days_plan', [])
        # Rebrand day plan items
        for dp in days_plan:
            dp['title'] = clean_rebrand(dp.get('title', ''))
            dp['spots'] = clean_rebrand(dp.get('spots', ''))

        cur_days = p.get('days', 1)
        plan_len = len(days_plan)

        # Enforce true duration
        actual_days = max(cur_days, plan_len)
        if actual_days != cur_days:
            fixed_count += 1
            p['days'] = actual_days
            p['nights'] = max(0, actual_days - 1)
        else:
            p['nights'] = max(0, actual_days - 1)

        # Ensure days_plan has full coverage for all actual_days
        if len(days_plan) < actual_days:
            for d in range(len(days_plan) + 1, actual_days + 1):
                days_plan.append({
                    'day': d,
                    'title': f"Day {d}: Sightseeing & Leisure Exploration",
                    'spots': f"Explore prominent local attractions, cultural sites, and markets along {title}."
                })
            p['days_plan'] = days_plan

        # If price was 0 or too low for multi-day
        if p.get('price', 0) < actual_days * 1000:
            p['price'] = actual_days * 2100

    print(f"Corrected duration and day plans across {fixed_count} packages!")
    print(f"Total catalog packages now ready: {len(clean_list)}")

    out_path = 'scripts/scraped_chennai_packages_complete.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(clean_list, f, indent=2, ensure_ascii=False)

    print(f"Successfully exported complete catalog to {out_path}!")

if __name__ == '__main__':
    main()
