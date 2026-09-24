import urllib.request
import sys
import re
import json
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

ALL_URLS = [
    'https://www.sblt.co.in/package/arupadaiveedu-tour-package-from-chennai',
    'https://www.sblt.co.in/package/muktinath-yatra-package-from-chennai',
    'https://www.sblt.co.in/package/panchabhoota-sthalam-yatra-from-chennai',
    'https://www.sblt.co.in/package/2-days-sabarimala-yatra-from-chennai',
    'https://www.sblt.co.in/package/navagraha-temple-tour-packages',
    'https://www.sblt.co.in/package/karnataka-pilgrimage-tour-package-from-chennai',
    'https://www.sblt.co.in/package/rameswaram-tour-package-chennai',
    'https://www.sblt.co.in/package/sabarimala-tour-package-from-chennai',
    'https://www.sblt.co.in/package/4-days-shirdi-tour-package-chennai',
    'https://www.sblt.co.in/package/ahobilam-temple-tour-package-chennai',
    'https://www.sblt.co.in/package/amarnath-yatra-package-from-chennai',
    'https://www.sblt.co.in/package/shirdi-tour-package-from-chennai',
    'https://www.sblt.co.in/package/gaya-varanasi-ayodhya-package-from-chennai',
    'https://www.sblt.co.in/package/yercaud-tour-package-from-chennai'
]

def clean_rebrand(text):
    if not text:
        return ""
    replacements = [
        (re.compile(r'SBLT\s+Tours\s*(?:&|and)\s*Travels', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'SBLT\s+Travel\s+Agency', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'SBLT\s+Travels', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'SBLT\s+Tours', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'SBLT', re.IGNORECASE), 'Siva Gayathri'),
        (re.compile(r'tours@sblt\.co\.in', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'sblt\.co\.in', re.IGNORECASE), 'sivagayathritravels.com'),
    ]
    cleaned = text
    for pattern, repl in replacements:
        cleaned = pattern.sub(repl, cleaned)
    return cleaned.strip()

def extract_package(url):
    req = urllib.request.Request(url, headers=HEADERS)
    html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
    soup = BeautifulSoup(html, 'html.parser')

    for el in soup.find_all(['header', 'footer', 'nav', 'script', 'style']):
        el.decompose()

    # Title
    h1s = [h.get_text(strip=True) for h in soup.find_all('h1')]
    raw_title = h1s[-1] if h1s and len(h1s[-1]) > 5 and h1s[-1] != 'Package Details' else (h1s[0] if h1s else 'Tour Package')
    title = clean_rebrand(raw_title)

    # Duration
    days = 1
    nights = 0
    for p in soup.find_all(['p', 'span', 'div']):
        t = p.get_text(strip=True)
        m = re.search(r'(\d+)\s*Days?\s*/\s*(\d+)\s*Nights?', t, re.IGNORECASE)
        if m:
            days = int(m.group(1))
            nights = int(m.group(2))
            break
        m2 = re.search(r'(\d+)\s*Nights?\s*/\s*(\d+)\s*Days?', t, re.IGNORECASE)
        if m2:
            nights = int(m2.group(1))
            days = int(m2.group(2))
            break

    # Price
    price = 0
    for text_node in soup.find_all(string=re.compile(r'₹')):
        t = text_node.strip()
        m = re.search(r'₹\s*([\d,]+)', t)
        if m:
            val = int(m.group(1).replace(',', ''))
            if 1000 <= val <= 250000:
                price = val
                break

    # If price still 0, check description text for "costs ₹XXXX" or "₹XXXX per person"
    if price == 0:
        desc_text = soup.get_text()
        m = re.search(r'₹\s*([\d,]+)', desc_text)
        if m:
            val = int(m.group(1).replace(',', ''))
            if 1000 <= val <= 250000:
                price = val

    # Description
    paragraphs = []
    for p in soup.find_all('p'):
        t = p.get_text(strip=True)
        if len(t) > 30 and not any(k in t.lower() for k in ['cookie', 'copyright', 'all rights', 'send enquiry', 'price starting']):
            paragraphs.append(clean_rebrand(t))

    full_desc = "\n\n".join(paragraphs)

    return {
        'url': url,
        'title': title,
        'days': days,
        'nights': nights,
        'price': price,
        'description': full_desc,
        'paragraphs': paragraphs
    }

def main():
    packages = []
    for u in ALL_URLS:
        try:
            pkg = extract_package(u)
            packages.append(pkg)
            print(f"[EXTRACTED] {pkg['title']} | {pkg['nights']}N/{pkg['days']}D | Rs.{pkg['price']:,}")
        except Exception as e:
            print(f"[FAILED] {u}: {e}")

    out_file = 'scripts/scraped_sblt_packages.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(packages, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(packages)} packages to {out_file}")

if __name__ == '__main__':
    main()
