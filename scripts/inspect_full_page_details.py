import sys
import urllib.request
import json
from bs4 import BeautifulSoup
import re

sys.stdout.reconfigure(encoding='utf-8')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
}

req = urllib.request.Request('https://hiphopholidays.in/wp-json/wp/v2/pages?per_page=100', headers=headers)
with urllib.request.urlopen(req) as resp:
    pages = json.loads(resp.read().decode('utf-8'))

tour_slugs = [
    'kerala-college-iv-trip',
    'karnataka-college-iv-trip',
    'tamil-nadu-college-iv-trip',
    'goa-college-iv-trip',
    'kerala-group-tours',
    'karnataka-group-tour',
    'tamil-nadu-group-tour',
    'goa-group-tours',
    'kerala-package-01',
    'karnataka-family-trip',
    'tamil-nadu-family-trip',
    'goa-family-trip',
    'kullu-manali',
    'honeymoon-trip',
    'diwali',
    'packages'
]

details = {}
for p in pages:
    slug = p['slug']
    if slug in tour_slugs:
        soup = BeautifulSoup(p['content']['rendered'], 'html.parser')
        
        # Remove script and style elements
        for s in soup(['script', 'style', 'noscript']):
            s.decompose()
            
        # Get clean text blocks
        lines = [line.strip() for line in soup.get_text(separator='\n').splitlines() if line.strip()]
        
        # Extract images
        images = []
        for img in soup.find_all('img', src=True):
            src = img['src']
            if any(ext in src.lower() for ext in ['.jpg', '.png', '.jpeg', '.webp']) and 'logo' not in src.lower():
                images.append(src)
                
        details[slug] = {
            'title': p['title']['rendered'],
            'url': p['link'],
            'lines': lines,
            'images': images[:5]
        }
        
        print(f"==================================================")
        print(f"SLUG: {slug} | TITLE: {p['title']['rendered']}")
        print(f"Total text lines: {len(lines)}")
        # Look for itinerary or day lines
        for i, l in enumerate(lines):
            if any(k in l.lower() for k in ['day 1', 'day 2', 'day 3', 'day 4', 'day 5', 'itinerary', 'starting from', 'duration', 'min people', 'pick up', 'price includes', 'price excludes']):
                print(f"  [{i}]: {l}")
                # Print next 3 lines
                for j in range(i+1, min(i+4, len(lines))):
                    print(f"       + {lines[j]}")

with open('scripts/hiphop_full_extracted_pages.json', 'w', encoding='utf-8') as f:
    json.dump(details, f, indent=2, ensure_ascii=False)
