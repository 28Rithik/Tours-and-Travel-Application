import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('scripts/hiphop_full_extracted_pages.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for slug in ['tamil-nadu-group-tour', 'tamil-nadu-family-trip', 'karnataka-family-trip', 'goa-college-iv-trip', 'goa-family-trip', 'kerala-college-iv-trip']:
    if slug in data:
        p = data[slug]
        print(f"\n=================== {slug} ({p['title']}) ===================")
        lines = p['lines']
        for i, l in enumerate(lines):
            if any(k in l.lower() for k in ['itinerary', 'day 1', 'day 2', 'day 3', 'day 4', 'package 1', 'package 2', 'package 3', 'package 4']):
                print(f"[{i}] {l}")
                for j in range(i+1, min(i+5, len(lines))):
                    print(f"     -> {lines[j]}")
