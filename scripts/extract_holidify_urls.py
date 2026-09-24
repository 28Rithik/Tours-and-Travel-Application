import urllib.request
import ssl
import re
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
print("Fetching sitemap1.xml...")
req = urllib.request.Request('https://www.holidify.com/sitemap1.xml', headers=headers)
resp = urllib.request.urlopen(req, context=ctx, timeout=30)

package_urls = []
# Stream line by line to avoid memory/buffer issues
for line in resp:
    line_str = line.decode('utf-8', errors='ignore')
    if '<loc>' in line_str and '/packages/' in line_str:
        m = re.search(r'<loc>(https://www\.holidify\.com/packages/[^<]+)</loc>', line_str)
        if m:
            package_urls.append(m.group(1))

print(f"Extracted {len(package_urls)} package listing URLs!")

with open('scripts/holidify_package_urls.json', 'w', encoding='utf-8') as f:
    json.dump(package_urls, f, indent=2)

print("Saved to scripts/holidify_package_urls.json")
