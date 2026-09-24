import json

with open('scripts/chennaitravels_category_packages.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for cat in ['temple_tour_packages', 'main_tour_packages']:
    items = data[cat]
    print(f"\n==================== {cat.upper()} ====================")
    tour_items = []
    for item in items:
        url = item['url']
        title = item['title']
        slug = item['slug']
        if any(k in slug for k in ['car-rental', 'rental', 'email-protection', 'innova', 'swift', 'glanza', 'tempo-traveller', 'bus-rental', 'coach-rental', 'call-driver', 'attach-vehicle', 'cancellation', 'policy', 'airport-transfer', 'employee-transport']):
            continue
        tour_items.append((slug, title, url))
    print(f"Total tour items in {cat}: {len(tour_items)}")
    for s, t, u in tour_items:
        print(f"  - {s:45} | {t[:40]:40} | {u}")

