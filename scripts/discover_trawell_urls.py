import os
import sys
import re
import json
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

OUTPUT_JSON = os.path.join(os.path.dirname(__file__), 'trawell_catalog_metadata.json')

def parse_hub(hub_url: str):
    found_cards = []
    try:
        r = requests.get(hub_url, headers=HEADERS, timeout=12)
        if r.status_code != 200:
            return found_cards
        soup = BeautifulSoup(r.text, 'html.parser')
        
        for a in soup.find_all('a', href=True):
            if '/tour/' in a['href'] and a.get_text(strip=True) == 'View Details':
                card = a.find_parent('div', class_=re.compile(r'card|tour|col|box|item|pkg', re.I))
                if not card:
                    continue
                
                t_url = a['href'].strip()
                if t_url.startswith('/'):
                    t_url = 'https://www.trawell.in' + t_url
                t_code = t_url.split('/')[-1].upper()

                title_tag = card.find(['h2', 'h3', 'h4', 'h5', 'strong']) or card.find('a', href=re.compile(r'/tour/'))
                title = title_tag.get_text(strip=True) if title_tag else ''

                card_text = card.get_text(' | ', strip=True)
                prices = re.findall(r'₹\s*([\d,]+)', card_text)
                durations = re.findall(r'(\d+D\s*/\s*\d+N|\d+\s*Days?|\d+\s*Nights?)', card_text, re.I)
                places = re.findall(r'(\d+)\s*Places', card_text, re.I)
                distance = re.findall(r'(\d+)\s*km', card_text, re.I)

                tag_spans = card.find_all(['span', 'p', 'div'], class_=re.compile(r'tag|cat|theme|type', re.I))
                tags = []
                for ts in tag_spans:
                    t_txt = ts.get_text(strip=True)
                    if any(c in t_txt.lower() for c in ['hill', 'pilgrimage', 'heritage', 'beach', 'wildlife', 'city', 'backwaters']):
                        tags.extend([x.strip() for x in t_txt.split('|') if x.strip()])

                offer_p = None
                strike_p = None
                if len(prices) > 1:
                    strike_p = int(prices[0].replace(',', ''))
                    offer_p = int(prices[1].replace(',', ''))
                elif prices:
                    offer_p = int(prices[0].replace(',', ''))

                found_cards.append({
                    'tour_code': t_code,
                    'tour_url': t_url,
                    'title': title,
                    'category_tags': tags,
                    'duration_str': durations[0] if durations else '',
                    'distance_str': f"{distance[0]} km" if distance else '',
                    'places_count': int(places[0]) if places else 0,
                    'strikethrough_price': strike_p,
                    'offer_price': offer_p
                })
    except Exception:
        pass
    return found_cards

def main():
    print("=" * 70, flush=True)
    print("SIVA GAYATHRI TOURS & TRAVELS — FAST MULTI-THREADED TRAWELL DISCOVERY", flush=True)
    print("=" * 70, flush=True)

    # 1. Read sitemap
    sitemap_text = ""
    step_sitemap = r'C:\Users\rithi\.gemini\antigravity-ide\brain\12e9440a-ec76-4489-aa28-9f0807948a00\.system_generated\steps\55\content.md'
    if os.path.exists(step_sitemap):
        with open(step_sitemap, 'r', encoding='utf-8', errors='ignore') as f:
            sitemap_text = f.read()
    else:
        print("Fetching sitemap from https://www.trawell.in/sitemap.xml ...", flush=True)
        resp = requests.get('https://www.trawell.in/sitemap.xml', headers=HEADERS, timeout=30)
        sitemap_text = resp.text

    sitemap_tours = set(re.findall(r'<loc>(https://www\.trawell\.in/tour/[^<]+)</loc>', sitemap_text))
    sitemap_itins = set(re.findall(r'<loc>(https://www\.trawell\.in/itineraries/[^<]+)</loc>', sitemap_text))

    print(f"Found {len(sitemap_tours)} tour package URLs in sitemap.", flush=True)

    discovered_packages = {}
    for tour_url in sitemap_tours:
        t_code = tour_url.strip().split('/')[-1].upper()
        discovered_packages[t_code] = {
            'tour_code': t_code,
            'tour_url': tour_url.strip(),
            'itinerary_url': None,
            'title': '',
            'category_tags': [],
            'duration_str': '',
            'distance_str': '',
            'places_count': 0,
            'strikethrough_price': None,
            'offer_price': None
        }

    # 2. Build Hub URLs
    origin_cities = [
        'bangalore', 'chennai', 'kochi', 'mumbai', 'pune', 'delhi', 'madurai',
        'jaipur', 'mysore', 'coimbatore', 'mangalore', 'hyderabad', 'ahmedabad',
        'bhopal', 'kozhikode', 'udaipur', 'bhubaneswar', 'varanasi', 'vizag',
        'aurangabad', 'panjim', 'andaman-islands', 'north-east-india', 'hubli'
    ]
    day_filters = ['one-day-trip', '2-day-trip', '3-day-trip', '4-day-trip', '5-day-trip', '6-day-trip', '7-day-trip', '8-day-trip']

    hub_urls = []
    for city in origin_cities:
        for df in day_filters:
            hub_urls.append(f"https://www.trawell.in/itineraries/{city}/{df}")

    print(f"Prepared {len(hub_urls)} regional hubs. Scanning concurrently with 15 workers...", flush=True)

    # 3. Concurrent Hub Crawl
    with ThreadPoolExecutor(max_workers=15) as executor:
        future_to_url = {executor.submit(parse_hub, h): h for h in hub_urls}
        completed = 0
        total_cards = 0
        for future in as_completed(future_to_url):
            completed += 1
            cards = future.result()
            for c in cards:
                t_code = c['tour_code']
                total_cards += 1
                if t_code not in discovered_packages:
                    discovered_packages[t_code] = c
                else:
                    pkg = discovered_packages[t_code]
                    if not pkg['title'] and c['title']:
                        pkg['title'] = c['title']
                    if not pkg['category_tags'] and c['category_tags']:
                        pkg['category_tags'] = c['category_tags']
                    if not pkg['duration_str'] and c['duration_str']:
                        pkg['duration_str'] = c['duration_str']
                    if not pkg['distance_str'] and c['distance_str']:
                        pkg['distance_str'] = c['distance_str']
                    if not pkg['places_count'] and c['places_count']:
                        pkg['places_count'] = c['places_count']
                    if not pkg['offer_price'] and c['offer_price']:
                        pkg['strikethrough_price'] = c['strikethrough_price']
                        pkg['offer_price'] = c['offer_price']

            if completed % 25 == 0 or completed == len(hub_urls):
                print(f"  Scanned {completed}/{len(hub_urls)} hubs... (Extracted {total_cards} card records)", flush=True)

    print(f"\nDiscovery complete! Total unique packages cataloged: {len(discovered_packages)}", flush=True)
    with_pricing = sum(1 for p in discovered_packages.values() if p.get('offer_price'))
    print(f"Packages with direct pricing: {with_pricing}/{len(discovered_packages)}", flush=True)

    # 4. Save metadata JSON
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(discovered_packages, f, indent=2)

    print(f"Saved catalog metadata to {OUTPUT_JSON}", flush=True)

if __name__ == '__main__':
    main()
