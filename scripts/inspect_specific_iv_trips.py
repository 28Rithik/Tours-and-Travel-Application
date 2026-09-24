import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('scripts/hiphop_full_extracted_pages.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for slug in ['kullu-manali', 'karnataka-college-iv-trip', 'tamil-nadu-college-iv-trip', 'goa-college-iv-trip', 'karnataka-group-tour', 'goa-group-tours', 'diwali']:
    if slug in data:
        p = data[slug]
        print(f"\n=================== {slug} ({p['title']}) ===================")
        lines = p['lines']
        for i, l in enumerate(lines):
            if any(k in l.lower() for k in ['day 1', 'day 2', 'day 3', 'day 4', 'day 5', 'itinerary', 'starting from', 'duration', 'min people', 'activities', 'price includes', 'price excludes']):
                print(f"[{i}] {l}")
                for j in range(i+1, min(i+5, len(lines))):
                    print(f"     -> {lines[j]}")
