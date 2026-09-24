import sys
import re
import json
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

test_urls = [
    'https://www.renghaholidays.com/packages/arulmigu-ramanathaswamy-temple-ramanathapuram-tamil-nadu-276-shiva-sthalangal',
    'https://www.renghaholidays.com/packages/alleppey-kochi-munnar-package-3n4d',
    'https://www.renghaholidays.com/packages/astonishing-dubai-with-abu-dhabi'
]

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page()

    # Session establishment
    page.goto('https://www.renghaholidays.com/', timeout=45000, wait_until='commit')
    for _ in range(15):
        page.wait_for_timeout(1000)
        try:
            if 'checking your browser' not in page.title().lower():
                break
        except:
            pass

    for u in test_urls:
        print("="*70)
        print("URL:", u)
        page.goto(u, timeout=25000, wait_until='domcontentloaded')
        page.wait_for_timeout(1500)
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Title
        h1 = soup.find('h1')
        title = h1.text.strip() if h1 else 'None'
        print("Title:", title)

        # Duration & Price
        price_match = re.findall(r'₹\s*([\d,]+)|Rs\.?\s*([\d,]+)', soup.text)
        print("Price matches in page:", price_match[:5])

        # Days in itinerary
        day_headers = soup.find_all(lambda t: t.name in ['h2', 'h3', 'h4', 'h5', 'b', 'strong'] and re.search(r'Day\s*0?\d+', t.text, re.I))
        print(f"Day headers found: {len(day_headers)}")
        for dh in day_headers[:4]:
            print("  Header:", dh.text.strip()[:80].replace('\n', ' '))

        # Inclusions
        inc = soup.find(string=re.compile(r'Inclusion', re.I))
        if inc:
            print("Inclusion found:", inc.parent.text.strip()[:100])

        # Image
        img = soup.find('img', class_=re.compile(r'banner|hero|package', re.I))
        if not img:
            img = soup.find('img', src=re.compile(r'/uploads/|/packages/', re.I))
        print("Hero img:", img['src'] if img else 'None')

    browser.close()
