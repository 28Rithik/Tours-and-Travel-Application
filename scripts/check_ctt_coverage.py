import json
import sys

from ctt_catalog_data import OUTSTATION_PACKAGES
from ctt_pilgrimage_data import PILGRIMAGE_PACKAGES
from ctt_pilgrimage_part2 import PILGRIMAGE_PACKAGES_PART2
from ctt_vacations_data import VACATION_PACKAGES
from ctt_vacations_part2 import VACATION_PACKAGES_PART2
from ctt_specialized_data import SPECIALIZED_PACKAGES

all_pkgs = (
    OUTSTATION_PACKAGES +
    PILGRIMAGE_PACKAGES +
    PILGRIMAGE_PACKAGES_PART2 +
    VACATION_PACKAGES +
    VACATION_PACKAGES_PART2 +
    SPECIALIZED_PACKAGES
)

print(f"Total defined packages in catalog: {len(all_pkgs)}")

with open('scripts/crawled_chennaitourstravels_packages.json', 'r', encoding='utf-8') as f:
    crawled = json.load(f)

print(f"Total crawled pages: {len(crawled)}")

pkg_codes = [p['code'] for p in all_pkgs]
print(f"Package codes range: {pkg_codes[0]} to {pkg_codes[-1]}")
print(f"All codes unique: {len(pkg_codes) == len(set(pkg_codes))}")

# Check sample names
print("\nFirst 5 packages:")
for p in all_pkgs[:5]:
    print(f"  [{p['code']}] {p['name']} ({p['duration_nights']}N/{p['duration_days']}D)")

print("\nLast 5 packages:")
for p in all_pkgs[-5:]:
    print(f"  [{p['code']}] {p['name']} ({p['duration_nights']}N/{p['duration_days']}D)")
