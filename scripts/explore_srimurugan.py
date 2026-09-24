import urllib.request
import re
import json
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 1. Check robots.txt & sitemap.xml
for f in ['robots.txt', 'sitemap.xml']:
    try:
        url = f'https://www.srimurugantravel.com/{f}'
        resp = urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=10)
        content = resp.read().decode('utf-8', errors='ignore')
        print(f"=== {f} (Status: {resp.status}, Length: {len(content)}) ===")
        print(content[:600])
        print("\n")
    except Exception as e:
        print(f"{f} error: {e}")

# 2. Parse home page for links
home_url = 'https://www.srimurugantravel.com/'
resp = urllib.request.urlopen(urllib.request.Request(home_url, headers=headers), timeout=15)
soup = BeautifulSoup(resp.read().decode('utf-8', errors='ignore'), 'html.parser')

all_links = set()
for a in soup.find_all('a', href=True):
    href = a['href'].strip()
    if href and not href.startswith('#') and not href.startswith('tel:') and not href.startswith('mailto:') and not href.startswith('javascript:'):
        if href.startswith('/'):
            href = 'https://www.srimurugantravel.com' + href
        elif not href.startswith('http'):
            href = 'https://www.srimurugantravel.com/' + href
        if 'srimurugantravel.com' in href:
            all_links.add(href)

print(f"Total internal links on homepage: {len(all_links)}")
for l in sorted(list(all_links)):
    print(" ", l)
