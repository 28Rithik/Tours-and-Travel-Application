import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('scripts/scraped_sblt_packages.json', encoding='utf-8') as f:
    data = json.load(f)

for p in data:
    print("=" * 80)
    print(f"TITLE: {p['title']} ({p['nights']}N / {p['days']}D) — Rs. {p['price']:,}")
    print(f"URL: {p['url']}")
    for idx, para in enumerate(p['paragraphs'], 1):
        print(f"  [{idx}] {para}")
