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

test_urls = [
    'https://www.chennaitravels.in/kolli-hills-tour-package',
    'https://www.chennaitravels.in/chennai-outside-city-sightseeing-tours.html'
]

for url in test_urls:
    print(f"\n{'='*70}\nFETCHING: {url}")
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            soup = BeautifulSoup(resp.read().decode('utf-8', errors='ignore'), 'html.parser')
            print("Title:", soup.title.string if soup.title else "No Title")
            text = soup.get_text('\n', strip=True)
            lines = [l for l in text.split('\n') if len(l) > 20]
            print(f"Total lines: {len(lines)}")
            for l in lines[:15]:
                print("  *", l[:100])
    except Exception as e:
        print(f"Error fetching {url}: {e}")
