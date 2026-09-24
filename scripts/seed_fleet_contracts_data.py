import os
import sys
import random
import datetime
from decimal import Decimal

# Configure UTF-8 for console output on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.utils import timezone
from core.models import Client, Vehicle, Driver
from fleet_contracts.models import (
    TransportContract, Route, RouteStop, Shift,
    ContractFleetRoster, ContractTripLog, ContractSLAPenalty,
    ContractMonthlyInvoice
)

def seed_fleet_contracts():
    print("==================================================================")
    print("  SEEDING 40 CORRELATED RECORDS FOR INSTITUTIONAL CONTRACTS & SLA")
    print("==================================================================")

    # Clean existing test data cleanly
    print("Clearing previous contract data...")
    from finance.models import DriverSettlement
    DriverSettlement.objects.filter(contract_trip__isnull=False).delete()
    ContractSLAPenalty.objects.all().delete()
    ContractMonthlyInvoice.objects.all().delete()
    ContractTripLog.objects.all().delete()
    ContractFleetRoster.objects.all().delete()
    Shift.objects.all().delete()
    RouteStop.objects.all().delete()
    Route.objects.all().delete()
    TransportContract.objects.all().delete()

    vehicles = list(Vehicle.objects.all())
    drivers = list(Driver.objects.all())
    print(f"Pool: {len(vehicles)} vehicles, {len(drivers)} drivers.")

    # 40 Institutional Clients definition
    client_definitions = [
        # 12 Corporate / IT / BPO
        ("Tata Consultancy Services (TCS OMR Campus)", "corporate", "Mr. Balaji Ramanathan", "+91 98401 22331", "balaji.r@tcs.example", "Siruseri IT Park, Chennai"),
        ("Infosys Limited (Mahindra World City)", "corporate", "Mrs. Gayathri Mohan", "+91 98402 33442", "gayathri.m@infosys.example", "Chengalpattu, Tamil Nadu"),
        ("Cognizant Technology Solutions (MEPZ Campus)", "corporate", "Mr. S. Karthikeyan", "+91 98403 44553", "karthik.s@cognizant.example", "Tambaram Sanatorium, Chennai"),
        ("Wipro Technologies (Sholinganallur Center)", "corporate", "Mr. Arunkumar G.", "+91 98404 55664", "arun.g@wipro.example", "OMR, Sholinganallur, Chennai"),
        ("Amazon Development Centre India (One IndiaBulls)", "corporate", "Ms. Deepa Narayanan", "+91 98405 66775", "deepa.n@amazon.example", "Ambattur Industrial Estate, Chennai"),
        ("HCL Technologies (Elcot SEZ)", "corporate", "Mr. Praveen Chandran", "+91 98406 77886", "praveen.c@hcl.example", "Sholinganallur, Chennai"),
        ("Zoho Corporation (Estancia IT Park)", "corporate", "Mr. Vigneshwaran R.", "+91 98407 88997", "vignesh.r@zohocorp.example", "Guduvanchery, Chennai"),
        ("PayPal India (Olympia Tech Park)", "corporate", "Mrs. Revathi Sundar", "+91 98408 99008", "revathi.s@paypal.example", "Guindy, Chennai"),
        ("Renault Nissan Technology & Business Centre", "corporate", "Mr. Michael D'Souza", "+91 98409 11229", "michael.d@rntbci.example", "Ascendas Tech Park, Mahindra City"),
        ("Standard Chartered Global Business Services", "corporate", "Mr. K. Sridharan", "+91 98410 22330", "sridhar.k@sc.example", "DLF Cyber City, Porur, Chennai"),
        ("L&T Technology Services (L&T Campus)", "corporate", "Mr. T. Murugesan", "+91 98411 33441", "murugesan.t@ltts.example", "Manapakkam, Mount Poonamallee Road"),
        ("Ford Global Technology & Business Center", "corporate", "Mrs. Malini Jayaraman", "+91 98412 44552", "malini.j@ford.example", "Ramanujan IT City, Taramani"),

        # 10 School & University Student Transport
        ("SSN College of Engineering (Autonomous)", "corporate", "Prof. R. Soundararajan", "+91 98413 55663", "transport@ssn.example", "Kalavakkam, OMR, Chennai"),
        ("Chettinad Vidyashram Senior Secondary School", "corporate", "Mr. V. Gurumoorthy", "+91 98414 66774", "admin@cv.example", "R.A. Puram, Chennai"),
        ("SBOA School and Junior College", "corporate", "Mr. P. Natarajan", "+91 98415 77885", "transport@sboajc.example", "Anna Nagar West Extension, Chennai"),
        ("Loyola College (Autonomous)", "corporate", "Rev. Fr. Joseph Antony", "+91 98416 88996", "bursar@loyola.example", "Sterling Road, Nungambakkam"),
        ("PSG College of Technology", "corporate", "Dr. K. Prakasan", "+91 98417 99007", "principal@psgtech.example", "Peelamedu, Coimbatore"),
        ("Vellore Institute of Technology (VIT Chennai)", "corporate", "Mr. Sekar Viswanathan", "+91 98418 11228", "transport@vit.example", "Vandalur-Kelambakkam Road"),
        ("SRM Institute of Science & Technology", "corporate", "Mr. B. Ravikumar", "+91 98419 22339", "director.transport@srm.example", "Kattankulathur, Chengalpattu"),
        ("Hindustan Institute of Technology and Science", "corporate", "Dr. Anand Jacob", "+91 98420 33440", "transport@hindustanuniv.example", "Padur, OMR, Chennai"),
        ("Amrita Vishwa Vidyapeetham (Ettimadai)", "corporate", "Dr. S. Mahadevan", "+91 98421 44551", "transport@amrita.example", "Ettimadai, Coimbatore"),
        ("DAV Boys Senior Secondary School", "corporate", "Mr. Ramesh Swaminathan", "+91 98422 55662", "davtransport@davchennai.example", "Gopalapuram, Chennai"),

        # 8 Manufacturing & Factory Shift Shuttle
        ("Hyundai Motor India Limited", "corporate", "Mr. C. Venkatakrishnan", "+91 98423 66773", "venkat.c@hyundai.example", "Irungattukottai, Sriperumbudur"),
        ("Saint-Gobain Glass India Ltd", "corporate", "Mr. P. Ananthakrishnan", "+91 98424 77884", "ananth.p@saint-gobain.example", "World Glass Complex, Sriperumbudur"),
        ("Renault Nissan Automotive India Pvt Ltd", "corporate", "Mr. S. Elango", "+91 98425 88995", "elango.s@renault.example", "SIPCOT Industrial Park, Oragadam"),
        ("Foxconn Hon Hai Technology India", "corporate", "Mr. David Chang", "+91 98426 99006", "david.c@foxconn.example", "Sunguvarchatram, Sriperumbudur"),
        ("TVS Motor Company Limited", "corporate", "Mr. N. Sundararajan", "+91 98427 11227", "sundar.n@tvsmotor.example", "Harita, Hosur, Tamil Nadu"),
        ("Apollo Tyres Limited", "corporate", "Mr. B. Sivakumar", "+91 98428 22338", "siva.b@apollotyres.example", "SIPCOT Industrial Growth Centre, Oragadam"),
        ("Ashok Leyland Limited (Ennore Unit)", "corporate", "Mr. M. Rajagopal", "+91 98429 33449", "rajagopal.m@ashokleyland.example", "Kathivakkam High Road, Ennore"),
        ("Royal Enfield (Unit of Eicher Motors)", "corporate", "Mr. K. Chandrasekar", "+91 98430 44550", "chandra.k@royalenfield.example", "Vallam Vadagal, Sriperumbudur"),

        # 6 Healthcare & Hospital Staff Shuttle
        ("Apollo Hospitals Enterprise Ltd (Greams Road)", "corporate", "Dr. Subbiah Shanmugam", "+91 98431 55661", "transport@apollohospitals.example", "Greams Lane, Thousand Lights, Chennai"),
        ("MIOT International Super Speciality Hospital", "corporate", "Mr. Senthilvelan P.", "+91 98432 66772", "admin@miotinternational.example", "Manapakkam, Chennai"),
        ("Fortis Malar Hospital", "corporate", "Mrs. Shanthi Ramamurthy", "+91 98433 77883", "contact@fortismalar.example", "Gandhi Nagar, Adyar, Chennai"),
        ("Sri Ramachandra Institute of Higher Education", "corporate", "Mr. N. Palaniswamy", "+91 98434 88994", "transport@sriramachandra.example", "Porur, Chennai"),
        ("Ganga Hospital & Orthopaedic Center", "corporate", "Dr. S. Rajasekaran", "+91 98435 99005", "admin@gangahospital.example", "Mettupalayam Road, Coimbatore"),
        ("Gleneagles Global Health City", "corporate", "Mr. Johnson George", "+91 98436 11226", "transport@globalhospitals.example", "Cheran Nagar, Perumbakkam, Chennai"),

        # 4 Government & PSU Official Transport
        ("TIDEL Park Limited", "corporate", "Mr. R. Thangaraj", "+91 98437 22337", "mddesk@tidelpark.example", "Tharamani, OMR, Chennai"),
        ("Bharat Heavy Electricals Limited (BHEL)", "corporate", "Mr. V. Krishnamurthy", "+91 98438 33448", "transport@bheltry.example", "TIRUCHIRAPPALLI Complex"),
        ("Chennai Port Authority", "corporate", "Capt. K. Harikrishnan", "+91 98439 44559", "harikrishnan.k@chennaiport.example", "Rajaji Salai, Chennai"),
        ("ISRO Propulsion Complex (IPRC)", "corporate", "Dr. P. Radhakrishnan", "+91 98440 55660", "transport@iprc.example", "Mahendragiri, Tirunelveli Dist"),
    ]

    # Category matching
    cat_map = {
        0: 'corporate', 1: 'corporate', 2: 'corporate', 3: 'corporate',
        4: 'corporate', 5: 'corporate', 6: 'corporate', 7: 'corporate',
        8: 'corporate', 9: 'corporate', 10: 'corporate', 11: 'corporate',
        12: 'school', 13: 'school', 14: 'school', 15: 'school',
        16: 'school', 17: 'school', 18: 'school', 19: 'school',
        20: 'school', 21: 'school',
        22: 'factory', 23: 'factory', 24: 'factory', 25: 'factory',
        26: 'factory', 27: 'factory', 28: 'factory', 29: 'factory',
        30: 'hospital', 31: 'hospital', 32: 'hospital', 33: 'hospital',
        34: 'hospital', 35: 'hospital',
        36: 'government', 37: 'government', 38: 'government', 39: 'government'
    }

    # Billing model distribution
    billing_models = ['per_trip', 'fixed_monthly', 'per_km', 'per_trip', 'fixed_monthly']
    statuses = ['active'] * 32 + ['completed'] * 5 + ['draft'] * 3
    random.shuffle(statuses)

    created_contracts = []
    created_routes = []
    created_shifts = []

    print("\n--- 1. Creating 40 Transport Contracts ---")
    for i, (org_name, party_type, contact_p, phone, email, address) in enumerate(client_definitions):
        client, _ = Client.objects.get_or_create(
            name=org_name,
            defaults={
                'party_type': party_type,
                'phone': phone,
                'email': email,
                'address': address,
                'is_active': True
            }
        )

        cat = cat_map[i]
        b_model = billing_models[i % len(billing_models)]
        status = statuses[i]

        if b_model == 'fixed_monthly':
            default_rate = Decimal(random.choice([180000, 240000, 320000, 450000]))
        elif b_model == 'per_trip':
            default_rate = Decimal(random.choice([1650, 1950, 2400, 2800, 3400]))
        else: # per_km
            default_rate = Decimal(random.choice([26.50, 28.00, 32.50, 35.00]))

        committed_buses = random.choice([2, 3, 4, 6, 8, 12])
        standby_spares = 1 if committed_buses <= 5 else 2

        if status == 'completed':
            start_d = datetime.date(2025, 4, 1)
            end_d = datetime.date(2026, 3, 31)
        elif status == 'draft':
            start_d = datetime.date(2026, 10, 1)
            end_d = datetime.date(2027, 9, 30)
        else: # active
            start_d = datetime.date(2026, 4, 1)
            end_d = datetime.date(2027, 3, 31)

        contract_name = f"{org_name.split('(')[0].strip()} Commute Contract 2026-27"
        if cat == 'school':
            contract_name = f"{org_name.split('(')[0].strip()} Student Bus Service 2026-27"
        elif cat == 'factory':
            contract_name = f"{org_name.split('(')[0].strip()} Shift Operations Transport"
        elif cat == 'hospital':
            contract_name = f"{org_name.split('(')[0].strip()} Healthcare Staff Shuttle"
        elif cat == 'government':
            contract_name = f"{org_name.split('(')[0].strip()} Official Duty Fleet Agreement"

        contract = TransportContract.objects.create(
            contract_category=cat,
            name=contract_name[:255],
            customer=client,
            start_date=start_d,
            end_date=end_d,
            billing_model=b_model,
            billing_cycle='calendar_month',
            default_rate=default_rate,
            gst_rate=Decimal('5.00'),
            payment_credit_days=random.choice([30, 45, 60]),
            committed_vehicle_count=committed_buses,
            standby_vehicle_count=standby_spares,
            fuel_escalation_enabled=(cat in ['factory', 'corporate', 'school']),
            base_diesel_price=Decimal('92.80'),
            fuel_revision_factor=Decimal('0.2500'),
            sla_penalty_cap_pct=Decimal('10.00'),
            contact_person=contact_p,
            contact_phone=phone,
            status=status,
            notes=f"SLA strictly enforced: >15 mins delay incurs ₹1,000 deduction per trip. AC mandatory on all primary fleet."
        )
        created_contracts.append(contract)

        # Create 1 main Route & Shift for each contract
        r_name = f"Route 1: Chennai Hub to {client.name.split()[0]}"
        route = Route.objects.create(
            contract=contract,
            name=r_name[:255],
            origin="Tambaram West Bus Stand" if i % 2 == 0 else "Koyambedu CMBT Terminal",
            destination=address,
            distance_km=random.randint(28, 55),
            estimated_travel_minutes=random.randint(45, 80),
            is_active=True
        )
        created_routes.append(route)

        shift = Shift.objects.create(
            route=route,
            shift_name="Shift 1: Morning Inbound Pickup" if i % 2 == 0 else "General Shift Arrival",
            direction='pickup',
            timing=datetime.time(random.choice([6, 7, 8]), random.choice([0, 30, 45])),
            days_of_week='Mon-Fri' if cat != 'hospital' else 'All 7 Days',
            grace_period_minutes=10,
            escort_guard_required=(cat == 'corporate')
        )
        created_shifts.append(shift)

    print(f"✅ Created {len(created_contracts)} Transport Contracts with Routes and Shifts.")

    # ------------------------------------------------------------------
    # 2. DEDICATED FLEET & CREW ROSTER (40 Allocations)
    # ------------------------------------------------------------------
    print("\n--- 2. Seeding 40 Dedicated Fleet & Crew Rosters ---")
    rosters_created = []
    today = timezone.now().date()

    for i in range(40):
        contract = created_contracts[i]
        route = created_routes[i]
        shift = created_shifts[i]

        primary_v = vehicles[i % len(vehicles)]
        primary_d = drivers[i % len(drivers)]
        standby_v = vehicles[(i + 40) % len(vehicles)]

        roster = ContractFleetRoster.objects.create(
            contract=contract,
            route=route,
            shift=shift,
            primary_vehicle=primary_v,
            primary_driver=primary_d,
            standby_vehicle=standby_v,
            start_date=contract.start_date,
            end_date=contract.end_date,
            is_active=(contract.status == 'active'),
            notes=f"Dedicated assignment for {contract.customer.name[:35]}"
        )
        rosters_created.append(roster)
    print(f"✅ Created {len(rosters_created)} Dedicated Fleet Roster allocations.")

    # ------------------------------------------------------------------
    # 3. DAILY TRIP LOGS (40 Logs to back SLA Penalties)
    # ------------------------------------------------------------------
    print("\n--- 3. Seeding 40 Trip Logs ---")
    trip_logs = []
    trip_statuses = ['delayed', 'breakdown', 'completed', 'delayed', 'completed']

    for i in range(40):
        shift = created_shifts[i]
        v = vehicles[i % len(vehicles)]
        d = drivers[i % len(drivers)]
        st = trip_statuses[i % len(trip_statuses)]
        trip_date = today - datetime.timedelta(days=random.randint(2, 45))

        delay_m = random.choice([18, 25, 34, 45]) if st in ['delayed', 'breakdown'] else 0
        delay_r = random.choice([
            "Heavy highway congestion near toll plaza",
            "Front tyre puncture near Porur flyover; replaced with spare",
            "Engine coolant temperature warning light illuminated",
            "Road waterlogging and route diversion due to rainfall",
            "Driver reported late at starting terminal"
        ]) if delay_m > 0 else ""

        tlog = ContractTripLog.objects.create(
            shift=shift,
            date=trip_date,
            vehicle=v,
            driver=d,
            status=st,
            passenger_count=random.randint(18, 48),
            opening_km=10000 + (i * 250),
            closing_km=10000 + (i * 250) + random.randint(35, 60),
            driver_bata=Decimal('0'), # zero to avoid side-effects
            toll_parking_charges=Decimal(random.choice([0, 110, 160, 220])),
            delay_minutes=delay_m,
            delay_reason=delay_r,
            is_replacement_vehicle=(st == 'breakdown')
        )
        trip_logs.append(tlog)
    print(f"✅ Created {len(trip_logs)} Contract Trip Logs.")

    # ------------------------------------------------------------------
    # 4. SLA PENALTIES & DEDUCTIONS (40 Records)
    # ------------------------------------------------------------------
    print("\n--- 4. Seeding 40 SLA Penalties & Deductions ---")
    penalties_created = []

    penalty_catalog = [
        ('late_arrival', 1000, "Bus reported 28 mins late at Velachery stop due to highway gridlock; breached 10-min grace period."),
        ('breakdown_delay', 3500, "Radiator hose leak on GST Road; standby bus deployed after 45 mins resulting in late campus delivery."),
        ('ac_failure', 1500, "AC compressor tripped during morning commute; ambient cabin temperature reached 34°C."),
        ('unauthorized_driver', 2000, "Unverified replacement driver without official uniform and ID badge operated morning shift."),
        ('escort_missing', 5000, "Mandatory security escort guard absent during 11:30 PM female employee night drop."),
        ('speed_violation', 1000, "GPS speed limiter breach recorded: 68 km/h on Chennai Bypass (Contractual cap 50 km/h)."),
        ('missed_trip', 7500, "Shift 2 morning inbound trip missed completely due to driver unexcused absence; client hired external cabs."),
        ('late_arrival', 1500, "Shift arrival delayed by 22 minutes at factory gate, delaying shift assembly startup."),
        ('ac_failure', 1500, "Air conditioning cooling deficient in rear section of 40-seater coach during afternoon trip."),
        ('breakdown_delay', 4000, "Battery discharge failure at depot; departure delayed by 40 mins before backup reached.")
    ]

    for i in range(40):
        contract = created_contracts[i]
        tlog = trip_logs[i]
        tmpl = penalty_catalog[i % len(penalty_catalog)]
        
        # 28 deductible, 12 waived
        is_waived = (i % 3 == 0)
        w_reason = "Waived as delay was caused by police diversion due to VIP convoy movement." if is_waived else ""
        amount = Decimal(tmpl[1]) + Decimal(random.choice([0, 250, 500, -200]))

        penalty = ContractSLAPenalty.objects.create(
            contract=contract,
            trip_log=tlog,
            date=tlog.date,
            penalty_type=tmpl[0],
            penalty_amount=amount,
            description=f"{tmpl[2]} [Recorded on {tlog.date.strftime('%d/%m/%Y')}]",
            waived=is_waived,
            waiver_reason=w_reason
        )
        penalties_created.append(penalty)
    print(f"✅ Created {len(penalties_created)} SLA Penalties & Performance Deductions.")

    # ------------------------------------------------------------------
    # 5. CONTRACT MONTHLY INVOICES (40 Invoices)
    # ------------------------------------------------------------------
    print("\n--- 5. Seeding 40 Contract Monthly Invoices ---")
    invoices_created = []

    invoice_months = [
        (datetime.date(2026, 6, 1), datetime.date(2026, 6, 1), datetime.date(2026, 6, 30), 'paid', '2026-06'),
        (datetime.date(2026, 7, 1), datetime.date(2026, 7, 1), datetime.date(2026, 7, 31), 'paid', '2026-07'),
        (datetime.date(2026, 8, 1), datetime.date(2026, 8, 1), datetime.date(2026, 8, 31), 'generated', '2026-08'),
        (datetime.date(2026, 9, 1), datetime.date(2026, 9, 1), datetime.date(2026, 9, 30), 'generated', '2026-09'),
    ]

    for i in range(40):
        contract = created_contracts[i]
        m_info = invoice_months[i % len(invoice_months)]
        billing_m = m_info[0]
        from_d = m_info[1]
        to_d = m_info[2]
        inv_status = m_info[3] if contract.status == 'active' else 'draft'

        inv_num = f"INV-ETS-{m_info[4]}-{i+1:03d}"
        trips = random.randint(44, 96)
        kms = Decimal(trips * random.randint(35, 55))

        base_amt = Decimal(random.choice([120000, 180000, 240000, 310000, 420000]))
        extra_km = Decimal(random.choice([0, 4500, 8200, 12500]))
        fuel_esc = Decimal(random.choice([0, 3200, 5800, 7400])) if contract.fuel_escalation_enabled else Decimal('0')
        toll_amt = Decimal(random.choice([2400, 4800, 7200, 9600]))
        
        # Link corresponding SLA penalty deduction if active
        matching_penalties = ContractSLAPenalty.objects.filter(contract=contract, waived=False)
        sla_ded = sum(p.penalty_amount for p in matching_penalties)

        inv = ContractMonthlyInvoice(
            contract=contract,
            invoice_number=inv_num,
            billing_month=billing_m,
            from_date=from_d,
            to_date=to_d,
            total_trips_completed=trips,
            total_kms_run=kms,
            base_contract_amount=base_amt,
            extra_km_amount=extra_km,
            fuel_escalation_amount=fuel_esc,
            toll_parking_amount=toll_amt,
            sla_penalty_deduction=sla_ded,
            gst_rate=Decimal('5.00'),
            status=inv_status,
            due_date=to_d + datetime.timedelta(days=contract.payment_credit_days),
            payment_reference=f"NEFT/CMS/2026/{random.randint(100000, 999999)}" if inv_status == 'paid' else "",
            notes=f"Monthly billing for {contract.name}. Generated automatically per agreed terms."
        )
        inv.save() # calculates totals via calculate_totals()
        invoices_created.append(inv)

    print(f"✅ Created {len(invoices_created)} Contract Monthly Invoices with calculated net taxable & GST.")

    print("\n==================================================================")
    print("  SEEDING COMPLETE: 40 REALISTIC RECORDS IN EACH OF THE 4 MODELS")
    print("==================================================================")

if __name__ == '__main__':
    seed_fleet_contracts()
