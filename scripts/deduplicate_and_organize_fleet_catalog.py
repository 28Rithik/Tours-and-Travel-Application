"""
Complete Deduplication, Canonicalization, and Categorization Script
for Travel ERP Fleet Assets.

1. Canonicalizes the 7 Vehicle Types that hold all 31,221 PackageVehicleTariff records:
   - Toyota Innova Crysta 2.4D -> Toyota Innova Crysta 2.4 GX+
   - Maruti Suzuki Swift Dzire Tour S -> Maruti Suzuki Dzire Lxi
   - Force Tempo Traveller (12-Seater Standard AC) -> Force Traveller T1 3350 AC
   - Force Urbania Luxury Van (17-Seater Long Wheelbase) -> Force Urbania 4400
   - BharatBenz Glider AC Luxury Coach (36-Seater Semi-Sleeper) -> Bharat Benz 1924 MG Glider Z+
   - Ashok Leyland Viking AC Deluxe Bus (40-Seater) -> Ashok Leyland Viking 11.4m Zedastra
   - 54-Seater Deluxe Pushback Air Suspension Coach -> Bharat Benz 1624 Prakash Zedastra

2. Purges the 22 generic duplicate test entries that have 0 tariffs and 0 vehicles:
   - Toyota Innova (Classic 2.5D), Toyota Fortuner 4x4 Luxury SUV, Toyota Etios GD Platinum,
     Honda City Executive Sedan, Hyundai Aura Prime, Kia Carens Luxury Plus,
     Mahindra Scorpio-N 4x4, Force Urbania (10S, 13S), Force Tempo Traveller (17S, 20S, 26S, 9S Maharaja),
     Tata Starbus Ultra AC Coach, Volvo 9600 AC Sleeper Coach, Tata Tigor EV / XPRES-T,
     BYD E6 / Atto 3, Olectra / JBM Electric, Scania Metrolink HD Coach 53S,
     Volvo B11R / 9600 Coach 49S, Maruti Suzuki Ertiga Smart Hybrid, Toyota Innova Hycross Hybrid.

3. Fixes duplicate names and typos from user text:
   - Purges 'Toyota Veilfire Executive Lounge' (keeps 'Toyota Vellfire Executive Lounge')
   - Purges 'BharatBenz 1017 : School' (keeps 'BharatBenz 1017 School Bus')
   - Purges 'BharatBenz 917 : School' (keeps 'BharatBenz 917 School Bus')
   - Purges 'Eicher Sykline Pro Next 3011 K' & duplicate 'Eicher Skyline Pro Next 3011 K' (keeps 'Eicher Skyline Pro Next 3011 K School')
   - Purges duplicate 'Force E - Traveller'
   - Purges duplicate plain 'Bharat Benz 1924'
   - Unifies 'Bharat Benz 1017 Ojes Body FG' into:
     * 'Bharat Benz 1017 Ojes Body FG (25-Seater 2x1)'
     * 'Bharat Benz 1017 Ojes Body FG (35-Seater 2x2)'
   - Unifies 'Volvo B8R 9600 SLX 15m' into:
     * 'Volvo B8R 9600 SLX 15m Sleeper (40 Berths)'
     * 'Volvo B8R 9600 SLX 15m Sleeper (42 Berths)'
   - Names bare chassis entries clearly:
     * 'Bharat Benz 1924 Heavy Coach Chassis (₹49L OEM)'
     * 'Ashok Leyland Garud TF 2513.5 Heavy Chassis (₹40L OEM)'

4. Corrects Misclassifications:
   - 'Force Motors Cityline AC' -> Luxury Van & Mini Coach (mini_coach)
   - 'BYD eMax 7 Premium' -> Electric Mobility (EV) (electric_ev)

5. Re-links all 13 Regional Fleet Vehicles stationed across Coimbatore Central HQ,
   Tirupur, Erode, Chennai, Hosur, and Trichy to the canonical records.
"""

import os
import sys
from decimal import Decimal

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from core.models import VehicleCategory, VehicleType, Vehicle
from packages.models import PackageVehicleTariff, Package
from operations.models import Booking

def run_deduplication():
    print("=" * 80)
    print("STARTING COMPREHENSIVE DEDUPLICATION & CANONICALIZATION OF FLEET ROSTER")
    print("=" * 80)

    # 1. Fetch Categories
    cats = {c.code: c for c in VehicleCategory.objects.all()}

    # 2. Map of Tariffs from Generic ID to Canonical Names
    # If a duplicate with the target name already exists, we will merge it into the tariff holder,
    # then rename the tariff holder to the canonical name!
    CANONICAL_MERGES = [
        {
            'tariff_holder_id': 1,
            'canonical_name': 'Toyota Innova Crysta 2.4 GX+',
            'duplicate_names': ['Toyota Innova Crysta 2.4 GX+', 'Toyota Innova Crysta 2.4D'],
            'category_code': 'suv_muv',
            'seats': 7,
            'fuel': 'diesel',
            'toll': 'car',
            'day_rate': Decimal('4200.00'),
            'km_rate': Decimal('18.00'),
            'bata': Decimal('500.00'),
            'night': Decimal('600.00'),
            'min_km': 250,
            'is_lux': True,
            'luggage': '4 Large Suitcases + 3 Handbags',
            'amenities': 'Pushback Captain Seats, Dual Blower AC, USB Fast Chargers, Sanitized Cabin',
        },
        {
            'tariff_holder_id': 3,
            'canonical_name': 'Maruti Suzuki Dzire Lxi',
            'duplicate_names': ['Maruti Suzuki Dzire Lxi', 'Maruti Suzuki Swift Dzire Tour S'],
            'category_code': 'sedan',
            'seats': 4,
            'fuel': 'petrol',
            'toll': 'car',
            'day_rate': Decimal('2400.00'),
            'km_rate': Decimal('12.50'),
            'bata': Decimal('350.00'),
            'night': Decimal('400.00'),
            'min_km': 250,
            'is_lux': False,
            'luggage': '2-3 Medium Trolley Bags',
            'amenities': 'High-Capacity Air Conditioning, Bluetooth Audio, Speed Governor, First Aid Kit',
        },
        {
            'tariff_holder_id': 4,
            'canonical_name': 'Force Traveller T1 3350 AC',
            'duplicate_names': ['Force Traveller T1 3350 AC', 'Force Tempo Traveller (12-Seater Standard AC)'],
            'category_code': 'mini_coach',
            'seats': 14,
            'fuel': 'diesel',
            'toll': 'lcv',
            'day_rate': Decimal('4800.00'),
            'km_rate': Decimal('20.00'),
            'bata': Decimal('600.00'),
            'night': Decimal('700.00'),
            'min_km': 300,
            'is_lux': False,
            'luggage': '14 Passenger Luggage Bags',
            'amenities': 'High-Capacity Air Conditioning, Reclining Seats, PA Audio System, Speed Governor',
        },
        {
            'tariff_holder_id': 12,
            'canonical_name': 'Force Urbania 4400',
            'duplicate_names': ['Force Urbania 4400', 'Force Urbania Luxury Van (17-Seater Long Wheelbase)'],
            'category_code': 'mini_coach',
            'seats': 16,
            'fuel': 'diesel',
            'toll': 'lcv',
            'day_rate': Decimal('7500.00'),
            'km_rate': Decimal('28.00'),
            'bata': Decimal('700.00'),
            'night': Decimal('700.00'),
            'min_km': 300,
            'is_lux': True,
            'luggage': '16 Passenger Rear Luggage Compartment',
            'amenities': 'Monocoque European Body, Independent Front Suspension, Individual AC Louvers, USB Ports on every seat, Reclining Bucket Seats',
        },
        {
            'tariff_holder_id': 13,
            'canonical_name': 'Bharat Benz 1924 MG Glider Z+',
            'duplicate_names': ['Bharat Benz 1924 MG Glider Z+', 'BharatBenz Glider AC Luxury Coach (36-Seater Semi-Sleeper)'],
            'category_code': 'luxury_coach',
            'seats': 36,
            'fuel': 'diesel',
            'toll': 'bus_2_axle',
            'day_rate': Decimal('17500.00'),
            'km_rate': Decimal('48.00'),
            'bata': Decimal('1000.00'),
            'night': Decimal('1200.00'),
            'min_km': 350,
            'is_lux': True,
            'luggage': '36 Passenger Underbelly Luggage Hold',
            'amenities': 'Private AC Sleeper Berths, Bedding & Linen, Individual USB Chargers, Air Suspension',
        },
        {
            'tariff_holder_id': 6,
            'canonical_name': 'Ashok Leyland Viking 11.4m Zedastra',
            'duplicate_names': ['Ashok Leyland Viking 11.4m Zedastra', 'Ashok Leyland Viking AC Deluxe Bus (40-Seater)'],
            'category_code': 'luxury_coach',
            'seats': 53,
            'fuel': 'diesel',
            'toll': 'bus_3_axle',
            'day_rate': Decimal('13500.00'),
            'km_rate': Decimal('38.00'),
            'bata': Decimal('850.00'),
            'night': Decimal('1000.00'),
            'min_km': 350,
            'is_lux': False,
            'luggage': '53 Bags in Underbelly Hold',
            'amenities': 'Pushback Reclining Seats (3x2), High-Capacity Air Conditioning, Air Suspension, LED TV',
        },
        {
            'tariff_holder_id': 8,
            'canonical_name': 'Bharat Benz 1624 Prakash Zedastra',
            'duplicate_names': ['Bharat Benz 1624 Prakash Zedastra', '54-Seater Deluxe Pushback Air Suspension Coach'],
            'category_code': 'luxury_coach',
            'seats': 53,
            'fuel': 'diesel',
            'toll': 'bus_3_axle',
            'day_rate': Decimal('13500.00'),
            'km_rate': Decimal('38.00'),
            'bata': Decimal('850.00'),
            'night': Decimal('1000.00'),
            'min_km': 350,
            'is_lux': False,
            'luggage': '53 Bags in Underbelly Hold',
            'amenities': 'Pushback Reclining Seats (3x2), Dual LCD Screens, Underbelly Luggage, Panic Buttons',
        },
    ]

    for item in CANONICAL_MERGES:
        th_id = item['tariff_holder_id']
        c_name = item['canonical_name']
        cat = cats[item['category_code']]
        
        # 1. Check if tariff holder exists
        th = VehicleType.objects.filter(id=th_id).first()
        if not th:
            print(f"[WARN] Tariff holder ID {th_id} not found!")
            continue

        # 2. Find any duplicate records with names in duplicate_names (excluding th itself)
        dupes = VehicleType.objects.filter(name__in=item['duplicate_names']).exclude(id=th_id)
        for dupe in dupes:
            # Re-point any vehicles assigned to dupe to th
            Vehicle.objects.filter(vehicle_type=dupe).update(vehicle_type=th, vehicle_category=cat)
            Booking.objects.filter(vehicle_type=dupe).update(vehicle_type=th)
            # Safe delete duplicate package tariffs
            for tariff in PackageVehicleTariff.objects.filter(vehicle_type=dupe):
                if PackageVehicleTariff.objects.filter(package=tariff.package, vehicle_type=th).exists():
                    tariff.delete()
                else:
                    tariff.vehicle_type = th
                    tariff.save()
            print(f"  * Merged duplicate VehicleType ID {dupe.id} ('{dupe.name}') into canonical ID {th.id}")
            dupe.delete()

        # 3. Update the canonical tariff holder record
        th.name = c_name
        th.vehicle_category = cat
        th.category = cat.name
        th.seating_capacity = item['seats']
        th.fuel_type = item['fuel']
        th.toll_class = item['toll']
        th.default_day_rate = item['day_rate']
        th.default_km_rate = item['km_rate']
        th.driver_bata = item['bata']
        th.night_halt_charge = item['night']
        th.minimum_km_per_day = item['min_km']
        th.extra_km_rate = item['km_rate']
        th.extra_hour_rate = Decimal('250.00') if item['seats'] <= 7 else Decimal('500.00')
        th.has_ac = True
        th.is_luxury = item['is_lux']
        th.luggage_capacity = item['luggage']
        th.amenities = item['amenities']
        th.description = f"{c_name} ({item['seats']}+D). Standard commercial passenger fleet specification for {cat.name} operations."
        th.save()
        print(f"[CANONICALIZED] ID {th.id} -> '{th.name}' ({th.seating_capacity} seats, {cat.name})")

    print("-" * 80)

    # 3. Purge the 22 Generic Test Placeholders (with 0 tariffs and 0 vehicles)
    GENERIC_TEST_NAMES = [
        'Toyota Innova (Classic 2.5D)',
        'Toyota Fortuner 4x4 Luxury SUV',
        'Toyota Etios GD Platinum',
        'Honda City Executive Sedan',
        'Hyundai Aura Prime',
        'Kia Carens Luxury Plus',
        'Mahindra Scorpio-N 4x4',
        'Force Urbania Luxury Van (10-Seater Executive)',
        'Force Urbania Luxury Van (13-Seater Medium)',
        'Force Tempo Traveller (17-Seater Deluxe AC)',
        'Force Tempo Traveller (20-Seater Super Deluxe AC)',
        'Force Tempo Traveller (26-Seater Mini Bus)',
        'Force Maharaja Tempo Traveller (9-Seater Luxury Recliner)',
        'Tata Starbus Ultra AC Coach (32-Seater Executive)',
        'Volvo 9600 AC Sleeper Coach (36-Berth Intercity Sleeper)',
        'Tata Tigor EV / XPRES-T (Electric Sedan - 4 Seater)',
        'BYD E6 / Atto 3 (Electric MPV - 5 Seater)',
        'Olectra / JBM Electric AC City & SEZ Shuttle (32-Seater)',
        'Scania Metrolink HD Multi-Axle Coach (53-Seater)',
        'Volvo B11R / 9600 Multi-Axle AC Luxury Coach (49-Seater)',
        'Maruti Suzuki Ertiga Smart Hybrid',
        'Toyota Innova Hycross Hybrid',
    ]

    purged_cnt = 0
    for gname in GENERIC_TEST_NAMES:
        for vt in VehicleType.objects.filter(name=gname):
            t_cnt = PackageVehicleTariff.objects.filter(vehicle_type=vt).count()
            v_cnt = Vehicle.objects.filter(vehicle_type=vt).count()
            if t_cnt == 0 and v_cnt == 0:
                print(f"[PURGED GENERIC TEST] ID {vt.id}: '{vt.name}'")
                vt.delete()
                purged_cnt += 1
            else:
                print(f"[RETAINED/REFERENCED] ID {vt.id}: '{vt.name}' (Tariffs: {t_cnt}, Vehicles: {v_cnt})")

    print(f"Total Generic Test Entries Purged: {purged_cnt}")
    print("-" * 80)

    # 4. Remove Typo / Exact Duplicate Aliases
    ALIAS_CLEANUPS = [
        # (duplicate_name, canonical_target_name)
        ('Toyota Veilfire Executive Lounge', 'Toyota Vellfire Executive Lounge'),
        ('BharatBenz 1017 : School', 'BharatBenz 1017 School Bus'),
        ('BharatBenz 917 : School', 'BharatBenz 917 School Bus'),
        ('Eicher Sykline Pro Next 3011 K', 'Eicher Skyline Pro Next 3011 K School'),
        ('Eicher Skyline Pro Next 3011 K', 'Eicher Skyline Pro Next 3011 K School'),
    ]

    for dup_name, canon_name in ALIAS_CLEANUPS:
        dupe_vts = VehicleType.objects.filter(name=dup_name)
        canon_vt = VehicleType.objects.filter(name=canon_name).first()
        for d in dupe_vts:
            if canon_vt and d.id != canon_vt.id:
                Vehicle.objects.filter(vehicle_type=d).update(vehicle_type=canon_vt)
                Booking.objects.filter(vehicle_type=d).update(vehicle_type=canon_vt)
                print(f"[PURGED DUPLICATE ALIAS] ID {d.id} '{d.name}' -> Merged into ID {canon_vt.id} '{canon_vt.name}'")
                d.delete()
            elif not canon_vt:
                d.name = canon_name
                d.save()
                print(f"[RENAMED ALIAS] ID {d.id} '{dup_name}' -> '{canon_name}'")

    # Clean up duplicate 42B entry if present
    VehicleType.objects.filter(name='Volvo B8R 9600 SLX 15m 42B').delete()

    print("-" * 80)

    # 5. Differentiate duplicate configurations in the user text:
    # 5a. Bharat Benz 1017 Ojes Body FG: 25-seater vs 35-seater
    ojes_all = list(VehicleType.objects.filter(name__icontains='Bharat Benz 1017 Ojes Body FG').order_by('id'))
    if len(ojes_all) >= 2:
        v25 = ojes_all[0]
        v35 = ojes_all[1]
        v25.name = 'Bharat Benz 1017 Ojes Body FG (25-Seater 2x1)'
        v25.seating_capacity = 25
        v25.vehicle_category = cats['mini_coach']
        v25.category = cats['mini_coach'].name
        v25.save()
        print(f"[DIFFERENTIATED] ID {v25.id}: '{v25.name}' (25 seats, mini_coach)")

        v35.name = 'Bharat Benz 1017 Ojes Body FG (35-Seater 2x2)'
        v35.seating_capacity = 35
        v35.vehicle_category = cats['luxury_coach']
        v35.category = cats['luxury_coach'].name
        v35.save()
        print(f"[DIFFERENTIATED] ID {v35.id}: '{v35.name}' (35 seats, luxury_coach)")

    # 5b. Volvo B8R 9600 SLX 15m: 40-berth vs 42-berth
    target_40_name = 'Volvo B8R 9600 SLX 15m Sleeper (40 Berths)'
    slx_40 = VehicleType.objects.filter(name__icontains='9600 SLX 15m Sleeper 40B').first()
    if slx_40:
        VehicleType.objects.filter(name=target_40_name).exclude(id=slx_40.id).delete()
        slx_40.name = target_40_name
        slx_40.seating_capacity = 40
        slx_40.vehicle_category = cats['luxury_coach']
        slx_40.category = cats['luxury_coach'].name
        slx_40.is_luxury = True
        slx_40.save()
        print(f"[CANONICALIZED] ID {slx_40.id}: '{slx_40.name}'")

    target_42_name = 'Volvo B8R 9600 SLX 15m Sleeper (42 Berths)'
    slx_42 = VehicleType.objects.filter(name__icontains='9600 SLX 15m Sleeper 42B').first()
    if slx_42:
        VehicleType.objects.filter(name=target_42_name).exclude(id=slx_42.id).delete()
        slx_42.name = target_42_name
        slx_42.seating_capacity = 42
        slx_42.vehicle_category = cats['luxury_coach']
        slx_42.category = cats['luxury_coach'].name
        slx_42.is_luxury = True
        slx_42.save()
        print(f"[CANONICALIZED] ID {slx_42.id}: '{slx_42.name}'")

    # 5c. Bare OEM Chassis platforms
    chassis_bb = VehicleType.objects.filter(name__icontains='Bharat Benz 1924 Chassis').first()
    if chassis_bb:
        chassis_bb.name = 'Bharat Benz 1924 Heavy Coach Chassis (Rs. 49L OEM)'
        chassis_bb.vehicle_category = cats['luxury_coach']
        chassis_bb.category = cats['luxury_coach'].name
        chassis_bb.seating_capacity = 45
        chassis_bb.description = 'Heavy Intercity Bus Chassis Platform (OM 926 engine, 240 HP, 6-speed overdrive gearbox). Ready for custom luxury sleeper or semi-sleeper coachbuilding.'
        chassis_bb.save()
        print(f"[CANONICALIZED CHASSIS] ID {chassis_bb.id}: '{chassis_bb.name}'")

    chassis_al = VehicleType.objects.filter(name__icontains='Garud TF 2513.5 - 40 Lakhs').first()
    if chassis_al:
        chassis_al.name = 'Ashok Leyland Garud TF 2513.5 Heavy Chassis (Rs. 40L OEM)'
        chassis_al.vehicle_category = cats['luxury_coach']
        chassis_al.category = cats['luxury_coach'].name
        chassis_al.seating_capacity = 45
        chassis_al.description = 'Ashok Leyland Garud TF 13.5m Multi-Axle Intercity Chassis Platform (H-Series 6-cylinder engine). Ideal for custom sleeper / semi-sleeper coachwork.'
        chassis_al.save()
        print(f"[CANONICALIZED CHASSIS] ID {chassis_al.id}: '{chassis_al.name}'")

    # 5d. Remove duplicate plain 'Bharat Benz 1924' if it has no coachbuilder specified and no tariffs
    plain_bb1924 = VehicleType.objects.filter(name='Bharat Benz 1924')
    for p in plain_bb1924:
        t_cnt = PackageVehicleTariff.objects.filter(vehicle_type=p).count()
        v_cnt = Vehicle.objects.filter(vehicle_type=p).count()
        if t_cnt == 0 and v_cnt == 0:
            print(f"[PURGED DUPLICATE PLAIN BB1924] ID {p.id}: '{p.name}'")
            p.delete()

    # 5e. Deduplicate Force E-Traveller
    e_travellers = list(VehicleType.objects.filter(name__icontains='Force E - Traveller'))
    if len(e_travellers) > 1:
        keep = e_travellers[0]
        for dupe in e_travellers[1:]:
            Vehicle.objects.filter(vehicle_type=dupe).update(vehicle_type=keep)
            print(f"[PURGED DUPLICATE EV] ID {dupe.id}: '{dupe.name}' -> Merged into ID {keep.id}")
            dupe.delete()

    print("-" * 80)

    # 6. Correct Misclassifications:
    # 6a. Force Motors Cityline AC (9 seats) -> mini_coach
    cityline = VehicleType.objects.filter(name__icontains='Cityline').first()
    if cityline:
        cityline.vehicle_category = cats['mini_coach']
        cityline.category = cats['mini_coach'].name
        cityline.seating_capacity = 9
        cityline.toll_class = 'lcv'
        cityline.fuel_type = 'diesel'
        cityline.save()
        print(f"[RECLASSIFIED] {cityline.name} -> Luxury Van & Mini Coach (mini_coach)")

    # 6b. BYD eMax 7 Premium (6 seats) -> electric_ev
    byd_emax = VehicleType.objects.filter(name__icontains='BYD eMax 7').first()
    if byd_emax:
        byd_emax.vehicle_category = cats['electric_ev']
        byd_emax.category = cats['electric_ev'].name
        byd_emax.fuel_type = 'electric'
        byd_emax.is_luxury = True
        byd_emax.toll_class = 'car'
        byd_emax.save()
        print(f"[RECLASSIFIED] {byd_emax.name} -> Electric Mobility (EV) (electric_ev)")

    # 6c. Toyota Vellfire Executive Lounge -> luxury_vip
    vellfire = VehicleType.objects.filter(name='Toyota Vellfire Executive Lounge').first()
    if vellfire:
        vellfire.vehicle_category = cats['luxury_vip']
        vellfire.category = cats['luxury_vip'].name
        vellfire.is_luxury = True
        vellfire.fuel_type = 'petrol'
        vellfire.save()
        print(f"[RECLASSIFIED] {vellfire.name} -> Ultra-Luxury VIP & Chauffeur Drive (luxury_vip)")

    print("-" * 80)

    # 7. Re-link all 13 Regional Fleet Vehicles stationed across 6 Hubs
    crysta = VehicleType.objects.filter(name='Toyota Innova Crysta 2.4 GX+').first()
    hycross = VehicleType.objects.filter(name='Toyota Innova Hycross VX').first()
    dzire = VehicleType.objects.filter(name='Maruti Suzuki Dzire Lxi').first()
    etios = VehicleType.objects.filter(name='Toyota Etios VXD').first()
    urbania = VehicleType.objects.filter(name='Force Urbania 4400').first()
    tt = VehicleType.objects.filter(name='Force Traveller T1 3350 AC').first()
    glider = VehicleType.objects.filter(name='Bharat Benz 1624 MG Glider 12m FG').first()
    volvo = VehicleType.objects.filter(name='Volvo 9400 B11R 14.5m Multi-Axle').first()
    scania = VehicleType.objects.filter(name='Scania Metrolink HD 14.5m Multi-Axle').first()

    for v in Vehicle.objects.all():
        m_lower = (v.model or '').lower() + ' ' + (v.brand or '').lower()
        if 'hycross' in m_lower and hycross:
            v.vehicle_type = hycross
        elif 'crysta' in m_lower and crysta:
            v.vehicle_type = crysta
        elif 'etios' in m_lower and etios:
            v.vehicle_type = etios
        elif 'dzire' in m_lower and dzire:
            v.vehicle_type = dzire
        elif 'urbania' in m_lower and urbania:
            v.vehicle_type = urbania
        elif 'tempo traveller' in m_lower and tt:
            v.vehicle_type = tt
        elif 'glider' in m_lower and glider:
            v.vehicle_type = glider
        elif 'volvo' in m_lower and volvo:
            v.vehicle_type = volvo
        elif 'scania' in m_lower and scania:
            v.vehicle_type = scania
        
        if v.vehicle_type:
            v.vehicle_category = v.vehicle_type.vehicle_category
        v.save()
        print(f"Vehicle {v.registration_number}: Linked to {v.vehicle_type.name} ({v.vehicle_category.name if v.vehicle_category else 'None'}) @ {v.base_depot}")

    print("=" * 80)
    print("FINAL CATALOG COUNTS PER CATEGORY:")
    print("=" * 80)
    for cat in VehicleCategory.objects.all().order_by('display_order'):
        print(f" - {cat.name:<45} ({cat.code}): {cat.vehicle_types.count():3d} Types, {cat.vehicles.count():2d} Vehicles")

    total_types = VehicleType.objects.count()
    print(f"\nTOTAL UNIQUE VEHICLE TYPES IN DATABASE: {total_types}")
    print("=" * 80)

if __name__ == '__main__':
    run_deduplication()
