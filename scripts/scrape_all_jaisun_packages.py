import urllib.request
import re
import sys
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

EXCLUDE_SLUGS = [
    'about-us', 'contact', 'gallery', 'special-offers', 'group-departures',
    'privacy-policy', 'terms', 'tour-packages', 'international-tour-packages',
    'domestic-packages', 'honeymoon-tour-packages', 'pilgrimage-tours',
    'academic-tour-packages', 'inbound-tour-packages', 'blog', 'uploads'
]

def clean_rebrand(text):
    if not text:
        return ""
    replacements = [
        (re.compile(r'Jaisun\s+Tourism', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'jaisuntourism\.com', re.IGNORECASE), 'sivagayathritravels.com'),
        (re.compile(r'booking@jaisuntourism\.com', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'info@jaisuntourism\.com', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'\+91[\s\d-]{9,15}'), '+91 98425 33777'),
    ]
    cleaned = text
    for pattern, repl in replacements:
        cleaned = pattern.sub(repl, cleaned)
    return cleaned.strip()

def clean_title(title):
    t = clean_rebrand(title)
    # Remove Tour Code suffixes like "Tour Code IDB004" or "Tour Code PC002"
    t = re.sub(r'Tour\s*Code\s*[A-Z0-9]+', '', t, flags=re.IGNORECASE)
    # Remove "From Coimbatore" or "In Coimbatore"
    t = re.sub(r'[\s–-]+(?:from|in)\s+coimbatore(?:\s+india)?', '', t, flags=re.IGNORECASE)
    # Remove duration from title if present like "11 Days 10 Nights" or "2 Nights 3 Days"
    t = re.sub(r'\d+\s*Days?\s*\d+\s*Nights?', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\d+\s*Nights?\s*\d+\s*Days?', '', t, flags=re.IGNORECASE)
    t = re.sub(r'[\u2013\u2014–-]+', '-', t)
    t = ' '.join(t.split()).strip(' -:')
    return t.upper()

def extract_package(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
    except Exception as e:
        return None, f"Fetch error {url}: {e}"

    for el in soup.find_all(['header', 'footer', 'nav', 'script', 'style', 'noscript']):
        el.decompose()

    h1 = soup.find('h1')
    raw_h1 = h1.get_text(strip=True) if h1 else url.rstrip('/').split('/')[-1].replace('-', ' ').title()
    title = clean_title(raw_h1)
    if not title.endswith('TOUR') and not title.endswith('PACKAGE') and not title.endswith('YATRA') and not title.endswith('CRUISE'):
        title = f"{title} TOUR PACKAGE"

    # Duration parsing
    full_text = soup.get_text(' ', strip=True)
    days = 0
    nights = 0

    dur_match1 = re.search(r'(\d+)\s*Days?\s*(?:and\s*)?(\d+)\s*Nights?', raw_h1 + ' ' + full_text[:1500], re.IGNORECASE)
    if dur_match1:
        days = int(dur_match1.group(1))
        nights = int(dur_match1.group(2))
    else:
        dur_match2 = re.search(r'(\d+)\s*Nights?\s*(?:and\s*)?(\d+)\s*Days?', raw_h1 + ' ' + full_text[:1500], re.IGNORECASE)
        if dur_match2:
            nights = int(dur_match2.group(1))
            days = int(dur_match2.group(2))

    # Days Plan from accordion
    days_plan = []
    plan_div = soup.find(class_='gotur-accordion') or soup.find(class_='faq-accordion') or soup.find(class_=re.compile(r'accordion', re.I))
    
    if plan_div:
        items = plan_div.find_all(class_='accordion')
        if not items:
            items = plan_div.find_all(class_=re.compile(r'accor', re.I))
            
        for idx, item in enumerate(items, 1):
            h = item.find(class_='accordion-title__text') or item.find(['h3', 'h4', 'h5', 'button'])
            c = item.find(class_='accordion-content') or item.find(class_=re.compile(r'collapse|body', re.I)) or item.find('p')
            h_text = h.get_text(strip=True) if h else f"Day {idx} Sightseeing"
            c_text = c.get_text(strip=True) if c else h_text
            
            # Remove "Day X:" prefix if repeated
            h_clean = re.sub(r'^Day\s*\d+\s*[:–-]\s*', '', h_text, flags=re.IGNORECASE)
            
            days_plan.append({
                'day': idx,
                'title': clean_rebrand(f"Day {idx}: {h_clean}"),
                'spots': clean_rebrand(c_text if len(c_text) > 10 else h_clean)
            })

    # If no accordion, look for Day 1 headings or paragraphs
    if not days_plan:
        day_tags = soup.find_all(lambda t: t.name in ['h3', 'h4', 'h5', 'strong', 'p'] and re.match(r'^Day\s*\d+\b', t.get_text(strip=True), re.I))
        for idx, dt in enumerate(day_tags, 1):
            txt = dt.get_text(strip=True)
            parts = re.split(r'[:–-]', txt, maxsplit=1)
            d_title = parts[0].strip()
            d_spots = parts[1].strip() if len(parts) > 1 else txt
            days_plan.append({
                'day': idx,
                'title': clean_rebrand(f"Day {idx}: {d_title}"),
                'spots': clean_rebrand(d_spots)
            })

    # Determine true duration
    if days == 0 and len(days_plan) > 0:
        days = len(days_plan)
        nights = max(0, days - 1)
    elif days > 0 and len(days_plan) == 0:
        for d in range(1, days + 1):
            days_plan.append({
                'day': d,
                'title': f"Day {d}: Guided Sightseeing & Exploration",
                'spots': f"Explore prominent tourist attractions, cultural sites, and picturesque views in {title}."
            })
    elif days > 0 and len(days_plan) > 0:
        days = max(days, len(days_plan))
        nights = max(nights, days - 1)
    else:
        days = 3
        nights = 2
        for d in range(1, days + 1):
            days_plan.append({
                'day': d,
                'title': f"Day {d}: Sightseeing & Leisure",
                'spots': f"Tour destinations and heritage attractions along {title}."
            })

    # Inclusions & Exclusions
    inclusions = []
    exclusions = []
    inc_h = soup.find(lambda t: t.name in ['h2', 'h3', 'h4', 'h5'] and 'inclusion' in t.text.lower())
    if inc_h:
        inc_parent = inc_h.find_parent(['section', 'div'])
        for li in inc_parent.find_all(['li', 'p']):
            txt = li.get_text(strip=True)
            if len(txt) > 5 and not any(ex in txt.lower() for ex in ['inclusion', 'overview', 'plan', 'book this']):
                if any(ex in txt.lower() for ex in ['excluded', 'not included', 'extra', 'optional']):
                    exclusions.append(clean_rebrand(txt))
                else:
                    inclusions.append(clean_rebrand(txt))

    # Overview Description
    desc_paras = []
    overview_h = soup.find(lambda t: t.name in ['h2', 'h3', 'h4', 'h5'] and 'overview' in t.text.lower())
    if overview_h:
        curr = overview_h.next_sibling
        while curr and len(desc_paras) < 3:
            if curr.name in ['p', 'div'] and len(curr.get_text(strip=True)) > 30:
                desc_paras.append(clean_rebrand(curr.get_text(strip=True)))
            curr = curr.next_sibling

    if not desc_paras:
        for p in soup.find_all('p'):
            pt = clean_rebrand(p.get_text(strip=True))
            if 40 < len(pt) < 400 and not any(ex in pt.lower() for ex in ['copyright', 'reserved', 'call now', 'enquiry']):
                desc_paras.append(pt)
                if len(desc_paras) >= 3:
                    break

    description = "\n\n".join(desc_paras) if desc_paras else f"Experience {title} with Siva Gayathri Tours & Travels. Comprehensive {days} Days / {nights} Nights itinerary with full fleet support."

    return {
        'url': url,
        'title': title,
        'days': days,
        'nights': nights,
        'days_plan': days_plan,
        'inclusions': inclusions,
        'exclusions': exclusions,
        'description': description,
    }, None

def main():
    sitemap_url = 'https://www.jaisuntourism.com/sitemap.xml'
    req = urllib.request.Request(sitemap_url, headers=HEADERS)
    root = ET.fromstring(urllib.request.urlopen(req, timeout=12).read())
    urls = [elem.text for elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]

    EXCLUDE_EXACT = {
        'https://www.jaisuntourism.com/',
        'https://www.jaisuntourism.com/about-us/',
        'https://www.jaisuntourism.com/contact/',
        'https://www.jaisuntourism.com/gallery/',
        'https://www.jaisuntourism.com/special-offers/',
        'https://www.jaisuntourism.com/group-departures/',
        'https://www.jaisuntourism.com/tour-packages/',
        'https://www.jaisuntourism.com/tour-packages/international-tour-packages/',
        'https://www.jaisuntourism.com/tour-packages/domestic-packages/',
        'https://www.jaisuntourism.com/tour-packages/honeymoon-tour-packages/',
        'https://www.jaisuntourism.com/tour-packages/pilgrimage-tours/',
        'https://www.jaisuntourism.com/tour-packages/academic-tour-packages/',
        'https://www.jaisuntourism.com/tour-packages/inbound-tour-packages/',
        'https://www.jaisuntourism.com/tour-packages/honeymoon-tour-packages/international-honeymoon-packages/',
        'https://www.jaisuntourism.com/tour-packages/honeymoon-tour-packages/domestic-honeymoon-packages/',
        'https://www.jaisuntourism.com/tour-packages/academic-tour-packages/international-academic-tours/',
        'https://www.jaisuntourism.com/tour-packages/academic-tour-packages/domestic-academic-tours/',
    }

    candidate_urls = []
    for u in urls:
        u_clean = u.strip()
        if u_clean in EXCLUDE_EXACT:
            continue
        if any(k in u_clean for k in ['/blog/', '/gallery/', '/uploads/', '.pdf', '.jpg', '.png']):
            continue
        candidate_urls.append(u_clean)

    print(f"Discovered {len(candidate_urls)} candidate tour package URLs from Jaisun Tourism sitemap!")

    results = []
    errors = 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(extract_package, u): u for u in candidate_urls}
        for future in as_completed(future_to_url):
            data, err = future.result()
            if data:
                results.append(data)
                print(f"  [{len(results):3d}/{len(candidate_urls)}] {data['title'][:50]} ({data['nights']}N/{data['days']}D, {len(data['days_plan'])} plan days)")
            else:
                errors += 1
                print(f"  [ERR] {err}")

    print(f"\nScraping complete: {len(results)} scraped successfully, {errors} errors.")
    out_file = 'scripts/scraped_jaisun_packages.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Saved all scraped packages to {out_file}!")

if __name__ == '__main__':
    main()
