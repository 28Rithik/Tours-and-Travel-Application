import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('scripts/crawled_chennaitourstravels_packages.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total crawled items: {len(data)}")

# Group by patterns
categories = {
    'south_special_multiday': [],
    'ex_chennai_1day_outstation': [],
    'pilgrimage_temple_circuits': [],
    'chennai_local_sightseeing': [],
    'destination_tour_guides': [],
    'other': []
}

for d in data:
    slug = d['slug']
    title = d['title']
    url = d['url']
    h = d.get('headings', [])
    
    if any(k in slug for k in ['ss-tour', 'mysore-ooty', 'bangalore-mysore']):
        categories['south_special_multiday'].append((slug, title, len(d.get('days_plan', []))))
    elif any(k in slug for k in ['chennai-', 'chenji', 'tirupathi', 'kanchipuram', 'mahabalipuram', 'pondichary', 'nagapattinam', 'vellore']) and 'temple' not in slug and 'local' not in slug:
        categories['ex_chennai_1day_outstation'].append((slug, title, len(d.get('days_plan', []))))
    elif any(k in slug for k in ['aarupadai', 'navagraha', 'navathirupati', 'navakailasam', 'temple', 'pilgrimage', 'divya-desam', 'panchabhoota']):
        categories['pilgrimage_temple_circuits'].append((slug, title, len(d.get('days_plan', []))))
    elif 'local' in slug or 'chennai-city' in slug:
        categories['chennai_local_sightseeing'].append((slug, title, len(d.get('days_plan', []))))
    elif '-tour' in slug or '-tourism' in slug:
        categories['destination_tour_guides'].append((slug, title, len(d.get('days_plan', []))))
    else:
        categories['other'].append((slug, title, len(d.get('days_plan', []))))

for cat, items in categories.items():
    print(f"\n==================== {cat.upper()} ({len(items)} items) ====================")
    for slug, title, num_days in items:
        print(f"  - {slug:35} | {title[:50]:50} | {num_days} days")
