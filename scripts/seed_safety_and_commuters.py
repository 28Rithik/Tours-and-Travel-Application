import os
import sys
import random
import datetime
from decimal import Decimal
import django

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

from django.utils import timezone
from fleet_contracts.models import (
    TransportContract, Route, RouteStop, Shift, ContractTripLog,
    NightSafetyEscortLog, CommuterManifest, ContractSLAPenalty
)

def seed_safety_and_commuters():
    print("--- Seeding Route Stops, Commuters, and Night Safety Escorts ---")
    
    # 1. Create Route Stops for existing routes if none exist
    routes = Route.objects.all()
    stops_created = 0
    chennai_locations = [
        ("Tambaram Railway Station", 0, "Near West Booking Counter"),
        ("Chromepet MIT Bridge", 12, "Bus Bay below flyover"),
        ("Pallavaram Bus Stand", 20, "Opposite Metro Pillar 14"),
        ("Guindy Kathipara Junction", 35, "Under Cloverleaf Bridge"),
        ("Velachery MRTS Station", 45, "Main Gate 2"),
        ("Perungudi Toll Plaza", 55, "OMR Service Lane"),
        ("Sholinganallur Junction", 70, "Near Wipro / Elcot SEZ Gate"),
        ("Siruseri SIPCOT Gate 1", 85, "TCS / Cognizant IT Park Hub"),
    ]

    for r in routes:
        if r.stops.count() == 0:
            for idx, (loc_name, offset, landmark) in enumerate(chennai_locations[:5], 1):
                RouteStop.objects.create(
                    route=r,
                    stop_order=idx,
                    name=loc_name,
                    scheduled_offset_minutes=offset,
                    pickup_landmark=landmark,
                    expected_passenger_count=random.randint(4, 12),
                    is_active=True
                )
                stops_created += 1
    print(f"Created {stops_created} RouteStops.")

    # 2. Seed CommuterManifest (40-50 records)
    first_names_f = ["Priya", "Ananya", "Deepa", "Kavitha", "Swathi", "Divya", "Meenakshi", "Sneha", "Nithya", "Aishwarya"]
    first_names_m = ["Karthik", "Arun", "Vignesh", "Suresh", "Ramesh", "Vijay", "Balaji", "Praveen", "Saravanan", "Ganesh"]
    last_names = ["Raman", "Natarajan", "Sundaram", "Krishnan", "Venkatesh", "Balasubramanian", "Murugan", "Chandran", "Iyer", "Reddy"]
    
    contracts = TransportContract.objects.all()
    all_stops = list(RouteStop.objects.all())

    commuters_created = 0
    if CommuterManifest.objects.count() < 40:
        for i in range(45):
            contract = random.choice(contracts)
            is_female = (random.random() < 0.6)
            fn = random.choice(first_names_f) if is_female else random.choice(first_names_m)
            ln = random.choice(last_names)
            full_name = f"{fn} {ln}"
            
            if contract.contract_category == 'corporate':
                c_type = 'employee'
                dept = random.choice(["Cloud Engineering", "Data Analytics", "HR Shared Services", "Digital Banking", "QA Automation"])
                c_id = f"EMP-{random.randint(10000, 99999)}"
                req_escort = is_female
            elif contract.contract_category == 'school':
                c_type = 'student'
                dept = f"Grade {random.randint(6, 12)}-{random.choice(['A', 'B', 'C'])}"
                c_id = f"STU-{random.randint(1000, 9999)}"
                req_escort = False
            elif contract.contract_category == 'factory':
                c_type = 'worker'
                dept = random.choice(["Shopfloor Assembly 1", "Paint Shop Division", "Quality Inspection", "Press Shop 3"])
                c_id = f"WRK-{random.randint(2000, 8000)}"
                req_escort = False
            else:
                c_type = 'staff'
                dept = random.choice(["Casualty Ward", "Administration", "Clinical Support", "Radiology Lab"])
                c_id = f"MED-{random.randint(3000, 7000)}"
                req_escort = is_female

            b_stop = random.choice(all_stops) if all_stops else None

            CommuterManifest.objects.create(
                contract=contract,
                commuter_type=c_type,
                commuter_id=c_id,
                name=full_name,
                gender='female' if is_female else 'male',
                phone=f"+91 9{random.randint(100000000, 999999999)}",
                emergency_contact_name=f"{random.choice(first_names_m)} {ln}",
                emergency_contact_phone=f"+91 9{random.randint(100000000, 999999999)}",
                department_or_grade=dept,
                boarding_stop=b_stop,
                requires_night_escort=req_escort,
                is_active=True
            )
            commuters_created += 1
    print(f"Created {commuters_created} CommuterManifest records. Total: {CommuterManifest.objects.count()}")

    # 3. Seed NightSafetyEscortLog records
    escort_names = ["R. Munuswamy", "K. Arumugam", "M. Selvaraj", "P. Shanmugam", "S. Govindaraj", "D. Manikandan"]
    agencies = ["SIS Security Services Ltd", "G4S Secure Solutions", "Tops Security India", "Securitas India Ltd"]
    statuses = ['verified_sms', 'verified_call', 'supervisor_signoff', 'pending']

    corp_trips = ContractTripLog.objects.filter(shift__route__contract__contract_category='corporate')
    escort_created = 0
    for trip in corp_trips:
        if trip.escort_logs.count() == 0:
            guard = random.choice(escort_names)
            agency = random.choice(agencies)
            status = random.choice(statuses)
            conf_by = "Transport Desk Supervisor" if status != 'pending' else ""
            
            NightSafetyEscortLog.objects.create(
                trip_log=trip,
                escort_guard_name=guard,
                security_agency=agency,
                guard_badge_number=f"SEC-TN-{random.randint(1000, 9999)}",
                guard_contact_phone=f"+91 9{random.randint(100000000, 999999999)}",
                female_passengers_count=random.randint(2, 6),
                first_pickup_time=datetime.time(20, random.choice([0, 15, 30])),
                last_female_drop_time=datetime.time(23, random.choice([15, 45])),
                last_drop_verification_status=status,
                safe_drop_confirmed_by=conf_by,
                remarks="Night employee drop with GPS geofence tracking and safe drop OTP confirmation."
            )
            escort_created += 1
    print(f"Created {escort_created} NightSafetyEscortLog records. Total: {NightSafetyEscortLog.objects.count()}")

    # 4. Create 5 fresh delayed trips without SLA penalties (to test auto-ingestion)
    shifts = Shift.objects.all()
    fresh_delayed = 0
    today = timezone.now().date()
    for i in range(5):
        sh = random.choice(shifts)
        dt = today - datetime.timedelta(days=random.randint(1, 10))
        tl = ContractTripLog.objects.create(
            shift=sh,
            date=dt,
            vehicle=sh.route.contract.roster_allocations.first().primary_vehicle if sh.route.contract.roster_allocations.exists() else None,
            driver=sh.route.contract.roster_allocations.first().primary_driver if sh.route.contract.roster_allocations.exists() else None,
            status='delayed',
            passenger_count=random.randint(15, 35),
            opening_km=14200 + i * 50,
            closing_km=14245 + i * 50,
            delay_minutes=random.choice([20, 25, 35, 40, 50]),
            delay_reason=random.choice([
                "Heavy Chennai bypass highway congestion at Porur toll",
                "Tyre puncture on service road, required 20 min roadside assistance",
                "Late release of evening shift team from IT park building 4"
            ])
        )
        fresh_delayed += 1
    print(f"Created {fresh_delayed} new unpenalized delayed trips to test auto-ingestion.")

if __name__ == '__main__':
    seed_safety_and_commuters()
