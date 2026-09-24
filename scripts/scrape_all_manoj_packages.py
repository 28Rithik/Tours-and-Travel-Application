import urllib.request
import re
import json
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

def clean_branding(text):
    if not text:
        return ""
    # Replace Manoj Travels variations with Siva Gayathri Tours & Travels
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

def scrape_single_package(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return None, f"Fetch error: {e}"

    soup = BeautifulSoup(html, 'html.parser')

    # Remove headers, footers, navs
    for el in soup.find_all(['header', 'footer', 'nav', 'script', 'style']):
        el.decompose()

    # Category name
    tourhead = soup.find('h3', class_='tourhead')
    category_name = clean_branding(tourhead.get_text(strip=True)) if tourhead else "Tour Package"

    # Package title / route
    textani = soup.find('h3', class_='textani')
    if textani:
        raw_title = textani.get_text(strip=True)
    else:
        # Fallback to URL slug
        raw_title = url.rstrip('/').split('/')[-1].replace('-', ' ').title()

    title = clean_branding(raw_title)

    # Description / lead
    desc = ""
    for p in soup.find_all('p'):
        pt = p.get_text(strip=True)
        if len(pt) > 25 and not 'cookie' in pt.lower() and not 'all rights' in pt.lower():
            desc = clean_branding(pt)
            break

    # Itinerary days from <dl>
    days = []
    dl = soup.find('dl')
    if dl:
        dts = dl.find_all('dt')
        dds = dl.find_all('dd')
        for dt, dd in zip(dts, dds):
            dt_text = dt.get_text(strip=True)
            dd_text = clean_branding(dd.get_text(strip=True))
            # Extract day number
            day_num_match = re.search(r'DAY\s*(\d+)', dt_text, re.IGNORECASE)
            day_num = int(day_num_match.group(1)) if day_num_match else len(days) + 1
            days.append({
                'day': day_num,
                'title': f"Day {day_num} - {title.replace('-', ' ')}",
                'details': dd_text
            })

    # If no dl, check fallback text
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
    }, None

def main():
    # Load all unique URLs from task log
    log_path = 'C:/Users/rithi/.gemini/antigravity-ide/brain/a52d1d7f-5f0a-4be5-ada5-541a5b0a7549/.system_generated/tasks/task-6812.log'
    with open(log_path, encoding='utf-8', errors='ignore') as f:
        log_text = f.read()

    matches = re.findall(r'https://manojtravels\.in/packageDetails/[^\s]+', log_text)
    urls = sorted(list(set(matches)))
    print(f"Total candidate URLs to scrape: {len(urls)}")

    results = []
    errors = 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(scrape_single_package, u): u for u in urls}
        for future in as_completed(future_to_url):
            data, err = future.result()
            if data:
                results.append(data)
            else:
                errors += 1

    print(f"\nSuccessfully scraped {len(results)} packages (Errors: {errors})")
    
    # Save to JSON artifact
    out_json = 'scripts/scraped_manoj_packages.json'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Saved scraped data to {out_json}")

    # Print summary statistics
    by_cat = {}
    for r in results:
        cat = r['category_name']
        by_cat[cat] = by_cat.get(cat, 0) + 1

    print("\nBreakdown by Category:")
    for c, count in sorted(by_cat.items()):
        print(f"  - {c}: {count} packages")

if __name__ == '__main__':
    main()
