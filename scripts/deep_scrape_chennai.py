import urllib.request
import sys
import re
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

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

def clean_title_str(t):
    t = clean_rebrand(t)
    t = re.sub(r'[\u2013\u2014\-–|:].*?(?:Secrets|No Driving|No Rush|Limited|Offer|Expect|Made Easy|Do It Right|Must Read|Book Now|Wonders|Bliss|Unveil|Explore Now|Revealed|Everlasting|Package Before|Simple Steps|Hidden Gems).*$', '', t, flags=re.IGNORECASE)
    t = re.sub(r'^(?:Exclusive|Explore|Discover|Unveil)\s+', '', t, flags=re.IGNORECASE)
    t = re.sub(r'from\s*(?:₹|Rs\.?)\s*[\d,]+', '', t, flags=re.IGNORECASE)
    t = re.sub(r'Starts\s*@.*', '', t, flags=re.IGNORECASE)
    t = re.sub(r'-\s*Siva\s+Gayathri\s+Tours\s*(?:&|and)?\s*Travels', '', t, flags=re.IGNORECASE)
    t = re.sub(r'[\u2013\u2014–]+', '-', t)
    t = ' '.join(t.split()).strip(' -:')
    return t.upper()

def extract_daily_tours_page():
    """Extracts all 16 standalone 1-day tours from daily-tours.html with their vehicle rates."""
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
        clean_name = re.sub(r'Cost:.*$', '', h_text, flags=re.IGNORECASE).strip()
        clean_name = clean_title_str(clean_name)
        if not clean_name.endswith('TOUR') and not clean_name.endswith('PACKAGE'):
            clean_name = f"{clean_name} TOUR PACKAGE"

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
                    if 'dzire' in h or 'etios' in h:
                        sedan_price = val
                    elif 'innova' in h:
                        innova_price = val

        # Find itinerary paragraph or spots
        prev_p = tab.find_previous('p')
        spots_text = prev_p.get_text(strip=True) if prev_p and len(prev_p.get_text(strip=True)) > 20 else clean_name

        packages.append({
            'url': f"{url}#tour-{idx}",
            'title': f"1-DAY {clean_name}",
            'days': 1,
            'nights': 0,
            'price': sedan_price,
            'sedan_price': sedan_price,
            'innova_price': innova_price,
            'days_plan': [{
                'day': 1,
                'title': f"Day 1: Full Day Sightseeing & Tour",
                'spots': spots_text
            }],
            'description': f"1-Day dedicated tour covering {clean_name}. Sightseeing attractions: {spots_text}"
        })

    print(f"Extracted {len(packages)} standalone daily tour packages from daily-tours.html")
    return packages

def parse_multi_option_page(url, soup, title):
    """Splits pages with multiple distinct itineraries into separate packages."""
    full_text = soup.get_text()
    itinerary_blocks = []
    
    # Split by "Tour Itinerary: X Night / Y Days"
    pattern = re.compile(r'(?:Tour\s+Itinerary|Itinerary\s+Option)\s*:\s*(\d+)\s*Nights?\s*/\s*(\d+)\s*Days?', re.IGNORECASE)
    matches = list(pattern.finditer(full_text))

    if len(matches) > 1:
        # Multi-option found!
        for i, m in enumerate(matches):
            n_nights = int(m.group(1))
            n_days = int(m.group(2))
            start_pos = m.end()
            end_pos = matches[i+1].start() if i+1 < len(matches) else len(full_text)
            block_text = full_text[start_pos:end_pos]
            
            # Extract day items from block
            day_matches = re.findall(r'(Day\s*\d+[^:\n]*[:\-\u2013\u2014]\s*([^\n\r]+))', block_text, re.IGNORECASE)
            days_plan = []
            for d_idx, (full_day_title, spot_desc) in enumerate(day_matches, 1):
                days_plan.append({
                    'day': d_idx,
                    'title': clean_rebrand(full_day_title.strip()),
                    'spots': clean_rebrand(spot_desc.strip())
                })
            
            actual_days = max(n_days, len(days_plan))
            itinerary_blocks.append({
                'url': f"{url}#option-{i+1}",
                'title': f"{clean_title_str(title)} (OPTION {i+1} - {n_nights}N/{actual_days}D)",
                'days': actual_days,
                'nights': n_nights,
                'price': actual_days * 2100,
                'days_plan': days_plan if days_plan else [{
                    'day': d,
                    'title': f"Day {d}: Sightseeing & Sacred Shrines",
                    'spots': title
                } for d in range(1, actual_days + 1)],
                'description': f"Comprehensive {n_nights} Nights / {actual_days} Days tour plan covering {title}."
            })

    return itinerary_blocks

if __name__ == '__main__':
    tours = extract_daily_tours_page()
    for t in tours[:5]:
        print(" ", t['title'], "| Price:", t['price'])
