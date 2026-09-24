import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()
sys.stdout.reconfigure(encoding='utf-8')

from packages.models import Package
from django.db.models import Count, Q
from django.test import Client
from django.contrib.auth import get_user_model

print("=" * 80)
print("COMPREHENSIVE POST-RECLASSIFICATION VERIFICATION")
print("=" * 80)

# 1. Total Package Count
total = Package.objects.count()
print(f"\n1. TOTAL PACKAGES IN DB: {total} (Expected: 6246)")
assert total == 6246, f"Expected 6246 packages, got {total}"

# 2. Category Distribution
print("\n2. CATEGORY BREAKDOWN:")
cat_counts = Package.objects.values('category').annotate(count=Count('id')).order_by('-count')
for item in cat_counts:
    print(f"   {item['category']:<20}: {item['count']} packages")

# 3. Pilgrimage Consolidation
pilg_count = Package.objects.filter(category='pilgrimage').count()
print(f"\n3. 'pilgrimage' category count: {pilg_count} (Expected: 0)")
assert pilg_count == 0, "Expected 0 packages with category='pilgrimage'"

# 4. Devotional Consistency
dev_pkgs = Package.objects.filter(category='devotional')
dev_flag_false = dev_pkgs.filter(is_devotional=False).count()
print(f"\n4. 'devotional' packages with is_devotional=False: {dev_flag_false} (Expected: 0)")
assert dev_flag_false == 0, "All devotional packages must have is_devotional=True"

# 5. International Consistency
intl_pkgs = Package.objects.filter(category='international')
intl_flag_false = intl_pkgs.filter(is_international=False).count()
print(f"\n5. 'international' packages with is_international=False: {intl_flag_false} (Expected: 0)")
assert intl_flag_false == 0, "All international packages must have is_international=True"

# 6. College IV Consistency
iv_pkgs = Package.objects.filter(category='college_iv')
iv_flag_false = iv_pkgs.filter(has_industrial_visit=False).count()
print(f"\n6. 'college_iv' packages with has_industrial_visit=False: {iv_flag_false} (Expected: 0)")
assert iv_flag_false == 0, "All college_iv packages must have has_industrial_visit=True"

# 7. Domestic in International Check
from scripts.reclassify_all_packages import DOMESTIC_REGIONS, INTL_COUNTRIES
domestic_leaks = []
for p in intl_pkgs:
    title_dest = f"{p.name} {p.destination}".lower()
    has_foreign = any(kw in title_dest for kw in INTL_COUNTRIES)
    is_visa = 'visa' in title_dest
    is_domestic = any(dr in title_dest for dr in DOMESTIC_REGIONS)
    if is_domestic and not has_foreign and not is_visa:
        domestic_leaks.append((p.id, p.package_code, p.name, p.destination))

print(f"\n7. Domestic packages leaking into 'international': {len(domestic_leaks)} (Expected: 0)")
if domestic_leaks:
    for leak in domestic_leaks:
        print(f"   LEAK: [{leak[0]}] {leak[1]}: {leak[2]} | Dest: {leak[3]}")
assert len(domestic_leaks) == 0, "Domestic packages found in international category"

# 8. International in Domestic Check (excluding Nepal holy yatra)
import re
intl_in_domestic = []
for p in Package.objects.exclude(category__in=['international', 'devotional']):
    title_dest = f"{p.name} {p.destination}".lower().replace("switzerland of india", "")
    has_foreign = any(re.search(r'\b' + re.escape(kw) + r'\b', title_dest) for kw in INTL_COUNTRIES)
    if has_foreign:
        intl_in_domestic.append((p.id, p.package_code, p.name, p.destination, p.category))

print(f"\n8. International packages leaking into domestic categories: {len(intl_in_domestic)} (Expected: 0)")
if intl_in_domestic:
    for leak in intl_in_domestic:
        print(f"   LEAK: [{leak[0]}] {leak[1]}: {leak[2]} | Dest: {leak[3]} | Cat: {leak[4]}")
assert len(intl_in_domestic) == 0, "International packages found in domestic categories"

# 9. Test Live Quotation Proposal Preview across All Categories
print("\n9. TESTING QUOTATION PROPOSAL VIEWS ACROSS ALL CATEGORIES:")
User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    admin_user = User.objects.create_superuser('admin_audit', 'admin@example.com', 'adminpass123')

client = Client()
client.force_login(admin_user)

categories = [
    'devotional', 'international', 'hill_station', 'holiday',
    'family_vacation', 'local_tour', 'college_iv', 'corporate_offsite', 'fixed_departure'
]

for cat in categories:
    pkg = Package.objects.filter(category=cat).first()
    if pkg:
        resp = client.get(f'/packages/quote/{pkg.id}/')
        status = resp.status_code
        content = resp.content.decode('utf-8')
        has_brand = "SIVA GAYATHRI" in content
        has_helpline = "98425 33777" in content
        print(f"   [{cat:<18}] PKG #{pkg.id} ({pkg.package_code}): HTTP {status} | Brand: {has_brand} | Helpline: {has_helpline}")
        assert status == 200, f"Quotation proposal failed for {cat}"
        assert has_brand, f"Brand missing in quotation for {cat}"
        assert has_helpline, f"Helpline missing in quotation for {cat}"

print("\n" + "=" * 80)
print("ALL VERIFICATION CHECKS PASSED WITH 100% ACCURACY!")
print("=" * 80)
