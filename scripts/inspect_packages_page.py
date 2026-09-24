import sys
import urllib.request
import json
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
}

req = urllib.request.Request('https://hiphopholidays.in/wp-json/wp/v2/pages/40', headers=headers)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))

html = data['content']['rendered']
soup = BeautifulSoup(html, 'html.parser')

print("Page 40 (Packages) analysis:")
headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5'])]
print(f"Total headings: {len(headings)}")
print("Headings:", headings[:40])

# Look for links
links = set()
for a in soup.find_all('a', href=True):
    href = a['href']
    if 'hiphopholidays.in' in href and not href.endswith(('.jpg', '.png', '.jpeg', '.webp')):
        links.add(href)
print(f"\nInternal links found in packages page ({len(links)}):")
for l in sorted(links):
    print("  Link:", l)

# Let's inspect sections or elementor containers
sections = soup.find_all(class_=lambda c: c and 'elementor-section' in c)
print(f"\nTotal elementor sections: {len(sections)}")

# Let's see all text chunks that look like itineraries or package blocks
for i, h in enumerate(headings):
    if any(k in h.lower() for k in ['kerala', 'karnataka', 'tamil nadu', 'goa', 'manali', 'ooty', 'kodaikanal', 'munnar', 'wayanad', 'package']):
        print(f"Heading [{i}]: {h}")
