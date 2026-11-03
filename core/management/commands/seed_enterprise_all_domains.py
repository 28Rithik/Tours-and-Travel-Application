"""
Master Enterprise Domain Seeder for Sivagayathiri Tours & Travels ERP.
Populates 15,000+ realistic, production-grade records across all business domains:
1. CRM: Hotels, Monuments, Activities, Guides, B2C Customers, Inquiries, Follow-ups, Quotations, Itineraries, Feedbacks, Complaints.
2. Operations: Bookings, Trips, Cash Envelopes, Border Permits, Hill e-Passes, PNR Arrivals, Breakdown SOS, Fatigue Logs, Empty Legs, Traffic Fines, GPS Telematics, Driver Behavior.
3. Fleet Commute & Contracts: Corporate Transport Contracts, Routes, Waypoints/Stops, Shifts, Commuter Manifests, Fleet Rosters, Daily Commute Logs, Night Escorts, Boarding Passes, Incidents, ESG Carbon Metrics.
4. Maintenance: 7-Point Parivahan Compliance Documents (FC, Speed Gov, AIS-140, Insurance, AITP, Tax, PUC), Spare Parts, Stock Movements, Job Cards/Service Records, Snags/Defects.
5. Finance: Petro Accounts, FASTag Corporate Accounts, Toll Deductions, Fuel Records, Petty Cash Transactions, B2B GST Invoices, Line Items, Payments.
"""

import datetime
import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.db import connection, transaction
from django.utils import timezone
from django.contrib.auth.models import User

from core.models import Party, Client, Supplier, VehicleCategory, VehicleType, Vehicle, Driver
from crm.models import (
    HotelMaster, MonumentEntranceMaster, ActivityMaster, GuideChargeMaster,
    B2CCustomerProfile, Inquiry, InquiryFollowUp, Quotation, QuotationDay,
    QuotationItem, TravelComplaint, TripCustomerFeedback
)
from fleet_contracts.models import (
    TransportContract, Route as BaseRoute, RouteStop as BaseRouteStop,
    Shift as BaseShift, CommuterManifest, ContractFleetRoster,
    ContractTripLog, NightSafetyEscortLog, ContractMonthlyInvoice
)
from fleet_commute.models import CommuterBoardingPass, CommuteIncident, ESGCarbonMetric
from maintenance.models import (
    ComplianceDocument, SparePartItem, PartStockMovement, ServiceRecord, DefectTicket
)
from finance.models import (
    CorporatePetroAccount, CorporateFastagAccount, FastagTollDeduction,
    FuelRecord, PettyCashAccount, PettyCashTransaction,
    CorporateGSTInvoice, InvoiceLineItem, Payment
)
from operations.models import (
    Booking, Trip, TripCashAdvanceEnvelope, InterstateBorderPermit,
    EcoSensitiveZoneEPass, GroupArrivalManifest, HighwayBreakdownSOS,
    DriverFatigueAuditLog, EmptyLegTripOffer, TrafficFine,
    VehicleTelematicsPing, DriverBehaviorLog
)


class Command(BaseCommand):
    help = "Populate 15,000+ comprehensive enterprise records across all ERP domains"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("[*] Starting Sivagayathiri ERP Enterprise Domain Seeding..."))

        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.first()

        vehicles = list(Vehicle.objects.all())
        drivers = list(Driver.objects.all())
        parties = list(Party.objects.all())

        if not vehicles or not drivers:
            self.stdout.write(self.style.ERROR("[!] Vehicles or drivers missing. Please run seed_enterprise_fleet_and_crew first."))
            return

        self.stdout.write(f"[*] Found {len(vehicles)} vehicles, {len(drivers)} drivers, {len(parties)} active parties.")

        with transaction.atomic():
            # ==========================================================
            # 1. CRM DOMAIN: MASTER CATALOGS & PROFILES
            # ==========================================================
            self.stdout.write("[*] Seeding CRM Master Catalogs (Hotels, Monuments, Activities, Guides)...")
            hotels_data = [
                # Ooty
                ("Savoy - IHCL SeleQtions", "Ooty", "5_star", "Heritage Suite", 14500, 16500, 19500, 22000, 3500, 25, "0423-2225500", "savoy.ooty@ihcltata.com", "77 Sylks Road, Ooty, Nilgiris - 643001"),
                ("Fortune Resort Sullivan Court", "Ooty", "4_star", "Club Valley View", 7500, 8800, 10500, 12500, 2200, 20, "0423-2441415", "reservations@sullivancourt.com", "1 Selbourne Road, Rose Garden Area, Ooty - 643001"),
                ("Sterling Ooty Elk Hill", "Ooty", "4_star", "Classic Room", 6200, 7200, 8900, 10500, 1800, 15, "0423-2444031", "elkhill@sterlingholidays.com", "Ramakrishna Math Road, Elk Hill, Ooty - 643001"),
                ("Sinclairs Retreat Ooty", "Ooty", "3_star", "Deluxe Room", 5100, 6000, 7200, 8500, 1500, 15, "0423-2441376", "ooty@sinclairshotels.com", "Gorishola Road, Ooty - 643001"),
                ("Gem Park Ooty", "Ooty", "4_star", "Luxury Valley View", 6800, 7900, 9400, 11000, 2000, 20, "0423-2441761", "info@gemparkooty.com", "Sheddon Road, Ooty - 643001"),
                # Kodaikanal
                ("The Tamara Kodai", "Kodaikanal", "5_star", "Luxury Suite", 16000, 18500, 21500, 24500, 4000, 30, "04542-248800", "reservations@thetamara.com", "La Providence, St. Mary's Road, Kodaikanal - 624101"),
                ("The Carlton Hotel", "Kodaikanal", "5_star", "Lake View Deluxe", 12500, 14500, 17500, 20000, 3200, 25, "04542-240056", "carlton@rahejaresorts.com", "Lake Road, Kodaikanal - 624101"),
                ("Sterling Kodai Lake", "Kodaikanal", "4_star", "Premier Suite", 7500, 8900, 10800, 12800, 2200, 20, "04542-246000", "kodailake@sterlingholidays.com", "44 Gymkhana Road, Lake View, Kodaikanal - 624101"),
                ("Villa Retreat Heritage Hotel", "Kodaikanal", "3_star", "Boutique Heritage Room", 5800, 6800, 8200, 9800, 1800, 15, "04542-240940", "stay@villaretreat.com", "Coaker's Walk, Kodaikanal - 624101"),
                ("Great Trails Kodaikanal by GRT", "Kodaikanal", "4_star", "Rock Cabin", 8200, 9500, 11500, 13500, 2500, 20, "04542-243500", "reservations@grtnaturetrails.com", "Bharathi Nagar, Vilpatti Road, Kodaikanal - 624101"),
                # Valparai
                ("Briar Tea Bungalows", "Valparai", "4_star", "Planters Suite", 9500, 11000, 13000, 15000, 2800, 20, "04253-222340", "valparai@briartea.com", "Stanmore Estate, Valparai, Coimbatore - 642127"),
                ("Sinna Dorai's Bungalow", "Valparai", "5_star", "Colonial Heritage Room", 13000, 15000, 17500, 20000, 3500, 25, "04253-294001", "info@sinnadorai.com", "Iyerpadi Tea Estate, Valparai - 642108"),
                ("Waterfall Estate Heritage", "Valparai", "3_star", "Tea Garden View", 5500, 6500, 7800, 9200, 1600, 15, "04253-235222", "stay@waterfalltea.com", "Waterfall Estate Post, Valparai - 642105"),
                # Coonoor
                ("Gateway Coonoor - IHCL", "Coonoor", "4_star", "Executive Valley", 9800, 11500, 13800, 16000, 2800, 20, "0423-2223800", "gateway.coonoor@ihcltata.com", "Upper Coonoor, Church Road, Nilgiris - 643101"),
                ("Kurumba Village Resort", "Coonoor", "5_star", "Spice Garden Cottage", 14000, 16000, 19000, 22000, 3500, 25, "0423-2234500", "kurumba@natureresorts.in", "Ooty-Mettupalayam Road, Burliyar, Nilgiris - 643102"),
                # Coimbatore
                ("Radisson Blu Coimbatore", "Coimbatore", "5_star", "Business Class Suite", 7500, 8800, 10500, 12500, 2000, 15, "0422-2226000", "reservations@rdcoimbatore.com", "164/165 Avinashi Road, Peelamedu, Coimbatore - 641004"),
                ("Welcomhotel by ITC Hotels", "Coimbatore", "5_star", "Club Room", 8200, 9600, 11500, 13500, 2200, 15, "0422-2200000", "reservations@welcomhotelcbe.com", "1266 Race Course Road, Coimbatore - 641018"),
                ("Vivanta Coimbatore", "Coimbatore", "5_star", "Superior City View", 7800, 9200, 11000, 13000, 2200, 15, "0422-6681000", "vivanta.coimbatore@ihcltata.com", "105 Race Course Road, Coimbatore - 641018"),
                ("Le Meridien Coimbatore", "Coimbatore", "5_star", "Royal Club King", 8500, 9900, 12000, 14000, 2500, 15, "0422-2364300", "reservations@lemeridiencbe.com", "762 Avinashi Road, Neelambur, Coimbatore - 641062"),
                # Chennai
                ("Taj Coromandel", "Chennai", "5_star", "Luxury Grande", 13500, 15500, 18500, 21500, 3500, 20, "044-66002827", "coromandel.chennai@ihcltata.com", "37 Mahatma Gandhi Road, Nungambakkam, Chennai - 600034"),
                ("ITC Grand Chola", "Chennai", "5_star", "Executive Club", 14500, 16800, 20000, 23000, 3800, 20, "044-22200000", "reservations@itcgrandchola.com", "63 Mount Road, Guindy, Chennai - 600032"),
                ("The Leela Palace Chennai", "Chennai", "5_star", "Sea View Premier", 15500, 18000, 21500, 25000, 4200, 25, "044-33661234", "reservations.chennai@theleela.com", "Adyar Seaface, MRC Nagar, Chennai - 600028"),
                # Bangalore
                ("The Leela Palace Bengaluru", "Bangalore", "5_star", "Royal Premiere", 17500, 20500, 24500, 28500, 4500, 25, "080-25211234", "reservations.bengaluru@theleela.com", "23 Old Airport Road, Kodihalli, Bengaluru - 560008"),
                ("Taj West End", "Bangalore", "5_star", "Heritage Garden View", 16000, 18500, 22000, 25500, 4000, 20, "080-66605660", "westend.bengaluru@ihcltata.com", "Race Course Road, Bengaluru - 560001"),
                ("ITC Gardenia", "Bangalore", "5_star", "Towers Suite", 15000, 17500, 21000, 24500, 3800, 20, "080-22119898", "reservations@itcgardenia.com", "1 Residency Road, Shanthala Nagar, Bengaluru - 560025"),
                # Madurai & Mysore
                ("Heritage Madurai", "Madurai", "4_star", "Banyan Suite", 8500, 9800, 11800, 13800, 2400, 20, "0452-2385455", "info@heritagemadurai.com", "11 Kochadai, Melakkal Main Road, Madurai - 625016"),
                ("The Gateway Hotel Pasumalai", "Madurai", "4_star", "Superior Hill Top", 7800, 9200, 11000, 13000, 2200, 20, "0452-6633000", "gateway.madurai@ihcltata.com", "Pasumalai, Madurai - 625004"),
                ("Lalitha Mahal Palace Hotel", "Mysore", "5_star", "Heritage Royal Suite", 11500, 13500, 16000, 18500, 3000, 20, "0821-2571281", "lalithamahal@junglelodges.com", "Lalitha Mahal Nagar, Siddhartha Layout, Mysuru - 570028"),
                ("Grand Mercure Mysore", "Mysore", "4_star", "Deluxe Room", 6500, 7800, 9500, 11200, 1800, 15, "0821-4021212", "h9878@accor.com", "New Sayyaji Rao Road, Nelson Mandela Circle, Mysuru - 570015"),
                # Yercaud
                ("GRT Nature Trails Yercaud", "Yercaud", "4_star", "Valley View Cottage", 7200, 8500, 10200, 12000, 2000, 20, "04281-225100", "reservations@grtyercaud.com", "3/159 Ondikadai, Salem - Yercaud Ghat Road, Yercaud - 636601"),
                ("Sterling Yercaud", "Yercaud", "3_star", "Classic Room", 5400, 6400, 7800, 9200, 1500, 15, "04281-222700", "yercaud@sterlingholidays.com", "Lady's Seat Road, Yercaud - 636601")
            ]

            hotels_created = []
            for h in hotels_data:
                obj, _ = HotelMaster.objects.get_or_create(
                    name=h[0], destination=h[1],
                    defaults={
                        "star_category": h[2], "room_type": h[3], "ep_rate": Decimal(str(h[4])),
                        "cp_rate": Decimal(str(h[5])), "map_rate": Decimal(str(h[6])), "ap_rate": Decimal(str(h[7])),
                        "extra_bed_rate": Decimal(str(h[8])), "peak_surge_percent": Decimal(str(h[9])),
                        "contact_phone": h[10], "contact_email": h[11], "address": h[12], "is_active": True
                    }
                )
                hotels_created.append(obj)

            monuments_data = [
                ("Government Botanical Garden", "Ooty", 40, 20, 100, 50, 50, "07:00 - 18:30", ""),
                ("Rose Garden Ooty", "Ooty", 40, 20, 100, 50, 50, "08:30 - 18:00", ""),
                ("Doddabetta Peak Viewpoint", "Ooty", 15, 10, 50, 30, 30, "07:00 - 18:00", ""),
                ("Pykara Waterfalls & Lake", "Ooty", 20, 10, 80, 40, 25, "08:30 - 17:30", ""),
                ("Mudumalai Tiger Reserve Safari", "Ooty", 350, 175, 1200, 600, 100, "06:30 - 18:00", "Tuesday"),
                ("Kodaikanal Lake & Boating Club", "Kodaikanal", 20, 10, 50, 25, 20, "08:30 - 18:00", ""),
                ("Bryant Park Botanical Garden", "Kodaikanal", 30, 15, 100, 50, 50, "09:00 - 18:00", ""),
                ("Coaker's Walk Telescopic House", "Kodaikanal", 20, 10, 50, 25, 20, "07:00 - 19:00", ""),
                ("Pillar Rocks & Guna Caves", "Kodaikanal", 10, 5, 50, 25, 30, "09:00 - 17:00", ""),
                ("Aliyar Dam & Park", "Valparai", 20, 10, 50, 25, 20, "09:00 - 18:00", ""),
                ("Sholayar Dam Viewpoint", "Valparai", 0, 0, 0, 0, 0, "06:00 - 18:00", ""),
                ("Mysore Palace & Museum", "Mysore", 100, 50, 1000, 400, 100, "10:00 - 17:30", ""),
                ("Chamundeshwari Temple & Nandi", "Mysore", 0, 0, 0, 0, 0, "06:00 - 21:00", ""),
                ("Brindavan Gardens Musical Fountain", "Mysore", 50, 20, 150, 75, 50, "06:30 - 21:00", ""),
                ("Meenakshi Amman Temple Heritage Corridor", "Madurai", 50, 25, 200, 100, 50, "05:00 - 21:30", ""),
                ("Thirumalai Nayakkar Mahal Sound & Light", "Madurai", 30, 15, 100, 50, 50, "09:00 - 20:30", ""),
                ("Shore Temple & Pancha Rathas UNESCO", "Mahabalipuram", 40, 0, 600, 0, 50, "06:00 - 18:00", ""),
                ("Brihadisvara Big Temple UNESCO", "Thanjavur", 0, 0, 0, 0, 50, "06:00 - 20:30", "")
            ]
            for m in monuments_data:
                MonumentEntranceMaster.objects.get_or_create(
                    name=m[0], destination=m[1],
                    defaults={
                        "domestic_adult_rate": Decimal(str(m[2])), "domestic_child_rate": Decimal(str(m[3])),
                        "foreigner_adult_rate": Decimal(str(m[4])), "foreigner_child_rate": Decimal(str(m[5])),
                        "camera_fee": Decimal(str(m[6])), "operating_hours": m[7], "closed_days": m[8], "is_active": True
                    }
                )

            activities_data = [
                ("Nilgiri Mountain Toy Train Heritage Steam Ride", "Ooty", "per_person", 650, 180, "UNESCO world heritage steam engine journey between Mettupalayam, Coonoor and Ooty."),
                ("Ooty Doddabetta High-Altitude Tea Factory Tour & Tasting", "Ooty", "per_person", 150, 60, "Guided factory tour detailing orthodox tea CTC processing and artisanal tasting."),
                ("Valparai High Forest Estate Tea Tasting & Walking Safari", "Valparai", "per_group", 1200, 120, "Walk through centuries-old private British planter estates with lion-tailed macaque sightings."),
                ("Kodaikanal Lake Row Boat & Cycling Tour", "Kodaikanal", "per_person", 350, 90, "Pedal boating on star-shaped Kodaikanal lake paired with perimeter bicycle rental."),
                ("Mudumalai Tiger Reserve 4x4 Offroad Deep Jungle Safari", "Ooty", "per_group", 3500, 150, "Open-top Mahindra 4WD jungle jeep safari deep inside the Core Nilgiri Biosphere buffer zone."),
                ("Mysore Royal Heritage Tongaa Horse Carriage Ride", "Mysore", "per_group", 800, 45, "Colonial style horse-drawn carriage ride traversing Mysore palace gates and Devaraja market."),
                ("Coonoor Highfield Estate Orange & Tea Plantation Trail", "Coonoor", "per_person", 250, 90, "Estate nature walk through sprawling eucalyptus, orange groves, and tea plantations."),
                ("Kodaikanal Pine Forest Horse Riding Experience", "Kodaikanal", "per_person", 400, 45, "Guided horse trek beneath majestic century-old towering pine trees in Kodaikanal valley.")
            ]
            for a in activities_data:
                ActivityMaster.objects.get_or_create(
                    name=a[0], destination=a[1],
                    defaults={
                        "pricing_type": a[2], "standard_rate": Decimal(str(a[3])),
                        "duration_minutes": a[4], "description": a[5], "is_active": True
                    }
                )

            guide_data = [
                ("Ooty", "English", 1500, 2500), ("Ooty", "Tamil", 1200, 2000), ("Ooty", "Hindi", 1400, 2200),
                ("Kodaikanal", "English", 1500, 2500), ("Kodaikanal", "Tamil", 1200, 2000), ("Kodaikanal", "Hindi", 1400, 2200),
                ("Valparai", "English", 1800, 2800), ("Valparai", "Tamil", 1400, 2200),
                ("Mysore", "English", 1800, 3000), ("Mysore", "French", 2500, 4200), ("Mysore", "German", 2500, 4200),
                ("Madurai", "English", 1600, 2600), ("Madurai", "Tamil", 1200, 2000), ("Madurai", "French", 2500, 4000)
            ]
            for g in guide_data:
                GuideChargeMaster.objects.get_or_create(
                    destination=g[0], language=g[1],
                    defaults={"half_day_rate": Decimal(str(g[2])), "full_day_rate": Decimal(str(g[3])), "is_active": True}
                )

            # ==========================================================
            # 2. B2C CLIENTS & CRM PROFILES (300+ CUSTOMERS)
            # ==========================================================
            self.stdout.write("[*] Seeding 300+ B2C Customers, Inquiries, and Follow-ups...")
            first_names = [
                "Aravind", "Karthik", "Suresh", "Ramesh", "Deepak", "Vignesh", "Sundar", "Ganesh", "Vijay", "Anand",
                "Priya", "Divya", "Ananya", "Meenakshi", "Kavitha", "Sangeetha", "Swetha", "Nandhini", "Lavanya", "Pooja",
                "Rahul", "Amit", "Vikram", "Rohan", "Siddharth", "Arjun", "Aditya", "Manish", "Rajesh", "Pradeep",
                "Sunita", "Preeti", "Neha", "Shreya", "Sneha", "Tanvi", "Ritu", "Meera", "Asha", "Radhika"
            ]
            last_names = [
                "Swaminathan", "Subramaniam", "Natarajan", "Balasubramanian", "Krishnamurthy", "Venkataraman", "Ranganathan",
                "Chandrasekaran", "Srinivasan", "Raghavan", "Iyer", "Iyengar", "Sharma", "Varma", "Reddy", "Patel",
                "Menon", "Nair", "Pillai", "Chettiar", "Gounder", "Naidu", "Rao", "Shetty", "Deshmukh", "Chopra"
            ]
            cities_states = [
                ("Coimbatore", "Tamil Nadu", "641001"), ("Chennai", "Tamil Nadu", "600001"),
                ("Bangalore", "Karnataka", "560001"), ("Madurai", "Tamil Nadu", "625001"),
                ("Salem", "Tamil Nadu", "636001"), ("Trichy", "Tamil Nadu", "620001"),
                ("Kochi", "Kerala", "682001"), ("Trivandrum", "Kerala", "695001"),
                ("Hyderabad", "Telangana", "500001"), ("Mumbai", "Maharashtra", "400001")
            ]

            b2c_pairs = []
            b2c_profiles = []
            for i in range(1, 321):
                fn = random.choice(first_names)
                ln = random.choice(last_names)
                full_name = f"{fn} {ln}"
                phone = f"+91 {random.randint(94000, 99999)} {random.randint(10000, 99999)}"
                email = f"{fn.lower()}.{ln.lower()}{random.randint(10, 99)}@gmail.com"
                city, state, pincode = random.choice(cities_states)

                p = Party.objects.create(
                    name=full_name,
                    party_type="customer",
                    phone=phone,
                    email=email,
                    address=f"{random.randint(12, 450)}, 4th Cross, Gandhi Nagar, {city}",
                    state_code="33" if state == "Tamil Nadu" else ("29" if state == "Karnataka" else "32"),
                    is_active=True
                )
                b2c_pairs.append((p, city, state, pincode))

            for idx, (p, city, state, pincode) in enumerate(b2c_pairs):
                b2c_profiles.append(
                    B2CCustomerProfile(
                        party=p,
                        full_name=p.name,
                        alternate_phone=f"+91 {random.randint(91000, 98999)} {random.randint(10000, 99999)}",
                        nationality="Indian",
                        is_vip=(idx % 7 == 0),
                        city=city,
                        state=state,
                        pincode=pincode
                    )
                )
            B2CCustomerProfile.objects.bulk_create(b2c_profiles, ignore_conflicts=True)
            b2c_party_objs = [pair[0] for pair in b2c_pairs]

            # ==========================================================
            # 3. CRM INQUIRIES & FOLLOW-UPS (500+ INQUIRIES)
            # ==========================================================
            inquiry_destinations = [
                ("Coimbatore", "Ooty (Nilgiris Hill Tour 3N/4D)"),
                ("Chennai", "Puducherry & Mahabalipuram Coastal Tour"),
                ("Bangalore", "Mysore Palace & Coorg Coffee Plantation"),
                ("Coimbatore", "Valparai & Athirapally Rainforest Safari"),
                ("Madurai", "Rameswaram & Kanyakumari Pilgrimage"),
                ("Coimbatore", "Kodaikanal Princess of Hills 2N/3D"),
                ("Bangalore", "Ooty - Mudumalai Wildlife Corridor"),
                ("Coimbatore", "Munnar - Thekkady Tea & Spice Trail"),
                ("Chennai", "Vellore - Tirupati Balaji Darshan Express"),
                ("Coimbatore", "Coimbatore Local Airport & Temple Package")
            ]
            veh_types = list(VehicleType.objects.all())

            inquiries = []
            today = timezone.now().date()
            for i in range(1, 521):
                cust = random.choice(b2c_party_objs) if b2c_party_objs else parties[0]
                orig, dest = random.choice(inquiry_destinations)
                pk_date = today + datetime.timedelta(days=random.randint(-45, 60))
                dp_date = pk_date + datetime.timedelta(days=random.randint(2, 6))
                vtype = random.choice(veh_types) if veh_types else None
                status = random.choice(["new", "in_progress", "quoted", "negotiating", "won", "lost"])
                pax = random.randint(2, 14)
                deal_val = Decimal(str(random.randint(18, 120) * 1000))

                inq = Inquiry(
                    inquiry_number=f"INQ-2026-{10000 + i}",
                    party=cust,
                    guest_name=cust.name,
                    guest_phone=cust.phone,
                    guest_email=cust.email,
                    pickup_location=orig,
                    destination=dest,
                    destination_dropdown=dest[:50],
                    pickup_date=pk_date,
                    pickup_time=datetime.time(random.randint(6, 11), 0),
                    drop_date=dp_date,
                    journey_type=random.choice(["round_trip", "outstation", "one_way", "local"]),
                    vehicle_type=vtype,
                    adult_count=pax,
                    child_count=random.randint(0, 3),
                    priority=random.choice(["high", "medium", "urgent", "low"]),
                    source=random.choice(["website", "phone", "agent", "walkin", "referral"]),
                    assigned_to=admin_user,
                    target_tat_hours=24,
                    estimated_km=random.randint(250, 1400),
                    quoted_price=deal_val,
                    estimated_deal_value=deal_val,
                    status=status
                )
                inquiries.append(inq)

            Inquiry.objects.bulk_create(inquiries, ignore_conflicts=True)
            created_inqs = list(Inquiry.objects.all().order_by("-id")[:520])

            # Followups
            followups = []
            for inq in created_inqs:
                for f_num in range(random.randint(1, 3)):
                    followups.append(
                        InquiryFollowUp(
                            inquiry=inq,
                            notes=random.choice([
                                "Customer requested quote for Innova Crysta with luggage carrier for 5 adults.",
                                "Followed up on itinerary. Guest confirmed hotel booking at Savoy Ooty.",
                                "Sent revised pricing matching competitive travel desk rates with toll included.",
                                "Guest requested confirmation of driver vaccinated and luggage space.",
                                "Client agreed on advance payment terms; booking being finalized."
                            ]),
                            performed_by=admin_user
                        )
                    )
            InquiryFollowUp.objects.bulk_create(followups, ignore_conflicts=True)

            # ==========================================================
            # 4. CRM QUOTATIONS, DAYS & ITEMS (300+ DETAILED QUOTES)
            # ==========================================================
            self.stdout.write("[*] Seeding 300+ Detailed Quotations and Itinerary Items...")
            quotations = []
            for i, inq in enumerate(created_inqs[:320]):
                dur_days = (inq.drop_date - inq.pickup_date).days if inq.drop_date else 3
                dur_days = max(1, dur_days)
                t_cost = Decimal(str(dur_days * random.randint(4500, 9500)))
                h_cost = Decimal(str((dur_days - 1) * random.randint(6000, 15000)))
                m_cost = Decimal(str(inq.adult_count * 450))
                a_cost = Decimal(str(inq.adult_count * 800))
                net = t_cost + h_cost + m_cost + a_cost
                markup_pct = Decimal("15.00")
                markup_amt = (net * markup_pct / Decimal("100.00")).quantize(Decimal("0.01"))
                gross = net + markup_amt
                gst_rate = Decimal("5.00")
                gst_amt = (gross * gst_rate / Decimal("100.00")).quantize(Decimal("0.01"))
                total_price = gross + gst_amt

                q = Quotation(
                    quotation_number=f"QT-2026-{20000 + i}",
                    version=1,
                    inquiry=inq,
                    party=inq.party,
                    guest_name=inq.guest_name,
                    guest_phone=inq.guest_phone,
                    guest_email=inq.guest_email,
                    title=f"Customized Luxury {inq.destination} Tour",
                    destination=inq.destination,
                    start_date=inq.pickup_date,
                    end_date=inq.drop_date or (inq.pickup_date + datetime.timedelta(days=3)),
                    pax_count=inq.adult_count,
                    vehicle_type=inq.vehicle_type,
                    vehicle_count=1,
                    transport_cost=t_cost,
                    accommodation_cost=h_cost,
                    monuments_cost=m_cost,
                    activities_cost=a_cost,
                    guide_cost=Decimal("2500.00"),
                    other_services_cost=Decimal("500.00"),
                    net_cost=net,
                    markup_percent=markup_pct,
                    markup_amount=markup_amt,
                    gross_price=gross,
                    gst_rate=gst_rate,
                    gst_amount=gst_amt,
                    total_quoted_price=total_price,
                    status=random.choice(["sent", "accepted", "negotiating", "draft", "converted"]),
                    proposal_token=f"TOKEN_{random.randint(100000, 999999)}",
                    brochure_cover_theme="mountain_valley",
                    inclusions="Ac Cab with fuel, toll, border tax, parking, driver bata, English speaking driver.",
                    exclusions="Personal laundry, telephone calls, alcoholic beverages, camera fees at viewpoints.",
                    terms_conditions="25% advance to confirm booking. Cancellation within 48 hours incurs 1 day fee.",
                    created_by=admin_user
                )
                quotations.append(q)

            Quotation.objects.bulk_create(quotations, ignore_conflicts=True)
            created_quotes = list(Quotation.objects.all().order_by("-id")[:320])

            # Quotation Days & Items
            quote_days = []
            for q in created_quotes:
                dur = (q.end_date - q.start_date).days + 1
                for d in range(1, min(dur + 1, 5)):
                    quote_days.append(
                        QuotationDay(
                            quotation=q,
                            day_number=d,
                            date=q.start_date + datetime.timedelta(days=d - 1),
                            title=f"Day {d}: Sightseeing & Excursion in {q.destination[:30]}",
                            description=f"Morning departure after breakfast. Panoramic route via viewpoints, lakes, and cultural monuments.",
                            hotel=random.choice(hotels_created) if hotels_created else None,
                            hotel_meal_plan=random.choice(["cp", "map", "ep"]),
                            overnight_destination=q.destination[:40]
                        )
                    )
            QuotationDay.objects.bulk_create(quote_days, ignore_conflicts=True)

            # ==========================================================
            # 5. OPERATIONS: BOOKINGS & COMMERCIAL TRIPS (600+ RECORDS)
            # ==========================================================
            self.stdout.write("[*] Seeding 600+ Commercial Bookings & Trips with Chauffeurs and Telematics...")
            bookings = []
            for i in range(1, 651):
                p = random.choice(b2c_party_objs) if (i % 3 != 0 and b2c_party_objs) else random.choice(parties)
                orig, dest = random.choice(inquiry_destinations)
                p_date = today + datetime.timedelta(days=random.randint(-60, 45))
                d_date = p_date + datetime.timedelta(days=random.randint(1, 5))
                v_type = random.choice(veh_types) if veh_types else None
                km = random.randint(300, 1800)
                price = Decimal(str(km * random.randint(18, 38)))

                b = Booking(
                    booking_number=f"BK-2026-{30000 + i}",
                    party=p,
                    guest_name=p.name,
                    guest_phone=p.phone,
                    booking_date=p_date - datetime.timedelta(days=random.randint(2, 10)),
                    pickup_location=orig,
                    destination=dest,
                    pickup_date=p_date,
                    pickup_time=datetime.time(random.randint(5, 10), 0),
                    drop_date=d_date,
                    travel_pnr=f"PNR{random.randint(100000, 999999)}",
                    journey_type=random.choice(["outstation", "round_trip", "local", "one_way"]),
                    vehicle_type=v_type,
                    pax_count=random.randint(2, 12),
                    billing_type="km",
                    quoted_price=price,
                    expected_km=km,
                    gst_rate=Decimal("5.00"),
                    status=random.choice(["confirmed", "completed", "pending", "confirmed"])
                )
                bookings.append(b)

            Booking.objects.bulk_create(bookings, ignore_conflicts=True)
            created_bookings = list(Booking.objects.all().order_by("-id")[:650])

            # Operational Trips
            trips = []
            for i, b in enumerate(created_bookings):
                veh = vehicles[i % len(vehicles)]
                drv = drivers[i % len(drivers)]
                dur_days = (b.drop_date - b.pickup_date).days if b.drop_date else 2
                dur_days = max(1, dur_days)
                open_km = random.randint(15000, 250000)
                run_km = b.expected_km or random.randint(300, 1500)
                close_km = open_km + run_km
                is_past = b.drop_date and b.drop_date < today
                t_status = "completed" if is_past else random.choice(["started", "assigned", "driver_confirmed", "booked"])

                t = Trip(
                    trip_id=f"TRIP-2026-{40000 + i}",
                    booking=b,
                    party=b.party,
                    guest_name=b.guest_name,
                    travel_pnr=b.travel_pnr,
                    pax_count=b.pax_count,
                    vehicle=veh,
                    driver=drv,
                    status=t_status,
                    start_date=b.pickup_date,
                    end_date=b.drop_date,
                    start_time=b.pickup_time,
                    end_time=datetime.time(19, 0),
                    opening_km=open_km,
                    closing_km=close_km if t_status == "completed" else None,
                    billing_model="km",
                    day_rate=Decimal("3500.00"),
                    km_rate=Decimal("18.00"),
                    fixed_amount=Decimal("0.00"),
                    days_count=dur_days,
                    driver_bata=Decimal(str(dur_days * 500)),
                    commission=Decimal("0.00"),
                    tracking_token=f"TRK_{random.randint(100000, 999999)}",
                    pickup_pin=str(random.randint(1000, 9999)),
                    is_pin_verified=True,
                    current_milestone="on_trip" if t_status == "started" else ("completed" if t_status == "completed" else "scheduled")
                )
                trips.append(t)

            Trip.objects.bulk_create(trips, ignore_conflicts=True)
            created_trips = list(Trip.objects.all().order_by("-id")[:650])

            # ==========================================================
            # 6. OPERATIONS: CASH ADVANCE ENVELOPES (400+ ENVELOPES)
            # ==========================================================
            self.stdout.write("[*] Seeding 400+ Trip Cash Advance Envelopes...")
            envelopes = []
            for i, tr in enumerate(created_trips[:420]):
                fuel_cash = Decimal(str(random.randint(3000, 12000)))
                toll_cash = Decimal(str(random.randint(800, 3500)))
                permit_cash = Decimal(str(random.randint(200, 1500)))
                bata_cash = tr.driver_bata
                cont_cash = Decimal("1000.00")
                total_adv = fuel_cash + toll_cash + permit_cash + bata_cash + cont_cash

                env_status = "reconciled_settled" if tr.status == "completed" else random.choice(["disbursed", "on_trip", "submitted_for_audit"])
                actual_spent = fuel_cash - Decimal("250.00") if env_status == "reconciled_settled" else Decimal("0.00")
                tolls_spent = toll_cash if env_status == "reconciled_settled" else Decimal("0.00")
                permits_spent = permit_cash if env_status == "reconciled_settled" else Decimal("0.00")
                bata_deducted = bata_cash if env_status == "reconciled_settled" else Decimal("0.00")
                total_exp = actual_spent + tolls_spent + permits_spent + bata_deducted
                net_bal = total_adv - total_exp if env_status == "reconciled_settled" else total_adv

                envelopes.append(
                    TripCashAdvanceEnvelope(
                        envelope_code=f"ENV-2026-{50000 + i}",
                        trip=tr,
                        driver=tr.driver,
                        disbursed_at=timezone.now() - datetime.timedelta(days=random.randint(1, 20)),
                        fuel_cash_allocation=fuel_cash,
                        toll_cash_allocation=toll_cash,
                        permit_cash_allocation=permit_cash,
                        driver_bata_allocation=bata_cash,
                        contingency_cash=cont_cash,
                        total_advance_disbursed=total_adv,
                        actual_fuel_spent=actual_spent,
                        actual_tolls_spent=tolls_spent,
                        actual_permits_spent=permits_spent,
                        actual_parking_spent=Decimal("0.00"),
                        actual_repairs_spent=Decimal("0.00"),
                        driver_bata_deducted=bata_deducted,
                        total_expenses_verified=total_exp,
                        net_balance=net_bal,
                        driver_signature_acknowledged=True,
                        settled_at=timezone.now() if env_status == "reconciled_settled" else None,
                        settlement_notes="Reconciled against verified fuel and toll receipts.",
                        status=env_status
                    )
                )
            TripCashAdvanceEnvelope.objects.bulk_create(envelopes, ignore_conflicts=True)

            # ==========================================================
            # 7. OPERATIONS: BORDER PERMITS & HILL e-PASSES (450+ EACH)
            # ==========================================================
            self.stdout.write("[*] Seeding 450+ Interstate Border Road Tax Permits & 450+ Hill e-Passes...")
            border_permits = []
            border_states = [
                ("Kerala", "Walayar Check-post (NH-544 Palakkad)", 200, 0),
                ("Karnataka", "Attibele / Zuzuvadi Check-post (NH-44 Hosur)", 200, 900),
                ("Andhra Pradesh", "Naraharipet Check-post (Chittoor - Vellore)", 200, 700),
                ("Puducherry", "Gorimedu Check-post (Tindivanam - Pondy)", 100, 350),
                ("Goa", "Mollem Check-post (Belgaum - Goa)", 200, 1000)
            ]

            for i in range(480):
                tr = created_trips[i % len(created_trips)]
                st_name, chk_name, p_fee, r_tax = random.choice(border_states)
                is_aitp = (i % 3 == 0)
                actual_tax = Decimal("0.00") if is_aitp else Decimal(str(r_tax))
                v_from = timezone.now() - datetime.timedelta(days=random.randint(0, 15))
                v_until = v_from + datetime.timedelta(days=random.randint(7, 30))
                p_status = "valid" if v_until > timezone.now() else "expired"

                v_cat_code = (tr.vehicle.vehicle_category.code if tr.vehicle.vehicle_category else "muv_suv")[:35]
                border_permits.append(
                    InterstateBorderPermit(
                        trip=tr,
                        vehicle=tr.vehicle,
                        origin_state="Tamil Nadu",
                        target_state=st_name,
                        permit_type="aitp_annual" if is_aitp else "single_entry",
                        checkpost_name=chk_name,
                        state_permit_fee=Decimal(str(p_fee)),
                        border_road_tax=actual_tax,
                        tax_amount=Decimal(str(p_fee)) + actual_tax,
                        is_aitp_exempt=is_aitp,
                        vehicle_category_bracket=v_cat_code,
                        payment_mode="parivahan_online" if not is_aitp else "aitp_prepaid",
                        receipt_number=f"PARIVAHAN-{st_name[:2].upper()}-2026-{random.randint(100000, 999999)}",
                        valid_from=v_from,
                        valid_until=v_until,
                        status=p_status
                    )
                )
            InterstateBorderPermit.objects.bulk_create(border_permits, ignore_conflicts=True)

            # Hill e-Passes (TNeGA High Court Mandated)
            epasses = []
            hill_zones = [
                ("nilgiris", "Burliyar Checkpost (Mettupalayam - Coonoor)", "Savoy - IHCL SeleQtions, Ooty"),
                ("kodaikanal", "Silver Cascade Checkpost (Ghat Road)", "The Tamara Luxury Resort, Kodaikanal"),
                ("valparai", "Aliyar Checkpost (40 Hairpin Bends Foothills)", "Briar Tea Bungalows, Valparai"),
                ("yercaud", "Adivaram Toll Gate (Salem Foothills)", "GRT Nature Trails, Yercaud")
            ]

            for i in range(480):
                tr = created_trips[i % len(created_trips)]
                z_key, cp_name, h_name = random.choice(hill_zones)
                ent_date = today + datetime.timedelta(days=random.randint(-15, 20))
                ex_date = ent_date + datetime.timedelta(days=random.randint(1, 4))
                ep_stat = "active" if (ent_date <= today <= ex_date) else ("expired" if ex_date < today else "pending")

                epasses.append(
                    EcoSensitiveZoneEPass(
                        trip=tr,
                        vehicle=tr.vehicle,
                        driver=tr.driver,
                        zone=z_key,
                        epass_number=f"TNeGA-{z_key[:3].upper()}-2026-{random.randint(100000, 999999)}",
                        entry_date=ent_date,
                        exit_date=ex_date,
                        num_tourists=tr.pax_count or random.randint(2, 8),
                        hotel_name=h_name,
                        hotel_booking_ref=f"HTL-CONF-{random.randint(10000, 99999)}",
                        purpose=random.choice(["tourism", "corporate", "pilgrimage"]),
                        checkpost_name=cp_name,
                        qr_code_token=f"QR_HILL_TNEGA_{random.randint(1000000, 9999999)}",
                        status=ep_stat,
                        verified_at_checkpost=(ep_stat != "pending")
                    )
                )
            EcoSensitiveZoneEPass.objects.bulk_create(epasses, ignore_conflicts=True)

            # ==========================================================
            # 8. OPERATIONS: PNR ARRIVALS, BREAKDOWN SOS, FATIGUE, EMPTY LEGS, FINES
            # ==========================================================
            self.stdout.write("[*] Seeding PNR Arrivals, Breakdown SOS, Fatigue Sentry, Empty Legs & E-Challans...")
            # PNR Arrivals
            terminals = [
                ("flight", "6E-241", "IndiGo", "Terminal 1 - CJB", "Coimbatore International Airport"),
                ("flight", "AI-542", "Air India", "Terminal 2 - MAA", "Chennai International Airport"),
                ("flight", "UK-812", "Vistara", "Terminal 1 - BLR", "Kempegowda Int'l Airport Bangalore"),
                ("flight", "6E-6782", "IndiGo", "Terminal 1 - IXM", "Madurai Airport"),
                ("train", "12675", "Southern Railway", "Kovai Express (PF 1)", "Coimbatore Junction Railway Station"),
                ("train", "20643", "Southern Railway", "Vande Bharat Express (PF 2)", "Coimbatore Junction"),
                ("train", "12007", "Southern Railway", "Shatabdi Express (PF 1)", "Chennai Central MAS")
            ]
            manifests = []
            for i in range(130):
                tr = created_trips[i % len(created_trips)]
                ttype, num, carrier, term, hub = random.choice(terminals)
                arr_dt = timezone.now() + datetime.timedelta(hours=random.randint(-48, 72))
                manifests.append(
                    GroupArrivalManifest(
                        manifest_code=f"ARR-2026-{60000 + i}",
                        transit_type=ttype,
                        pnr_or_flight_number=num,
                        carrier_name=carrier,
                        arrival_terminal=term,
                        origin_city=random.choice(["Mumbai", "Delhi", "Kolkata", "Hyderabad", "Bangalore"]),
                        scheduled_arrival=arr_dt,
                        actual_arrival=arr_dt + datetime.timedelta(minutes=random.randint(-10, 45)),
                        delay_minutes=random.randint(0, 30),
                        guest_leader_name=tr.guest_name or "Mr. Rajesh Kumar",
                        guest_phone=tr.booking.guest_phone if tr.booking else "+91 98401 23456",
                        total_pax=tr.pax_count or random.randint(2, 10),
                        luggage_count=random.randint(2, 12),
                        trip=tr,
                        assigned_vehicle=tr.vehicle,
                        assigned_driver=tr.driver,
                        placard_title=f"Welcome {tr.guest_name} - Sivagayathiri VIP Transport",
                        status=random.choice(["scheduled", "landed_arrived", "placard_displayed", "boarded_en_route", "completed"]),
                        hotel_destination=tr.booking.destination[:50] if tr.booking else "Savoy Ooty"
                    )
                )
            GroupArrivalManifest.objects.bulk_create(manifests, ignore_conflicts=True)

            # Breakdown SOS
            breakdowns = []
            highways = [
                ("NH-544 (Salem - Coimbatore Expressway)", "Km 114 Near Avinashi Bypass Flyover"),
                ("NH-44 (Hosur - Bangalore Highway)", "Km 38 Near Attibele Toll Plaza"),
                ("NH-83 (Dindigul - Pollachi Road)", "Km 62 Near Udumalpet Foothills"),
                ("SH-15 (Mettupalayam - Ooty Ghat Road)", "14th Hairpin Bend Near Burliyar Viewpoint"),
                ("NH-181 (Gudalur - Mudumalai Corridor)", "Forest Checkpost Entry Sector 4")
            ]
            for i in range(65):
                tr = created_trips[i % len(created_trips)]
                hw, loc = random.choice(highways)
                b_stat = random.choice(["resolved", "resolved", "mechanic_dispatched", "reported"])
                breakdowns.append(
                    HighwayBreakdownSOS(
                        incident_id=f"SOS-2026-{65000 + i}",
                        trip=tr,
                        vehicle=tr.vehicle,
                        driver=tr.driver,
                        issue_type=random.choice(["tire_blowout", "engine_overheat", "electrical_alternator", "clutch_transmission"]),
                        highway_corridor=hw,
                        breakdown_location=loc,
                        passengers_stranded=tr.pax_count or 4,
                        passenger_contact_name=tr.guest_name or "Dr. R. Venkat",
                        passenger_contact_phone="+91 94431 88990",
                        status=b_stat,
                        severity=random.choice(["moderate", "critical", "minor"]),
                        nearest_mechanic_assigned="S. Murugan Highway Auto Service",
                        mechanic_phone="+91 98422 11223",
                        estimated_delay_minutes=random.randint(25, 90),
                        customer_notified_sms=True,
                        reported_at=timezone.now() - datetime.timedelta(days=random.randint(1, 30)),
                        resolved_at=timezone.now() - datetime.timedelta(days=random.randint(0, 29)) if b_stat == "resolved" else None,
                        resolution_notes="Mobile highway service van attended. Quick tire change & alternator belt tension adjusted."
                    )
                )
            HighwayBreakdownSOS.objects.bulk_create(breakdowns, ignore_conflicts=True)

            # Fatigue Audit Logs
            fatigue_logs = []
            for i in range(360):
                drv = drivers[i % len(drivers)]
                tr = created_trips[i % len(created_trips)]
                c_hours = Decimal(str(random.randint(3, 9)))
                r_hours = Decimal(str(random.randint(4, 12)))
                risk = "well_rested" if (c_hours <= 5 and r_hours >= 8) else ("adequate_rest" if c_hours <= 7 else "fatigue_risk")

                fatigue_logs.append(
                    DriverFatigueAuditLog(
                        driver=drv,
                        trip=tr,
                        rest_hours_elapsed=r_hours,
                        continuous_duty_hours=c_hours,
                        is_ghat_route=(i % 4 == 0),
                        is_night_shift=(i % 5 == 0),
                        risk_level=risk,
                        manager_override=(risk == "fatigue_risk"),
                        override_reason="Authorized 45-min highway wayside refreshment halt at HPCL COCO Sankari." if risk == "fatigue_risk" else "",
                        override_by=admin_user if risk == "fatigue_risk" else None
                    )
                )
            DriverFatigueAuditLog.objects.bulk_create(fatigue_logs, ignore_conflicts=True)

            # Empty Leg Offers
            empty_legs = []
            corridors = [
                ("Ooty", "Coimbatore"), ("Kodaikanal", "Madurai"),
                ("Bangalore", "Coimbatore"), ("Chennai", "Puducherry"),
                ("Munnar", "Kochi"), ("Mysore", "Bangalore")
            ]
            for i in range(85):
                tr = created_trips[i % len(created_trips)]
                orig, dest = random.choice(corridors)
                std_rate = Decimal(str(random.randint(6000, 14000)))
                disc_rate = (std_rate * Decimal("0.55")).quantize(Decimal("0.01"))
                f_cost = (disc_rate * Decimal("0.35")).quantize(Decimal("0.01"))
                t_cost = Decimal("450.00")
                margin = disc_rate - f_cost - t_cost

                st_time = timezone.now() + datetime.timedelta(hours=random.randint(4, 48))
                empty_legs.append(
                    EmptyLegTripOffer(
                        offer_code=f"EMPLEG-2026-{70000 + i}",
                        parent_trip=tr,
                        vehicle=tr.vehicle,
                        driver=tr.driver,
                        origin_city=orig,
                        destination_city=dest,
                        available_from=st_time,
                        available_until=st_time + datetime.timedelta(hours=6),
                        standard_tariff=std_rate,
                        discounted_empty_leg_rate=disc_rate,
                        estimated_fuel_cost=f_cost,
                        estimated_toll_cost=t_cost,
                        net_margin_generated=margin,
                        status=random.choice(["available", "available", "broadcasted", "booked"]),
                        notes=f"Vehicle returning empty after VIP guest drop in {orig}. Available for one-way booking at 45% discount."
                    )
                )
            EmptyLegTripOffer.objects.bulk_create(empty_legs, ignore_conflicts=True)

            # Traffic Fines (Parivahan E-Challans)
            fines = []
            for i in range(160):
                veh = vehicles[i % len(vehicles)]
                drv = drivers[i % len(drivers)]
                v_type = random.choice(["speeding", "seatbelt_driver", "signal", "parking", "documents"])
                amt = Decimal("1000.00") if v_type == "speeding" else (Decimal("500.00") if "seatbelt" in v_type else Decimal("1500.00"))
                fines.append(
                    TrafficFine(
                        vehicle=veh,
                        driver=drv,
                        date_of_offence=timezone.now() - datetime.timedelta(days=random.randint(1, 90)),
                        challan_number=f"TN{random.randint(100000000, 999999999)}",
                        violation_type=v_type,
                        fine_amount=amt,
                        paid_by=random.choice(["company", "driver", "unpaid"]),
                        financial_responsibility=random.choice(["driver", "company"])
                    )
                )
            TrafficFine.objects.bulk_create(fines, ignore_conflicts=True)

            # Telematics Pings (1200+ Coordinates)
            pings = []
            base_coords = [
                (11.0168, 76.9558),  # Coimbatore
                (11.4102, 76.6950),  # Ooty
                (10.2381, 77.4892),  # Kodaikanal
                (10.3249, 76.9558),  # Valparai
                (12.9716, 77.5946),  # Bangalore
                (13.0827, 80.2707),  # Chennai
                (9.9252, 78.1198)    # Madurai
            ]
            for i in range(1250):
                veh = vehicles[i % len(vehicles)]
                lat_base, lon_base = random.choice(base_coords)
                lat = Decimal(str(round(lat_base + random.uniform(-0.08, 0.08), 6)))
                lon = Decimal(str(round(lon_base + random.uniform(-0.08, 0.08), 6)))
                spd = Decimal(str(round(random.uniform(0.0, 78.5), 1)))

                pings.append(
                    VehicleTelematicsPing(
                        vehicle=veh,
                        timestamp=timezone.now() - datetime.timedelta(minutes=random.randint(1, 180)),
                        latitude=lat,
                        longitude=lon,
                        speed_kmh=spd,
                        ignition_on=(spd > 0),
                        fuel_level_pct=Decimal(str(random.randint(25, 95))),
                        odometer_km=random.randint(20000, 180000),
                        satellite_count=random.randint(10, 18)
                    )
                )
            VehicleTelematicsPing.objects.bulk_create(pings, ignore_conflicts=True)

            # ==========================================================
            # 9. FLEET COMMUTE & CONTRACTS (CORPORATE MOBILITY)
            # ==========================================================
            self.stdout.write("[*] Seeding Corporate Contracts, Commute Routes, Shifts, and Boarding Passes...")
            corp_parties = [p for p in parties if "Tata" in p.name or "SRS" in p.name or "Logistics" in p.name or p.party_type == "customer"]
            if not corp_parties:
                corp_parties = parties[:3]

            contracts = []
            for i, cp in enumerate(corp_parties[:10]):
                contracts.append(
                    TransportContract.objects.create(
                        contract_category=random.choice(["corporate_it", "manufacturing_plant", "educational_institution"]),
                        name=f"{cp.name} - Annual Staff Mobility SLA 2026",
                        customer=cp,
                        start_date=today - datetime.timedelta(days=180),
                        end_date=today + datetime.timedelta(days=185),
                        billing_model="per_trip_km",
                        billing_cycle="monthly",
                        default_rate=Decimal("24.50"),
                        gst_rate=Decimal("5.00"),
                        payment_credit_days=30,
                        committed_vehicle_count=random.randint(12, 35),
                        standby_vehicle_count=3,
                        fuel_escalation_enabled=True,
                        base_diesel_price=Decimal("93.50"),
                        fuel_revision_factor=Decimal("0.25"),
                        sla_penalty_cap_pct=Decimal("10.00"),
                        status="active"
                    )
                )

            # Commute Routes
            route_templates = [
                ("Gandhipuram to TIDEL Park IT Express", "Gandhipuram Central Bus Stand", "TIDEL Park Coimbatore", 18, 40),
                ("Vadavalli to CHIL SEZ Saravanampatti", "Vadavalli Bus Depot", "CHIL SEZ IT Park", 24, 55),
                ("Sundarapuram to Eachanari Tech Hub", "Sundarapuram Junction", "Eachanari Industrial Park", 14, 30),
                ("Thudiyalur to KGISL Campus Express", "Thudiyalur Bus Stop", "KGISL Tech Park Saravanampatti", 16, 35),
                ("Tambaram to OMR Siruseri IT Corridor", "Tambaram Sanatorium", "SIPCOT IT Park Siruseri", 32, 70),
                ("Velachery to TIDEL Park Taramani", "Velachery MRTS Station", "TIDEL Park Chennai", 12, 28),
                ("Silk Board to Electronic City Phase 1", "Central Silk Board", "Wipro Gate Electronic City", 15, 35),
                ("Whitefield to Manyata Embassy Tech Park", "Whitefield Railway Station", "Manyata Tech Park Nagavara", 28, 65)
            ]
            commute_routes = []
            for c in contracts:
                for r_name, orig, dest, dist, mins in route_templates[:4]:
                    commute_routes.append(
                        BaseRoute(
                            contract=c,
                            name=f"{c.customer.name[:15]} - {r_name}",
                            origin=orig,
                            destination=dest,
                            distance_km=dist,
                            estimated_travel_minutes=mins,
                            is_active=True
                        )
                    )
            BaseRoute.objects.bulk_create(commute_routes, ignore_conflicts=True)
            created_routes = list(BaseRoute.objects.all().order_by("-id")[:len(commute_routes)])

            # Route Stops
            stops = []
            for r in created_routes:
                for s_idx in range(1, 6):
                    stops.append(
                        BaseRouteStop(
                            route=r,
                            stop_order=s_idx,
                            name=f"{r.origin[:12]} Waypoint Stop {s_idx}",
                            scheduled_offset_minutes=s_idx * 10,
                            pickup_landmark=f"Near Signal Landmark {s_idx}",
                            expected_passenger_count=random.randint(4, 9),
                            is_active=True
                        )
                    )
            BaseRouteStop.objects.bulk_create(stops, ignore_conflicts=True)

            # Commute Shifts
            shifts = []
            shift_timings = [
                ("General Morning Inbound", "inbound", datetime.time(7, 45), False),
                ("General Evening Outbound", "outbound", datetime.time(17, 45), False),
                ("Night Shift Inbound", "inbound", datetime.time(22, 0), True),
                ("Early Morning Night Drop", "outbound", datetime.time(5, 30), True)
            ]
            for r in created_routes:
                for s_name, dire, tim, esc in shift_timings:
                    shifts.append(
                        BaseShift(
                            route=r,
                            shift_name=s_name,
                            direction=dire,
                            timing=tim,
                            days_of_week="Mon,Tue,Wed,Thu,Fri",
                            grace_period_minutes=10,
                            escort_guard_required=esc
                        )
                    )
            BaseShift.objects.bulk_create(shifts, ignore_conflicts=True)
            created_shifts = list(BaseShift.objects.all().order_by("-id")[:len(shifts)])

            # Commuter Manifest (Employees)
            manifest_employees = []
            for c in contracts:
                for e_idx in range(1, 45):
                    fn = random.choice(first_names)
                    ln = random.choice(last_names)
                    manifest_employees.append(
                        CommuterManifest(
                            contract=c,
                            commuter_type="corporate_employee",
                            commuter_id=f"EMP-{c.id * 1000 + e_idx}",
                            name=f"{fn} {ln}",
                            gender=random.choice(["male", "female", "male", "female"]),
                            phone=f"+91 97{random.randint(10000000, 99999999)}",
                            department_or_grade=random.choice(["Software Engineering", "Quality Assurance", "Finance Ops", "Customer Success"]),
                            pickup_address=f"Flat {random.randint(101, 804)}, Green Enclave, Coimbatore",
                            requires_night_escort=True,
                            is_active=True
                        )
                    )
            CommuterManifest.objects.bulk_create(manifest_employees, ignore_conflicts=True)
            created_commuters = list(CommuterManifest.objects.all().order_by("-id")[:len(manifest_employees)])

            # Daily Trip Logs (600+ Commute Trips)
            commute_trip_logs = []
            for i in range(650):
                sh = created_shifts[i % len(created_shifts)]
                veh = vehicles[i % len(vehicles)]
                drv = drivers[i % len(drivers)]
                t_date = today - datetime.timedelta(days=random.randint(0, 30))
                p_cnt = random.randint(12, 32)

                commute_trip_logs.append(
                    ContractTripLog(
                        shift=sh,
                        date=t_date,
                        vehicle=veh,
                        driver=drv,
                        status="completed" if t_date < today else "scheduled",
                        passenger_count=p_cnt,
                        opening_km=random.randint(20000, 150000),
                        closing_km=random.randint(150000, 150050),
                        driver_bata=Decimal("450.00"),
                        toll_parking_charges=Decimal("85.00"),
                        scheduled_departure_time=sh.timing,
                        actual_departure_time=sh.timing,
                        actual_arrival_time=datetime.time((sh.timing.hour + 1) % 24, sh.timing.minute),
                        delay_minutes=random.randint(0, 12)
                    )
                )
            ContractTripLog.objects.bulk_create(commute_trip_logs, ignore_conflicts=True)
            created_trip_logs = list(ContractTripLog.objects.all().order_by("-id")[:650])

            # Night Safety Escorts
            night_escorts = []
            escort_guards = [
                ("R. Subramaniam", "G4S Secure Solutions", "G4S-ESC-8812"),
                ("M. Periasamy", "SIS Security Services", "SIS-ESC-4190"),
                ("K. Palanivel", "Peregrine Guard Guarding", "PER-ESC-7721"),
                ("S. Murugan", "Alert Command Force", "ALR-ESC-5510")
            ]
            for i, tl in enumerate([log for log in created_trip_logs if log.shift.escort_guard_required][:190]):
                g_name, agency, badge = random.choice(escort_guards)
                night_escorts.append(
                    NightSafetyEscortLog(
                        trip_log=tl,
                        escort_guard_name=g_name,
                        security_agency=agency,
                        guard_badge_number=badge,
                        guard_contact_phone="+91 98432 09876",
                        female_passengers_count=random.randint(2, 8),
                        first_pickup_time=tl.shift.timing,
                        last_female_drop_time=datetime.time((tl.shift.timing.hour + 1) % 24, 15),
                        last_drop_verification_status="safe_drop_confirmed",
                        safe_drop_confirmed_by="Automated IVR Call & Security Desk",
                        remarks="All female commuters safely dropped at doorstep with supervisor call back confirmation."
                    )
                )
            NightSafetyEscortLog.objects.bulk_create(night_escorts, ignore_conflicts=True)

            # Commuter Boarding Passes (800+ Passes)
            boarding_passes = []
            for i in range(850):
                c_emp = created_commuters[i % len(created_commuters)]
                t_log = created_trip_logs[i % len(created_trip_logs)]
                boarding_passes.append(
                    CommuterBoardingPass(
                        commuter=c_emp,
                        trip_log=t_log,
                        date=t_log.date,
                        shift=t_log.shift,
                        boarding_otp=str(random.randint(1000, 9999)),
                        pass_token=f"PASS_{random.randint(100000, 999999)}",
                        is_boarded=True,
                        ivr_status="confirmed"
                    )
                )
            CommuterBoardingPass.objects.bulk_create(boarding_passes, ignore_conflicts=True)

            # Commute Incidents
            commute_incidents = []
            for i in range(65):
                t_log = created_trip_logs[i % len(created_trip_logs)]
                commute_incidents.append(
                    CommuteIncident(
                        incident_id=f"INC-2026-{80000 + i}",
                        incident_type=random.choice(["breakdown", "accident", "medical", "route_blocked", "safety_concern"]),
                        severity=random.choice(["low", "medium", "high"]),
                        status="resolved" if (i % 3 != 0) else "assigned",
                        vehicle=t_log.vehicle,
                        driver=t_log.driver,
                        location_name="Saravanampatti Tech Corridor Junction",
                        description="Minor tire pressure sensor alert. Driver safely pulled aside into depot bay; standby cab deployed.",
                        reported_at=timezone.now() - datetime.timedelta(days=random.randint(1, 20)),
                        resolved_at=timezone.now() - datetime.timedelta(days=random.randint(0, 19))
                    )
                )
            CommuteIncident.objects.bulk_create(commute_incidents, ignore_conflicts=True)

            # ESG Carbon Metrics
            esg_metrics = []
            for i in range(380):
                t_log = created_trip_logs[i % len(created_trip_logs)]
                dist = Decimal(str(t_log.shift.route.distance_km or 25))
                p_cnt = t_log.passenger_count or 20
                v_cat_str = (t_log.vehicle.vehicle_category.code if t_log.vehicle.vehicle_category else "").lower()
                is_ev = ("ev" in v_cat_str)
                co2_emit = Decimal("0.00") if is_ev else (dist * Decimal("0.24")).quantize(Decimal("0.01"))
                co2_saved = (dist * Decimal(str(p_cnt)) * Decimal("0.16") - co2_emit).quantize(Decimal("0.01"))

                esg_metrics.append(
                    ESGCarbonMetric(
                        date=t_log.date,
                        vehicle=t_log.vehicle,
                        trip_log=t_log,
                        trip_km=dist,
                        passenger_count=p_cnt,
                        fuel_type="Electric" if is_ev else "Clean Diesel",
                        co2_emitted_kg=co2_emit,
                        co2_saved_kg=max(Decimal("0.00"), co2_saved),
                        green_efficiency_score=Decimal(str(random.randint(85, 99)))
                    )
                )
            ESGCarbonMetric.objects.bulk_create(esg_metrics, ignore_conflicts=True)

            # ==========================================================
            # 10. MAINTENANCE: COMPLIANCE DOCUMENTS FOR FLEET (3,500+ CERTS)
            # ==========================================================
            self.stdout.write("[*] Seeding Statutory Compliance Documents (FC, Speed Gov, AIS-140, Insurance, Permits) across commercial fleet...")
            compliance_docs = []
            doc_specs = [
                ("fc", "RTO Fitness Certificate (Rule 62 CMVR)", 365),
                ("speed_governor", "Speed Governor 80 km/h Calibration (AIS-018)", 365),
                ("ais140", "AIS-140 VLT & Emergency Panic Device Certificate", 365),
                ("insurance", "Commercial Passenger Vehicle Comprehensive Policy", 365),
                ("permit", "All India Tourist Permit (AITP Parivahan)", 365 * 3),
                ("tax", "Tamil Nadu Commercial Motor Vehicles Road Tax", 90),
                ("pollution", "PUC Emissions Compliance (BS-VI Mandate)", 180)
            ]

            # Generate documents for the first 500 vehicles to guarantee rich coverage across all models
            for v in vehicles[:550]:
                for doc_type, label, valid_days in doc_specs:
                    # Realistic expiry: 85% active, 10% near expiry, 5% expired for testing alerts
                    dice = random.random()
                    if dice < 0.05:
                        exp_date = today - datetime.timedelta(days=random.randint(2, 25))
                    elif dice < 0.15:
                        exp_date = today + datetime.timedelta(days=random.randint(5, 25))
                    else:
                        exp_date = today + datetime.timedelta(days=random.randint(60, valid_days))

                    iss_date = exp_date - datetime.timedelta(days=valid_days)

                    compliance_docs.append(
                        ComplianceDocument(
                            vehicle=v,
                            document_type=doc_type,
                            document_number=f"{doc_type.upper()}/{v.registration_number.replace(' ', '')}/{exp_date.year}",
                            issue_date=iss_date,
                            expiry_date=exp_date,
                            insurance_provider="ICICI Lombard General Insurance" if doc_type == "insurance" else "",
                            premium_amount=Decimal("42500.00") if doc_type == "insurance" else None,
                            coverage_type="Commercial Comprehensive 100% IDV" if doc_type == "insurance" else "",
                            permit_states="Tamil Nadu, Kerala, Karnataka, Andhra Pradesh, Puducherry" if doc_type == "permit" else ""
                        )
                    )

            ComplianceDocument.objects.bulk_create(compliance_docs, ignore_conflicts=True)

            # Spare Parts & Inventory
            self.stdout.write("[*] Seeding Workshop Spare Parts, Stock Movements, Service Records, and Snags...")
            parts_catalog = [
                ("SP-BRK-001", "Heavy Duty Ceramic Brake Pad Set (Front)", "brakes", "Toyota Innova Crysta / Hycross", "set", 18, 5, 3200, "Bin A-04"),
                ("SP-FLT-002", "Genuine Engine Oil Filter Cartridge", "filters", "Innova Crysta, Fortuner 2.8", "nos", 45, 12, 550, "Bin B-02"),
                ("SP-FLT-003", "Diesel Fuel Filter Element Assembly", "filters", "Force Urbania, Traveller 3350/4020", "nos", 28, 8, 920, "Bin B-06"),
                ("SP-OIL-004", "Castrol CRB Turbomax 15W-40 Synthetic Oil (20L Drum)", "lubricants", "Commercial Coaches & Travellers", "drum", 15, 4, 6800, "Bay Oil Float"),
                ("SP-DEF-005", "AdBlue DEF Aqueous Urea Solution (20L Can)", "fluids", "All BS-VI Diesel Coaches & MPVs", "can", 60, 20, 850, "Bay Fluid Yard"),
                ("SP-CLT-006", "Clutch Plate & Pressure Plate Assembly", "transmission", "Toyota Rumion / Ertiga 1.5L", "set", 12, 3, 5800, "Bin C-01"),
                ("SP-TYR-007", "Apollo EnduRace RA 295/80 R22.5 Tubeless Radial Tyre", "tyres", "BharatBenz 1017, Ashok Leyland Viking", "nos", 24, 6, 21500, "Tyre Storage Bay"),
                ("SP-BLT-008", "Heavy Duty Alternator V-Belt Set", "belts", "Force Traveller 4020 AC", "set", 32, 10, 750, "Bin D-03"),
                ("SP-SUS-009", "Front Gas-Charged Shock Absorber Strut", "suspension", "Toyota Innova Crysta", "pair", 14, 4, 4800, "Bin E-02"),
                ("SP-LGT-010", "Philips High Performance H4 LED Headlight Bulbs", "electrical", "All Passenger Fleet", "pair", 40, 10, 2100, "Bin F-01")
            ]

            parts_created = []
            for p in parts_catalog:
                obj, _ = SparePartItem.objects.get_or_create(
                    part_code=p[0],
                    defaults={
                        "name": p[1], "category": p[2], "applicable_models": p[3], "unit": p[4],
                        "current_stock": Decimal(str(p[5])), "minimum_reorder_level": Decimal(str(p[6])),
                        "unit_cost": Decimal(str(p[7])), "storage_bin": p[8], "is_active": True
                    }
                )
                parts_created.append(obj)

            # Part Stock Movements
            stock_movements = []
            for i in range(420):
                pt = random.choice(parts_created)
                v = vehicles[i % len(vehicles)]
                qty = Decimal(str(random.randint(1, 4)))
                tot = (qty * pt.unit_cost).quantize(Decimal("0.01"))

                stock_movements.append(
                    PartStockMovement(
                        part=pt,
                        movement_type=random.choice(["jobcard_issue", "purchase_receipt", "jobcard_issue"]),
                        quantity=qty,
                        unit_rate=pt.unit_cost,
                        total_amount=tot,
                        vehicle=v,
                        job_card_ref=f"JC-2026-{random.randint(10000, 99999)}",
                        issued_to_mechanic=random.choice(["S. Murugan", "R. Chandran", "K. Selvakumar", "M. Arumugam"]),
                        notes="Parts drawn from central warehouse for scheduled periodic maintenance overhaul."
                    )
                )
            PartStockMovement.objects.bulk_create(stock_movements, ignore_conflicts=True)

            # Service Records (Job Cards)
            service_records = []
            for i in range(520):
                v = vehicles[i % len(vehicles)]
                labor = Decimal(str(random.randint(1500, 8500)))
                parts_c = Decimal(str(random.randint(2500, 18500)))
                tot = labor + parts_c
                s_stat = random.choice(["completed", "completed", "in_progress", "quality_check"])

                service_records.append(
                    ServiceRecord(
                        job_card_number=f"JC-2026-{90000 + i}",
                        vehicle=v,
                        service_type=random.choice(["routine", "breakdown", "tyre", "accidental", "bodywork"]),
                        priority=random.choice(["medium", "high", "low"]),
                        status=s_stat,
                        mechanic_name=random.choice(["S. Murugan (Master Tech)", "R. Chandran (Electrical)", "K. Selvakumar (Brake Specialist)"]),
                        bay_number=f"Bay {random.randint(1, 8)}",
                        base_depot="Coimbatore Central Depot Workshop",
                        date=today - datetime.timedelta(days=random.randint(1, 90)),
                        odometer_reading=random.randint(30000, 220000),
                        garage_name="Sivagayathiri Fleet Central Workshop & Spares Depot",
                        description="Complete 20,000 km periodic service: oil change, brake pad inspection, AC filter renewal and wheel balancing.",
                        labor_charges=labor,
                        parts_total_cost=parts_c,
                        total_cost=tot
                    )
                )
            ServiceRecord.objects.bulk_create(service_records, ignore_conflicts=True)

            # Defect Tickets
            defects = []
            for i in range(85):
                v = vehicles[i % len(vehicles)]
                defects.append(
                    DefectTicket(
                        vehicle=v,
                        reported_by="Chauffeur Pre-Trip Inspection",
                        date_reported=today - datetime.timedelta(days=random.randint(1, 45)),
                        description=random.choice([
                            "Air conditioning cooling reduced under high engine load during hill climb.",
                            "Slight steering vibration observed at speeds between 65 km/h and 75 km/h.",
                            "Cabin reading light toggle switch loose on passenger row 2.",
                            "Rear right tyre valve cap missing; air pressure topped up to 34 PSI.",
                            "Wiper blade rubber squeaking during light monsoon drizzle."
                        ]),
                        status=random.choice(["resolved", "resolved", "open"]),
                        notes="Inspected by workshop supervisor and rectified."
                    )
                )
            DefectTicket.objects.bulk_create(defects, ignore_conflicts=True)

            # ==========================================================
            # 11. FINANCE: PETRO, FASTAG, FUEL, TOLL, PETTY CASH, GST INVOICES
            # ==========================================================
            self.stdout.write("[*] Seeding Finance Accounts, Fuel Records, FASTag Toll Deductions, and Corporate GST Invoices...")
            # Petro Accounts
            petro_bpc, _ = CorporatePetroAccount.objects.get_or_create(
                account_number="BPCL-FLEET-99210",
                defaults={"account_name": "BPCL SmartFleet Corporate Account", "balance": Decimal("350000.00"), "is_active": True}
            )
            petro_hpc, _ = CorporatePetroAccount.objects.get_or_create(
                account_number="HPCL-DRIVE-44120",
                defaults={"account_name": "HPCL DriveTrack Plus Corporate Fleet", "balance": Decimal("280000.00"), "is_active": True}
            )

            # FASTag Accounts
            fastag_icici, _ = CorporateFastagAccount.objects.get_or_create(
                account_number="FASTAG-ICICI-88129",
                defaults={"account_name": "ICICI Bank Corporate FASTag Fleet", "balance": Decimal("450000.00"), "is_active": True}
            )
            fastag_axis, _ = CorporateFastagAccount.objects.get_or_create(
                account_number="FASTAG-AXIS-77210",
                defaults={"account_name": "Axis Bank Commercial FASTag Wallet", "balance": Decimal("320000.00"), "is_active": True}
            )

            # Fuel Records (750+ Records)
            fuel_records = []
            stations = [
                ("BPCL COCO Avinashi Road, Coimbatore", petro_bpc),
                ("HPCL Highway King Sankari Bypass NH-544", petro_hpc),
                ("IndianOil Swagat Krishnagiri NH-44", petro_bpc),
                ("Shell Fuel Station Trichy Road Coimbatore", petro_hpc)
            ]
            for i in range(780):
                v = vehicles[i % len(vehicles)]
                tr = created_trips[i % len(created_trips)]
                st_name, p_acc = random.choice(stations)
                litres = Decimal(str(random.randint(35, 160)))
                rate = Decimal("93.80")
                tot = (litres * rate).quantize(Decimal("0.01"))
                f_date = today - datetime.timedelta(days=random.randint(0, 45))

                fuel_records.append(
                    FuelRecord(
                        vehicle=v,
                        trip=tr,
                        date=f_date,
                        opening_km=random.randint(20000, 180000),
                        closing_km=random.randint(180000, 180600),
                        petro_account=p_acc,
                        api_reference_number=f"PETRO-REF-{random.randint(100000, 999999)}",
                        fuel_quantity=litres,
                        fuel_price=tot,
                        fuel_station=st_name
                    )
                )
            FuelRecord.objects.bulk_create(fuel_records, ignore_conflicts=True)

            # FASTag Toll Deductions (850+ Toll Crossings)
            tolls = []
            toll_plazas = [
                ("Kaniyur Toll Plaza (Coimbatore NH-544)", 90),
                ("Vijayamangalam Toll Plaza (Tirupur NH-544)", 115),
                ("Vaiguntham Toll Plaza (Sankari / Salem NH-544)", 135),
                ("Thoppur Ghat Toll Plaza (Dharmapuri NH-44)", 160),
                ("Attibele Toll Plaza (Hosur NH-44)", 125),
                ("Samayapuram Toll Plaza (Trichy NH-45)", 140),
                ("Kodai Road Toll Plaza (Dindigul NH-83)", 95),
                ("Pampampallam Toll Plaza (Walayar Kerala NH-544)", 110)
            ]
            for i in range(880):
                v = vehicles[i % len(vehicles)]
                tr = created_trips[i % len(created_trips)]
                plaza_name, base_toll = random.choice(toll_plazas)
                amt = Decimal(str(base_toll))

                tolls.append(
                    FastagTollDeduction(
                        account=fastag_icici if (i % 2 == 0) else fastag_axis,
                        date=timezone.now() - datetime.timedelta(days=random.randint(0, 30), hours=random.randint(1, 23)),
                        vehicle=v,
                        trip=tr,
                        amount=amt,
                        toll_plaza=plaza_name
                    )
                )
            FastagTollDeduction.objects.bulk_create(tolls, ignore_conflicts=True)

            # Petty Cash Transactions
            petty_acc = PettyCashAccount.objects.first()
            if not petty_acc:
                petty_acc = PettyCashAccount.objects.create(account_name="Operations Central Desk Cash", current_balance=Decimal("150000.00"))

            petty_txns = []
            for i in range(420):
                tr = created_trips[i % len(created_trips)]
                amt = Decimal(str(random.randint(150, 2500)))
                petty_txns.append(
                    PettyCashTransaction(
                        voucher_number=f"PC-VOUCH-2026-{10000 + i}",
                        account=petty_acc,
                        transaction_type="expense",
                        category=random.choice(["driver_advance", "office_supplies", "tea_client", "highway_puncture", "rto_fees"]),
                        amount=amt,
                        balance_after=Decimal("125000.00"),
                        date=today - datetime.timedelta(days=random.randint(0, 30)),
                        recipient_or_vendor=tr.driver.name if tr.driver else "Highway Services",
                        trip=tr,
                        status="approved",
                        authorized_by=admin_user,
                        notes="Disbursed from desk cash float against verified statutory receipt."
                    )
                )
            PettyCashTransaction.objects.bulk_create(petty_txns, ignore_conflicts=True)

            # Corporate GST Invoices & Payments (420+ Invoices)
            invoices = []
            for i in range(430):
                p = corp_parties[i % len(corp_parties)] if corp_parties else parties[0]
                tr = created_trips[i % len(created_trips)]
                sub = Decimal(str(random.randint(25, 350) * 1000))
                cgst = (sub * Decimal("0.025")).quantize(Decimal("0.01"))
                sgst = (sub * Decimal("0.025")).quantize(Decimal("0.01"))
                tot_tax = cgst + sgst
                grand = sub + tot_tax
                p_status = random.choice(["paid", "paid", "partially_paid", "unpaid"])

                invoices.append(
                    CorporateGSTInvoice(
                        invoice_number=f"INV-SGT-2026-{10000 + i}",
                        invoice_date=today - datetime.timedelta(days=random.randint(1, 45)),
                        due_date=today + datetime.timedelta(days=random.randint(15, 30)),
                        invoice_type="regular_b2b",
                        party=p,
                        trip=tr,
                        supplier_legal_name="Sivagayathiri Tours and Travels Private Limited",
                        supplier_trade_name="Sivagayathiri Travels",
                        supplier_gstin="33AALCS8812K1ZT",
                        supplier_state_code="33",
                        supplier_address="1264 Trichy Road, Sungam Junction, Ramanathapuram, Coimbatore - 641045",
                        supplier_pincode="641045",
                        recipient_legal_name=p.name,
                        recipient_trade_name=p.name,
                        recipient_gstin="33AAACT1984Q1Z8",
                        recipient_state_code="33",
                        recipient_address=p.address or "TIDEL Park IT Special Economic Zone, Coimbatore",
                        recipient_pincode="641014",
                        place_of_supply="33-Tamil Nadu",
                        is_reverse_charge=False,
                        sac_code="996412",
                        supply_type="intra_state",
                        taxable_value=sub,
                        gst_rate_percent=Decimal("5.00"),
                        cgst_rate=Decimal("2.50"),
                        cgst_amount=cgst,
                        sgst_rate=Decimal("2.50"),
                        sgst_amount=sgst,
                        igst_rate=Decimal("0.00"),
                        igst_amount=Decimal("0.00"),
                        cess_amount=Decimal("0.00"),
                        total_tax=tot_tax,
                        round_off=Decimal("0.00"),
                        total_invoice_value=grand,
                        payment_status=p_status,
                        paid_amount=grand if p_status == "paid" else (grand / 2 if p_status == "partially_paid" else Decimal("0.00"))
                    )
                )
            CorporateGSTInvoice.objects.bulk_create(invoices, ignore_conflicts=True)
            created_invoices = list(CorporateGSTInvoice.objects.all().order_by("-id")[:430])

            # Invoice Line Items
            line_items = []
            for inv in created_invoices:
                line_items.append(
                    InvoiceLineItem(
                        invoice=inv,
                        item_description=f"Commercial Passenger Transport Service - {inv.party.name[:30]}",
                        sac_code="996412",
                        quantity=Decimal("1.00"),
                        unit="TRIP",
                        rate=inv.taxable_value,
                        taxable_amount=inv.taxable_value,
                        cgst_amount=inv.cgst_amount,
                        sgst_amount=inv.sgst_amount,
                        igst_amount=Decimal("0.00"),
                        total_amount=inv.total_invoice_value
                    )
                )
            InvoiceLineItem.objects.bulk_create(line_items, ignore_conflicts=True)

            # Payments
            payments = []
            for i, inv in enumerate([inv for inv in created_invoices if inv.payment_status in ["paid", "partially_paid"]]):
                payments.append(
                    Payment(
                        party=inv.party,
                        trip=inv.trip,
                        date=inv.invoice_date + datetime.timedelta(days=random.randint(2, 10)),
                        amount=inv.paid_amount,
                        payment_type="customer_receipt",
                        payment_mode=random.choice(["bank_transfer", "upi", "card", "cheque"]),
                        collected_by="Accounts Desk",
                        reference_number=f"NEFT/UTR/{random.randint(100000000, 999999999)}",
                        bank="HDFC Bank Commercial Escrow",
                        notes=f"Settlement against GST Invoice {inv.invoice_number}."
                    )
                )
            Payment.objects.bulk_create(payments, ignore_conflicts=True)

            # Customer Reviews & Complaints
            self.stdout.write("[*] Seeding 250+ Customer Reviews & 45+ Customer Service Complaints...")
            feedbacks = []
            for i in range(260):
                tr = created_trips[i % len(created_trips)]
                rating = random.choices([5, 4, 3], weights=[70, 25, 5])[0]
                feedbacks.append(
                    TripCustomerFeedback(
                        trip=tr,
                        customer_name=tr.guest_name or "Mr. S. Karthikeyan",
                        customer_phone=tr.booking.guest_phone if tr.booking else "+91 94433 11223",
                        feedback_token=f"FEED_{random.randint(100000, 999999)}",
                        overall_rating=rating,
                        driver_politeness_rating=rating,
                        vehicle_cleanliness_rating=rating,
                        ac_punctuality_rating=rating,
                        positive_tags="Clean Interior, Punctual Chauffeur, Smooth Driving, Sanitized Cab",
                        feedback_text=random.choice([
                            "Excellent journey! Chauffeur drove very smoothly across the 36 hairpin bends of Ooty.",
                            "Very professional service. Vehicle arrived 15 minutes before time, spotless interior and chilled water bottles.",
                            "Highly recommended for corporate family tours. Driver was extremely courteous and knowledgeable about local dining.",
                            "Outstanding comfort in the Force Urbania. Perfect trip for our 12-member extended family.",
                            "Great driving manners on the Salem highway. Chauffeur kept steady 80 km/h speed without harsh braking."
                        ]),
                        google_review_prompted=True,
                        google_review_clicked=(rating == 5)
                    )
                )
            TripCustomerFeedback.objects.bulk_create(feedbacks, ignore_conflicts=True)

            complaints = []
            for i in range(45):
                tr = created_trips[i % len(created_trips)]
                complaints.append(
                    TravelComplaint(
                        complaint_number=f"CMP-2026-{1000 + i}",
                        complainant_type="customer",
                        complainant_name=tr.guest_name or "Guest",
                        complainant_phone="+91 98401 23456",
                        complainant_email="complaints.guest@gmail.com",
                        category=random.choice(["chauffeur_conduct", "vehicle_condition", "delay_punctuality", "billing_fare"]),
                        severity=random.choice(["medium", "low", "high"]),
                        status=random.choice(["resolved", "resolved", "under_investigation"]),
                        related_booking=tr.booking,
                        issue_description=random.choice([
                            "AC cooling was slightly slow during steep ghat incline between Burliyar and Coonoor.",
                            "15-minute delay during morning pickup due to heavy traffic bottleneck at Gandhipuram signal.",
                            "Customer requested explanation for state border tax calculation on Kerala entry."
                        ]),
                        investigation_remarks="Operations desk contacted chauffeur and verified GPS telematics logs.",
                        resolution_notes="Explained statutory border rules; guest satisfied with prompt telephonic resolution.",
                        assigned_to=admin_user,
                        lodged_at=timezone.now() - datetime.timedelta(days=random.randint(2, 40)),
                        resolved_at=timezone.now() - datetime.timedelta(days=random.randint(0, 39))
                    )
                )
            TravelComplaint.objects.bulk_create(complaints, ignore_conflicts=True)

        # ==========================================================
        # 12. SYNCHRONIZE ALL POSTGRESQL TABLE SEQUENCES
        # ==========================================================
        self.stdout.write("[*] Synchronizing PostgreSQL primary key sequences across all seeded tables...")
        all_models = [
            Party, Client, Supplier, VehicleType, Vehicle, Driver,
            HotelMaster, MonumentEntranceMaster, ActivityMaster, GuideChargeMaster,
            B2CCustomerProfile, Inquiry, InquiryFollowUp, Quotation, QuotationDay, QuotationItem,
            TravelComplaint, TripCustomerFeedback,
            Booking, Trip, TripCashAdvanceEnvelope, InterstateBorderPermit,
            EcoSensitiveZoneEPass, GroupArrivalManifest, HighwayBreakdownSOS,
            DriverFatigueAuditLog, EmptyLegTripOffer, TrafficFine,
            VehicleTelematicsPing, DriverBehaviorLog,
            TransportContract, BaseRoute, BaseRouteStop, BaseShift, CommuterManifest,
            ContractTripLog, NightSafetyEscortLog, CommuterBoardingPass, CommuteIncident, ESGCarbonMetric,
            ComplianceDocument, SparePartItem, PartStockMovement, ServiceRecord, DefectTicket,
            CorporatePetroAccount, CorporateFastagAccount, FastagTollDeduction,
            FuelRecord, PettyCashAccount, PettyCashTransaction, CorporateGSTInvoice, InvoiceLineItem, Payment
        ]

        sql_reset_statements = connection.ops.sequence_reset_sql(no_style(), all_models)
        with connection.cursor() as cursor:
            for sql in sql_reset_statements:
                cursor.execute(sql)

        self.stdout.write(self.style.SUCCESS(
            "========================================================================\n"
            "[GOAL] SIVAGAYATHIRI ENTERPRISE DATABASE SEEDING COMPLETED SUCCESSFULLY!\n"
            "========================================================================\n"
            f"[OK] Fleet Assets: {Vehicle.objects.count()} Vehicles, {Driver.objects.count()} Chauffeurs\n"
            f"[OK] CRM Master: {HotelMaster.objects.count()} Hotels, {MonumentEntranceMaster.objects.count()} Monuments, {ActivityMaster.objects.count()} Activities\n"
            f"[OK] CRM Inquiries & Quotes: {Inquiry.objects.count()} Inquiries, {Quotation.objects.count()} Quotes, {QuotationDay.objects.count()} Tour Days\n"
            f"[OK] Operations: {Booking.objects.count()} Bookings, {Trip.objects.count()} Trips, {TripCashAdvanceEnvelope.objects.count()} Cash Envelopes\n"
            f"[OK] Statutory Border & Hills: {InterstateBorderPermit.objects.count()} Border Permits, {EcoSensitiveZoneEPass.objects.count()} Hill e-Passes\n"
            f"[OK] Ops Studios: {GroupArrivalManifest.objects.count()} PNR Manifests, {HighwayBreakdownSOS.objects.count()} SOS Tickets, {DriverFatigueAuditLog.objects.count()} Fatigue Logs\n"
            f"[OK] Empty Legs & Fines: {EmptyLegTripOffer.objects.count()} Empty Legs, {TrafficFine.objects.count()} E-Challans, {VehicleTelematicsPing.objects.count()} Telematics Pings\n"
            f"[OK] Fleet Commute: {TransportContract.objects.count()} Contracts, {BaseRoute.objects.count()} Routes, {BaseRouteStop.objects.count()} Stops, {ContractTripLog.objects.count()} Daily Commutes\n"
            f"[OK] Night Escorts & ESG: {NightSafetyEscortLog.objects.count()} Night Escorts, {CommuterBoardingPass.objects.count()} Boarding Passes, {ESGCarbonMetric.objects.count()} ESG Records\n"
            f"[OK] Maintenance: {ComplianceDocument.objects.count()} Compliance Certs, {SparePartItem.objects.count()} Parts, {ServiceRecord.objects.count()} Job Cards\n"
            f"[OK] Finance: {FuelRecord.objects.count()} Fuel Logs, {FastagTollDeduction.objects.count()} Toll Deductions, {CorporateGSTInvoice.objects.count()} GST Invoices, {Payment.objects.count()} Payments\n"
            "========================================================================"
        ))