import os
import sys
import re
import json
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

pages = [
    'coimbatore-to-tiruchendur-group-tour.html',
    'coimbatore-to-sabarimala-group-tour.html',
    'coimbatore-to-tiruvannamalai-group-tour.html',
    'coimbatore-to-rameswaram-group-tour.html',
    'group-tours-from-coimbatore.html',
    'hourlypackages.html',
    'onewaydroptaxi.html'
]

print("=" * 70)
print("INSPECTING BHARATHIYAR TRAVELS PAGES")
print("=" * 70)

for p in pages:
    url = f"https://www.bharathiyartravels.com/{p}"
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        h1 = soup.find('h1')
        title = h1.text.strip() if h1 else (soup.title.text.strip() if soup.title else p)
        print(f"\n--- {p} ({len(r.text)} bytes) ---")
        print(f"Title: {title}")
        
        # Look for prices, vehicles, itinerary
        text_snippets = [s for s in soup.stripped_strings if any(w in s.lower() for w in ['₹', 'rs', 'day', 'itinerary', 'inclusions', 'price', 'tariff'])]
        print("Key snippets:", text_snippets[:8])
