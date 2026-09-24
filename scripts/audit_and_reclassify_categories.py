import os
import django

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()
sys.stdout.reconfigure(encoding='utf-8')

from packages.models import Package
from django.db.models import Count

print(f"Total packages in DB: {Package.objects.count()}")

print("\n--- Package Counts by Category ---")
cat_counts = Package.objects.values('category').annotate(count=Count('id')).order_by('-count')
for item in cat_counts:
    print(f"  {item['category']}: {item['count']}")

print("\n--- Package Counts by Prefix and Category ---")
prefixes = ['SGT-HOL-', 'SGT-TRW-', 'SGT-CT-', 'SGT-HHH-', 'SGT-CTT-', 'SGT-PRB-', 'SGT-BHR-', 'SGT-SRM-', 'SGT-RNG-', 'SGT-']
for pref in prefixes:
    qs = Package.objects.filter(package_code__startswith=pref)
    if qs.exists():
        cats = qs.values('category').annotate(count=Count('id')).order_by('-count')
        cat_str = ", ".join([f"{c['category']}: {c['count']}" for c in cats])
        print(f"  {pref} (Total {qs.count()}): {cat_str}")

# Check for un-prefixed packages
unprefixed = Package.objects.exclude(package_code__startswith='SGT-')
if unprefixed.exists():
    cats = unprefixed.values('category').annotate(count=Count('id')).order_by('-count')
    cat_str = ", ".join([f"{c['category']}: {c['count']}" for c in cats])
    print(f"  NON-SGT (Total {unprefixed.count()}): {cat_str}")
