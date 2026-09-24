import urllib.request
import ssl
import sys
from bs4 import BeautifulSoup
import json
import re

sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

def inspect_page(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove scripts and styles
            for s in soup(['script', 'style']):
                s.decompose()
                
            title = soup.title.string.strip() if soup.title else url
            headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'strong'])]
            tables = soup.find_all('table')
            
            # Extract text blocks
            paras = [p.get_text(strip=True) for p in soup.find_all(['p', 'li', 'td']) if len(p.get_text(strip=True)) > 20]
            
            print(f"\n=======================================================")
            print(f"URL: {url}")
            print(f"Title: {title}")
            print(f"Tables: {len(tables)} | Headings: {len(headings)}")
            print(f"Sample Headings: {headings[:8]}")
            print(f"Sample Text: {paras[:4]}")
            
            # Look for pricing or day numbers
            days = [p for p in paras if any(k in p.lower() for k in ['day 1', 'day 2', 'day 01', 'days', 'nights', 'rs.', '₹', 'inr'])]
            print(f"Day/Price mentions ({len(days)}): {days[:4]}")
            
    except Exception as e:
        print(f"Error inspecting {url}: {e}")

test_urls = [
    'https://www.chennaitourstravels.com/special-tour-packages.php',
    'https://www.chennaitourstravels.com/tamil-nadu-tour-package.php',
    'https://www.chennaitourstravels.com/south-special.php',
    'https://www.chennaitourstravels.com/students-ss-tour-package.php',
    'https://www.chennaitourstravels.com/weekend-ss-tour-package.php',
    'https://www.chennaitourstravels.com/aarupadaiveedu.php',
    'https://www.chennaitourstravels.com/tariff.php'
]

for u in test_urls:
    inspect_page(u)
