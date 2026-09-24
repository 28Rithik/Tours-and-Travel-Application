import urllib.request
import json
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

req = urllib.request.Request('https://hiphopholidays.in/wp-json/wp/v2/pages?per_page=100', headers=headers)
with urllib.request.urlopen(req) as resp:
    pages = json.loads(resp.read().decode('utf-8'))

print(f"Total pages retrieved: {len(pages)}")

tour_pages = []
for p in pages:
    slug = p.get('slug', '')
    title = p.get('title', {}).get('rendered', '')
    content = p.get('content', {}).get('rendered', '')
    link = p.get('link', '')
    
    # Check if page has itinerary or tour keywords
    has_tour_kw = any(w in (slug + title + content).lower() for w in ['iv trip', 'tour', 'package', 'itinerary', 'starting from', 'day 1', 'day 2', 'kerala', 'karnataka', 'tamil nadu', 'goa', 'manali'])
    if has_tour_kw and slug not in ['about', 'services', 'contact', 'privacy-policy', 'terms-and-conditions', 'maintenance', 'gallery']:
        tour_pages.append({
            'id': p['id'],
            'slug': slug,
            'title': title,
            'link': link,
            'content_len': len(content),
            'content_sample': content[:500]
        })

print(f"Tour related pages: {len(tour_pages)}")
for tp in tour_pages:
    print(f"- [{tp['id']}] {tp['title']} ({tp['slug']}) - Len: {tp['content_len']} - {tp['link']}")

with open('scripts/hiphop_tour_pages_summary.json', 'w', encoding='utf-8') as f:
    json.dump(tour_pages, f, indent=2)
