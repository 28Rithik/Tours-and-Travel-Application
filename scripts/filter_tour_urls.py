import json

with open('scripts/chennaitourstravels_links.json', 'r', encoding='utf-8') as f:
    links = json.load(f)

# Normalize URLs: replace http://www. or http:// with https://www.chennaitourstravels.com
clean_links = set()
for l in links:
    norm = l.replace('http://', 'https://').replace('https://chennaitourstravels.com', 'https://www.chennaitourstravels.com')
    # Filter out static assets or non-tour pages
    if any(norm.endswith(ext) for ext in ['.jpg', '.png', '.jpeg', '.gif', '.css', '.js']):
        continue
    clean_links.add(norm)

clean_links = sorted(clean_links)
print(f"Total clean URLs: {len(clean_links)}")

exclude_slugs = ['contact', 'about', 'feedback', 'disclaimer', 'privacy', 'sitemap', 'index.php', 'car-rental-chennai.php', 'van-rental-chennai.php', 'bus-rental-chennai.php']

tour_urls = []
for l in clean_links:
    slug = l.split('/')[-1].lower()
    if not any(ex in slug for ex in exclude_slugs):
        tour_urls.append(l)

print(f"Tour URLs ({len(tour_urls)}):")
for u in tour_urls:
    print("  ", u)

with open('scripts/chennaitourstravels_tour_urls.json', 'w', encoding='utf-8') as f:
    json.dump(tour_urls, f, indent=2)
