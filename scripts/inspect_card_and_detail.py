import sys
import urllib.request
import re
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

# 1. Inspect Card on listing
list_url = 'https://www.holidify.com/region/south-india/packages.html?pageNum=0'
req = urllib.request.Request(list_url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
soup = BeautifulSoup(html, 'html.parser')

cards = soup.find_all('div', class_=lambda c: c and ('package-card' in c.lower() or ('package' in c and 'card' in c)))
if not cards:
    cards = soup.select('.col-12.col-lg-9 #pacakgeList > div')

print(f"Cards found on page: {len(cards)}")
first_card = None
detail_url = None
for c in cards:
    link = c.find('a', href=lambda h: h and '/tour-package/' in h)
    if link:
        first_card = c
        detail_url = 'https://www.holidify.com' + link['href']
        break

if first_card:
    print("\n=== FIRST CARD TEXT ===")
    print(first_card.get_text(separator=' | ', strip=True))

if detail_url:
    print(f"\n=== FETCHING DETAIL PAGE: {detail_url} ===")
    d_req = urllib.request.Request(detail_url, headers={'User-Agent': 'Mozilla/5.0'})
    d_html = urllib.request.urlopen(d_req, timeout=15).read().decode('utf-8', errors='ignore')
    d_soup = BeautifulSoup(d_html, 'html.parser')

    # Title
    h1 = d_soup.find('h1')
    print("H1 Title:", h1.text.strip() if h1 else 'None')

    # Overview / Duration / Price
    price_tag = d_soup.find(class_=re.compile(r'price', re.I))
    print("Price Tag:", price_tag.text.strip() if price_tag else 'None')

    # Overview text
    overview = d_soup.find(class_=re.compile(r'overview|description|about', re.I))
    if overview:
        print("Overview snippet:", overview.text.strip()[:200])

    # Itinerary days
    itinerary_sections = d_soup.find_all(class_=re.compile(r'itinerary|day-plan|dayPlan|daywise', re.I))
    print("Itinerary sections found:", len(itinerary_sections))
    for s in itinerary_sections[:5]:
        print(" Itinerary element:", s.name, s.get('class'), s.text.strip()[:100])

    # Check headings for Day 1, Day 2 etc.
    day_headings = d_soup.find_all(lambda tag: tag.name in ['h2', 'h3', 'h4', 'h5', 'div'] and re.match(r'^(Day\s*\d+|Day\s*-\s*\d+)', tag.text.strip(), re.I))
    print("Day headings count:", len(day_headings))
    for dh in day_headings:
        print(" ", dh.text.strip())

    # Inclusions & Exclusions
    inc_sections = d_soup.find_all(lambda tag: tag.name in ['div', 'ul', 'section'] and any(k in tag.get('class', []) for k in ['inclusion', 'inclusions', 'exclusion', 'exclusions']))
    print("Inclusions/Exclusions sections:", len(inc_sections))
