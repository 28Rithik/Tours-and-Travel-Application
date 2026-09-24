import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('scripts/crawled_chennaitourstravels_packages.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total crawled pages: {len(data)}")

# Let's inspect what unique pages we have and check their content
print("\nSummary of all 90 entries:")
for i, d in enumerate(data):
    slug = d.get('slug') or 'home'
    url = d.get('url', '')
    title = d.get('title', '')
    text_len = len(d.get('content_summary', ''))
    days_cnt = len(d.get('days_plan', []))
    print(f"{i+1:02d}. slug={slug:32} | days={days_cnt:2} | len={text_len:5} | title={title[:40]}")
