import json
import os
import sys
import django

sys.path.append('c:/Users/rithi/Documents/Documents Project Intership and Course/Projects/Rag chatbot/Travels Trip Managment Application')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import Package

with open('scripts/chennaitravels_category_packages.json', 'r', encoding='utf-8') as f:
    cat_data = json.load(f)

# Collect all distinct tour slugs/urls from the 3 pages
all_page_links = {}
for cat_name, items in cat_data.items():
    for item in items:
        slug = item['slug']
        url = item['url']
        title = item['title']
        if any(k in slug for k in ['car-rental', 'rental', 'email-protection', 'innova', 'swift', 'glanza', 'tempo-traveller', 'bus-rental', 'coach-rental', 'call-driver', 'attach-vehicle', 'cancellation', 'policy', 'airport-transfer', 'employee-transport']):
            continue
        clean_slug = slug.replace('.html', '').replace('/', '')
        if clean_slug and clean_slug not in all_page_links:
            all_page_links[clean_slug] = {'title': title, 'url': url, 'cat': cat_name}

print(f"Total distinct package slugs on the 3 category pages: {len(all_page_links)}")

# Check against existing packages in database
existing_ct = Package.objects.filter(package_code__startswith='SGT-CT-')
existing_names_slugs = set()
for p in existing_ct:
    s = p.package_code.lower()
    n = p.name.lower()
    existing_names_slugs.add(s)
    existing_names_slugs.add(n)

missing_slugs = []
matched_slugs = []

for slug, info in all_page_links.items():
    # Check if slug or title matches any existing package
    matched = False
    for p in existing_ct:
        # Check matching slug fragments
        slug_parts = [part for part in slug.split('-') if len(part) > 3 and part not in ['tour', 'package', 'chennai', 'from']]
        if any(part in p.package_code.lower() or part in p.name.lower() for part in slug_parts):
            matched = True
            matched_slugs.append((slug, p.package_code, p.name))
            break
    if not matched:
        missing_slugs.append((slug, info['title'], info['url'], info['cat']))

print(f"\nMatched slugs to existing SGT-CT packages: {len(matched_slugs)}")
print(f"Missing slugs (new packages on the site): {len(missing_slugs)}")

if missing_slugs:
    print("\n--- MISSING PACKAGES TO SCRAPE & IMPORT ---")
    for s, t, u, c in missing_slugs:
        print(f"  - {s:35} | {t:30} | {c:20} | {u}")
