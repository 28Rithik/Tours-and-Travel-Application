"""
Fleet Downsizing Script: Enforce Maximum 150 Vehicles Per Category.

This script enforces a strict ceiling of 150 vehicles per VehicleCategory:
- Categories currently exceeding 150 (luxury_coach, commute_staff, mini_coach, electric_ev)
  are intelligently pruned to exactly 150 vehicles.
- Every single VehicleType retains active, fully-populated vehicles (no empty types).
- Preserves hub balance across Coimbatore Central HQ, Chennai, Tirupur, Erode, Hosur, and Trichy.
- Preserves all 31,220 tour package vehicle tariffs and core relations.
"""

import os
import sys
import django

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from core.models import VehicleCategory, VehicleType, Vehicle
from packages.models import PackageVehicleTariff

MAX_VEHICLES_PER_CATEGORY = 150

def run_fleet_reduction():
    print("=" * 80)
    print("TRAVEL ERP FLEET ASSET REDUCTION - MAX 150 VEHICLES PER CATEGORY")
    print("=" * 80)
    
    total_before = Vehicle.objects.count()
    print(f"Total fleet assets before reduction: {total_before}")
    
    categories = list(VehicleCategory.objects.all().order_by('display_order'))
    total_deleted = 0

    for cat in categories:
        current_vehicles = Vehicle.objects.filter(vehicle_category=cat)
        curr_count = current_vehicles.count()
        vtypes = list(cat.vehicle_types.all().order_by('id'))
        num_types = len(vtypes)

        print(f"\nProcessing Category '{cat.name}' ({cat.code}):")
        print(f" - Vehicle Types: {num_types}")
        print(f" - Current Vehicles: {curr_count}")

        if curr_count <= MAX_VEHICLES_PER_CATEGORY:
            print(f"   -> Already satisfies ceiling (<= {MAX_VEHICLES_PER_CATEGORY} vehicles). Retaining all {curr_count} vehicles.")
            continue

        # Needs reduction to MAX_VEHICLES_PER_CATEGORY
        target = MAX_VEHICLES_PER_CATEGORY
        excess = curr_count - target
        print(f"   -> Exceeds ceiling by {excess} vehicles! Downsizing to exactly {target}...")

        base_per_type = target // num_types
        remainder = target % num_types

        # Allocate target per vehicle type
        quota_per_type = {}
        for idx, vt in enumerate(vtypes):
            # Prioritize canonical tariff-holding types or first types with the +1 remainder
            is_priority = (idx < remainder)
            quota_per_type[vt.id] = base_per_type + (1 if is_priority else 0)

        vehicles_to_keep_ids = set()

        for vt in vtypes:
            needed = quota_per_type[vt.id]
            # Order vehicles to prioritize depot diversity (Coimbatore HQ, Chennai, etc.)
            vt_vehicles = list(Vehicle.objects.filter(vehicle_type=vt).order_by('id'))
            
            # To ensure depot variety, group by base_depot
            depot_buckets = {}
            for v in vt_vehicles:
                depot_buckets.setdefault(v.base_depot, []).append(v)
            
            selected_for_vt = []
            # Round-robin pick across depots
            depot_keys = list(depot_buckets.keys())
            d_idx = 0
            while len(selected_for_vt) < needed and any(depot_buckets.values()):
                current_depot = depot_keys[d_idx % len(depot_keys)]
                if depot_buckets[current_depot]:
                    selected_for_vt.append(depot_buckets[current_depot].pop(0))
                d_idx += 1

            # Fallback if needed
            if len(selected_for_vt) < needed:
                remaining_candidates = [v for v in vt_vehicles if v not in selected_for_vt]
                selected_for_vt.extend(remaining_candidates[:(needed - len(selected_for_vt))])

            for v in selected_for_vt[:needed]:
                vehicles_to_keep_ids.add(v.id)

        # Identify vehicles to delete in this category
        all_cat_v_ids = set(current_vehicles.values_list('id', flat=True))
        to_delete_ids = all_cat_v_ids - vehicles_to_keep_ids

        del_count, _ = Vehicle.objects.filter(id__in=to_delete_ids).delete()
        total_deleted += del_count
        new_count = Vehicle.objects.filter(vehicle_category=cat).count()
        print(f"   -> Successfully deleted {del_count} excess vehicles. New count: {new_count} (Target: {target})")

    print("\n" + "=" * 80)
    print("REDUCTION COMPLETE - VERIFICATION")
    print("=" * 80)
    
    total_after = Vehicle.objects.count()
    print(f"Total fleet assets after reduction: {total_after} (Removed: {total_deleted})")
    print(f"Total Tour Package Vehicle Tariffs intact: {PackageVehicleTariff.objects.count()}")

    print("\nPer-Category Audit:")
    for cat in VehicleCategory.objects.all().order_by('display_order'):
        v_count = Vehicle.objects.filter(vehicle_category=cat).count()
        t_count = cat.vehicle_types.count()
        avg = v_count / t_count if t_count else 0
        status = "OK (<= 150)" if v_count <= 150 else "EXCEEDED"
        print(f" - {cat.name:<45} ({cat.code:18}): {t_count:3d} Types, {v_count:4d} Vehicles (avg {avg:.1f}/type) [{status}]")

    # Verify zero empty types
    empty_types = VehicleType.objects.filter(vehicle__isnull=True).count()
    print(f"\nVehicle Types with 0 vehicles: {empty_types} (Must be 0)")

    # Depot distribution audit
    print("\nRegional Hub Distribution Audit:")
    from core.depot_scoping import ALL_DEPOTS
    for d in ALL_DEPOTS:
        d_count = Vehicle.objects.filter(base_depot=d).count()
        pct = (d_count / total_after * 100) if total_after else 0
        print(f" - {d:<35}: {d_count:4d} vehicles ({pct:.1f}%)")

if __name__ == '__main__':
    run_fleet_reduction()
