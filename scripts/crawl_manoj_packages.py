import urllib.request
import re
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

def fetch_url(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def main():
    # First, fetch tourPackages home
    home_html = fetch_url('https://manojtravels.in/tourPackages')
    if not home_html:
        return

    soup = BeautifulSoup(home_html, 'html.parser')
    
    # Extract all package detail links from navbar and body
    category_links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/packageDetails/' in href or 'packageDetails/' in href:
            cleaned = href if href.startswith('http') else 'https://manojtravels.in/' + href.lstrip('/')
            if cleaned not in category_links:
                category_links.append(cleaned)

    print(f"Found {len(category_links)} base category/package links on tourPackages page:")
    for l in category_links:
        print("  -", l)

    # Now discover all sub-packages by visiting each category page
    all_packages = {}
    for cat_url in category_links:
        print(f"\nScanning category link: {cat_url}...")
        html = fetch_url(cat_url)
        if not html:
            continue
        sub_soup = BeautifulSoup(html, 'html.parser')
        
        # Look for the side menu or links on this page
        for a in sub_soup.find_all('a', href=True):
            href = a['href']
            if 'packageDetails/' in href:
                full_url = href if href.startswith('http') else 'https://manojtravels.in/' + href.lstrip('/')
                text = a.get_text(strip=True)
                if full_url not in all_packages:
                    all_packages[full_url] = text

    print(f"\n==========================================")
    print(f"TOTAL UNIQUE TOUR PACKAGES FOUND: {len(all_packages)}")
    print(f"==========================================")
    for u, t in sorted(all_packages.items()):
        print(f"{t:40} | {u}")

if __name__ == '__main__':
    main()
