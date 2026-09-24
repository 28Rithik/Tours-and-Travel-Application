import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('scripts/crawled_chennaitourstravels_packages.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total entries: {len(data)}")

targets = ['chennai-kanchipuram-tour-packages', 'aarupadaiveedu', 'chennai-tirupathi-tour-packages', 'students-ss-tour-package', 'weekend-ss-tour-package', 'navagraha-tour', 'goa-ss-tour-package']

for d in data:
    if d['slug'] in targets:
        print(f"\n{'='*60}")
        print(f"SLUG: {d['slug']}")
        print(f"TITLE: {d['title']}")
        print(f"URL: {d['url']}")
        print(f"DAYS: {d.get('days')}, NIGHTS: {d.get('nights')}, PRICE: {d.get('price')}")
        print(f"HEADINGS: {d.get('headings')}")
        print(f"DAYS PLAN ({len(d.get('days_plan', []))} items):")
        for dp in d.get('days_plan', []):
            print(f"  Day {dp.get('day')}: {dp.get('activities')[:120]}")
        print("CONTENT SUMMARY (first 400 chars):")
        print(d.get('content_summary', '')[:400])
