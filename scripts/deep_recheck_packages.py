import os
import sys
import re
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()
sys.stdout.reconfigure(encoding='utf-8')

from packages.models import Package, TempleDarshanSlot, PackageVehicleTariff, ItineraryDay
from django.db.models import Count, Q

print("=" * 80)
print("DEEP DIVE RECHECK OF ALL 6,246 PACKAGES & SECTION ORGANIZATION")
print("=" * 80)

# Check 1: 1-Day Packages Breakdown
one_day_pkgs = Package.objects.filter(Q(duration_days=1) | Q(duration_nights=0))
print(f"\n1. All 1-Day Packages ({one_day_pkgs.count()} total):")
for cat, cnt in one_day_pkgs.values('category').annotate(count=Count('id')).values_list('category', 'count'):
    print(f"   {cat:<20}: {cnt} packages")

print("\n   Sample 1-day packages in hill_station:")
for p in one_day_pkgs.filter(category='hill_station')[:10]:
    print(f"      [{p.id}] {p.package_code}: {p.name} | Dest: {p.destination}")

print("\n   Sample 1-day packages in holiday:")
for p in one_day_pkgs.filter(category='holiday')[:10]:
    print(f"      [{p.id}] {p.package_code}: {p.name} | Dest: {p.destination}")

print("\n   Sample 1-day packages in devotional:")
for p in one_day_pkgs.filter(category='devotional')[:10]:
    print(f"      [{p.id}] {p.package_code}: {p.name} | Dest: {p.destination}")

# Check 2: Hill Stations with no hill station keywords
from scripts.reclassify_all_packages import HILL_STATION_KEYWORDS, DEVOTIONAL_KEYWORDS, INTL_COUNTRIES

print("\n2. Checking 'hill_station' packages for non-hill content:")
non_hill_in_hill = []
for p in Package.objects.filter(category='hill_station'):
    text = f"{p.name} {p.destination}".lower().replace("switzerland of india", "khajjiar himachal")
    has_hill = any(re.search(r'\b' + re.escape(kw) + r'\b', text) for kw in HILL_STATION_KEYWORDS)
    if not has_hill:
        non_hill_in_hill.append(p)
print(f"   --> Found {len(non_hill_in_hill)} packages in 'hill_station' without explicit hill keywords")
for p in non_hill_in_hill[:15]:
    print(f"      [{p.id}] {p.package_code}: {p.name} | Dest: {p.destination}")

# Check 3: Holiday packages with hill station or devotional keywords
print("\n3. Checking 'holiday' packages for hill or devotional keywords:")
hill_in_holiday = []
dev_in_holiday = []
for p in Package.objects.filter(category='holiday'):
    text = f"{p.name} {p.destination}".lower().replace("switzerland of india", "khajjiar himachal")
    has_hill = any(re.search(r'\b' + re.escape(kw) + r'\b', text) for kw in HILL_STATION_KEYWORDS)
    has_dev = any(re.search(r'\b' + re.escape(kw) + r'\b', text) for kw in DEVOTIONAL_KEYWORDS)
    if has_hill:
        hill_in_holiday.append((p, [kw for kw in HILL_STATION_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', text)]))
    if has_dev:
        dev_in_holiday.append((p, [kw for kw in DEVOTIONAL_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', text)]))

print(f"   --> Found {len(hill_in_holiday)} 'holiday' packages matching hill station keywords")
for p, kws in hill_in_holiday[:10]:
    print(f"      [{p.id}] {p.package_code}: {p.name} | Matched Hills: {kws}")

print(f"   --> Found {len(dev_in_holiday)} 'holiday' packages matching devotional keywords")
for p, kws in dev_in_holiday[:10]:
    print(f"      [{p.id}] {p.package_code}: {p.name} | Matched Devotional: {kws}")

# Check 4: Family Vacation packages
print("\n4. Checking 'family_vacation' packages:")
hill_in_family = []
dev_in_family = []
for p in Package.objects.filter(category='family_vacation'):
    text = f"{p.name} {p.destination}".lower().replace("switzerland of india", "khajjiar himachal")
    has_hill = any(re.search(r'\b' + re.escape(kw) + r'\b', text) for kw in HILL_STATION_KEYWORDS)
    has_dev = any(re.search(r'\b' + re.escape(kw) + r'\b', text) for kw in DEVOTIONAL_KEYWORDS)
    if has_hill:
        hill_in_family.append((p, [kw for kw in HILL_STATION_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', text)]))
    if has_dev:
        dev_in_family.append((p, [kw for kw in DEVOTIONAL_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', text)]))

print(f"   --> Found {len(hill_in_family)} 'family_vacation' packages matching hill keywords")
for p, kws in hill_in_family[:10]:
    print(f"      [{p.id}] {p.package_code}: {p.name} | Matched Hills: {kws}")

print(f"   --> Found {len(dev_in_family)} 'family_vacation' packages matching devotional keywords")
for p, kws in dev_in_family[:10]:
    print(f"      [{p.id}] {p.package_code}: {p.name} | Matched Devotional: {kws}")

# Check 5: Temple Darshan Slots Coverage across Devotional packages
print("\n5. Temple Darshan Slots coverage in 'devotional' packages:")
dev_total = Package.objects.filter(category='devotional').count()
dev_with_slots = Package.objects.filter(category='devotional', temple_slots__isnull=False).distinct().count()
print(f"   Devotional packages: {dev_total} | With TempleDarshanSlot: {dev_with_slots} | Without slots: {dev_total - dev_with_slots}")

# Check 6: Vehicle Tariffs Coverage across Local 1-Day packages
print("\n6. Vehicle Tariffs coverage in 'local_tour' packages:")
local_total = Package.objects.filter(category='local_tour').count()
local_with_tariffs = Package.objects.filter(category='local_tour', vehicle_tariffs__isnull=False).distinct().count()
print(f"   Local 1-Day packages: {local_total} | With VehicleTariffs: {local_with_tariffs} | Without tariffs: {local_total - local_with_tariffs}")

print("\n" + "=" * 80)
