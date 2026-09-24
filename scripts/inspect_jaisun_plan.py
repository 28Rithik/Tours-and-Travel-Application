import urllib.request
from bs4 import BeautifulSoup
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

for test_url in [
    'https://www.jaisuntourism.com/char-dham-yatra-tour-package-from-coimbatore/',
    'https://www.jaisuntourism.com/dubai-tour-package-from-coimbatore/',
    'https://www.jaisuntourism.com/switzerland-tour-package-from-coimbatore/'
]:
    req = urllib.request.Request(test_url, headers=HEADERS)
    soup = BeautifulSoup(urllib.request.urlopen(req, timeout=12).read().decode('utf-8', errors='ignore'), 'html.parser')
    plan_div = soup.find(class_='gotur-accordion') or soup.find(class_='faq-accordion')
    print(f"\n=== {test_url.split('/')[-2]} ===")
    if plan_div:
        items = plan_div.find_all(class_='accordion')
        print(f"Accordion items count: {len(items)}")
        for idx, item in enumerate(items[:3], 1):
            h = item.find(class_='accordion-title__text')
            c = item.find(class_='accordion-content')
            print(f"  Day {idx}: {h.get_text(strip=True) if h else 'No Title'}")
            print(f"    Body: {c.get_text(strip=True)[:100] if c else 'No Content'}")

# Check Inclusions
print("\n--- INCLUSIONS ---")
inc_h = soup.find(lambda t: t.name in ['h2', 'h3', 'h4', 'h5'] and 'inclusion' in t.text.lower())
if inc_h:
    print('Inc Heading:', inc_h.get_text())
    inc_parent = inc_h.find_parent(['section', 'div'])
    for li in inc_parent.find_all(['li', 'p']):
        t = li.get_text(strip=True)
        if len(t) > 5 and not any(ex in t.lower() for ex in ['inclusion', 'overview', 'plan']):
            print('  *', t[:100])

# Check Price / Cost
print("\n--- PRICE / COST ---")
price_matches = re.findall(r'(?:₹|Rs\.?)\s*[\d,]+', soup.get_text())
print('Prices found in page:', price_matches[:5])
