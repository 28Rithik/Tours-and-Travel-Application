import os
import sys
import re
import html
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from packages.models import Package, ItineraryDay

print("=" * 80)
print("  AUDITING PACKAGES FOR BEAUTIFICATION OPPORTUNITIES")
print("=" * 80)

total_pkgs = Package.objects.count()
print(f"Total packages in DB: {total_pkgs}")

all_caps_names = []
html_entity_names = []
redundant_tour_package_names = []
double_dash_names = []
missing_itineraries = []
missing_tariffs = []

for p in Package.objects.all():
    name = p.name or ''
    # Check all caps
    letters = [c for c in name if c.isalpha()]
    if letters and all(c.isupper() for c in letters) and len(letters) > 10:
        all_caps_names.append((p.id, p.package_code, name))
    
    # Check HTML entities
    if '&' in name and any(ent in name for ent in ['&#', '&amp;', '&quot;', '&lt;', '&gt;', '&nbsp;']):
        html_entity_names.append((p.id, p.package_code, name))

    # Check redundant words
    if 'tour package' in name.lower() and name.lower().count('tour package') >= 2:
        redundant_tour_package_names.append((p.id, p.package_code, name))

    # Check double dashes or underscores
    if '--' in name or '_' in name:
        double_dash_names.append((p.id, p.package_code, name))

    # Check itinerary days
    if not p.itinerary_days.exists():
        missing_itineraries.append((p.id, p.package_code, name))

    # Check vehicle tariffs
    if not p.vehicle_tariffs.exists():
        missing_tariffs.append((p.id, p.package_code, name))

print(f"\n1. ALL CAPS Names                        : {len(all_caps_names)}")
for _, code, name in all_caps_names[:5]:
    print(f"     [{code}] {name[:60]}")

print(f"\n2. HTML Entity Names                     : {len(html_entity_names)}")
for _, code, name in html_entity_names[:5]:
    print(f"     [{code}] {name[:60]}")

print(f"\n3. Redundant 'TOUR PACKAGE' in Names     : {len(redundant_tour_package_names)}")
for _, code, name in redundant_tour_package_names[:5]:
    print(f"     [{code}] {name[:60]}")

print(f"\n4. Double Dashes / Underscores in Names  : {len(double_dash_names)}")
for _, code, name in double_dash_names[:5]:
    print(f"     [{code}] {name[:60]}")

print(f"\n5. Packages Missing Itinerary Days       : {len(missing_itineraries)}")
print(f"6. Packages Missing Vehicle Tariffs      : {len(missing_tariffs)}")

print("\n" + "=" * 80)
