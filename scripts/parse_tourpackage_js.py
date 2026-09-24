import os
import sys
import re
import json

sys.stdout.reconfigure(encoding='utf-8')

with open('scripts/tourpackage.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

# Let's inspect where packageData starts and ends
start_idx = js_content.find('const packageData = {')
if start_idx == -1:
    print("Could not find const packageData")
    sys.exit(1)

# Find the end of packageData (before the next top-level const or function)
end_markers = ['const tabsRow', 'function', 'const VEHICLES']
end_idx = len(js_content)
for m in ['const tabsRow', 'const allDestinations', 'const tabs =']:
    pos = js_content.find(m, start_idx)
    if pos != -1 and pos < end_idx:
        end_idx = pos

package_data_str = js_content[start_idx:end_idx]
print(f"packageData string length: {len(package_data_str)}")

# We can parse duration sections: "1D", "2D", "3D", "4D", "5D", "6D", "7D"
dur_pattern = re.compile(r'\"([1-7]D)\":\s*\{\s*title:\s*\"([^\"]+)\",\s*(?:subtitle:\s*\"([^\"]+)\",)?(?:\s*kmLimit:\s*(\d+),)?\s*destinations:\s*\{')

dur_matches = list(dur_pattern.finditer(package_data_str))
print(f"Found {len(dur_matches)} duration sections:")

dur_blocks = []
for i in range(len(dur_matches)):
    m = dur_matches[i]
    dur_key = m.group(1)
    title = m.group(2)
    start_pos = m.end()
    end_pos = dur_matches[i+1].start() if i + 1 < len(dur_matches) else len(package_data_str)
    dur_blocks.append((dur_key, title, package_data_str[start_pos:end_pos]))
    print(f"  • {dur_key}: {title}")

parsed_packages = []

for dur_key, dur_title, block_str in dur_blocks:
    days_num = int(dur_key[0])
    # Destinations are defined like:
    # "Destination Name": {
    #    hash: "...",
    #    kmLimit: 300,
    #    vehicles: [ ... ],
    #    itinerary: [ ... ]
    # }
    
    # Split by destination header
    dest_splits = list(re.finditer(r'\"([^\"]+)\":\s*\{', block_str))
    for j in range(len(dest_splits)):
        dm = dest_splits[j]
        dest_name = dm.group(1)
        d_start = dm.end()
        d_end = dest_splits[j+1].start() if j + 1 < len(dest_splits) else len(block_str)
        dest_content = block_str[d_start:d_end]

        # Extract hash
        hash_m = re.search(r'hash:\s*\"([^\"]+)\"', dest_content)
        dest_hash = hash_m.group(1) if hash_m else dest_name.lower().replace(' ', '-')

        # Extract kmLimit
        km_m = re.search(r'kmLimit:\s*(\d+)', dest_content)
        km_limit = int(km_m.group(1)) if km_m else (days_num * 300)

        # Extract vehicle prices
        # vehicles: [ { ...VEHICLES.sedan, price: 6000 }, ... ]
        v_prices = {}
        for vm in re.finditer(r'VEHICLES\.([a-zA-Z0-9_]+),\s*price:\s*([0-9]+|null)', dest_content):
            v_key = vm.group(1)
            p_val = vm.group(2)
            v_prices[v_key] = int(p_val) if p_val != 'null' else None

        # Extract itinerary
        # itinerary: [ { day: "Day 1", text: "..." }, ... ]
        itinerary = []
        for im in re.finditer(r'\{\s*day:\s*\"([^\"]+)\",\s*text:\s*\"([^\"]+)\"\s*\}', dest_content):
            itinerary.append({
                'day': im.group(1),
                'text': im.group(2)
            })

        parsed_packages.append({
            'duration_tier': dur_key,
            'duration_days': days_num,
            'duration_nights': max(1, days_num - 1) if days_num > 1 else 0,
            'tier_title': dur_title,
            'destination_name': dest_name,
            'hash': dest_hash,
            'km_limit': km_limit,
            'vehicle_prices': v_prices,
            'itinerary': itinerary
        })

print(f"\nTotal Tour Packages Extracted from tourpackage.js: {len(parsed_packages)}")
with open('scripts/bharathiyar_packages.json', 'w', encoding='utf-8') as out:
    json.dump(parsed_packages, out, indent=2)

print("Saved to scripts/bharathiyar_packages.json")
for p in parsed_packages:
    prices_str = ", ".join(f"{k}: {v}" for k, v in p['vehicle_prices'].items() if v)
    print(f"  [{p['duration_tier']}] {p['destination_name']:<35} | {len(p['itinerary'])} days | {prices_str}")
