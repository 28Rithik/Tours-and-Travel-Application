import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from django.db import connection, transaction
from packages.models import Package

print("=" * 80)
print("  HIGH-SPEED PACKAGE DATA CLEANUP & REPAIR")
print("=" * 80)

with connection.cursor() as cursor:
    cursor.execute("PRAGMA synchronous = OFF")
    cursor.execute("PRAGMA journal_mode = MEMORY")

# 1. High-Speed Update of hotel_star_category for SGT-HOL- packages
print("\n1. Fixing hotel_star_category for all Holidify packages...")
updated_hotels = Package.objects.filter(package_code__startswith='SGT-HOL-').update(
    hotel_star_category='Star Category Hotel & Resort'
)
print(f"✅ Reset hotel_star_category for {updated_hotels} SGT-HOL- packages to 'Star Category Hotel & Resort'.")

# Check any other package with overlong hotel_star_category
with connection.cursor() as cursor:
    cursor.execute("UPDATE packages_package SET hotel_star_category = 'Star Category Hotel & Resort' WHERE LENGTH(hotel_star_category) > 50")
    print(f"✅ Cleaned any remaining overlong hotel_star_category fields.")

# 2. High-Speed Cleaning of description fields
print("\n2. Sanitizing description fields for all Holidify packages...")
hol_packages = list(Package.objects.filter(package_code__startswith='SGT-HOL-').only('id', 'name', 'destination', 'duration_nights', 'duration_days', 'description'))
print(f"Loaded {len(hol_packages)} Holidify packages for description sanitization.")

packages_to_update = []
for p in hol_packages:
    desc = p.description or ''
    if 'bootstrap' in desc.lower() or '/*!' in desc or ':root' in desc:
        # Extract clean narrative description
        m = re.split(r'\(?/\*!|\(?:root|\(?bootstrap', desc, flags=re.IGNORECASE)
        clean_text = m[0].strip().rstrip('(').strip()
        if not clean_text.endswith('.'):
            clean_text += '.'
        clean_text += f" Includes comfortable Star Category Hotel & Resort accommodation, private AC vehicle transfers, and dedicated tour assistance from Siva Gayathri Tours & Travels."
        p.description = clean_text
        packages_to_update.append(p)

print(f"Sanitized {len(packages_to_update)} contaminated descriptions. Running bulk update...")
with transaction.atomic():
    Package.objects.bulk_update(packages_to_update, ['description'], batch_size=500)
print("✅ Bulk update of clean descriptions completed successfully!")

# 3. Fix malformed package names and destinations
print("\n3. Fixing malformed package names and destinations...")
fixes = [
    ('SGT-CT-TOUR-PACKAGES-FROM-1D', '1-Day Chennai City Sightseeing Tour', 'Chennai, Tamil Nadu'),
    ('SGT-CT-TOUR-PACKAGES-2D', '2-Day Chennai & Mahabalipuram Heritage Tour', 'Chennai & Mahabalipuram, Tamil Nadu'),
    ('SGT-RH-15-DAY-TRANSPACIFI-10D', None, 'Japan & Alaska (Transpacific Cruise)'),
    ('SGT-RH-4-DAY-WESTERN-CARI-4D', None, 'Western Caribbean (Tampa, FL Cruise)'),
    ('SGT-SMT-DOM-northeast', 'Northeast Explorer - Assam & Meghalaya', 'Northeast India (Assam & Meghalaya)'),
    ('SGT-SMT-TRN-kasi-gaya', 'Varanasi (Kasi) & Gaya Sacred Yatra', 'Varanasi (Kasi) & Gaya, India'),
    ('SGT-SMT-TRN-kasi-nephal', 'Kasi & Nepal Himalayan Spiritual Tour', 'Kasi & Nepal (Kathmandu, Pokhara)'),
    ('SGT-SMT-TRN-shimla-kasi', 'Shimla, Kullu, Manali & Kasi Grand Circuit', 'Shimla, Kullu, Manali & Kasi'),
]

for code, new_name, new_dest in fixes:
    pkg = Package.objects.filter(package_code=code).first()
    if pkg:
        if new_name:
            pkg.name = new_name
        if new_dest:
            pkg.destination = new_dest
        pkg.save(update_fields=['name', 'destination'] if new_name else ['destination'])
        print(f"  [FIXED] [{code}] -> Name: {pkg.name!r} | Dest: {pkg.destination!r}")

# Fix destinations with ', India'
comma_pkgs = Package.objects.filter(destination=', India')
for p in comma_pkgs:
    p.destination = f"{p.name.split('-')[0].strip()}, India"
    p.save(update_fields=['destination'])
    print(f"  [FIXED] [{p.package_code}] Destination set to {p.destination!r}")

# 4. Final verification
rem_hotel = Package.objects.filter(hotel_star_category__icontains='bootstrap').count()
rem_desc = Package.objects.filter(description__icontains='bootstrap').count()
with connection.cursor() as cursor:
    cursor.execute("SELECT COUNT(*) FROM packages_package WHERE LENGTH(hotel_star_category) > 60")
    overlong_count = cursor.fetchone()[0]

print("\n" + "=" * 80)
print("  CLEANUP VERIFICATION REPORT")
print("=" * 80)
print(f"Packages with bootstrap in hotel_star_category : {rem_hotel} (Target: 0)")
print(f"Packages with bootstrap in description         : {rem_desc} (Target: 0)")
print(f"Packages with overlong hotel_star_category     : {overlong_count} (Target: 0)")
print("=" * 80)
