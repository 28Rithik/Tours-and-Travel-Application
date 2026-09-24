import os
import sys
import re
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()
sys.stdout.reconfigure(encoding='utf-8')

from packages.models import Package
from django.db.models import Q, Count

print("=" * 80)
print("DETAILED MISCLASSIFICATION ANALYSIS")
print("=" * 80)

# Check 1: category='devotional' vs is_devotional flag
dev_cat_flag_false = Package.objects.filter(category__in=['devotional', 'pilgrimage'], is_devotional=False).count()
print(f"1. Packages with category in [devotional, pilgrimage] but is_devotional=False: {dev_cat_flag_false}")

# Check 2: is_devotional=True but category NOT in [devotional, pilgrimage]
flag_true_cat_other = Package.objects.filter(is_devotional=True).exclude(category__in=['devotional', 'pilgrimage']).count()
print(f"2. Packages with is_devotional=True but category NOT devotional/pilgrimage: {flag_true_cat_other}")
for p in Package.objects.filter(is_devotional=True).exclude(category__in=['devotional', 'pilgrimage'])[:10]:
    print(f"   [{p.id}] {p.package_code}: {p.name} | Cat: {p.category}")

# Check 3: category='international' vs is_international flag
intl_cat_flag_false = Package.objects.filter(category='international', is_international=False).count()
print(f"\n3. Packages with category='international' but is_international=False: {intl_cat_flag_false}")

# Check 4: is_international=True but category!='international'
flag_intl_cat_other = Package.objects.filter(is_international=True).exclude(category='international').count()
print(f"4. Packages with is_international=True but category!='international': {flag_intl_cat_other}")
for p in Package.objects.filter(is_international=True).exclude(category='international')[:10]:
    print(f"   [{p.id}] {p.package_code}: {p.name} | Cat: {p.category}")

# Check 5: What are the 196 1-day international packages?
print("\n5. Inspecting 1-day 'international' packages:")
for p in Package.objects.filter(category='international', duration_days=1)[:10]:
    print(f"   [{p.id}] {p.package_code}: {p.name} | Dest: {p.destination} | Nights: {p.duration_nights} | Days: {p.duration_days}")

# Check 6: All packages with 'pilgrimage' category
print("\n6. All 8 packages with category='pilgrimage':")
for p in Package.objects.filter(category='pilgrimage'):
    print(f"   [{p.id}] {p.package_code}: {p.name} | Dest: {p.destination}")

# Check 7: Packages with keywords like 'corporate', 'team outing', 'offsite', 'conclave'
print("\n7. Corporate / Offsite packages:")
corp_pkgs = Package.objects.filter(
    Q(name__icontains='corporate') | Q(name__icontains='offsite') | Q(name__icontains='team outing') | Q(name__icontains='conclave')
)
print(f"   Found {corp_pkgs.count()} packages with corporate keywords:")
for p in corp_pkgs:
    print(f"   [{p.id}] {p.package_code}: {p.name} | Current Cat: {p.category}")

# Check 8: Packages with 'college iv', 'industrial visit', 'students tour'
print("\n8. College IV packages:")
iv_pkgs = Package.objects.filter(
    Q(name__icontains='industrial visit') | Q(name__icontains='college iv') | Q(name__icontains='iv tour') | Q(name__icontains='students tour') | Q(name__icontains='expedition')
)
print(f"   Found {iv_pkgs.count()} packages with IV/Expedition keywords:")
for p in iv_pkgs[:15]:
    print(f"   [{p.id}] {p.package_code}: {p.name} | Current Cat: {p.category}")

# Check 9: Packages with 0 nights / 1 day:
print("\n9. Sample 1-day packages and their categories:")
for p in Package.objects.filter(duration_days=1, duration_nights=0)[:15]:
    print(f"   [{p.id}] {p.package_code}: {p.name} | Cat: {p.category}")
