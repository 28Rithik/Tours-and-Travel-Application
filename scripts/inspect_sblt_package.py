import urllib.request
import re
from bs4 import BeautifulSoup

import sys
sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

def inspect(url):
    print("=" * 80)
    print("URL:", url)
    req = urllib.request.Request(url, headers=HEADERS)
    html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
    soup = BeautifulSoup(html, 'html.parser')
    for el in soup.find_all(['header', 'footer', 'nav', 'script', 'style']):
        el.decompose()

    print("Title tag:", soup.title.string.strip() if soup.title else "")
    
    # Check all headings
    for h in soup.find_all(['h1', 'h2', 'h3', 'h4']):
        print(f"HEAD <{h.name} class='{h.get('class')}'>: {h.get_text(strip=True)[:80]}")

    # Check paragraphs and list items
    for p in soup.find_all(['p', 'li']):
        t = p.get_text(strip=True)
        if any(k in t.upper() for k in ['DAY 1', 'DAY 2', 'DAY 3', 'DAY 4', 'INCLUSION', 'EXCLUSION', 'PRICE', 'RS', 'ITINERARY']):
            print(f"  [{p.name}]: {t[:120]}")

if __name__ == '__main__':
    inspect('https://www.sblt.co.in/package/arupadaiveedu-tour-package-from-chennai')
    inspect('https://www.sblt.co.in/package/muktinath-yatra-package-from-chennai')
