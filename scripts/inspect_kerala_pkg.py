import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('scripts/crawled_chennaitourstravels_packages.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for d in data:
    if 'kerala-package' in d['url']:
        headings = d.get('headings', [])
        print("Kerala-package Headings:")
        for h in headings:
            print("  -", h)
        print("\nLength of content_summary:", len(d.get('content_summary', '')))
        print("Total days plan:", len(d.get('days_plan', [])))
        break
