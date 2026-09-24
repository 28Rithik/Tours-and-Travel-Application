import os
import sys
import json
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

url = "https://hiphopholidays.in/kerala-college-iv-trip/"
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

print("Page Title:", soup.title.text if soup.title else "No title")

# Look for duration, price, itinerary
for item in soup.find_all(['div', 'section', 'ul'], class_=lambda c: c and any(k in c.lower() for k in ['itinerary', 'day', 'schedule', 'elementor-widget-accordion', 'elementor-widget-toggle', 'timeline', 'price', 'overview'])):
    text = ' '.join(item.stripped_strings)
    if any(w in text.lower() for w in ['day 1', 'day 2', 'itinerary', 'duration', 'industrial visit']):
        print(f"\n--- MATCH ({item.name}, {item.get('class')}) ---")
        print(text[:400])
