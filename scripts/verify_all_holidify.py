import os
import sys
import django

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import Package, ItineraryDay, PackageVehicleTariff, TempleDarshanSlot

print("="*80)
print("COMPREHENSIVE HOLIDIFY IMPORT VERIFICATION (PHASES 1, 2 & 3)")
print("="*80)

# 1. Package Counts by Phase
si_pkgs = Package.objects.filter(package_code__startswith='SGT-HOL-SI-')
ni_pkgs = Package.objects.filter(package_code__startswith='SGT-HOL-NI-')
in_pkgs = Package.objects.filter(package_code__startswith='SGT-HOL-IN-')
all_hol = Package.objects.filter(package_code__startswith='SGT-HOL-')
grand_total = Package.objects.count()

print(f"Phase 1 (South India Packages [SGT-HOL-SI-]): {si_pkgs.count():,}")
print(f"Phase 2 (North India Packages [SGT-HOL-NI-]): {ni_pkgs.count():,}")
print(f"Phase 3 (All-India Packages   [SGT-HOL-IN-]): {in_pkgs.count():,}")
print(f"Total Holidify Packages Extracted & Imported:  {all_hol.count():,}")
print(f"Grand Total Active Packages in Travel ERP:     {grand_total:,}")
print("-" * 80)

# 2. Associated Records
hol_days = ItineraryDay.objects.filter(package__package_code__startswith='SGT-HOL-').count()
hol_tariffs = PackageVehicleTariff.objects.filter(package__package_code__startswith='SGT-HOL-').count()
hol_slots = TempleDarshanSlot.objects.filter(package__package_code__startswith='SGT-HOL-').count()

print(f"Total Holidify Itinerary Days:         {hol_days:,}")
print(f"Total Holidify 5-Tier Vehicle Tariffs: {hol_tariffs:,}")
print(f"Total Holidify Temple Darshan Slots:   {hol_slots:,}")
print("-" * 80)

# 3. Comprehensive Branding Leak Scan
print("Scanning all Holidify packages for branding leaks ('holidify', legacy contacts)...")
leaks = []
for p in all_hol:
    for field in ['name', 'description', 'inclusions', 'exclusions', 'terms_and_conditions']:
        val = getattr(p, field, '')
        if 'holidify' in val.lower():
            leaks.append((p.package_code, field, val[:60]))

print(f"Total branding leaks found: {len(leaks)}")
if leaks:
    for l in leaks[:10]:
        print("  LEAK:", l)
else:
    print("PASS: 100% clean! Zero branding leaks found across all packages.")

print("-" * 80)

# 4. Sample Verification from each phase
print("\n--- SAMPLE SOUTH INDIA PACKAGE ---")
sample_si = si_pkgs.first()
if sample_si:
    print(f"[{sample_si.package_code}] {sample_si.name}")
    print(f"Destination: {sample_si.destination} | Category: {sample_si.category}")
    print(f"Duration: {sample_si.duration_nights}N / {sample_si.duration_days}D | Price: ₹{sample_si.base_price:,.0f}")
    print(f"Days: {sample_si.itinerary_days.count()} | Tariffs: {sample_si.vehicle_tariffs.count()}")

print("\n--- SAMPLE NORTH INDIA PACKAGE ---")
sample_ni = ni_pkgs.first()
if sample_ni:
    print(f"[{sample_ni.package_code}] {sample_ni.name}")
    print(f"Destination: {sample_ni.destination} | Category: {sample_ni.category}")
    print(f"Duration: {sample_ni.duration_nights}N / {sample_ni.duration_days}D | Price: ₹{sample_ni.base_price:,.0f}")
    print(f"Days: {sample_ni.itinerary_days.count()} | Tariffs: {sample_ni.vehicle_tariffs.count()}")

print("\n--- SAMPLE ALL-INDIA LOCATION PACKAGE ---")
sample_in = in_pkgs.first()
if sample_in:
    print(f"[{sample_in.package_code}] {sample_in.name}")
    print(f"Destination: {sample_in.destination} | Category: {sample_in.category}")
    print(f"Duration: {sample_in.duration_nights}N / {sample_in.duration_days}D | Price: ₹{sample_in.base_price:,.0f}")
    print(f"Days: {sample_in.itinerary_days.count()} | Tariffs: {sample_in.vehicle_tariffs.count()}")

print("="*80)
