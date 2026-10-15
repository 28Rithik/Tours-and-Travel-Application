import os
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import django
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from core.models import VehicleType, VehicleCategory, Vehicle
from packages.models import PackageVehicleTariff

out_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audit_duplicates.txt')
with open(out_file, 'w', encoding='utf-8') as out:
    out.write("=" * 80 + "\n")
    out.write("AUDITING VEHICLE CATEGORIES & VEHICLE TYPES FOR DUPLICATES AND MISCLASSIFICATIONS\n")
    out.write("=" * 80 + "\n\n")

    # 1. Exact duplicates or near duplicates
    name_map = defaultdict(list)
    for vt in VehicleType.objects.all():
        norm = " ".join(vt.name.lower().replace("-", " ").replace(":", " ").replace("+", " ").split())
        name_map[norm].append(vt)

    duplicates_found = 0
    out.write("--- 1. DUPLICATE CLUSTERS (NORMALIZED) ---\n")
    for norm, vts in name_map.items():
        if len(vts) > 1:
            duplicates_found += 1
            out.write(f"\n[Cluster #{duplicates_found}] Normalized: '{norm}'\n")
            for vt in vts:
                tariff_count = PackageVehicleTariff.objects.filter(vehicle_type=vt).count()
                vehicle_count = Vehicle.objects.filter(vehicle_type=vt).count()
                out.write(f"  * ID {vt.id:3d}: '{vt.name}' | Seats: {vt.seating_capacity} | Cat: {vt.vehicle_category.code if vt.vehicle_category else None} | Tariffs: {tariff_count} | Assigned Vehicles: {vehicle_count}\n")

    out.write(f"\nTotal duplicate clusters found: {duplicates_found}\n\n")

    # 2. Category inspection
    out.write("--- 2. CATEGORY AUDIT ---\n")
    for cat in VehicleCategory.objects.all().order_by('display_order'):
        vts = cat.vehicle_types.all().order_by('seating_capacity', 'name')
        out.write(f"\nCategory: {cat.name} ({cat.code}) - {vts.count()} types\n")
        for vt in vts:
            tariff_count = PackageVehicleTariff.objects.filter(vehicle_type=vt).count()
            vehicle_count = Vehicle.objects.filter(vehicle_type=vt).count()
            out.write(f"  [{vt.id:3d}] {vt.name:<48} | {vt.seating_capacity:2d} seats | Fuel: {vt.fuel_type:<8} | AC: {vt.has_ac} | Lux: {vt.is_luxury} | Tariffs: {tariff_count} | Vehicles: {vehicle_count}\n")

print(f"Audit written to {out_file}")

# 2. Similar names (fuzzy)
print("\n--- 2. POTENTIAL NEAR-DUPLICATES (SUBSTRING / FUZZY) ---")
all_vts = list(VehicleType.objects.all().order_by('name'))
fuzzy_clusters = []
for i, vt1 in enumerate(all_vts):
    n1 = vt1.name.lower()
    for vt2 in all_vts[i+1:]:
        n2 = vt2.name.lower()
        # Check if one is a substring of the other and they have similar seats
        if (n1 in n2 or n2 in n1) and abs(vt1.seating_capacity - vt2.seating_capacity) <= 2:
            print(f"  * Similar: ID {vt1.id} '{vt1.name}' ({vt1.seating_capacity}s, {vt1.vehicle_category.code if vt1.vehicle_category else None}) <---> ID {vt2.id} '{vt2.name}' ({vt2.seating_capacity}s, {vt2.vehicle_category.code if vt2.vehicle_category else None})")

# 3. Category inspection
print("\n--- 3. CATEGORY AUDIT ---")
for cat in VehicleCategory.objects.all().order_by('display_order'):
    vts = cat.vehicle_types.all().order_by('seating_capacity', 'name')
    print(f"\nCategory: {cat.name} ({cat.code}) - {vts.count()} types")
    for vt in vts:
        print(f"  [{vt.id:3d}] {vt.name:<48} | {vt.seating_capacity:2d} seats | Fuel: {vt.fuel_type:<8} | AC: {vt.has_ac} | Lux: {vt.is_luxury}")

print("\n" + "=" * 80)
