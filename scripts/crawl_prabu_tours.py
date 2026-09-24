import os
import sys
import re
import json
import time
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

PAGES = [
    ('1day-ooty-tour-packages.php', 1, 'hill_station'),
    ('guruvayur-tour-packages-coimbatore.php', 1, 'devotional'),
    ('athirapally-waterfalls-malampuzha-dam.php', 1, 'holiday'),
    ('coimbatore-black-thunder-themepark.php', 1, 'family_vacation'),
    ('valparai-tour-packages-coimbatore.php', 1, 'hill_station'),
    ('palani-tour-packages-coimbatore.php', 1, 'devotional'),
    ('coimbatore-templetours-avinashi-lingeshwara-pariyur-amman-bhavani-chennimalai-murugan-sivanmalai.php', 1, 'devotional'),
    ('maruthamalai-perur-vellingiri-puliyakulam-temple-tours.php', 1, 'devotional'),
    ('karamadai-ranganathar-vanabathrakaliamman-then-thirupathi-bannariamman-templetours.php', 1, 'devotional'),
    ('thirumoorthihills-pollachi-masaniamman-temple-aaliyardam-eachanari-mahalakshmi-templetours.php', 1, 'devotional'),
    ('guruvayur-cochin-2days-packages.php', 2, 'devotional'),
    ('mysore-coimbatore-tour-packages.php', 2, 'holiday'),
    ('valparai-packages-tours-coimbatore.php', 2, 'hill_station'),
    ('ooty-2days-tourpackages-coimbatore.php', 2, 'hill_station'),
    ('munnar-2days-tourpackages-coimbatore.php', 2, 'hill_station'),
    ('coimbatore-tiruvannamalai-tourpackages.php', 2, 'devotional'),
    ('coimbatore-sabarimala-tourpackages.php', 2, 'devotional'),
    ('navagraha-temple-tourpackages.php', 2, 'devotional'),
    ('ooty-tour-packages-coimbatore.php', 3, 'hill_station'),
    ('kodaikanal-tour-packages-coimbatore.php', 3, 'hill_station'),
    ('coorg-mysore-packages-coimbatore.php', 3, 'hill_station'),
    ('valparai-three-days-packages-coimbatore.php', 3, 'hill_station'),
    ('palani-madurai-rameshwaram-tourpackages.php', 3, 'devotional'),
    ('ooty-coorg-hill-station-packages.php', 4, 'hill_station'),
    ('ooty-wayanad-hill-station-packages.php', 4, 'hill_station'),
    ('alleppey-munnar-leisure-tourpackages-coimbatore.php', 5, 'holiday'),
    ('kerala-tourspackages-from-coimbatore.php', 5, 'holiday'),
    ('ooty-mudumalai-coonoor-tourpackages.php', 5, 'hill_station'),
    ('kumarakom-kerala-packagetours.php', 6, 'holiday'),
    ('kerala-packagetours-coimbatore.php', 6, 'holiday'),
    ('ooty-wayanad-coorg-bangalore.php', 6, 'hill_station'),
    ('honeymoon-tour-packages-coimbatore.php', 6, 'family_vacation'),
    ('kerala-honeymoon-tour-packages.php', 6, 'family_vacation'),
    ('bangalore-mysore-ooty-tourpackages.php', 7, 'holiday'),
    ('kerala-tour-packages-coimbatore.php', 7, 'holiday'),
    ('ooty-kodaikanal-rameshwaram-madurai-packages.php', 7, 'holiday'),
    ('ooty-mysore-coorg-packagetours.php', 7, 'hill_station'),
    ('kodaikanal-madurai-rameshwaram-kanyakumari.php', 8, 'holiday'),
    ('madurai-kanyakumari-kovalam-trivandrum-tourpackages.php', 8, 'holiday'),
]

def clean_rebrand(text: str) -> str:
    if not text:
        return ""
    s = text
    s = s.replace('\u2013', ' - ').replace('\u2014', ' - ').replace('\u00a0', ' ').replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    s = re.sub(r'https?://(?:www\.)?prabutourstravels\.com\S*', '', s, flags=re.I)
    s = re.sub(r'wa\.me/\+?91\d+', 'wa.me/919842533777', s, flags=re.I)
    s = re.sub(r'\b(?:www\.)?prabutourstravels\.com\b', 'sivagayathritravels.com', s, flags=re.I)
    s = re.sub(r'\b(?:www\.)?besttempotravellerrental\.com\b', 'sivagayathritravels.com', s, flags=re.I)
    s = re.sub(r'\bPrabu(?:\s+Tours(?:\s+and(?:\s+Travels)?)?|\s+Travels)?\b', 'Siva Gayathri Tours & Travels', s, flags=re.I)
    s = re.sub(r'\bMr\.Prabu\b', 'Mr. Rithik CA', s, flags=re.I)
    s = re.sub(r'\+91-?9840108069|98401-?08069|9840108069', '+91 98425 33777', s)
    s = re.sub(r'\+91-?8220202056|82202-?02056|8220202056', '+91 94381 7131', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def crawl_package(filename, def_days, category):
    url = f"https://www.prabutourstravels.com/{filename}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, 'html.parser')

        # Title
        h1 = soup.find('h1')
        title = clean_rebrand(h1.text.strip()) if h1 else filename.replace('.php', '').replace('-', ' ').title()
        title = re.sub(r'Tour from Coimbatore', 'Tour from Coimbatore', title, flags=re.I)
        title = re.sub(r'Tourpackages', 'Tour Package', title, flags=re.I)
        title = title.upper()
        if not any(title.endswith(suf) for suf in ['PACKAGE', 'TOUR', 'TRIP', 'SPECIAL']):
            title = f"{title} TOUR PACKAGE"

        # Destination
        dest_h4 = soup.find(lambda e: e.name in ['h4', 'h3', 'h2'] and 'destination covered' in e.text.lower())
        dest = ""
        if dest_h4:
            p_next = dest_h4.find_next(['p', 'div', 'ul'])
            if p_next:
                dest = clean_rebrand(p_next.text.strip())
        if not dest:
            dest = title.replace('TOUR PACKAGE', '').replace('FROM COIMBATORE', '').strip()

        # Itinerary Days
        days = []
        for li in soup.find_all('li', class_='list-group-item'):
            span = li.find('span', class_='day-pad')
            if span:
                d_name = span.text.strip()
                span.extract()
                d_text = clean_rebrand(li.text.strip())
                days.append({
                    'day': d_name,
                    'text': d_text
                })

        # Inclusions & Exclusions
        inclusions = [
            "Chauffeur-driven sanitized tourist vehicle for the entire sightseeing circuit",
            "Driver day & night allowance and bata included",
            "Toll gate charges, interstate permits, and vehicle parking fees included",
            "All applicable travel taxes & GST included with zero hidden extras",
            "Dedicated 24/7 tour coordination by Siva Gayathri Tours & Travels"
        ]
        exclusions = [
            "Monument entrance tickets, boating charges, and safari ride passes",
            "Temple special darshan passes and pooja charges",
            "Lunch, dinner, snacks, and personal beverages",
            "Hotel stay unless explicitly opted with room accommodation",
            "Personal laundry, room service, or driver gratuity tips"
        ]

        actual_days = len(days) if len(days) > 0 else def_days
        actual_nights = max(1, actual_days - 1) if actual_days > 1 else 0

        # If days weren't parsed from list-group-item, generate standard itinerary
        if not days:
            for d in range(1, actual_days + 1):
                days.append({
                    'day': f"Day {d}",
                    'text': f"Full day sightseeing covering key attractions across {dest}. Private sanitized tourist vehicle transfers managed by Siva Gayathri Tours & Travels."
                })

        return {
            'filename': filename,
            'url': url,
            'title': title,
            'destination': dest,
            'category': category,
            'duration_days': actual_days,
            'duration_nights': actual_nights,
            'inclusions': inclusions,
            'exclusions': exclusions,
            'itinerary': days
        }
    except Exception as e:
        print(f"Error crawling {filename}: {e}")
        return None

def main():
    print("=" * 70, flush=True)
    print("CRAWLING ALL 39 TOUR PACKAGES FROM PRABU TOURS & TRAVELS", flush=True)
    print("=" * 70, flush=True)

    results = []
    for fn, days, cat in PAGES:
        data = crawl_package(fn, days, cat)
        if data:
            results.append(data)
            print(f"  ✓ [{data['duration_days']}D] {data['title'][:50]} ({len(data['itinerary'])} days parsed)", flush=True)
        else:
            print(f"  ✗ Failed to fetch {fn}", flush=True)

    print("\n" + "=" * 70, flush=True)
    print(f"TOTAL PACKAGES CRAWLED: {len(results)}", flush=True)
    print("=" * 70, flush=True)

    with open('scripts/prabu_crawled_packages.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print("Saved to scripts/prabu_crawled_packages.json", flush=True)

if __name__ == '__main__':
    main()
