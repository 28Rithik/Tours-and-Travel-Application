import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from packages.models import Package

print("=" * 80)
print("  EXECUTING COMPREHENSIVE PACKAGE DATA CLEANUP & REPAIR")
print("=" * 80)

# 1. Clean hotel_star_category
print("\n1. Cleaning corrupted hotel_star_category fields...")
corrupted_hotel_pkgs = Package.objects.filter(hotel_star_category__icontains='bootstrap')
c1 = corrupted_hotel_pkgs.count()
print(f"Found {c1} packages with bootstrap in hotel_star_category.")
corrupted_hotel_pkgs.update(hotel_star_category='Star Category Hotel & Resort')

# Also check for any overlong hotel_star_category > 60 chars
overlong_hotel_pkgs = [p for p in Package.objects.all() if len(p.hotel_star_category or '') > 60]
print(f"Found {len(overlong_hotel_pkgs)} additional overlong hotel_star_category packages.")
for p in overlong_hotel_pkgs:
    p.hotel_star_category = 'Star Category Hotel & Resort'
    p.save(update_fields=['hotel_star_category'])

print(f"✅ All hotel_star_category fields restored to clean standard values.")

# 2. Clean description fields
print("\n2. Cleaning corrupted description fields...")
corrupted_desc_pkgs = Package.objects.filter(description__icontains='bootstrap')
c2 = corrupted_desc_pkgs.count()
print(f"Found {c2} packages with bootstrap CSS in description.")

fixed_desc_count = 0
for p in corrupted_desc_pkgs.iterator():
    desc = p.description or ''
    # Remove everything from /*! or :root or bootstrap onwards
    cleaned_desc = re.sub(r'\(?/\*!.*', '', desc, flags=re.DOTALL).strip()
    cleaned_desc = re.sub(r'\(?:root\s*\{.*', '', cleaned_desc, flags=re.DOTALL).strip()
    cleaned_desc = re.sub(r'\(?bootstrap.*', '', cleaned_desc, flags=re.DOTALL).strip()
    cleaned_desc = cleaned_desc.rstrip('(').strip()

    if not cleaned_desc.endswith('.'):
        cleaned_desc += '. Includes comfortable star category hotel & resort accommodation and professional tour assistance from Siva Gayathri Tours & Travels.'

    p.description = cleaned_desc
    p.save(update_fields=['description'])
    fixed_desc_count += 1

print(f"✅ Fixed and sanitized {fixed_desc_count} package descriptions.")

# 3. Fix malformed package names and destinations
print("\n3. Fixing malformed package names and destinations...")

# Specific fixes
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
        updated = []
        if new_name and pkg.name != new_name:
            pkg.name = new_name
            updated.append('name')
        if new_dest and pkg.destination != new_dest:
            pkg.destination = new_dest
            updated.append('destination')
        if updated:
            pkg.save(update_fields=updated)
            print(f"  [FIXED] [{code}] Updated {', '.join(updated)} -> Name: {pkg.name!r}, Dest: {pkg.destination!r}")

# Fix any remaining destination that is just ', India'
comma_india_pkgs = Package.objects.filter(destination=', India')
print(f"Fixing {comma_india_pkgs.count()} destinations with ', India':")
for p in comma_india_pkgs:
    clean_dest = f"{p.name.split('-')[0].strip()}, India"
    p.destination = clean_dest
    p.save(update_fields=['destination'])
    print(f"  [FIXED] [{p.package_code}] Destination set to {p.destination!r}")

# 4. Final verification
rem_hotel = Package.objects.filter(hotel_star_category__icontains='bootstrap').count()
rem_desc = Package.objects.filter(description__icontains='bootstrap').count()
overlong_hotel = [p for p in Package.objects.all() if len(p.hotel_star_category or '') > 100]

print("\n" + "=" * 80)
print("  CLEANUP VERIFICATION REPORT")
print("=" * 80)
print(f"Remaining packages with bootstrap in hotel_star_category: {rem_hotel} (Must be 0)")
print(f"Remaining packages with bootstrap in description        : {rem_desc} (Must be 0)")
print(f"Remaining packages with overlong hotel_star_category    : {len(overlong_hotel)} (Must be 0)")
print("=" * 80)
