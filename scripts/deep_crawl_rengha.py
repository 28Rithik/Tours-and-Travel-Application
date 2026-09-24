import sys
import re
import json
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

print("Starting deep crawl of https://www.renghaholidays.com/...")

all_package_urls = set()

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    context = browser.new_context(viewport={'width': 1536, 'height': 800})
    page = context.new_page()

    # Establish session
    print("Navigating to https://www.renghaholidays.com/...")
    page.goto('https://www.renghaholidays.com/', timeout=45000, wait_until='commit')
    for _ in range(15):
        page.wait_for_timeout(1000)
        try:
            if 'checking your browser' not in page.title().lower():
                break
        except:
            pass

    # 1. Inspect sitemap.xml
    try:
        page.goto('https://www.renghaholidays.com/sitemap.xml', timeout=15000)
        page.wait_for_timeout(2000)
        content = page.content()
        # Look for <loc>
        locs = re.findall(r'<loc>(https://www\.renghaholidays\.com/(?:packages|page)/[^<]+)</loc>', content)
        print(f"Found {len(locs)} direct package/page locs in sitemap.xml")
        for l in locs:
            all_package_urls.add(l.strip())
    except Exception as e:
        print(f"Sitemap error: {e}")

    # 2. Get list of country pages from menu
    page.goto('https://www.renghaholidays.com/packages?', timeout=30000)
    page.wait_for_timeout(2000)
    html = page.content()
    soup = BeautifulSoup(html, 'html.parser')
    
    country_links = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/packages/country/' in href or '/packages/city/' in href or '/packages/category/' in href or '/packages/pilgrimage' in href:
            if href.startswith('/'):
                href = 'https://www.renghaholidays.com' + href
            country_links.add(href)

    print(f"Found {len(country_links)} country/category listing hubs!")

    # 3. Visit each country hub and collect package cards
    for c_url in sorted(list(country_links)):
        try:
            print(f"Visiting hub: {c_url.split('/')[-1]}...")
            page.goto(c_url, timeout=20000, wait_until='domcontentloaded')
            page.wait_for_timeout(1000)
            c_html = page.content()
            c_soup = BeautifulSoup(c_html, 'html.parser')
            # Look for package links
            for a in c_soup.find_all('a', href=True):
                h = a['href'].strip()
                if '/packages/' in h and not any(k in h for k in ['/country/', '/city/', '/category/', '/packages?', 'javascript:']):
                    if h.startswith('/'):
                        h = 'https://www.renghaholidays.com' + h
                    if h.rstrip('/') != 'https://www.renghaholidays.com/packages':
                        all_package_urls.add(h)
        except Exception as e:
            print(f"  Error on {c_url}: {e}")

    # 4. Check main /packages? with multiple scroll/pagination
    page.goto('https://www.renghaholidays.com/packages?', timeout=30000)
    page.wait_for_timeout(2000)
    for _ in range(10):
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        page.wait_for_timeout(1000)
    p_html = page.content()
    p_soup = BeautifulSoup(p_html, 'html.parser')
    for a in p_soup.find_all('a', href=True):
        h = a['href'].strip()
        if '/packages/' in h and not any(k in h for k in ['/country/', '/city/', '/category/', '/packages?', 'javascript:']):
            if h.startswith('/'):
                h = 'https://www.renghaholidays.com' + h
            if h.rstrip('/') != 'https://www.renghaholidays.com/packages':
                all_package_urls.add(h)

    # Filter out social share URLs or non-canonical
    cleaned = []
    for u in all_package_urls:
        u_clean = u.split('?')[0].split('#')[0]
        if 'linkedin.com' in u_clean or 'twitter.com' in u_clean or 'facebook.com' in u_clean:
            # extract the actual url parameter
            m = re.search(r'url=(https://www\.renghaholidays\.com/packages/[^&]+)', u)
            if m:
                u_clean = m.group(1)
            else:
                continue
        if u_clean.startswith('https://www.renghaholidays.com/packages/') or u_clean.startswith('https://www.renghaholidays.com/page/'):
            if u_clean.rstrip('/') not in ['https://www.renghaholidays.com/packages', 'https://www.renghaholidays.com/page']:
                cleaned.append(u_clean)

    cleaned = sorted(list(dict.fromkeys(cleaned)))
    print("\n" + "="*70)
    print(f"TOTAL UNIQUE RENGHA TOUR PACKAGES DISCOVERED: {len(cleaned)}")
    print("="*70)
    for u in cleaned[:30]:
        print(" ", u)
    if len(cleaned) > 30:
        print(f"  ... and {len(cleaned) - 30} more packages!")

    with open('scripts/all_rengha_package_urls.json', 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, indent=2)

    browser.close()
