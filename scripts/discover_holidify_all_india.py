import os
import sys
import re
import json
import urllib.request
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
urls_file = os.path.join(WORKSPACE_ROOT, 'scripts', 'holidify_package_urls.json')
all_listing_urls = json.load(open(urls_file, encoding='utf-8'))

# International keywords to exclude
intl_keys = [
    'dubai', 'singapore', 'malaysia', 'thailand', 'bangkok', 'pattaya', 'phuket', 'bali', 'indonesia', 'vietnam', 'cambodia',
    'maldives', 'mauritius', 'seychelles', 'sri-lanka', 'bhutan', 'nepal', 'europe', 'switzerland', 'paris', 'london', 'africa',
    'cape-town', 'kenya', 'turkey', 'greece', 'egypt', 'baku', 'georgia', 'almaty', 'international', 'france', 'rome', 'santorini',
    'mykonos', 'sydney', 'venice', 'tanzania', 'istanbul', 'krabi', 'hajj', 'umrah'
]

india_listings = []
for u in all_listing_urls:
    u_lower = u.lower()
    if not any(k in u_lower for k in intl_keys):
        india_listings.append(u)

# Add all 80 pages of country/india/packages.html
for p in range(80):
    india_listings.append(f'https://www.holidify.com/country/india/packages.html?pageNum={p}')

india_listings = list(dict.fromkeys(india_listings))
print(f"Total Pan-India listing pages to crawl: {len(india_listings)}")

def fetch_links(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        links = ['https://www.holidify.com' + a['href'] if a['href'].startswith('/') else a['href'] 
                 for a in soup.find_all('a', href=True) if '/tour-package/' in a['href']]
        return links
    except Exception as e:
        return []

all_pkg_links = set()
with ThreadPoolExecutor(max_workers=14) as ex:
    for result in ex.map(fetch_links, india_listings):
        for l in result:
            all_pkg_links.add(l)

india_urls = sorted(list(all_pkg_links))
print(f"Total unique All-India package detail links: {len(india_urls)}")

out_path = os.path.join(WORKSPACE_ROOT, 'scripts', 'holidify_all_india_urls.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(india_urls, f, indent=2)
print(f"Saved to {out_path}")
