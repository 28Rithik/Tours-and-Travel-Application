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
        for h in soup.find_all(['h2', 'h3']):
            htext = h.get_text(strip=True)
            if any(k in htext.lower() for k in ['itinerary', 'day', 'tariff', 'details']):
                print(f"\nHeading: {htext}")
                # print sibling paragraphs
                for sib in h.find_next_siblings(['p', 'ul', 'ol', 'div'])[:5]:
                    txt = sib.get_text('\n', strip=True)
                    if len(txt) > 20:
                        print(f"  Sibling text: {txt[:200]}...\n")
