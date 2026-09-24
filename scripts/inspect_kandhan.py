import urllib.request
from bs4 import BeautifulSoup
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

intl_pages = [
    'australia.html', 'bali.html', 'bhutan.html', 'cambodia.html', 'china.html', 
    'denmark.html', 'dubai.html', 'europe.html', 'france.html', 'georgia.html', 
    'hong-kong.html', 'israel.html', 'japan.html', 'kenya.html', 'malaysia.html', 
    'maldives.html', 'mauritius.html', 'nepal.html', 'norway.html', 'singapore.html', 
    'south-korea.html', 'sri-lanka.html', 'sweden.html', 'switzerland.html', 
    'thailand.html', 'turkey.html', 'united-kingdom.html', 'usa.html', 'vietnam.html'
]

print("=== CHECKING INTERNATIONAL PACKAGES ===")
for p in intl_pages:
    url = f'https://www.kandhantravels.com/{p}'
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find main package title
        h_title = "N/A"
        for h in soup.find_all(['h2', 'h3', 'h4']):
            t = h.get_text(strip=True)
            if re.search(r'\d+-Day\b', t, re.IGNORECASE) or any(k in t.lower() for k in ['tour', 'adventure', 'escape', 'extravaganza', 'explore', 'getaway', 'journey']):
                if not any(ex in t.lower() for ex in ['contact', 'services', 'about', 'tempo', 'coach', 'international tours', 'hire tempo']):
                    h_title = t
                    break
                    
        # Find Days
        days_found = []
        for el in soup.find_all(['p', 'li', 'h4', 'h5', 'strong']):
            txt = el.get_text(strip=True)
            m = re.match(r'^(Day\s*\d+[^:–-]*[:–-])\s*(.*)', txt)
            if m and len(txt) > 15:
                days_found.append((m.group(1), m.group(2)[:60]))
                
        print(f"{p:20} | Days: {len(days_found):2d} | Title: {h_title}")
    except Exception as e:
        print(f"{p:20} | Error: {e}")

print("\n=== CHECKING DEVOTIONAL PACKAGES ===")
dev_pages = [
    'devotional-packages.html',
    'devotion.html',
    'madurai.html',
    'kanyakumari.html',
    'mahabalipuram.html',
    'tanjore.html',
    'velankanni.html'
]

for p in dev_pages:
    url = f'https://www.kandhantravels.com/{p}'
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        h1 = soup.find('h1')
        headings = [h.get_text(strip=True) for h in soup.find_all(['h2', 'h3', 'h4']) if not any(ex in h.get_text(strip=True).lower() for ex in ['contact', 'services', 'about', 'tempo', 'coach'])]
        print(f"{p:25} | Title: {soup.title.string.strip() if soup.title else ''} | Headings: {headings[:4]}")
    except Exception as e:
        print(f"{p:25} | Error: {e}")
