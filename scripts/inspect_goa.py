import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('scripts/hiphop_full_extracted_pages.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# check goa if it was fetched or fetch it directly
import urllib.request
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}
req = urllib.request.Request('https://hiphopholidays.in/wp-json/wp/v2/pages/644', headers=headers)
with urllib.request.urlopen(req) as resp:
    p = json.loads(resp.read().decode('utf-8'))

soup = BeautifulSoup(p['content']['rendered'], 'html.parser')
lines = [l.strip() for l in soup.get_text(separator='\n').splitlines() if l.strip()]
print(f"Page 644 (Goa) - Lines: {len(lines)}")
for i, l in enumerate(lines):
    if any(k in l.lower() for k in ['day 1', 'day 2', 'day 3', 'itinerary', 'north goa', 'south goa', 'beach', 'cruise', 'baga', 'calangute', 'aguada']):
        print(f"[{i}] {l}")
        for j in range(i+1, min(i+4, len(lines))):
            print(f"     -> {lines[j]}")
