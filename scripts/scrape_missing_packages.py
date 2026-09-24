import urllib.request
import re
import json
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

def clean_branding(text):
    if not text:
        return ""
    replacements = [
        (re.compile(r'Manoj\s+Tours\s*(?:&|and)\s*Travels', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Manoj\s+Travels', re.IGNORECASE), 'Siva Gayathri Tours & Travels'),
        (re.compile(r'Manoj', re.IGNORECASE), 'Siva Gayathri'),
        (re.compile(r'info@manojtravels\.in', re.IGNORECASE), 'info@sivagayathritravels.com'),
        (re.compile(r'\+91\s*98650\s*89000'), '+91 98425 33777'),
    ]
    cleaned = text
    for pattern, repl in replacements:
        cleaned = pattern.sub(repl, cleaned)
    return cleaned.strip()

def scrape_single(url):
    print(f"Scraping {url}...")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode('utf-8', errors='ignore')

    soup = BeautifulSoup(html, 'html.parser')
    for el in soup.find_all(['header', 'footer', 'nav', 'script', 'style']):
        el.decompose()

    tourhead = soup.find('h3', class_='tourhead')
    category_name = clean_branding(tourhead.get_text(strip=True)) if tourhead else "Five Days Tour Packages"

    textani = soup.find('h3', class_='textani')
    if textani:
        raw_title = textani.get_text(strip=True)
    else:
        raw_title = url.rstrip('/').split('/')[-1].replace('-', ' ').title()

    title = clean_branding(raw_title)

    desc = ""
    for p in soup.find_all('p'):
        pt = p.get_text(strip=True)
        if len(pt) > 25 and not 'cookie' in pt.lower() and not 'all rights' in pt.lower():
            desc = clean_branding(pt)
            break

    days = []
    dl = soup.find('dl')
    if dl:
        dts = dl.find_all('dt')
        dds = dl.find_all('dd')
        for dt, dd in zip(dts, dds):
            dt_text = dt.get_text(strip=True)
            dd_text = clean_branding(dd.get_text(strip=True))
            day_num_match = re.search(r'DAY\s*(\d+)', dt_text, re.IGNORECASE)
            day_num = int(day_num_match.group(1)) if day_num_match else len(days) + 1
            days.append({
                'day': day_num,
                'title': f"Day {day_num} - {title.replace('-', ' ')}",
                'details': dd_text
            })

    if not days:
        days.append({
            'day': 1,
            'title': f"Day 1 - {title.replace('-', ' ')}",
            'details': desc or title
        })

    return {
        'url': url,
        'category_name': category_name,
        'title': title,
        'description': desc,
        'days': days,
        'days_count': len(days)
    }

def main():
    missing_urls = [
        "https://manojtravels.in/packageDetails/6/coimbatore-ooty-wayanad-calicut",
        "https://manojtravels.in/packageDetails/6/coimbatore-ooty-wayanad-coimbatore",
        "https://manojtravels.in/packageDetails/6/madurai-munnar-ooty-mysore",
        "https://manojtravels.in/packageDetails/6/coimbatore-ooty-wayanad-coorg-mangalore",
        "https://manojtravels.in/packageDetails/6/madurai-rameshwaram-kanyakumari-trivandrum",
        "https://manojtravels.in/packageDetails/6/tirupur-ooty-kodaikanal-madurai-tirupur",
        "https://manojtravels.in/packageDetails/6/mysore-ooty-munnar-coimbatore",
        "https://manojtravels.in/packageDetails/6/mysore-ooty-kodaikanal-mysore",
        "https://manojtravels.in/packageDetails/6/madurai-ooty-mysore-bangalore",
    ]

    scraped_path = 'scripts/scraped_manoj_packages.json'
    with open(scraped_path, encoding='utf-8') as f:
        existing = json.load(f)

    existing_urls = set(p['url'] for p in existing)

    added = 0
    for url in missing_urls:
        if url in existing_urls:
            continue
        try:
            pkg_data = scrape_single(url)
            existing.append(pkg_data)
            added += 1
            print(f"Successfully scraped: {pkg_data['title']} ({pkg_data['days_count']} Days)")
        except Exception as e:
            print(f"Failed {url}: {e}")

    with open(scraped_path, 'w', encoding='utf-8') as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    print(f"\nAdded {added} missing packages. Total scraped records now: {len(existing)}")

if __name__ == '__main__':
    main()
