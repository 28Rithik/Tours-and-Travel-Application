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

start_urls = [
    'https://www.chennaitravels.in/tour-packages.html',
    'https://www.chennaitravels.in/temple-tour-packages',
    'https://www.chennaitravels.in/leisure-tour-packages',
    'https://www.chennaitravels.in/'
]

discovered_links = set()

def get_links_from_url(url):
    print(f"Fetching: {url}")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                if href.startswith('#') or href.startswith('javascript:') or href.startswith('tel:') or href.startswith('mailto:'):
                    continue
                if href.startswith('/'):
                    full = 'https://www.chennaitravels.in' + href
                elif href.startswith('http'):
                    full = href
                else:
                    full = 'https://www.chennaitravels.in/' + href
                
                # Filter for chennaitravels.in links
                if 'chennaitravels.in' in full and not any(k in full for k in ['privacy', 'terms', 'contact', 'about', 'login', 'cart', 'blog']):
                    discovered_links.add(full)
    except Exception as e:
        print(f"Error fetching {url}: {e}")

for u in start_urls:
    get_links_from_url(u)

print(f"\nTotal discovered internal links: {len(discovered_links)}")

# Filter for tour package links
tour_package_urls = []
for link in sorted(discovered_links):
    # Check if link looks like a tour package
    if any(k in link.lower() for k in ['tour', 'package', 'temple', 'leisure', 'darshan', 'honeymoon', 'hill']):
        tour_package_urls.append(link)

print(f"Total tour package URLs identified: {len(tour_package_urls)}")

with open('scripts/chennaitravels_in_tour_urls.json', 'w', encoding='utf-8') as f:
    json.dump(tour_package_urls, f, indent=2)

print("Saved tour URLs to scripts/chennaitravels_in_tour_urls.json")
for u in tour_package_urls[:20]:
    print("  *", u)
