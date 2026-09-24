import sys
import urllib.request
import re
import json
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

urls = json.load(open('scripts/holidify_south_urls.json', encoding='utf-8'))[:5]

def parse_holidify_package(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
    soup = BeautifulSoup(html, 'html.parser')

    # 1. Title
    h1 = soup.find('h1')
    raw_title = h1.text.strip() if h1 else 'South India Tour Package'
    # Clean Unicode arrows and extra spaces
    clean_title = raw_title.replace('\u2192', '-').replace('\u2013', '-').replace('\u2014', '-')
    clean_title = re.sub(r'\s+', ' ', clean_title).strip()

    # Extract Holidify package ID from URL (e.g. 20605 from 4-nights-5-days-kerala-getaway-20605.html)
    id_match = re.search(r'-(\d+)\.html', url)
    pkg_id = id_match.group(1) if id_match else '000'

    # 2. Duration & Category from .atf-top-highlights
    highlights = soup.find(class_=re.compile(r'atf-top-highlights', re.I))
    duration_str = ''
    theme_tag = ''
    if highlights:
        p_tags = [p.text.strip() for p in highlights.find_all('p') if p.text.strip()]
        for pt in p_tags:
            if re.search(r'\d+\s*N\s*/\s*\d+\s*D', pt, re.I):
                duration_str = pt
            else:
                if not theme_tag:
                    theme_tag = pt

    days = 3
    nights = 2
    if duration_str:
        dn_match = re.search(r'(\d+)\s*N\s*/\s*(\d+)\s*D', duration_str, re.I)
        if dn_match:
            nights = int(dn_match.group(1))
            days = int(dn_match.group(2))
    else:
        # fallback to title regex
        dn_match = re.search(r'(\d+)\s*(?:Nights?|N)\s*[/&, -]*\s*(\d+)\s*(?:Days?|D)', clean_title, re.I)
        if dn_match:
            nights = int(dn_match.group(1))
            days = int(dn_match.group(2))
        else:
            d_only = re.search(r'(\d+)\s*(?:Days?|Day)', clean_title, re.I)
            if d_only:
                days = int(d_only.group(1))
                nights = max(1, days - 1)

    # 3. Pricing
    price = 0
    final_p = soup.find(class_=re.compile(r'final-price', re.I))
    if final_p:
        pm = re.search(r'[\d,]+', final_p.text.replace('₹', ''))
        if pm:
            try:
                price = float(pm.group(0).replace(',', ''))
            except:
                pass
    if not price:
        all_prices = re.findall(r'₹\s*([\d,]+)', soup.text)
        if all_prices:
            for p_str in all_prices:
                val = float(p_str.replace(',', ''))
                if 2000 <= val <= 300000:
                    price = val
                    break
    if not price:
        price = days * 3500

    # 4. Stay info
    stay_info = 'Star Category Hotel / Resort'
    for tag in soup.find_all(text=re.compile(r'STAY', re.I)):
        parent_txt = tag.parent.text.strip().replace('\n', ' ')
        if 'hotels' in parent_txt.lower() or 'houseboat' in parent_txt.lower() or 'resort' in parent_txt.lower():
            stay_info = parent_txt.replace('STAY', '').strip()
            break

    # 5. Overview / description
    overview_p = []
    # Holidify detail page has overview text or first itinerary intro
    desc_div = soup.find('div', class_=re.compile(r'description|overview|about', re.I))
    if desc_div:
        overview_p.append(desc_div.text.strip())

    # 6. Hero image
    hero_image = ''
    swipe_img = soup.find('div', class_='swipe-image')
    if swipe_img and swipe_img.get('style') and 'url(' in swipe_img.get('style'):
        m = re.search(r"url\(['\"]?(.*?)['\"]?\)", swipe_img.get('style'))
        if m and 'patt.png' not in m.group(1):
            hero_image = m.group(1)
    if not hero_image:
        for lbg in soup.find_all('div', class_='lazyBG'):
            orig = lbg.get('data-original')
            if orig and 'patt.png' not in orig:
                hero_image = orig
                break

    # 7. Itinerary days
    itinerary = []
    h2 = soup.find('h2', id='itinerary')
    sec = h2.find_next_sibling('div') if h2 else None
    if sec:
        # Accordion day blocks
        day_blocks = sec.find_all('div', class_=lambda c: c and 'accordion' in c.lower())
        if not day_blocks:
            day_blocks = sec.find_all('div', class_=lambda c: c and 'day' in c.lower())
        if not day_blocks:
            day_blocks = sec.find_all(recursive=False)

        # Parse each block
        seen_days = set()
        for blk in day_blocks:
            header = blk.find(['button', 'h3', 'h4', 'h5', 'a', 'div'], class_=lambda c: c and any(k in c.lower() for k in ['header', 'title', 'heading', 'btn']))
            htxt = header.text.strip() if header else blk.text.strip()[:60]
            # Match Day X
            dm = re.search(r'Day\s*(\d+)\b[:\s-]*(.*)', htxt, re.I)
            if dm:
                d_num = int(dm.group(1))
                d_title = dm.group(2).strip() or f"Sightseeing & Tour - Day {d_num}"
                if d_num in seen_days:
                    continue
                seen_days.add(d_num)
                
                body = blk.find(class_=lambda c: c and any(k in c.lower() for k in ['collapse', 'body', 'content', 'desc']))
                b_text = body.text.strip() if body else blk.text.strip()
                # Clean header out of body
                b_text = b_text.replace(htxt, '').strip()
                
                itinerary.append({
                    'day': d_num,
                    'title': d_title,
                    'activities': b_text
                })

    # 8. Inclusions & Exclusions
    inclusions = []
    exclusions = []
    inc_div = soup.find('div', class_=lambda c: c and 'inclusions' in c.lower())
    if inc_div:
        for li in inc_div.find_all(['li', 'p', 'div']):
            t = li.text.strip()
            if t and len(t) > 3 and t not in inclusions:
                inclusions.append(t)
    exc_div = soup.find('div', class_=lambda c: c and 'exclusions' in c.lower())
    if exc_div:
        for li in exc_div.find_all(['li', 'p', 'div']):
            t = li.text.strip()
            if t and len(t) > 3 and t not in exclusions:
                exclusions.append(t)

    return {
        'url': url,
        'pkg_id': pkg_id,
        'title': clean_title,
        'days': days,
        'nights': nights,
        'theme': theme_tag,
        'price': price,
        'stay_info': stay_info,
        'hero_image': hero_image,
        'itinerary_count': len(itinerary),
        'itinerary_sample': itinerary[0] if itinerary else None,
        'inclusions_count': len(inclusions),
        'exclusions_count': len(exclusions),
    }

for u in urls:
    data = parse_holidify_package(u)
    print(f"\n==============================")
    print(f"ID: {data['pkg_id']} | Title: {data['title']}")
    print(f"Duration: {data['nights']}N / {data['days']}D | Theme: {data['theme']} | Price: ₹{data['price']:,.0f}")
    print(f"Stay: {data['stay_info']} | Image: {data['hero_image'][:60]}...")
    print(f"Itinerary Days: {data['itinerary_count']} | Inclusions: {data['inclusions_count']} | Exclusions: {data['exclusions_count']}")
    if data['itinerary_sample']:
        print(f" Day 1: {data['itinerary_sample']['title']} -> {data['itinerary_sample']['activities'][:100]}...")
