import urllib.request
import ssl
import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

for u in ['https://www.chennaitravels.in/kolli-hills-tour-package', 'https://www.chennaitravels.in/chennai-outside-city-sightseeing-tours.html']:
    req = urllib.request.Request(u, headers=HEADERS)
    with urllib.request.urlopen(req, context=ctx) as r:
        soup = BeautifulSoup(r.read().decode('utf-8', errors='ignore'), 'html.parser')
        print(f"\n{'='*70}\nURL: {u}")
        print("H1:", [h.get_text(strip=True) for h in soup.find_all('h1')])
        print("H2:", [h.get_text(strip=True) for h in soup.find_all('h2')][:5])
        paragraphs = [p.get_text(strip=True) for p in soup.find_all(['p', 'li']) if len(p.get_text(strip=True)) > 25]
        print("First 8 paragraphs:")
        for p in paragraphs[:8]:
            print("  >", p[:120])
