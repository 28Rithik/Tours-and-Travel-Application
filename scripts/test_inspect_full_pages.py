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
    'https://chennaitourstravels.com/aarupadaiveedu.php',
    'https://chennaitourstravels.com/chennai-tirupathi-tour-packages.php',
    'https://chennaitourstravels.com/navathirupati-tour.php',
    'https://chennaitourstravels.com/navakailasam-tour.php',
    'https://chennaitourstravels.com/kerala-package/',
]

for url in test_urls:
    print("\n" + "="*80)
    print("TEST URL:", url)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            for s in soup(['script', 'style', 'noscript']):
                s.decompose()
            text = soup.get_text('\n', strip=True)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            print("Total lines:", len(lines))
            print("--- First 30 lines ---")
            for line in lines[:30]:
                print("  >", line[:100])
    except Exception as e:
        print("ERROR:", e)
