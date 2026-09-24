import os
import sys
import re
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from packages.models import Package

print("=" * 80)
print("  AUDIT OF HOTEL STAR CATEGORIES & BRAND LEAKS ACROSS ENTIRE DB")
print("=" * 80)

# 1. Inspect hotel_star_category
star_cats = Counter()
overlong_hotel_cats = 0
for p in Package.objects.all():
    val = p.hotel_star_category or ''
    if len(val) > 100 or 'bootstrap' in val.lower():
        overlong_hotel_cats += 1
    else:
        star_cats[val] += 1

print(f"Total packages with overlong/bootstrap hotel_star_category: {overlong_hotel_cats}")
print(f"Top 10 normal hotel_star_category values:")
for val, cnt in star_cats.most_common(10):
    print(f"  - {val!r}: {cnt} packages")

# 2. Inspect descriptions with bootstrap
bootstrap_desc_cnt = Package.objects.filter(description__icontains='bootstrap').count()
print(f"\nTotal packages with bootstrap in description: {bootstrap_desc_cnt}")

# 3. Check for competitor leaks across ALL 6182 packages in name, destination, description
competitors = [
    'holidify', 'trawell', 'rengha', 'manoj travel', 'aspire holiday',
    'sri murugan', 'jaisun', 'eroutes', 'bharathiyar', 'prabu tour',
    'kandhan', 'srigo', 'hip hop', 'sblt'
]

print("\nCompetitor brand mentions across ALL packages:")
for comp in competitors:
    pat = re.compile(re.escape(comp), re.IGNORECASE)
    cnt_name = 0
    cnt_desc = 0
    cnt_inc = 0
    for p in Package.objects.all():
        if pat.search(p.name or ''):
            cnt_name += 1
        if pat.search(p.description or ''):
            cnt_desc += 1
        if pat.search(p.inclusions or ''):
            cnt_inc += 1
    if cnt_name + cnt_desc + cnt_inc > 0:
        print(f"  - '{comp}': {cnt_name} in names, {cnt_desc} in descriptions, {cnt_inc} in inclusions")
    else:
        print(f"  - '{comp}': 0 leaks (clean)")

# 4. Check the 3 bad destination packages
print("\nBad destination packages details:")
for p in Package.objects.filter(destination__in=['', 'S', '4']):
    print(f"ID {p.id}: [{p.package_code}] {p.name}")
    print(f"  Days: {p.duration_days}, Nights: {p.duration_nights}, Price: {p.base_price}")
