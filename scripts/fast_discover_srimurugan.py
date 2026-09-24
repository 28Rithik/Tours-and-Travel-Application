import urllib.request
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

hub_urls = [
    'https://www.srimurugantravel.com/',
    'https://www.srimurugantravel.com/domestic',
    'https://www.srimurugantravel.com/international',
    'https://www.srimurugantravel.com/train',
    'https://www.srimurugantravel.com/group-tour',
    'https://www.srimurugantravel.com/honeymoon-tour',
    'https://www.srimurugantravel.com/education-tours',
    'https://www.srimurugantravel.com/weekend-tour',
    'https://www.srimurugantravel.com/rameshwaram',
    'https://www.srimurugantravel.com/sabarimala',
    'https://www.srimurugantravel.com/tour_list_page',
    'https://www.srimurugantravel.com/domestic.php',
    'https://www.srimurugantravel.com/international.php',
    'https://www.srimurugantravel.com/train_tours.php',
    'https://www.srimurugantravel.com/train-tour.php',
    'https://www.srimurugantravel.com/group-tour.php',
]

def fetch_links_from_url(url):
    found_links = set()
    try:
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            if not href or href.startswith('#') or href.startswith('tel:') or href.startswith('mailto:') or href.startswith('javascript:'):
                continue
            full_url = urljoin(url, href).split('#')[0]
            if 'srimurugantravel.com' in full_url and 'blog.srimurugantravel.com' not in full_url:
                found_links.add(full_url)
    except Exception as e:
        print(f"Error {url}: {e}")
    return list(found_links)

print("Fetching links from all hubs in parallel...")
all_links = set()
with ThreadPoolExecutor(max_workers=10) as ex:
    for res in ex.map(fetch_links_from_url, hub_urls):
        for l in res:
            all_links.add(l)

print(f"Total raw links discovered across hubs: {len(all_links)}")

# Filter down to package detail pages
pkg_patterns = [
    re.compile(r'/domestic/[a-zA-Z0-9_-]+'),
    re.compile(r'/international/[a-zA-Z0-9_-]+'),
    re.compile(r'/train/[a-zA-Z0-9_-]+'),
    re.compile(r'brochure(?:_domestic)?\.php\?.*id='),
    re.compile(r'/(?:rameshwaram|sabarimala)$'),
]

packages = set()
for l in all_links:
    for pat in pkg_patterns:
        if pat.search(l):
            packages.add(l)
            break

package_list = sorted(list(packages))
print(f"Total Unique Sri Murugan Tour Package URLs: {len(package_list)}")

with open('scripts/srimurugan_package_urls.json', 'w', encoding='utf-8') as f:
    json.dump(package_list, f, indent=2)

dom = [u for u in package_list if '/domestic/' in u]
intl = [u for u in package_list if '/international/' in u]
train = [u for u in package_list if '/train/' in u]
brochures = [u for u in package_list if 'brochure' in u]
other = [u for u in package_list if u not in dom and u not in intl and u not in train and u not in brochures]

print(f"  Domestic: {len(dom)}")
print(f"  International: {len(intl)}")
print(f"  Train Tours: {len(train)}")
print(f"  Brochures: {len(brochures)}")
print(f"  Other Hubs: {len(other)}")
