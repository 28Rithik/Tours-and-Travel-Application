import sys
import urllib.request
import re
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

url = 'https://www.srimurugantravel.com/domestic/ayodhya-ram-mandir-special'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore'), 'html.parser')

print("=== ITINERARY DAYS ON-PAGE ===")
for h4 in soup.find_all(['h4', 'h5', 'h3']):
    if 'day' in h4.text.lower():
        p = h4.find_next_sibling()
        p_txt = p.text.strip().replace('\n', ' ') if p else 'None'
        print(f"{h4.text.strip()}: {p_txt[:150]}")

print("\n=== INCLUSIONS & EXCLUSIONS ===")
for sec in soup.find_all(class_=re.compile(r'inclusion|exclusion|detail|overview|package', re.I)):
    txt = sec.get_text(separator=' | ', strip=True)
    if 'inclusion' in txt.lower() or 'exclusion' in txt.lower() or 'package' in txt.lower():
        print(f"[{sec.get('class')}]: {txt[:200]}")

print("\n=== PRICING & TARIFF DETAILS ===")
for tag in soup.find_all(['span', 'p', 'b', 'strong', 'div', 'h3', 'h4']):
    if any(k in tag.text.lower() for k in ['₹', 'rs.', 'price', 'fare', 'cost', 'per person']):
        if len(tag.text.strip()) < 100:
            print(f"Tag <{tag.name}>: {tag.text.strip()}")
