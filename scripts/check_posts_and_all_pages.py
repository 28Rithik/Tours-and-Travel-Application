import sys
import urllib.request
import json

sys.stdout.reconfigure(encoding='utf-8')

# Check posts
try:
    req = urllib.request.Request('https://hiphopholidays.in/wp-json/wp/v2/posts?per_page=100', headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        posts = json.loads(resp.read().decode('utf-8'))
    print(f"Posts found: {len(posts)}")
    for p in posts:
        print(f"- Post: {p['title']['rendered']} ({p['link']})")
except Exception as e:
    print(f"Posts error: {e}")

# Check all pages titles and URLs
with open('scripts/hiphop_pages.json', 'r', encoding='utf-8') as f:
    pages = json.load(f)

print(f"\nAll {len(pages)} pages from hiphopholidays.in:")
for p in pages:
    print(f"ID {p['id']}: {p['title']} ({p['slug']}) -> {p['link']}")
