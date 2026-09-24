import urllib.request
import ssl
import sys
from bs4 import BeautifulSoup
import re
import json

sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

def clean_brand(text):
    if not text:
        return ""
    text = re.sub(r'Content on this page requires a newer version of Adobe Flash Player\.?', '', text, flags=re.I)
    text = re.sub(r'HAPPY TIME AHEAD WITH (?:OUR )?TRAVEL AHEAD(?:\s*TOURS)?\.?', 'Happy Journey with Siva Gayathri Tours & Travels!', text, flags=re.I)
    text = re.sub(r'Travel Ahead(?:\s*Tours)?', 'Siva Gayathri Tours & Travels', text, flags=re.I)
    text = re.sub(r'Chennai Tours\s*(?:and|&)?\s*Travels(?:\s*-\s*Direct Tour Operators)?', 'Siva Gayathri Tours & Travels', text, flags=re.I)
    text = re.sub(r'chennaitourstravels\.com', 'sivagayathritravels.com', text, flags=re.I)
    text = re.sub(r'\+?91[\s-]?[0-9]{10}', '+91 98425 33777', text)
    text = re.sub(r'[a-zA-Z0-9_.+-]+@(?:chennaitourstravels|travelahead)\.[a-zA-Z0-9-.]+', 'booking@sivagayathritravels.com', text, flags=re.I)
    return text.strip()

test_urls = [
    ('chennai-kanchipuram', 'https://chennaitourstravels.com/chennai-kanchipuram-tour-packages.php'),
    ('chennai-mahabalipuram', 'https://chennaitourstravels.com/chennai-mahabalipuram-tour-packages.php'),
    ('chennai-pondicherry', 'https://chennaitourstravels.com/chennai-pondichary-tour-packages.php'),
    ('chennai-vellore', 'https://chennaitourstravels.com/chennai-vellore-tour-packages.php'),
    ('chennai-chenji', 'https://chennaitourstravels.com/chennai-chenji-tour-packages.php'),
    ('navagraha-tour', 'https://chennaitourstravels.com/navagraha-tour.php'),
    ('weekend-ss', 'https://chennaitourstravels.com/weekend-ss-tour-package.php'),
    ('students-ss', 'https://chennaitourstravels.com/students-ss-tour-package.php'),
    ('pilgrimage-ss', 'https://chennaitourstravels.com/pilgrimage-ss-tour-package.php'),
]

for name, url in test_urls:
    print(f"\n{'='*70}\nFETCHING: {name} ({url})")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            for s in soup(['script', 'style', 'noscript']):
                s.decompose()
            
            title = soup.title.string.strip() if soup.title else ""
            
            # Find main content
            text_lines = [clean_brand(l.strip()) for l in soup.get_text('\n').split('\n') if l.strip()]
            text_clean = '\n'.join([l for l in text_lines if l and 'Adobe Flash' not in l])
            
            # Look for pricing
            rates = re.findall(r'(?:Rs\.?|₹|INR)\s*([0-9,]+)', text_clean, re.I)
            
            print(f"Title: {title}")
            print(f"Rates found: {rates[:5]}")
            print(f"First 15 lines of content:")
            for l in text_lines[:15]:
                if l and 'Adobe Flash' not in l:
                    print("  *", l[:90])
    except Exception as e:
        print("Error:", e)
