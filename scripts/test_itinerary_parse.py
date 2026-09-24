import sys
import urllib.request
import re
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

url = 'https://www.holidify.com/tour-package/4-nights-5-days-kerala-getaway-20605.html'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore'), 'html.parser')

h2 = soup.find('h2', id='itinerary')
sec = h2.find_next_sibling('div') if h2 else None

if sec:
    # Each day item
    day_cards = sec.find_all('div', class_=lambda c: c and 'accordion' in c.lower() or (c and 'day' in c.lower()))
    if not day_cards:
        day_cards = sec.find_all(recursive=False)
    print(f"Total day items: {len(day_cards)}")
    for i, dc in enumerate(day_cards):
        # find day title
        header = dc.find(['button', 'h3', 'h4', 'h5', 'a', 'div'], class_=lambda c: c and any(k in c.lower() for k in ['header', 'title', 'heading', 'btn']))
        title_text = header.text.strip() if header else 'Unknown'
        body = dc.find(class_=lambda c: c and any(k in c.lower() for k in ['collapse', 'body', 'content', 'desc']))
        body_text = body.text.strip() if body else dc.text.strip()
        print(f"\n--- DAY {i+1} ---")
        print(f"Header: {title_text[:100]}")
        print(f"Body: {body_text[:200]}")
