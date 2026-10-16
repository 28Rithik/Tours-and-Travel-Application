"""
Master Vehicle Population Script for Travel ERP Fleet Assets.

Ensures that EVERY single VehicleType in the database has exactly 15 fully-populated,
realistic commercial fleet vehicles stationed across the 6 regional operating hubs:
1. Coimbatore Central HQ (Primary Location - 35% of fleet)
2. Chennai Branch (Metro & Airport Concierge - 25% of fleet)
3. Tirupur Branch (Industrial / Knitwear Corridor - 12% of fleet)
4. Erode Branch (Textile & Inter-State Corridor - 10% of fleet)
5. Hosur Branch (Industrial Border Corridor - 10% of fleet)
6. Trichy Branch (Central Transit & Temple City - 8% of fleet)

Each vehicle is populated with 100% realistic Tamil Nadu commercial transport specs:
- Unique commercial RTO registration (TN 38, TN 39, TN 33, TN 07, TN 70, TN 45, etc.)
- Strict VIN / Chassis number (17-char ISO standard) & Engine Number
- Real GPS IMEI (15 digits) & FASTag electronic toll RFID
- Active commercial compliance dates (RC, Fitness, Insurance, All India Tourist Permit, Road Tax, PUC)
- Realistic odometer readings, fuel tank capacity, DEF capacity, telemetry location
- Financing specs (Sundaram Finance, Cholamandalam, HDFC, ICICI)
- Amenities flags (AC, Sleeper, Air Suspension, Video Coach) matching the model
"""

import os
import sys
import random
import string
from datetime import date, timedelta
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

from core.models import VehicleType, VehicleCategory, Vehicle
from core.depot_scoping import (
    DEPOT_COIMBATORE,
    DEPOT_CHENNAI,
    DEPOT_TIRUPUR,
    DEPOT_ERODE,
    DEPOT_HOSUR,
    DEPOT_TRICHY,
)

# Depot allocation weights and RTO codes
DEPOT_CONFIG = [
    {
        'depot': DEPOT_COIMBATORE,
        'weight': 35,
        'rto_prefixes': ['TN 38', 'TN 37', 'TN 66', 'TN 99'],
        'loc_names': ['Coimbatore Central HQ - Bay A', 'Coimbatore Central HQ - Bay B', 'Coimbatore Airport Terminal Garage', 'Coimbatore Gandhipuram Transit Hub'],
    },
    {
        'depot': DEPOT_CHENNAI,
        'weight': 25,
        'rto_prefixes': ['TN 07', 'TN 10', 'TN 14', 'TN 09', 'TN 18'],
        'loc_names': ['Chennai Branch - Guindy Tech Garage', 'Chennai Airport Concierge Bay', 'Chennai Central Depot - Koyambedu', 'Chennai OMR Express Depot'],
    },
    {
        'depot': DEPOT_TIRUPUR,
        'weight': 12,
        'rto_prefixes': ['TN 39', 'TN 42'],
        'loc_names': ['Tirupur Branch - Avinashi Road Yard', 'Tirupur Industrial Area Station', 'Tirupur Export Corridor Depot'],
    },
    {
        'depot': DEPOT_ERODE,
        'weight': 10,
        'rto_prefixes': ['TN 33', 'TN 34', 'TN 36'],
        'loc_names': ['Erode Branch - Perundurai Road Terminal', 'Erode Central Transit Yard', 'Erode SIPCOT Depot'],
    },
    {
        'depot': DEPOT_HOSUR,
        'weight': 10,
        'rto_prefixes': ['TN 70'],
        'loc_names': ['Hosur Branch - SIPCOT Phase II Garage', 'Hosur Border Express Hub', 'Hosur NH44 Transit Yard'],
    },
    {
        'depot': DEPOT_TRICHY,
        'weight': 8,
        'rto_prefixes': ['TN 45', 'TN 48', 'TN 81'],
        'loc_names': ['Trichy Branch - Central Bus Stand Bay', 'Trichy International Airport Concierge', 'Trichy Srirangam Pilgrimage Garage'],
    },
]

INSURERS = [
    'Tata AIG General Insurance Co.',
    'ICICI Lombard General Insurance',
    'HDFC ERGO General Insurance',
    'New India Assurance Co. Ltd.',
    'Bajaj Allianz General Insurance',
    'Cholamandalam MS General Insurance',
]

FINANCIERS = [
    'Sundaram Finance Ltd.',
    'Cholamandalam Investment and Finance',
    'HDFC Bank Commercial Vehicle Loan',
    'ICICI Bank Commercial Equipment Finance',
    'Shriram Transport Finance Co.',
]

COLORS_LUXURY = ['Pearl White', 'Diamond White', 'Obsidian Black', 'Iridium Silver', 'Royal Navy Blue']
COLORS_STANDARD = ['Super White', 'Pure White', 'Silky Silver', 'Magnesium Grey', 'Golden Bronze']

def get_brand_from_name(name):
    n_lower = name.lower()
    if 'toyota' in n_lower:
        return 'Toyota'
    elif 'maruti' in n_lower or 'suzuki' in n_lower or 'dzire' in n_lower or 'ertiga' in n_lower or 'ciaz' in n_lower or 'invicto' in n_lower:
        return 'Maruti Suzuki'
    elif 'mercedes' in n_lower:
        return 'Mercedes-Benz'
    elif 'bharat benz' in n_lower or 'bharatbenz' in n_lower:
        return 'BharatBenz'
    elif 'force' in n_lower or 'urbania' in n_lower or 'traveller' in n_lower or 'cityline' in n_lower or 'monobus' in n_lower:
        return 'Force Motors'
    elif 'ashok leyland' in n_lower or 'viking' in n_lower or 'garud' in n_lower or 'oyster' in n_lower or 'lynx' in n_lower:
        return 'Ashok Leyland'
    elif 'volvo eicher' in n_lower or 'eicher' in n_lower or 'starline' in n_lower:
        return 'Volvo Eicher (VECV)'
    elif 'volvo' in n_lower:
        return 'Volvo Buses India'
    elif 'scania' in n_lower:
        return 'Scania Commercial Vehicles'
    elif 'sml' in n_lower or 'isuzu' in n_lower or 'hiroi' in n_lower:
        return 'SML Isuzu'
    elif 'tata' in n_lower or 'winger' in n_lower or 'starbus' in n_lower:
        return 'Tata Motors'
    elif 'hyundai' in n_lower or 'aura' in n_lower:
        return 'Hyundai Motor India'
    elif 'honda' in n_lower or 'city' in n_lower or 'amaze' in n_lower:
        return 'Honda Cars India'
    elif 'kia' in n_lower or 'carens' in n_lower or 'carnival' in n_lower:
        return 'Kia Motors India'
    elif 'mahindra' in n_lower or 'marazzo' in n_lower or 'cruzio' in n_lower:
        return 'Mahindra & Mahindra'
    elif 'byd' in n_lower:
        return 'BYD Auto India'
    elif 'mg' in n_lower:
        return 'MG Motor India'
    return 'Commercial Vehicle'

def get_tank_and_def(vt):
    cat_code = vt.vehicle_category.code if vt.vehicle_category else 'sedan'
    fuel = vt.fuel_type
    
    if fuel == 'electric':
        return 0, 0
    elif cat_code == 'sedan':
        tank = random.choice([37, 40, 42, 45])
        def_cap = 0
    elif cat_code in ['suv_muv', 'luxury_vip']:
        tank = random.choice([55, 60, 65, 70])
        def_cap = random.choice([12, 14, 16]) if fuel == 'diesel' else 0
    elif cat_code == 'mini_coach':
        tank = random.choice([70, 75, 80, 90])
        def_cap = random.choice([18, 20, 24]) if fuel == 'diesel' else 0
    elif cat_code in ['luxury_coach', 'commute_staff', 'specialized_vanity']:
        if vt.seating_capacity >= 45:
            tank = random.choice([350, 400, 450, 500])
            def_cap = random.choice([40, 50, 60]) if fuel == 'diesel' else 0
        else:
            tank = random.choice([160, 190, 220, 250])
            def_cap = random.choice([25, 30, 35]) if fuel == 'diesel' else 0
    else:
        tank = 60
        def_cap = 15 if fuel == 'diesel' else 0
    return tank, def_cap

def generate_random_vin(brand):
    prefix = 'MB1' if 'Bharat' in brand else ('MAK' if 'Toyota' in brand else ('MC2' if 'Force' in brand else ('YV3' if 'Volvo' in brand else 'MAT')))
    chars = string.ascii_uppercase.replace('I', '').replace('O', '').replace('Q', '') + string.digits
    suffix = ''.join(random.choices(chars, k=14))
    return f"{prefix}{suffix}"[:17]

def generate_random_engine(brand, fuel):
    pfx = 'D4D' if 'Toyota' in brand else ('FM26' if 'Force' in brand else ('OM926' if 'Bharat' in brand else ('D11K' if 'Volvo' in brand else 'ENG')))
    return f"{pfx}-{random.randint(100000, 999999)}"

def populate_all_vehicles(target_per_type=15):
    print("=" * 80)
    print(f"POPULATING VEHICLES: EXACTLY {target_per_type} FULLY-POPULATED VEHICLES PER VEHICLE TYPE")
    print("=" * 80)

    # 1. Collect all currently used registrations to ensure 100% uniqueness
    used_regs = set(Vehicle.objects.values_list('registration_number', flat=True))
    print(f"Initial existing vehicles in database: {len(used_regs)}")

    # 2. Today's date for reference
    today = date(2026, 10, 15)

    all_vtypes = list(VehicleType.objects.all().order_by('id'))
    print(f"Total active VehicleTypes: {len(all_vtypes)}")
    print(f"Target total fleet size: {len(all_vtypes) * target_per_type} vehicles")

    vehicles_to_create = []
    reg_counter = 1001

    # Status distribution pool
    STATUS_POOL = ['available'] * 10 + ['on_trip'] * 3 + ['assigned'] * 1 + ['maintenance'] * 1

    depot_list = []
    for d_cfg in DEPOT_CONFIG:
        depot_list.extend([d_cfg] * d_cfg['weight'])

    created_per_cat = {c.code: 0 for c in VehicleCategory.objects.all()}

    for vt in all_vtypes:
        existing_for_type = Vehicle.objects.filter(vehicle_type=vt)
        curr_count = existing_for_type.count()
        needed = target_per_type - curr_count

        if needed <= 0:
            print(f"VehicleType '{vt.name}' already has {curr_count} vehicles (Target: {target_per_type}) - skipping.")
            continue

        brand = get_brand_from_name(vt.name)
        tank_cap, def_cap = get_tank_and_def(vt)

        # Features
        has_ac = True
        is_sleeper = ('sleeper' in vt.name.lower() or 'berth' in vt.name.lower() or 'maharaja' in vt.name.lower())
        has_air = (vt.seating_capacity >= 35 or 'volvo' in vt.name.lower() or 'scania' in vt.name.lower() or 'glider' in vt.name.lower() or 'zedastra' in vt.name.lower() or 'air' in vt.amenities.lower())
        has_video = (vt.is_luxury or vt.seating_capacity >= 20 or 'vanity' in vt.name.lower() or 'caravan' in vt.name.lower())

        for idx in range(needed):
            # Select depot based on weighted probability
            d_cfg = random.choice(depot_list)
            depot_name = d_cfg['depot']
            rto_pfx = random.choice(d_cfg['rto_prefixes'])
            loc_name = random.choice(d_cfg['loc_names'])

            # Generate unique registration
            while True:
                series = f"{random.choice(string.ascii_uppercase)}{random.choice(string.ascii_uppercase)}"
                num = random.randint(1000, 9999)
                reg_no = f"{rto_pfx} {series} {num}"
                if reg_no not in used_regs:
                    used_regs.add(reg_no)
                    break

            # Technical specs
            year = random.choice([2022, 2023, 2023, 2024, 2024, 2025, 2025, 2026])
            color = random.choice(COLORS_LUXURY if vt.is_luxury else COLORS_STANDARD)
            current_km = random.randint(8500, 142000)
            next_service = current_km + random.randint(2500, 5000)

            # Dates
            rc_exp = date(year + 15, random.randint(1, 12), random.randint(1, 28))
            ins_exp = today + timedelta(days=random.randint(45, 360))
            fc_exp = today + timedelta(days=random.randint(60, 365))
            permit_exp = today + timedelta(days=random.randint(180, 900))
            tax_exp = today + timedelta(days=random.randint(60, 240))
            poll_exp = today + timedelta(days=random.randint(45, 180))

            # Financing (40% financed)
            is_fin = random.random() < 0.40
            fin_name = random.choice(FINANCIERS) if is_fin else ""
            emi_amt = Decimal(random.randint(18000, 85000)) if is_fin else None
            loan_end = today + timedelta(days=random.randint(180, 1000)) if is_fin else None

            # GPS & FASTag
            gps_imei = f"8675400{random.randint(10000000, 99999999)}"
            fastag_id = f"FAST-3388-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"

            # Insurance
            ins_provider = random.choice(INSURERS)
            ins_policy = f"POL-TN-{year}-{random.randint(100000, 999999)}"

            v_status = random.choice(STATUS_POOL)

            v = Vehicle(
                registration_number=reg_no,
                vehicle_type=vt,
                vehicle_category=vt.vehicle_category,
                ownership_type='owned',
                status=v_status,
                base_depot=depot_name,
                brand=brand,
                model=vt.name,
                year=year,
                color=color,
                fuel_type=vt.fuel_type,
                fuel_tank_capacity=tank_cap,
                def_capacity=def_cap,
                seating_capacity=vt.seating_capacity,
                current_km=current_km,
                next_service_due_km=next_service,
                has_ac=has_ac,
                is_sleeper=is_sleeper,
                has_air_suspension=has_air,
                has_video_coach=has_video,
                rc_expiry=rc_exp,
                insurance_expiry=ins_exp,
                fc_expiry=fc_exp,
                permit_expiry=permit_exp,
                tax_expiry=tax_exp,
                pollution_expiry=poll_exp,
                insurance_provider=ins_provider,
                insurance_policy_number=ins_policy,
                is_financed=is_fin,
                financier_name=fin_name,
                emi_amount=emi_amt,
                loan_end_date=loan_end,
                gps_imei=gps_imei,
                fastag_id=fastag_id,
                engine_number=generate_random_engine(brand, vt.fuel_type),
                chassis_number=generate_random_vin(brand),
                expected_mileage=vt.expected_mileage_kmpl,
                current_location=loc_name,
            )
            vehicles_to_create.append(v)
            if vt.vehicle_category:
                created_per_cat[vt.vehicle_category.code] = created_per_cat.get(vt.vehicle_category.code, 0) + 1

    print(f"Prepared {len(vehicles_to_create)} new vehicle records to bulk insert...")

    # 3. Bulk Create in chunks of 500 for optimal memory and speed
    CHUNK_SIZE = 500
    for i in range(0, len(vehicles_to_create), CHUNK_SIZE):
        chunk = vehicles_to_create[i:i + CHUNK_SIZE]
        Vehicle.objects.bulk_create(chunk)
        print(f"  * Inserted batch {i + 1} to {i + len(chunk)} / {len(vehicles_to_create)}")

    print("=" * 80)
    print("POPULATION COMPLETE!")
    print("=" * 80)
    print(f"Total Vehicles in Database Now: {Vehicle.objects.count()}")
    print("\nVehicles Per Category:")
    for cat in VehicleCategory.objects.all().order_by('display_order'):
        v_count = Vehicle.objects.filter(vehicle_category=cat).count()
        t_count = cat.vehicle_types.count()
        print(f" - {cat.name:<45} ({cat.code}): {t_count:3d} Types, {v_count:4d} Vehicles ({v_count / t_count:.1f} per type avg)")

    print("\nVehicles Per Regional Hub Depot:")
    for d_cfg in DEPOT_CONFIG:
        d_name = d_cfg['depot']
        d_count = Vehicle.objects.filter(base_depot=d_name).count()
        print(f" - {d_name:<40}: {d_count:4d} Vehicles ({d_count * 100 / Vehicle.objects.count():.1f}%)")

    print("=" * 80)

if __name__ == '__main__':
    populate_all_vehicles(target_per_type=15)
