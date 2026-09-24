import urllib.request
import sys
import re
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

def inspect(url):
    print("=" * 80)
    print("URL:", url)
    soup = BeautifulSoup(urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=15).read().decode('utf-8', errors='ignore'), 'html.parser')
    for el in soup.find_all(['header', 'footer', 'nav', 'script', 'style']):
        el.decompose()

    # Look for day occurrences
    day_matches = soup.find_all(string=re.compile(r'Day\s*\d+', re.IGNORECASE))
    print(f"Day string matches ({len(day_matches)}):")
    for m in day_matches[:10]:
        print(f"  [{m.parent.name}]: {repr(m.strip())[:100]} | Parent: {m.parent.get_text(' ', strip=True)[:150]}")

    # Look for list items or accordions
    lis = soup.find_all(['li', 'dt', 'dd', 'h3', 'h4'])
    print(f"\nPotential itinerary elements ({len(lis)}):")
    for li in lis[:15]:
        t = li.get_text(' ', strip=True)
        if any(k in t.lower() for k in ['day', 'morning', 'visit', 'pickup', 'temple', 'reach']):
            print(f"  <{li.name}>: {t[:120]}")

if __name__ == '__main__':
    inspect('https://www.chennaitravels.in/chennai-pondicherry-2-day-tour-package.html')
    inspect('https://www.chennaitravels.in/chennai-to-tirupati-tour-package.html')
