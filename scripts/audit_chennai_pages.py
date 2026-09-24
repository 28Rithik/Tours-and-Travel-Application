import json
import re
import sys
import urllib.request
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

with open('scripts/scraped_chennai_packages.json', 'r', encoding='utf-8') as f:
    packages = json.load(f)

print(f"Total existing packages in JSON: {len(packages)}")

def check_page_options(p):
    url = p['url'].split('#')[0]
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(' ', strip=True)
        itins = re.findall(r'(?:Tour\s+Itinerary|Itinerary\s+Option)\s*:\s*(\d+\s*Nights?\s*/\s*\d+\s*Days?)', text, re.IGNORECASE)
        day1s = len(re.findall(r'\bDay\s*1\s*[:\-\u2013\u2014]', text, re.IGNORECASE))
        tables = len(soup.find_all('table'))
        return {
            'url': url,
            'title': p['title'],
            'itins': itins,
            'day1s': day1s,
            'tables': tables,
            'json_days': p.get('days', 1),
            'json_plan_len': len(p.get('days_plan', []))
        }
    except Exception as e:
        return {'url': url, 'error': str(e)}

print("Auditing all 126 pages for multi-itinerary, embedded tables, and day count discrepancies...")
results = []
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(check_page_options, p) for p in packages]
    for fut in as_completed(futures):
        res = fut.result()
        if 'error' not in res:
            results.append(res)

multi_itins = [r for r in results if len(r['itins']) > 1]
print(f"\n--- Multi-Itinerary Pages Found: {len(multi_itins)} ---")
for m in multi_itins:
    print(f"  {m['title'][:45]}: {len(m['itins'])} itineraries -> {m['itins']} | URL: {m['url']}")

multi_day1 = [r for r in results if r['day1s'] > 1 and len(r['itins']) <= 1]
print(f"\n--- Pages with multiple 'Day 1' but no 'Tour Itinerary' tag: {len(multi_day1)} ---")
for m in multi_day1:
    print(f"  {m['title'][:45]}: {m['day1s']} Day 1 occurrences | URL: {m['url']}")

table_pages = [r for r in results if r['tables'] >= 3]
print(f"\n--- Pages with 3+ tables: {len(table_pages)} ---")
for t in table_pages:
    print(f"  {t['title'][:45]}: {t['tables']} tables | URL: {t['url']}")
