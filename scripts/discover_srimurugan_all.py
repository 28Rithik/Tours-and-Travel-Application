import urllib.request
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

start_urls = [
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

visited = set()
to_visit = list(start_urls)
package_urls = set()
all_site_urls = set()

# Pattern for tour package pages
pkg_patterns = [
    re.compile(r'/domestic/[a-zA-Z0-9_-]+'),
    re.compile(r'/international/[a-zA-Z0-9_-]+'),
    re.compile(r'/train/[a-zA-Z0-9_-]+'),
    re.compile(r'brochure(?:_domestic)?\.php\?.*id='),
    re.compile(r'/(?:rameshwaram|sabarimala)$'),
]

non_package_endings = [
    '.pdf', '.jpg', '.png', '.jpeg', '.gif', '.css', '.js',
    '/login', '/contact', '/about', '/privacy-policy', '/refund-policy', '/terms',
    '/privacy-policy.php', '/refund-policy.php', '/terms.php', '/contact.php'
]

print("Crawling Sri Murugan Travels to discover all packages...")

while to_visit:
    url = to_visit.pop(0)
    if url in visited:
        continue
    visited.add(url)
    
    # Check if this URL is a package detail page
    for pat in pkg_patterns:
        if pat.search(url):
            package_urls.add(url)
            break

    # Only fetch HTML from srimurugantravel.com
    parsed = urlparse(url)
    if 'srimurugantravel.com' not in parsed.netloc:
        continue
    if any(url.lower().endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.jpeg', '.gif', '.css', '.js']):
        continue

    try:
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')

        # Check if page has schema.org TouristTrip (which proves it is a package!)
        if soup.find('script', type='application/ld+json', string=re.compile(r'TouristTrip', re.I)):
            package_urls.add(url)

        # Find new links
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            if not href or href.startswith('#') or href.startswith('tel:') or href.startswith('mailto:') or href.startswith('javascript:'):
                continue
            full_url = urljoin(url, href).split('#')[0]
            if 'srimurugantravel.com' in full_url and 'blog.srimurugantravel.com' not in full_url:
                if full_url not in visited and full_url not in to_visit:
                    if not any(full_url.rstrip('/').endswith(np) for np in non_package_endings):
                        to_visit.append(full_url)
    except Exception as e:
        pass

print(f"\nCrawling complete!")
print(f"Total pages crawled: {len(visited)}")
print(f"Total Package URLs discovered: {len(package_urls)}")

package_list = sorted(list(package_urls))
with open('scripts/srimurugan_package_urls.json', 'w', encoding='utf-8') as f:
    json.dump(package_list, f, indent=2)

print("\nSample Package URLs by Category:")
dom = [u for u in package_list if '/domestic/' in u]
intl = [u for u in package_list if '/international/' in u]
train = [u for u in package_list if '/train/' in u]
other = [u for u in package_list if u not in dom and u not in intl and u not in train]

print(f"Domestic Packages ({len(dom)}):")
for u in dom[:5]:
    print(" ", u)
print(f"International Packages ({len(intl)}):")
for u in intl[:5]:
    print(" ", u)
print(f"Train Tour Packages ({len(train)}):")
for u in train[:5]:
    print(" ", u)
print(f"Other Packages ({len(other)}):")
for u in other:
    print(" ", u)
