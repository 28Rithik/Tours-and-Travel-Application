import sys
import urllib.request
import re
import json
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

test_urls = [
    'https://www.srimurugantravel.com/domestic/ayodhya-ram-mandir-special',
    'https://www.srimurugantravel.com/train/udupi-murudeswarar-kollur-dharmasthala---kukke',
    'https://www.srimurugantravel.com/international/dubai-abudhabi'
]

def parse_srimurugan_package(url):
    req = urllib.request.Request(url, headers=headers)
    html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
    soup = BeautifulSoup(html, 'html.parser')

    # 1. JSON-LD data
    ld_trip = None
    for s in soup.find_all('script', type='application/ld+json'):
        try:
            d = json.loads(s.string)
            if d.get('@type') == 'TouristTrip':
                ld_trip = d
                break
        except:
            pass

    # Title
    title = ''
    if ld_trip and ld_trip.get('name'):
        title = ld_trip['name']
    if not title:
        title = soup.title.string.strip() if soup.title else ''
    title = re.sub(r'Sri Murugan.*', '', title, flags=re.I).strip()
    title = title.title()

    # Image
    hero_image = ld_trip.get('image', '') if ld_trip else ''
    if not hero_image:
        img_tag = soup.find('img', src=re.compile(r'/uploads/cms/|/cms/|/images/tours/', re.I))
        if img_tag:
            hero_image = img_tag['src']
            if hero_image.startswith('/'):
                hero_image = 'https://www.srimurugantravel.com' + hero_image

    # Duration
    days = 4
    nights = 3
    # Check page for "X Days"
    d_match = re.search(r'(\d+)\s*Days?', soup.text, re.I)
    if d_match:
        days = int(d_match.group(1))
        nights = max(1, days - 1)
    elif ld_trip and 'itinerary' in ld_trip:
        num_items = ld_trip['itinerary'].get('numberOfItems', len(ld_trip['itinerary'].get('itemListElement', [])))
        if num_items > 0:
            days = num_items
            nights = max(1, days - 1)

    # Price
    price = 0
    # Search for "Rs.From X" or "Rs. X"
    pm = re.search(r'Rs\.?\s*(?:From\s*)?([\d,]+)', soup.text, re.I)
    if pm:
        try:
            price = float(pm.group(1).replace(',', ''))
        except:
            pass
    if not price:
        pm2 = re.search(r'₹\s*([\d,]+)', soup.text)
        if pm2:
            try:
                price = float(pm2.group(1).replace(',', ''))
            except:
                pass
    if not price:
        price = days * 4500

    # Itinerary days
    itinerary = []
    # Try from on-page H4 tags first
    h_tags = soup.find_all(['h4', 'h5', 'h3'])
    for h in h_tags:
        dm = re.search(r'DAY\s*(\d+)', h.text.strip(), re.I)
        if dm:
            d_num = int(dm.group(1))
            p = h.find_next_sibling(['p', 'div', 'ul'])
            p_text = p.text.strip() if p else ''
            p_text = re.sub(r'\s+', ' ', p_text).strip()
            # extract title and activity
            d_title = f"Day {d_num}: Sightseeing & Excursions"
            if '-' in p_text:
                parts = p_text.split('-', 1)
                d_title = f"Day {d_num}: {parts[0].strip().title()}"
            itinerary.append({
                'day': d_num,
                'title': d_title,
                'description': p_text
            })

    # If on-page had no H4 tags, fallback to JSON-LD itinerary
    if not itinerary and ld_trip and 'itinerary' in ld_trip:
        elements = ld_trip['itinerary'].get('itemListElement', [])
        for el in elements:
            item = el.get('item', {})
            name = item.get('name', '')
            desc = item.get('description', '')
            dm = re.search(r'Day\s*(\d+)', name, re.I)
            d_num = int(dm.group(1)) if dm else el.get('position', len(itinerary)+1)
            itinerary.append({
                'day': d_num,
                'title': f"Day {d_num}: {desc.split('-')[0].strip().title() if '-' in desc else name}",
                'description': desc
            })

    # Inclusions
    inclusions = []
    inc_header = soup.find(text=re.compile(r'Package Inclusion|Inclusion', re.I))
    if inc_header:
        container = inc_header.find_parent(['div', 'section', 'li', 'td'])
        if container:
            for line in container.get_text(separator='\n').splitlines():
                l = line.strip()
                if l and not any(k in l.lower() for k in ['package inclusion', 'inclusion']):
                    inclusions.append(l)

    return {
        'url': url,
        'title': title,
        'days': days,
        'nights': nights,
        'price': price,
        'hero_image': hero_image,
        'itinerary_count': len(itinerary),
        'inclusions_count': len(inclusions),
        'sample_itinerary': itinerary[:2],
        'inclusions': inclusions[:5]
    }

for u in test_urls:
    res = parse_srimurugan_package(u)
    print("="*60)
    print(f"Title: {res['title']} | Duration: {res['nights']}N / {res['days']}D | Price: ₹{res['price']:,.0f}")
    print(f"Image: {res['hero_image']}")
    print(f"Itinerary Count: {res['itinerary_count']} | Inclusions Count: {res['inclusions_count']}")
    print("Sample Day 1:", res['sample_itinerary'][0] if res['sample_itinerary'] else 'None')
    print("Sample Inclusions:", res['inclusions'])
