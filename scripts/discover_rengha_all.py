import sys
import re
import json
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

print("Launching Chrome via Playwright to explore https://www.renghaholidays.com/...")

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    context = browser.new_context(viewport={'width': 1536, 'height': 800})
    page = context.new_page()

    # 1. Establish session
    print("Navigating to https://www.renghaholidays.com/...")
    page.goto('https://www.renghaholidays.com/', timeout=45000, wait_until='commit')
    for _ in range(15):
        page.wait_for_timeout(1000)
        try:
            if 'checking your browser' not in page.title().lower():
                break
        except:
            pass

    print(f"Homepage Title: {page.title()}")

    # 2. Check sitemap.xml in browser context
    sitemap_urls = []
    try:
        page.goto('https://www.renghaholidays.com/sitemap.xml', timeout=15000)
        page.wait_for_timeout(2000)
        content = page.content()
        sitemap_urls = re.findall(r'<loc>(https://www\.renghaholidays\.com/[^<]*)</loc>', content)
        print(f"URLs found in sitemap.xml: {len(sitemap_urls)}")
    except Exception as e:
        print(f"Sitemap check error: {e}")

    # 3. Check /packages? listing page
    print("Navigating to https://www.renghaholidays.com/packages?...")
    page.goto('https://www.renghaholidays.com/packages?', timeout=30000, wait_until='networkidle')
    page.wait_for_timeout(3000)
    print(f"Packages Page Title: {page.title()}")

    # Scroll down to load lazy/infinite content
    prev_height = 0
    for i in range(15):
        curr_height = page.evaluate('document.body.scrollHeight')
        if curr_height == prev_height:
            break
        prev_height = curr_height
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        page.wait_for_timeout(1500)

    html = page.content()
    soup = BeautifulSoup(html, 'html.parser')

    all_links = set()
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if '/packages/' in href or '/page/' in href or '/tour/' in href:
            if href.startswith('/'):
                href = 'https://www.renghaholidays.com' + href
            if 'renghaholidays.com' in href:
                all_links.add(href)

    print(f"Total package links found on /packages? after scrolling: {len(all_links)}")

    # Check pagination elements
    pagination = soup.find_all(class_=re.compile(r'pagination|page', re.I))
    print(f"Pagination elements count: {len(pagination)}")
    for p_el in pagination[:3]:
        print("  Pagination:", p_el.get_text(strip=True)[:100])

    # Also check navigation menu categories
    nav_links = set()
    for a in soup.select('nav a, header a, .menu a, .dropdown a'):
        href = a.get('href', '')
        if href and 'renghaholidays.com' in href or href.startswith('/'):
            if href.startswith('/'):
                href = 'https://www.renghaholidays.com' + href
            nav_links.add(href)

    print(f"Total navigation links: {len(nav_links)}")
    for l in sorted(list(nav_links)):
        if any(k in l.lower() for k in ['package', 'tour', 'domestic', 'international', 'holiday', 'honeymoon']):
            print("  Nav link:", l)

    # Combine sitemap URLs and page links
    combined_pkg_urls = set()
    for u in sitemap_urls + list(all_links):
        if '/packages/' in u or '/page/' in u:
            # exclude listing base URLs
            if u.rstrip('/') not in ['https://www.renghaholidays.com/packages']:
                combined_pkg_urls.add(u)

    print(f"\nTotal combined unique package URLs found so far: {len(combined_pkg_urls)}")
    for u in sorted(list(combined_pkg_urls))[:20]:
        print(" ", u)

    with open('scripts/rengha_discovered_urls.json', 'w', encoding='utf-8') as f:
        json.dump(sorted(list(combined_pkg_urls)), f, indent=2)

    browser.close()
