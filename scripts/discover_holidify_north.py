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

north_keys = [
    'himachal', 'shimla', 'manali', 'dharamshala', 'dalhousie', 'kasol', 'spiti', 'kullu', 'kaza',
    'uttarakhand', 'rishikesh', 'haridwar', 'mussoorie', 'nainital', 'auli', 'kedarnath', 'badrinath', 'corbett', 'dehradun',
    'kashmir', 'srinagar', 'gulmarg', 'pahalgam', 'ladakh', 'leh',
    'rajasthan', 'jaipur', 'udaipur', 'jodhpur', 'jaisalmer', 'pushkar', 'mount-abu', 'ranthambore',
    'delhi', 'agra', 'golden-triangle', 'varanasi', 'kashi', 'ayodhya', 'mathura', 'amritsar', 'north-india',
    'kinnaur', 'kufri', 'mcleodganj', 'tirthan', 'khajjiar', 'bir-billing', 'taj-mahal', 'char-dham'
]

north_listings = []
for u in all_listing_urls:
    u_lower = u.lower()
    if any(k in u_lower for k in north_keys):
        north_listings.append(u)

# Add all 40 pages of region/north-india/packages.html
for p in range(40):
    north_listings.append(f'https://www.holidify.com/region/north-india/packages.html?pageNum={p}')

north_listings = list(dict.fromkeys(north_listings))
print(f"Total North India listing pages to crawl: {len(north_listings)}")

def fetch_links(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        links = ['https://www.holidify.com' + a['href'] if a['href'].startswith('/') else a['href'] 
                 for a in soup.find_all('a', href=True) if '/tour-package/' in a['href']]
        return links
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

all_pkg_links = set()
with ThreadPoolExecutor(max_workers=12) as ex:
    for result in ex.map(fetch_links, north_listings):
        for l in result:
            all_pkg_links.add(l)

north_urls = sorted(list(all_pkg_links))
print(f"Total unique North India package detail links: {len(north_urls)}")

out_path = os.path.join(WORKSPACE_ROOT, 'scripts', 'holidify_north_urls.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(north_urls, f, indent=2)
print(f"Saved to {out_path}")
