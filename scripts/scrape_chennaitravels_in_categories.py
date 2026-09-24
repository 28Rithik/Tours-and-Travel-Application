import urllib.request
import ssl
import sys
from bs4 import BeautifulSoup
import re
import json

sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

target_pages = {
    'main_tour_packages': 'https://www.chennaitravels.in/tour-packages.html',
    'temple_tour_packages': 'https://www.chennaitravels.in/temple-tour-packages',
    'leisure_tour_packages': 'https://www.chennaitravels.in/leisure-tour-packages'
}

results = {}

for category_key, url in target_pages.items():
    print(f"\n{'='*70}\nFETCHING CATEGORY PAGE: {url}")
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all package cards or links inside this page
            package_links = []
            for a in soup.find_all('a', href=True):
                h = a['href'].strip()
                text = a.get_text(strip=True)
                if not h or h.startswith('#') or h.startswith('tel:') or h.startswith('javascript:'):
                    continue
                full_url = h if h.startswith('http') else 'https://www.chennaitravels.in/' + h.lstrip('/')
                
                # Check if it looks like a package or sub-package link
                if 'chennaitravels.in' in full_url:
                    slug = full_url.split('/')[-1]
                    if any(k in slug for k in ['tour', 'package', 'darshan', 'temple', 'honeymoon', 'hills']) or len(text) > 8:
                        if not any(k in slug for k in ['privacy', 'terms', 'contact', 'about', 'login', 'cart', 'blog']):
                            package_links.append({'title': text, 'url': full_url, 'slug': slug})
            
            # De-duplicate by url
            unique_links = {}
            for pl in package_links:
                if pl['url'] not in unique_links and pl['url'] != url:
                    unique_links[pl['url']] = pl
            
            results[category_key] = list(unique_links.values())
            print(f"Discovered {len(unique_links)} packages on {category_key}:")
            for pl in list(unique_links.values())[:10]:
                print(f"  - {pl['title'][:40]:40} | {pl['url']}")
    except Exception as e:
        print(f"Error fetching {url}: {e}")

with open('scripts/chennaitravels_category_packages.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)

print("\nSaved category packages to scripts/chennaitravels_category_packages.json")
