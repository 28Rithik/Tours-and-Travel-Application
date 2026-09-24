import os
import sys
import re
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from packages.models import Package, ItineraryDay, PackageVehicleTariff

print("=" * 80)
print("  COMPREHENSIVE DATA CORRUPTION & BUG DIAGNOSTIC AUDIT")
print("=" * 80)

total_pkgs = Package.objects.count()
print(f"Total Packages to scan: {total_pkgs}\n")

# Bug categories
css_in_fields = defaultdict(list)
html_tags_in_fields = defaultdict(list)
overlong_short_fields = defaultdict(list)
empty_or_bad_names = []
empty_or_bad_dest = []
zero_price = []
bad_hotel_category = []

css_pattern = re.compile(r'(?:bootstrap|:root\s*\{|-webkit-|@media|font-family\s*:|/\*!|\.col-(?:xs|sm|md|lg))', re.IGNORECASE)
html_tag_pattern = re.compile(r'<\s*(?:script|style|div|span|p|br|table|thead|tbody|tr|td|th|ul|li|a|img|h[1-6]|link|meta)\b[^>]*>', re.IGNORECASE)

fields_to_check = [
    'name', 'destination', 'hotel_star_category', 'vehicle_seating_desc',
    'bus_amenities_desc', 'inclusions', 'exclusions', 'terms_and_conditions',
    'description', 'contact_persons_footer', 'temple_darshan_info', 'visa_guidelines'
]

short_field_limits = {
    'name': 255,
    'destination': 255,
    'hotel_star_category': 100,
    'vehicle_seating_desc': 150,
    'bus_amenities_desc': 255,
    'temple_dress_code': 255,
}

print("1. Scanning Packages for CSS, HTML tags, and overlong text...")
for pkg in Package.objects.all().iterator():
    for f in fields_to_check:
        val = getattr(pkg, f, '')
        if not val or not isinstance(val, str):
            continue

        # Check for CSS leakage
        if css_pattern.search(val):
            css_in_fields[f].append((pkg.id, pkg.package_code, len(val), val[:80]))

        # Check for HTML tag leakage
        if f in ['name', 'destination', 'hotel_star_category', 'vehicle_seating_desc', 'bus_amenities_desc']:
            if html_tag_pattern.search(val):
                html_tags_in_fields[f].append((pkg.id, pkg.package_code, len(val), val[:80]))

        # Check for overlong values in short fields
        if f in short_field_limits and len(val) > short_field_limits[f]:
            overlong_short_fields[f].append((pkg.id, pkg.package_code, len(val), val[:80]))

    # Specific sanity checks
    if not pkg.name or len(pkg.name.strip()) < 3:
        empty_or_bad_names.append((pkg.id, pkg.package_code, pkg.name))
    if not pkg.destination or len(pkg.destination.strip()) < 2:
        empty_or_bad_dest.append((pkg.id, pkg.package_code, pkg.destination))
    if pkg.base_price <= 0 and pkg.price_with_food <= 0 and pkg.price_without_food <= 0:
        zero_price.append((pkg.id, pkg.package_code, pkg.name))

print("\n2. Scanning ItineraryDay records for CSS and HTML injection...")
itinerary_css = []
itinerary_html = []
for day in ItineraryDay.objects.all().iterator():
    for f in ['title', 'route_segment', 'activities', 'morning_activity', 'sightseeing_spots', 'evening_night_activity', 'night_stay_location']:
        val = getattr(day, f, '')
        if not val or not isinstance(val, str):
            continue
        if css_pattern.search(val):
            itinerary_css.append((day.id, day.package.package_code, day.day_number, f, len(val)))
        if f in ['title', 'route_segment', 'night_stay_location'] and html_tag_pattern.search(val):
            itinerary_html.append((day.id, day.package.package_code, day.day_number, f, len(val)))

print("=" * 80)
print("  DIAGNOSTIC FINDINGS SUMMARY")
print("=" * 80)

print(f"\nA. CSS INJECTION IN PACKAGE FIELDS:")
for f, items in css_in_fields.items():
    print(f"  - Field '{f}': {len(items)} corrupted packages!")
    for pid, code, vlen, snippet in items[:5]:
        print(f"      [{code}] (id {pid}, length {vlen}): {snippet!r}")

print(f"\nB. OVERLONG VALUES IN SHORT FIELDS:")
for f, items in overlong_short_fields.items():
    print(f"  - Field '{f}' (limit {short_field_limits[f]}): {len(items)} overlong packages!")
    for pid, code, vlen, snippet in items[:5]:
        print(f"      [{code}] (id {pid}, length {vlen}): {snippet!r}")

print(f"\nC. RAW HTML TAGS IN SHORT FIELDS:")
for f, items in html_tags_in_fields.items():
    print(f"  - Field '{f}': {len(items)} packages with raw HTML tags")
    for pid, code, vlen, snippet in items[:5]:
        print(f"      [{code}] (id {pid}): {snippet!r}")

print(f"\nD. ITINERARY DAY CORRUPTIONS:")
print(f"  - CSS in ItineraryDay fields: {len(itinerary_css)} records")
for did, code, day_num, f, vlen in itinerary_css[:5]:
    print(f"      [{code}] Day {day_num} in '{f}' (id {did}, length {vlen})")
print(f"  - Raw HTML in Short Itinerary fields: {len(itinerary_html)} records")

print(f"\nE. OTHER PACKAGE SANITY CHECKS:")
print(f"  - Empty or Bad Names: {len(empty_or_bad_names)}")
print(f"  - Empty or Bad Destinations: {len(empty_or_bad_dest)}")
print(f"  - Zero Price Packages: {len(zero_price)}")

print("\n" + "=" * 80)
