import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('scripts/crawled_chennaitourstravels_packages.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=== FIRST 30 ITEMS ===")
for i, d in enumerate(data[:30]):
    slug = d.get('slug')
    title = d.get('title')
    days_cnt = len(d.get('days_plan', []))
    dur = f"{d.get('nights', 0)}N/{d.get('days', 0)}D"
    price = d.get('price', 0)
    print(f"[{i+1:02d}] {slug:35} | {dur:7} | Price: {price:7} | Days: {days_cnt:2} | Title: {title[:45]}")

print("\n=== INSPECT ITEM 37 (108 days) & OTHERS WITH MANY DAYS ===")
for d in data:
    if len(d.get('days_plan', [])) > 10:
        print(f"Slug: '{d.get('slug')}' | URL: {d.get('url')} | Days extracted: {len(d.get('days_plan', []))}")

