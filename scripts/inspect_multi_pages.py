import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('scripts/crawled_chennaitourstravels_packages.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for d in data:
    if 'kerala-package' in d['url'] or 'pilgrimage-ss-tour-package' in d['url']:
        print("="*70)
        print(f"URL: {d['url']}")
        print(f"Slug: {d['slug']}")
        print(f"Title: {d['title']}")
        print(f"Headings: {d['headings']}")
        print(f"Total days extracted: {len(d.get('days_plan', []))}")
        print("First 5 days extracted:")
        for dp in d.get('days_plan', [])[:5]:
            print(f"   Day {dp['day']}: {dp['activities'][:100]}")
        print("Content Summary Sample (first 1000 chars):")
        print(d.get('content_summary', '')[:1000])
