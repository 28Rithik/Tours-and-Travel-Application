import sys
import urllib.request
import json
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
}

req = urllib.request.Request('https://hiphopholidays.in/wp-json/wp/v2/pages?per_page=100', headers=headers)
with urllib.request.urlopen(req) as resp:
    pages = json.loads(resp.read().decode('utf-8'))

print(f"Total pages: {len(pages)}")

target_slugs = [
    'packages',
    'college-iv-trip',
    'kerala-college-iv-trip',
    'kerala-group-tours',
    'kerala-package-01',
    'karnataka-college-iv-trip',
    'karnataka-group-tour',
    'karnataka-family-trip',
    'tamil-nadu-college-iv-trip',
    'tamil-nadu-group-tour',
    'tamil-nadu-family-trip',
    'goa-college-iv-trip',
    'goa-group-tours',
    'goa-family-trip',
    'kullu-manali',
    'honeymoon-trip',
    'group-tours',
    'kerala',
    'karnataka',
    'tamil-nadu',
    'goa'
]

results = {}
for p in pages:
    slug = p['slug']
    if slug in target_slugs:
        soup = BeautifulSoup(p['content']['rendered'], 'html.parser')
        # Extract all text, headings, list items
        headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])]
        
        # Extract text snippets mentioning days, itinerary, price
        itinerary_texts = []
        for el in soup.find_all(['p', 'li', 'span', 'div']):
            txt = el.get_text(strip=True)
            if any(k in txt.lower() for k in ['day 1', 'day 2', 'day 3', 'day 4', 'day 5', 'itinerary', 'starting from', '₹', 'price includes', 'price excludes']):
                if len(txt) > 5 and len(txt) < 300 and txt not in itinerary_texts:
                    itinerary_texts.append(txt)
                    
        results[slug] = {
            'id': p['id'],
            'title': p['title']['rendered'],
            'link': p['link'],
            'headings_count': len(headings),
            'headings_sample': headings[:15],
            'itinerary_snippets_count': len(itinerary_texts),
            'itinerary_snippets_sample': itinerary_texts[:10]
        }
        print(f"\n==========================================")
        print(f"PAGE: {p['title']['rendered']} ({slug})")
        print(f"Headings ({len(headings)}): {headings[:8]}")
        print(f"Snippets ({len(itinerary_texts)}): {itinerary_texts[:6]}")

with open('scripts/hiphop_pages_deep_analysis.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
