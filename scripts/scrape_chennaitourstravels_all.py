import urllib.request
import ssl
import sys
from bs4 import BeautifulSoup
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

with open('scripts/chennaitourstravels_tour_urls.json', 'r', encoding='utf-8') as f:
    urls = json.load(f)

# Filter out map pages or non-tour pages
target_urls = []
for u in urls:
    slug = u.split('/')[-1].lower()
    if any(k in slug for k in ['map-of', 'tariff', 'book_tour', 'index11']):
        continue
    target_urls.append(u)

print(f"Targeting {len(target_urls)} tour pages for crawling...")

def parse_page(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove scripts, styles
            for s in soup(['script', 'style', 'noscript']):
                s.decompose()

            page_title = soup.title.string.strip() if soup.title else url.split('/')[-1]
            slug = url.split('/')[-1].replace('.php', '').replace('.html', '')

            # Extract headings
            headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'strong']) if len(h.get_text(strip=True)) > 3]

            # Look for Day 1, Day 2, Day 01, Day 02
            paras = [p.get_text(strip=True) for p in soup.find_all(['p', 'li', 'td']) if len(p.get_text(strip=True)) > 15]

            # Extract day items
            days_plan = []
            for p in paras:
                if re.match(r'^Day\s*\d+\s*:', p, re.IGNORECASE) or 'day 0' in p.lower() or 'day 1' in p.lower():
                    # Split if multiple days in same paragraph
                    sub_days = re.split(r'(?=Day\s*\d+\s*:)', p, flags=re.IGNORECASE)
                    for sd in sub_days:
                        sd = sd.strip()
                        if len(sd) > 10:
                            m_d = re.match(r'^Day\s*(\d+)\s*:\s*(.*)', sd, re.IGNORECASE)
                            if m_d:
                                d_num = int(m_d.group(1))
                                d_txt = m_d.group(2).strip()
                            else:
                                d_num = len(days_plan) + 1
                                d_txt = sd
                            days_plan.append({'day': d_num, 'activities': d_txt})

            # Check for price
            price = 0
            price_match = re.search(r'(?:Rs|₹|INR)[:.\s]*([0-9,]+)', ' '.join(paras), re.IGNORECASE)
            if price_match:
                try:
                    price = float(price_match.group(1).replace(',', ''))
                except:
                    price = 0

            # Check duration
            days = len(days_plan)
            dur_match = re.search(r'(\d+)\s*(?:Nights?|N)\s*[/-]?\s*(\d+)\s*(?:Days?|D)', ' '.join(headings + paras), re.IGNORECASE)
            if dur_match:
                nights = int(dur_match.group(1))
                days = int(dur_match.group(2))
            else:
                dur_match2 = re.search(r'(\d+)\s*Days?', ' '.join(headings + paras), re.IGNORECASE)
                if dur_match2:
                    days = int(dur_match2.group(1))
                    nights = max(0, days - 1)
                else:
                    nights = max(0, days - 1) if days > 0 else 1
                    days = max(1, days)

            # Extract clean main content summary
            main_text = ' '.join(paras[:10])

            return {
                'url': url,
                'slug': slug,
                'title': page_title,
                'headings': headings[:10],
                'days_plan': days_plan,
                'days': days,
                'nights': nights,
                'price': price,
                'content_summary': main_text[:1000]
            }
    except Exception as e:
        return {'url': url, 'error': str(e)}

results = []
errors = 0
with ThreadPoolExecutor(max_workers=10) as executor:
    future_to_url = {executor.submit(parse_page, u): u for u in target_urls}
    for future in as_completed(future_to_url):
        res = future.result()
        if 'error' in res:
            errors += 1
            print(f"  [ERR] {res['url']}: {res['error']}")
        else:
            results.append(res)
            print(f"  [{len(results)}/{len(target_urls)}] {res['slug']} — {res['nights']}N/{res['days']}D, {len(res['days_plan'])} itinerary days, Price: ₹{res['price']}")

print(f"\nCrawling complete: {len(results)} pages parsed successfully, {errors} errors.")
with open('scripts/crawled_chennaitourstravels_packages.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("Saved all crawled data to scripts/crawled_chennaitourstravels_packages.json!")
