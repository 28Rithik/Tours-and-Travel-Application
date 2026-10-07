import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

files = [
    'packages/static/packages/js/package_dynamic_form.js',
    'packages/static/packages/js/departures_iv_dynamic.js',
    'packages/static/packages/js/manifest_dynamic_form.js',
    'packages/static/packages/css/package_admin_custom.css',
]

keywords = ['jazzy', 'nav-tabs', 'tab-pane', 'card-body', 'card-header', 'card', 'nav-link', 'bootstrap', 'collapse', 'inline-group']

for fpath in files:
    print(f"=== {fpath} ===")
    if not os.path.exists(fpath):
        print("  FILE NOT FOUND")
        continue
    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    print(f"  Size: {len(content)} chars, {len(content.splitlines())} lines")
    for kw in keywords:
        matches = list(re.finditer(r'\b' + re.escape(kw) + r'\b', content, re.IGNORECASE))
        if matches:
            print(f"  Keyword '{kw}': {len(matches)} occurrences")
            for m in matches[:3]:
                start = max(0, m.start() - 35)
                end = min(len(content), m.end() + 35)
                snippet = content[start:end].replace('\n', ' ')
                print(f"    ...{snippet}...")
