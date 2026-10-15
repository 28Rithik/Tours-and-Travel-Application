"""
Seed Master Vehicle Categories for Enterprise Fleet Management.
Standardizes Indian tours, travel, and corporate passenger mobility categories:
1. Sedan & Compact (Dzire, Etios, Aura - 4+1)
2. Premium MUV & SUV (Innova Crysta, Hycross, Ertiga - 6+1/7+1)
3. Luxury Van & Mini Coach (Force Urbania, Tempo Traveller - 12S to 26S)
4. Intercity Luxury Coach / Bus (Volvo, Scania, BharatBenz - 36S to 54S)
5. Electric Mobility (EV) (Zero-emission Corporate Fleet)

Also links existing VehicleType and Vehicle records to their respective categories.
"""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from core.models import VehicleCategory, VehicleType, Vehicle

CATEGORIES = [
    {
        'name': 'Sedan & Compact',
        'code': 'sedan',
        'description': 'Swift Dzire, Toyota Etios, Hyundai Aura. Economical for airport transfers, city packages, and couple/small family tours.',
        'icon': 'fa-solid fa-car-side',
        'badge_color': '#0284c7',
        'seating_range': '4 + 1 Seats',
        'display_order': 1,
        'is_active': True,
    },
    {
        'name': 'Premium MUV & SUV',
        'code': 'suv_muv',
        'description': 'Toyota Innova Crysta, Innova Hycross, Maruti Ertiga, Kia Carens. Premium family vacations, hill stations (Ooty, Kodaikanal), and VIP transport.',
        'icon': 'fa-solid fa-van-shuttle',
        'badge_color': '#8b5cf6',
        'seating_range': '6 - 7 Seats',
        'display_order': 2,
        'is_active': True,
    },
    {
        'name': 'Luxury Van & Mini Coach',
        'code': 'mini_coach',
        'description': 'Force Urbania, Force Tempo Traveller (12S, 17S, 20S, 26S). Group pilgrimages, wedding delegations, and corporate SEZ team shuttles.',
        'icon': 'fa-solid fa-bus-simple',
        'badge_color': '#10b981',
        'seating_range': '12 - 26 Seats',
        'display_order': 3,
        'is_active': True,
    },
    {
        'name': 'Intercity Luxury Coach / Bus',
        'code': 'luxury_coach',
        'description': 'Volvo 9600 Multi-Axle, Scania Metrolink, BharatBenz (36S to 54S Air Suspension Sleeper & Pushback Coaches). College IVs, long-haul tours, and industrial staff contracts.',
        'icon': 'fa-solid fa-bus',
        'badge_color': '#f59e0b',
        'seating_range': '36 - 54 Seats',
        'display_order': 4,
        'is_active': True,
    },
    {
        'name': 'Electric Mobility (EV)',
        'code': 'electric_ev',
        'description': 'Zero-emission electric sedans and vans for ESG-conscious corporate clients and green city shuttles.',
        'icon': 'fa-solid fa-bolt',
        'badge_color': '#06b6d4',
        'seating_range': '4 - 14 Seats',
        'display_order': 5,
        'is_active': True,
    },
]

def seed_categories():
    print("=" * 80)
    print("SEEDING ENTERPRISE VEHICLE CATEGORIES")
    print("=" * 80)

    category_objs = {}
    for data in CATEGORIES:
        cat, created = VehicleCategory.objects.update_or_create(
            code=data['code'],
            defaults=data
        )
        category_objs[data['code']] = cat
        action = "CREATED" if created else "UPDATED"
        print(f"[{action}] {cat.name} ({cat.code}) - {cat.seating_range}")

    print("\n" + "-" * 80)
    print("MAPPING EXISTING VEHICLE TYPES TO CATEGORIES")
    print("-" * 80)

    # Heuristic mapping for existing vehicle types
    vtypes = VehicleType.objects.all()
    mapped_types = 0
    for vt in vtypes:
        name_lower = vt.name.lower()
        seats = vt.seating_capacity

        target_cat = None
        if 'ev' in name_lower or 'electric' in name_lower:
            target_cat = category_objs['electric_ev']
        elif 'bus' in name_lower or 'coach' in name_lower or 'volvo' in name_lower or seats >= 30:
            target_cat = category_objs['luxury_coach']
        elif 'tempo' in name_lower or 'traveller' in name_lower or 'urbania' in name_lower or (10 <= seats <= 26):
            target_cat = category_objs['mini_coach']
        elif 'innova' in name_lower or 'crysta' in name_lower or 'ertiga' in name_lower or 'fortuner' in name_lower or (5 <= seats <= 8):
            target_cat = category_objs['suv_muv']
        elif 'sedan' in name_lower or 'dzire' in name_lower or 'etios' in name_lower or seats <= 4:
            target_cat = category_objs['sedan']
        else:
            target_cat = category_objs['suv_muv']

        vt.vehicle_category = target_cat
        if not vt.category:
            vt.category = target_cat.name
        vt.save()
        mapped_types += 1
        print(f"  • {vt.name} ({seats} seats) -> {target_cat.name}")

    print(f"\nTotal Vehicle Types Mapped: {mapped_types}")

    print("\n" + "-" * 80)
    print("SYNCHRONIZING FLEET VEHICLES TO VEHICLE CATEGORIES")
    print("-" * 80)

    vehicles = Vehicle.objects.all()
    synced_vehicles = 0
    for v in vehicles:
        if v.vehicle_type and v.vehicle_type.vehicle_category:
            v.vehicle_category = v.vehicle_type.vehicle_category
            v.save(update_fields=['vehicle_category'])
            synced_vehicles += 1

    print(f"Total Fleet Vehicles Synchronized: {synced_vehicles}")
    print("=" * 80)

if __name__ == '__main__':
    seed_categories()
