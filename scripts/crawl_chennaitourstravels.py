import urllib.request
import ssl
import sys
from bs4 import BeautifulSoup
import json
import re

sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

def fetch_url(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

html = fetch_url('https://chennaitourstravels.com/index.php')
if not html:
    html = fetch_url('https://chennaitourstravels.com/')

if html:
    print(f"Homepage fetched successfully! HTML length: {len(html)}")
    soup = BeautifulSoup(html, 'html.parser')
    
    # Title
    print(f"Page Title: {soup.title.string if soup.title else 'No Title'}")
    
    # Collect all internal links
    links = set()
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if not href or href.startswith(('#', 'javascript:', 'tel:', 'mailto:')):
            continue
        if href.startswith('http') and 'chennaitourstravels.com' not in href:
            continue
        # Clean relative link
        if href.startswith('http'):
            full_url = href
        elif href.startswith('/'):
            full_url = 'https://chennaitourstravels.com' + href
        else:
            full_url = 'https://chennaitourstravels.com/' + href
            
        links.add(full_url)
        
    print(f"Total internal links discovered: {len(links)}")
    tour_links = [l for l in sorted(links) if any(k in l.lower() for k in ['tour', 'package', 'tariff', 'trip', 'temple', 'darshan', 'car-rental', '.php', '.html'])]
    print(f"Tour & Package related links ({len(tour_links)}):")
    for l in tour_links[:40]:
        print(f"  - {l}")
        
    with open('scripts/chennaitourstravels_links.json', 'w', encoding='utf-8') as f:
        json.dump(list(links), f, indent=2)
else:
    print("Failed to fetch homepage.")
