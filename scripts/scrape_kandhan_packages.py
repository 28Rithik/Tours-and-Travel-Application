import urllib.request
import re
import sys
import json
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

INTL_PAGES = [
    ('australia.html', 'Australia', 'AUD'),
    ('bali.html', 'Bali, Indonesia', 'IDR'),
    ('bhutan.html', 'Bhutan', 'INR'),
    ('cambodia.html', 'Cambodia', 'USD'),
    ('china.html', 'China', 'CNY'),
    ('denmark.html', 'Denmark', 'EUR'),
    ('dubai.html', 'Dubai, UAE', 'AED'),
    ('europe.html', 'Europe (Multi-Country)', 'EUR'),
    ('france.html', 'France', 'EUR'),
    ('georgia.html', 'Georgia', 'USD'),
    ('hong-kong.html', 'Hong Kong', 'HKD'),
    ('israel.html', 'Israel', 'USD'),
    ('japan.html', 'Japan', 'JPY'),
    ('kenya.html', 'Kenya', 'USD'),
    ('malaysia.html', 'Malaysia', 'MYR'),
    ('maldives.html', 'Maldives', 'USD'),
    ('mauritius.html', 'Mauritius', 'MUR'),
    ('nepal.html', 'Nepal', 'INR'),
    ('norway.html', 'Norway', 'EUR'),
    ('singapore.html', 'Singapore', 'SGD'),
    ('south-korea.html', 'South Korea', 'KRW'),
    ('sri-lanka.html', 'Sri Lanka', 'LKR'),
    ('sweden.html', 'Sweden', 'EUR'),
    ('switzerland.html', 'Switzerland', 'EUR'),
    ('thailand.html', 'Thailand', 'THB'),
    ('turkey.html', 'Turkey', 'USD'),
    ('united-kingdom.html', 'United Kingdom', 'GBP'),
    ('usa.html', 'United States of America', 'USD'),
    ('vietnam.html', 'Vietnam', 'USD'),
]

DEV_PAGES = [
    ('devotional-packages.html', 'Tamil Nadu Sacred Pilgrimage Circuits'),
    ('devotion.html', 'Sabarimalai, Srirangam & Srivilliputhur Divya Desam Yatra'),
    ('madurai.html', 'Madurai Meenakshi Amman Temple Heritage Circuit'),
    ('kanyakumari.html', 'Kanyakumari Cape Comorin & Rameshwaram Theertham Yatra'),
    ('mahabalipuram.html', 'Mahabalipuram Shore Temple & Coastal Heritage Tour'),
    ('tanjore.html', 'Thanjavur Brihadeeswarar Big Temple Chola Heritage Tour'),
    ('velankanni.html', 'Velankanni Basilica of Our Lady of Good Health Pilgrimage'),
]

def clean_rebrand(text):
    if not text:
        return ""
    replacements = [
        (re.compile(r'Kandhan\s+Travels', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'kandhantravels\.com', re.IGNORECASE), 'sivagayathritravels.com'),
        (re.compile(r'booking@kandhantravels\.com', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'info@kandhantravels\.com', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'\+91[\s\d-]{9,15}'), '+91 98425 33777'),
        (re.compile(r'9500076953'), '9842533777'),
        (re.compile(r'Mettupalayam', re.IGNORECASE), 'Coimbatore & Chennai'),
    ]
    cleaned = text
    for pattern, repl in replacements:
        cleaned = pattern.sub(repl, cleaned)
    return cleaned.strip()

def scrape_intl_page(page_info):
    filename, country, curr = page_info
    url = f'https://www.kandhantravels.com/{filename}'
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=12).read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        for el in soup.find_all(['header', 'footer', 'nav', 'script', 'style']):
            el.decompose()

        # Title
        raw_title = ""
        h3 = soup.find('h3')
        if h3 and len(h3.get_text(strip=True)) > 5:
            raw_title = h3.get_text(strip=True)
        else:
            h2 = soup.find('h2')
            raw_title = h2.get_text(strip=True) if h2 else f"{country} Tour Package"

        # Check if title was accidentally Turkey in Thailand
        if filename == 'thailand.html' and 'turkey' in raw_title.lower():
            raw_title = "6-Day Thailand Extravaganza: Bangkok, Pattaya & Coral Island"

        title = clean_rebrand(raw_title).upper()

        # Days Plan
        days_plan = []
        seen_days = set()
        
        # Look for Day 1: ... paragraphs
        for p in soup.find_all('p'):
            txt = p.get_text(strip=True)
            # Match "Day 1: Arrival in ..." or "Day 01 - ..."
            m = re.match(r'^Day\s*(\d+)[\s:–-]+(.*)', txt, re.IGNORECASE)
            if m:
                d_num = int(m.group(1))
                if d_num in seen_days:
                    continue
                seen_days.add(d_num)
                rest = m.group(2).strip()
                # Split title from detail if there's an en-dash or colon
                parts = re.split(r'[:–-]', rest, maxsplit=1)
                day_title = f"Day {d_num}: {parts[0].strip()}"
                day_spots = parts[1].strip() if len(parts) > 1 else rest
                days_plan.append({
                    'day': d_num,
                    'title': clean_rebrand(day_title),
                    'spots': clean_rebrand(day_spots if len(day_spots) > 10 else day_title)
                })

        days_plan.sort(key=lambda x: x['day'])
        
        # If no explicit Day paragraphs found, check list items
        if not days_plan:
            for li in soup.find_all('li'):
                txt = li.get_text(strip=True)
                m = re.match(r'^Day\s*(\d+)[\s:–-]+(.*)', txt, re.IGNORECASE)
                if m:
                    d_num = int(m.group(1))
                    if d_num in seen_days:
                        continue
                    seen_days.add(d_num)
                    rest = m.group(2).strip()
                    parts = re.split(r'[:–-]', rest, maxsplit=1)
                    days_plan.append({
                        'day': d_num,
                        'title': clean_rebrand(f"Day {d_num}: {parts[0].strip()}"),
                        'spots': clean_rebrand(parts[1].strip() if len(parts) > 1 else rest)
                    })
            days_plan.sort(key=lambda x: x['day'])

        # Determine days from title or days_plan
        dur_match = re.search(r'(\d+)[\s-]*Day', title, re.IGNORECASE)
        days = int(dur_match.group(1)) if dur_match else max(1, len(days_plan))
        days = max(days, len(days_plan))
        nights = max(0, days - 1)

        # If days_plan is shorter than days, generate standard days
        if len(days_plan) < days:
            for d in range(len(days_plan) + 1, days + 1):
                days_plan.append({
                    'day': d,
                    'title': f"Day {d}: Sightseeing & Cultural Wonders of {country}",
                    'spots': f"Guided city tours, iconic landmark visits, shopping, and leisure exploration across {country}."
                })

        # Description
        desc_paras = [clean_rebrand(p.get_text(strip=True)) for p in soup.find_all('p') if len(p.get_text(strip=True)) > 40 and not p.get_text(strip=True).startswith('Day ')]
        description = "\n\n".join(desc_paras[:3]) if desc_paras else f"Experience the best of {country} with this exclusive {days} Days / {nights} Nights international tour package."

        return {
            'type': 'international',
            'url': url,
            'filename': filename,
            'title': title,
            'country': country,
            'currency': curr,
            'days': days,
            'nights': nights,
            'days_plan': days_plan,
            'description': description,
            'price': days * 8500  # realistic international package baseline
        }
    except Exception as e:
        print(f"Error scraping {filename}: {e}")
        return None

def main():
    print(f"Scraping {len(INTL_PAGES)} International Package pages from kandhantravels.com...")
    intl_results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(scrape_intl_page, info) for info in INTL_PAGES]
        for f in as_completed(futures):
            res = f.result()
            if res:
                intl_results.append(res)
                print(f"  [INTL] {res['title'][:50]} ({res['nights']}N/{res['days']}D, {len(res['days_plan'])} days plan)")

    print(f"\nSuccessfully scraped {len(intl_results)} international packages!")
    
    out_file = 'scripts/scraped_kandhan_packages.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(intl_results, f, indent=2, ensure_ascii=False)
    print(f"Saved to {out_file}")

if __name__ == '__main__':
    main()
