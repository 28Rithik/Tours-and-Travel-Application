import json
import re
import sys

# Ensure UTF-8 output if possible
sys.stdout.reconfigure(encoding='utf-8')

with open('scripts/crawled_chennaitourstravels_packages.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total crawled items: {len(data)}")

rich_items = [d for d in data if len(d.get('days_plan', [])) > 0]
other_items = [d for d in data if len(d.get('days_plan', [])) == 0]

print(f"Items with days_plan extracted: {len(rich_items)}")
print(f"Items without days_plan: {len(other_items)}")

print("\n--- SAMPLE EXTRACTED DAYS PLAN (first 5) ---")
for r in rich_items[:5]:
    print(f"Slug: {r['slug']} | Title: {r['title']}")
    print(f"Duration: {r['nights']}N/{r['days']}D | Price: Rs.{r['price']} | Days: {len(r['days_plan'])}")
    for dp in r['days_plan'][:2]:
        print(f"   Day {dp['day']}: {dp['activities'][:80]}...")

print("\n--- SAMPLE ITEMS WITHOUT DAYS PLAN (inspecting content & headings) ---")
for o in other_items[:15]:
    print(f"\nSlug: {o['slug']} | URL: {o['url']}")
    print(f"Title: {o['title']}")
    print(f"Headings: {o['headings'][:4]}")
    desc_preview = (o.get('description') or '')[:120].replace('\n', ' ')
    print(f"Desc preview: {desc_preview}")
