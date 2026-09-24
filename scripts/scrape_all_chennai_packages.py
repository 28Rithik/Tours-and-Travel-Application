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

EXCLUDE_PATTERNS = [
    '-rental', 'car-travels', 'b2b-', 'privacy-policy', 'import-module',
    'payment-confirmation', 'attach-vehicles', 'airport-tariff', 'contact-',
    'film-production', 'monthly-car', 'corporate-car'
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

def extract_package(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return None, f"Fetch error: {e}"

    soup = BeautifulSoup(html, 'html.parser')

    for el in soup.find_all(['header', 'footer', 'nav', 'script', 'style', 'noscript']):
        el.decompose()

    # Title: Try meta og:title, title tag, or h1/h2
    raw_title = ""
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content'):
        raw_title = og_title['content'].split('|')[0].split(':')[0].strip()
    elif soup.title:
        raw_title = soup.title.string.split('|')[0].split(':')[0].strip()
    else:
        h1 = soup.find('h1')
        raw_title = h1.get_text(strip=True) if h1 else url.rstrip('.html').split('/')[-1].replace('-', ' ').title()

    title = clean_rebrand(raw_title)

    # Determine Duration (Days & Nights)
    days = 1
    nights = 0
    full_text = soup.get_text(' ', strip=True)

    # Look for "X Days / Y Nights" or "X Day / Y Night"
    dur_match = re.search(r'(\d+)\s*Days?\s*/\s*(\d+)\s*Nights?', full_text, re.IGNORECASE)
    if dur_match:
        days = int(dur_match.group(1))
        nights = int(dur_match.group(2))
    else:
        dur_match2 = re.search(r'(\d+)\s*Nights?\s*/\s*(\d+)\s*Days?', full_text, re.IGNORECASE)
        if dur_match2:
            nights = int(dur_match2.group(1))
            days = int(dur_match2.group(2))
        else:
            # Check for "2 Days", "3 Days", "1 Day", "One Day" in title or URL
            num_match = re.search(r'(\d+)\s*Day', title + ' ' + url, re.IGNORECASE)
            if num_match:
                days = int(num_match.group(1))
                nights = max(0, days - 1)
            elif 'one day' in (title + ' ' + url).lower() or 'day tour' in (title + ' ' + url).lower():
                days = 1
                nights = 0

    # Extract Price / Tariffs from tables or text
    price = 0
    price_match = re.search(r'(?:₹|Rs\.?)\s*([\d,]+)', full_text)
    if price_match:
        val_str = price_match.group(1).replace(',', '')
        if val_str.isdigit():
            val = int(val_str)
            if 1000 <= val <= 250000:
                price = val

    # Extract Itinerary Days
    # Check if there are Day 1, Day 2 headings
    days_plan = []
    day_headings = soup.find_all(lambda tag: tag.name in ['h2', 'h3', 'h4', 'strong', 'b'] and re.search(r'Day\s*\d+', tag.text, re.IGNORECASE))
    
    if day_headings:
        for idx, dh in enumerate(day_headings, 1):
            dh_text = clean_rebrand(dh.get_text(strip=True))
            # Collect following sibling tags until next day heading
            spots = []
            curr = dh.find_next_sibling()
            while curr and not (curr.name in ['h2', 'h3', 'h4'] and re.search(r'Day\s*\d+', curr.text, re.IGNORECASE)):
                if curr.name in ['h3', 'h4', 'li', 'p']:
                    ct = clean_rebrand(curr.get_text(strip=True))
                    if 5 < len(ct) < 180 and not any(k in ct.lower() for k in ['trip tip', 'reserve', 'we plan', 'enquiry']):
                        spots.append(ct)
                curr = curr.find_next_sibling()

            spot_summary = ", ".join(spots[:8]) if spots else dh_text
            days_plan.append({
                'day': idx,
                'title': dh_text,
                'spots': spot_summary
            })

    # If no explicit Day 1/2 headings found, look for attraction H3s or list items
    if not days_plan:
        attractions = []
        for h3 in soup.find_all(['h3', 'li']):
            ht = clean_rebrand(h3.get_text(strip=True))
            if 5 < len(ht) < 100 and not any(k in ht.lower() for k in ['trip tip', 'reserve', 'we plan', 'enquiry', 'worry-free', 'reconnect', 'memories', 'why choose', 'advantage', 'price']):
                attractions.append(ht)

        if attractions:
            # Distribute attractions across days
            chunk_size = max(1, len(attractions) // days)
            for d in range(1, days + 1):
                chunk = attractions[(d-1)*chunk_size : d*chunk_size]
                days_plan.append({
                    'day': d,
                    'title': f"Day {d} - Sightseeing & Temple Visits",
                    'spots': ", ".join(chunk[:6]) if chunk else title
                })
        else:
            for d in range(1, days + 1):
                days_plan.append({
                    'day': d,
                    'title': f"Day {d} - {title}",
                    'spots': title
                })

    # Description
    desc_paras = []
    for p in soup.find_all('p'):
        pt = clean_rebrand(p.get_text(strip=True))
        if len(pt) > 50 and not any(k in pt.lower() for k in ['cookie', 'all rights', 'copyright']):
            desc_paras.append(pt)

    return {
        'url': url,
        'title': title,
        'days': days,
        'nights': nights,
        'price': price,
        'days_plan': days_plan,
        'description': "\n\n".join(desc_paras[:4])
    }, None

def main():
    sitemap_url = 'https://www.chennaitravels.in/page-sitemap.xml'
    req = urllib.request.Request(sitemap_url, headers=HEADERS)
    root = ET.fromstring(urllib.request.urlopen(req, timeout=15).read())
    all_urls = [elem.text for elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]

    candidate_urls = []
    for u in all_urls:
        u_low = u.lower()
        if any(ex in u_low for ex in EXCLUDE_PATTERNS):
            continue
        if any(k in u_low for k in ['package', 'tour', 'sightseeing', 'yatra', 'darshan']):
            candidate_urls.append(u)

    print(f"Total candidate package URLs to scrape: {len(candidate_urls)}")

    results = []
    errors = 0

    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_url = {executor.submit(extract_package, u): u for u in candidate_urls}
        for future in as_completed(future_to_url):
            data, err = future.result()
            if data:
                results.append(data)
                print(f"  [OK] {data['title'][:55]} ({data['nights']}N/{data['days']}D, {len(data['days_plan'])} days)")
            else:
                errors += 1

    print(f"\nScraping complete: {len(results)} scraped successfully, {errors} errors.")
    out_file = 'scripts/scraped_chennai_packages.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Saved all scraped packages to {out_file}")

if __name__ == '__main__':
    main()
