import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('scripts/hiphop_full_extracted_pages.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for slug in ['karnataka-college-iv-trip', 'goa', 'kullu-manali']:
    if slug in data:
        p = data[slug]
        print(f"\n=================== {slug} ({p['title']}) ===================")
        lines = p['lines']
        for i, l in enumerate(lines):
            if any(k in l.lower() for k in ['itinerary', 'day 1', 'day 2', 'day 3', 'package 1', 'package 2', 'package 3', '₹', 'price', 'guest', 'cost', 'hotel']):
                print(f"[{i}] {l}")
                for j in range(i+1, min(i+4, len(lines))):
                    print(f"     -> {lines[j]}")
