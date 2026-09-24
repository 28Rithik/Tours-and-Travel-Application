import os
import sys
import django

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from packages.models import Package, ItineraryDay, PackageVehicleTariff, TempleDarshanSlot

pkgs = Package.objects.filter(package_code__startswith='SGT-HOL-NI-')
print(f"Total SGT-HOL-NI- Packages: {pkgs.count()}")
print(f"Total Itinerary Days: {ItineraryDay.objects.filter(package__package_code__startswith='SGT-HOL-NI-').count()}")
print(f"Total Vehicle Tariffs: {PackageVehicleTariff.objects.filter(package__package_code__startswith='SGT-HOL-NI-').count()}")
print(f"Total Temple Slots: {TempleDarshanSlot.objects.filter(package__package_code__startswith='SGT-HOL-NI-').count()}")

# Branding leak check
leaks = []
for p in pkgs:
    for field in ['name', 'description', 'inclusions', 'exclusions', 'terms_and_conditions']:
        val = getattr(p, field, '')
        if 'holidify' in val.lower():
            leaks.append((p.package_code, field, val[:60]))

print(f"Branding leaks in SGT-HOL-NI-: {len(leaks)}")
if leaks:
    for l in leaks[:5]:
        print("  Leak:", l)

sample = pkgs.first()
if sample:
    print(f"\nSample Package: [{sample.package_code}] {sample.name}")
    print(f"Destination: {sample.destination} | Category: {sample.category}")
    print(f"Duration: {sample.duration_nights}N / {sample.duration_days}D | Price: ₹{sample.base_price:,.0f}")
    print(f"Itinerary Days in DB: {sample.itinerary_days.count()}")
    print(f"Vehicle Tariffs in DB: {sample.vehicle_tariffs.count()}")
    first_day = sample.itinerary_days.first()
    if first_day:
        print(f"Day 1 Title: {first_day.title}")
        print(f"Day 1 Activities: {first_day.activities[:150]}...")
