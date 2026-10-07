import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import django
from decimal import Decimal
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from django.test import Client
from django.contrib.auth import get_user_model
from packages.models import Package, PackageTemplate, CollegeIVExpedition, TourPassengerManifest
from operations.models import Trip
from core.models import Party, Vehicle, VehicleType, Driver
from finance.models import DriverAdvance, TripExpense, SupplierTripCost, DriverSettlement
from finance_treasury.models import TripProfitReport
from packages.manifest_autoassign import auto_assign_for_expedition

def run_simulation():
    print("================================================================================")
    print("      END-TO-END SIMULATION: FLY-BUS TOUR & TRIP CASH DESK SETTLEMENT          ")
    print("================================================================================")

    # 1. SETUP MASTER ENTITIES
    vtype, _ = VehicleType.objects.get_or_create(
        name="52-Seat Volvo AC Multi-Axle Coach",
        defaults={'seating_capacity': 52}
    )

    driver, _ = Driver.objects.get_or_create(
        name="Murugan K (Senior Captain)",
        defaults={'phone': '9842511111', 'license_number': 'TN38-2015-00445', 'status': 'active'}
    )

    college_party, _ = Party.objects.get_or_create(
        name="Dr. N.G.P. Arts and Science College",
        defaults={
            'party_type': 'corporate',
            'phone': '9842211223',
            'billing_cycle': 'trip',
        }
    )

    dmc_party, _ = Party.objects.get_or_create(
        name="Royal North Star Coaches New Delhi",
        defaults={
            'party_type': 'supplier',
            'phone': '9811022334',
            'billing_cycle': 'trip'
        }
    )

    outsourced_bus, _ = Vehicle.objects.get_or_create(
        registration_number="DL 01 AA 9988",
        defaults={
            'vehicle_type': vtype,
            'ownership_type': 'outsourced',
            'owner_party': dmc_party,
            'seating_capacity': 52,
            'status': 'available'
        }
    )

    # 2. CREATE FLY-BUS PACKAGE (Option 1)
    print("\n[STEP 1] Creating Fly-Bus Tour Package (Delhi-Agra Golden Triangle)...")
    pkg, _ = Package.objects.get_or_create(
        package_code="PKG-DEL-AGR-05D-FLY",
        defaults={
            'name': "5 DAYS / 4 NIGHTS DELHI - AGRA - JAIPUR GOLDEN TRIANGLE FLIGHT IV",
            'destination': "Delhi / Agra / Jaipur",
            'category': "college_iv",
            'transit_mode': "flight_coach",
            'duration_days': 5,
            'duration_nights': 4,
            'pricing_type': "per_person",
            'base_price': Decimal('8500.00'),
            'price_with_food': Decimal('8500.00'),
            'price_without_food': Decimal('6800.00'),
            'flight_estimate_per_pax': Decimal('9500.00'),
            'min_pax': 100,
            'complementary_staff_count': 4,
            'hotel_star_category': "3-Star Deluxe Hotel (Delhi & Agra)",
            'room_sharing_type': "4_sharing",
            'meal_plan': "AP",
            'vehicle_seating_desc': "2 x 52-Seater Luxury AC Destination Coaches",
            'inclusions': "Return Flight Coimbatore-Delhi-Coimbatore\nHotel stay 4 nights\nAll Meals Breakfast Lunch Dinner\nAC Coach for all transfers & sightseeing\nTour Manager\nEntry permits",
            'exclusions': "Monument camera fees\nPersonal shopping",
            'terms_and_conditions': "Original Aadhaar Card mandatory for airport security\nReporting 2 hours prior to departure at CJB Airport\nBaggage: 15kg checkin + 7kg cabin",
            'is_active': True
        }
    )
    print(f"  -> Package Created: {pkg.name}")
    print(f"  -> Transit Mode: {pkg.get_transit_mode_display()}")
    print(f"  -> Land Package (AP Plan): Rs. {pkg.price_with_food:,.2f}")
    print(f"  -> Flight Estimate Per Pax: Rs. {pkg.flight_estimate_per_pax:,.2f}")
    print(f"  -> Total Flight-Inclusive Rate: Rs. {pkg.price_with_food_flight_inclusive:,.2f}")

    # 3. CREATE COLLEGE IV EXPEDITION
    print("\n[STEP 2] Creating College IV Expedition for 100 Students + 4 Faculty...")
    iv, _ = CollegeIVExpedition.objects.get_or_create(
        college_name="Dr. N.G.P. Arts and Science College",
        department_and_batch="B.Com & BBA (Batch 2023-26)",
        defaults={
            'package': pkg,
            'faculty_incharge_name': "Dr. S. K. Ramesh (HOD)",
            'faculty_incharge_phone': "9842211223",
            'student_count_male': 60,
            'student_count_female': 40,
            'faculty_count': 4,
            'total_pax': 104,
            'transit_mode': 'flight_coach',
            'onward_transit_details': "IndiGo 6E-241 | CJB (08:30 AM) -> DEL (11:25 AM)",
            'return_transit_details': "IndiGo 6E-248 | DEL (07:45 PM) -> CJB (10:40 PM)",
            'transit_pnr_or_booking_ref': "IND-DEL-9842",
            'baggage_allowance': "15 kg Check-in + 7 kg Cabin per passenger",
            'reporting_terminal': "Coimbatore International Airport (CJB) - Terminal 1",
            'destination_city': "Delhi / Agra / Jaipur",
            'destination_coach_partner': "Royal North Star Coaches New Delhi (2 x 52-Seat Volvo AC)",
            'aadhaar_id_mandatory': True,
            'industry_visit_targets': "Mother Dairy Plant Patparganj & Maruti Suzuki Plant Manesar",
            'permission_status': 'approved',
            'bus_count': 2,
            'tour_manager_assigned': "Rithik CA / Anandh C",
            'has_dj_campfire': True,
            'start_date': datetime.date(2026, 10, 10),
            'end_date': datetime.date(2026, 10, 14),
            'status': 'confirmed'
        }
    )
    print(f"  -> Expedition Created: {iv}")
    print(f"  -> Flight Details: {iv.onward_transit_details} (PNR: {iv.transit_pnr_or_booking_ref})")

    # 4. POPULATE ROSTER & RUN AUTO-ASSIGNMENT
    print("\n[STEP 3] Generating Passenger Manifest & Auto-Assigning Coaches + Rooms...")
    TourPassengerManifest.objects.filter(iv_expedition=iv).delete()
    
    passengers_to_create = []
    # 4 Faculty
    for i in range(1, 5):
        gender = 'male' if i <= 2 else 'female'
        passengers_to_create.append(TourPassengerManifest(
            iv_expedition=iv,
            passenger_name=f"Prof. Faculty Staff {i}",
            gender=gender,
            category='faculty',
            aadhaar_number=f"3344-5500-000{i}",
            ticket_or_pnr_status="Confirmed",
            phone=f"984221100{i}"
        ))
    # 60 Boys
    for i in range(1, 61):
        passengers_to_create.append(TourPassengerManifest(
            iv_expedition=iv,
            passenger_name=f"Student Boy {i:02d}",
            roll_number=f"23BCM{i:03d}",
            gender='male',
            category='student',
            aadhaar_number=f"3344-1100-{i:04d}",
            ticket_or_pnr_status="Confirmed",
            phone=f"98423{i:05d}"
        ))
    # 40 Girls
    for i in range(1, 41):
        passengers_to_create.append(TourPassengerManifest(
            iv_expedition=iv,
            passenger_name=f"Student Girl {i:02d}",
            roll_number=f"23BBA{i:03d}",
            gender='female',
            category='student',
            aadhaar_number=f"3344-2200-{i:04d}",
            ticket_or_pnr_status="Confirmed",
            phone=f"98424{i:05d}"
        ))
    TourPassengerManifest.objects.bulk_create(passengers_to_create)
    print(f"  -> Created {len(passengers_to_create)} passengers in roster.")

    # Run auto-assign
    res = auto_assign_for_expedition(iv.id)
    print(f"  -> Auto-Assign Result: {res['total_passengers']} assigned across {res.get('n_buses', 2)} buses.")
    print(f"     Faculty: {res['faculty_assigned']} staff spread equally.")
    print(f"     Boys: {res['male_students_assigned']} | Girls: {res['female_students_assigned']}")
    
    # Check sample bus and room
    sample_p = TourPassengerManifest.objects.filter(iv_expedition=iv).first()
    print(f"  -> Sample Passenger: {sample_p.passenger_name} -> {sample_p.bus_assignment}, Seat {sample_p.seat_number}, Room {sample_p.room_sharing_number}, Aadhaar: {sample_p.aadhaar_number}")

    # 5. DISPATCH TO OPERATIONS (Option 3)
    print("\n[STEP 4] Dispatching Expedition to Operations (Trip Creation)...")
    paying_students = iv.student_count_male + iv.student_count_female
    total_rate = pkg.price_with_food + pkg.flight_estimate_per_pax # Rs 18,000/student
    total_revenue = total_rate * Decimal(paying_students) # Rs 18,00,000

    trip = Trip.objects.create(
        party=college_party,
        guest_name=f"{iv.college_name} ({iv.department_and_batch})",
        package=pkg,
        vehicle=outsourced_bus,
        driver=driver,
        pax_count=iv.total_pax,
        travel_pnr=iv.transit_pnr_or_booking_ref,
        start_date=iv.start_date,
        end_date=iv.end_date,
        days_count=5,
        billing_model='fixed',
        fixed_amount=total_revenue,
        driver_bata=Decimal('7500.00'), # 5 days x 1,500
        partner_handover_notes=f"Fly-Bus Convoy: 2 Buses in Delhi. Onward Flight: {iv.onward_transit_details}",
        status='assigned'
    )
    iv.linked_trip = trip
    iv.status = 'on_tour'
    iv.save(update_fields=['linked_trip', 'status'])
    print(f"  -> Operational Trip Created: {trip.trip_id}")
    print(f"  -> Fixed Billing Revenue: Rs. {trip.fixed_amount:,.2f} ({paying_students} students x Rs. {total_rate:,.2f})")
    print(f"  -> Expedition status updated to '{iv.status}' and linked to Trip #{trip.trip_id}")

    # 6. TRIP CASH DESK & DRIVER ADVANCES SETTLEMENT (Option 3)
    print("\n[STEP 5] Trip Cash Desk & Advances Settlement Integration...")
    
    # A. Corporate Cashier Advance
    advance = DriverAdvance.objects.create(
        driver=driver,
        trip=trip,
        date=datetime.date(2026, 10, 10),
        amount=Decimal('30000.00'),
        notes="Cash Desk Advance: Rs. 30,000 issued for Yamuna Expressway tolls, parking, and driver allowance"
    )
    print(f"  -> Driver Advance Issued: Rs. {advance.amount:,.2f} to {driver.name} (Linked to Trip {trip.trip_id})")

    # B. On-Road Trip Expenses
    e1 = TripExpense.objects.create(
        trip=trip,
        expense_type='toll',
        amount=Decimal('1850.00'),
        date=datetime.date(2026, 10, 11),
        description="Yamuna Expressway Toll (Both Ways Convoy)",
        paid_by='company',
        billable_to_customer=False
    )
    e2 = TripExpense.objects.create(
        trip=trip,
        expense_type='parking',
        amount=Decimal('600.00'),
        date=datetime.date(2026, 10, 12),
        description="Taj Mahal Agra Multi-Level Tourist Bus Parking",
        paid_by='company',
        billable_to_customer=False
    )
    e3 = TripExpense.objects.create(
        trip=trip,
        expense_type='permit',
        amount=Decimal('2500.00'),
        date=datetime.date(2026, 10, 10),
        description="Delhi NCR Commercial Tourist Vehicle Entry Permit",
        paid_by='company',
        billable_to_customer=False
    )
    print(f"  -> On-Road Expenses Logged: Tolls (Rs. {e1.amount}), Parking (Rs. {e2.amount}), Permit (Rs. {e3.amount})")
    print(f"     Total Company-Paid On-Road Expenses: Rs. {trip.company_paid_expenses:,.2f}")

    # C. Delhi Coach Supplier DMC Cost
    scost = SupplierTripCost.objects.create(
        trip=trip,
        supplier=dmc_party,
        vehicle=outsourced_bus,
        date=datetime.date(2026, 10, 10),
        amount=Decimal('140000.00'),
        description="Delhi & Golden Triangle 5-Day Coach Fleet Invoice (2 AC Coaches)"
    )
    print(f"  -> Destination DMC Supplier Cost Logged: Rs. {scost.amount:,.2f} ({dmc_party.name})")

    # D. Driver Settlement & Return of Unspent Advance
    # Batta: Rs. 7,500. Advance adjusted against batta: Rs. 7,500. Remainder Rs. 22,500 deposited back.
    settlement = DriverSettlement.objects.filter(driver=driver, trip=trip).first()
    if not settlement:
        settlement = DriverSettlement.objects.create(
            driver=driver,
            trip=trip,
            total_days=Decimal('5.00'),
            batta=Decimal('7500.00'),
        )
    settlement.advance_adjusted = Decimal('7500.00')
    settlement.settled_on = datetime.date(2026, 10, 15)
    settlement.save()
    trip.status = 'settled'
    trip.save(update_fields=['status'])
    print(f"  -> Driver Settlement Completed: Total Batta Rs. {settlement.batta:,.2f}, Adjusted: Rs. {settlement.advance_adjusted:,.2f}")
    print(f"  -> Trip #{trip.trip_id} status updated to 'settled'.")

    # 7. TRIP P&L REPORT RECONCILIATION
    print("\n[STEP 6] Live Trip Profit & Loss (P&L) Reconciliation...")
    report_trip = TripProfitReport.objects.get(pk=trip.pk)
    print(f"  -> Total Billing Revenue: Rs. {report_trip.total_amount:,.2f}")
    print(f"  -> Total Supplier Cost:  Rs. {report_trip.total_supplier_cost:,.2f}")
    print(f"  -> Total On-Road Costs:   Rs. {report_trip.company_paid_expenses:,.2f}")
    print(f"  -> Driver Batta Cost:    Rs. {report_trip.driver_bata:,.2f}")
    print(f"  -> NET PROFIT / MARGIN:   Rs. {report_trip.net_profit:,.2f}")
    assert report_trip.net_profit > 0, "Net profit must be positive!"
    print(f"  [SUCCESS] P&L verified! Net Margin: Rs. {report_trip.net_profit:,.2f} on {report_trip.guest_name}")

    # 8. QUOTATION TEMPLATE VERIFICATION
    print("\n[STEP 7] Verifying 5-Page Official Tour Proposal Quotation HTML...")
    admin_user = get_user_model().objects.filter(is_superuser=True).first()
    client = Client()
    if admin_user:
        client.force_login(admin_user)
    
    response = client.get(f"/packages/quote/{pkg.id}/")
    print(f"  -> Quotation Proposal View HTTP Status: {response.status_code}")
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    
    html_content = response.content.decode('utf-8')
    checks = [
        ("Flight + Destination Coach", "Transit Mode"),
        ("FLIGHT &amp; AIRLINE TRANSIT LOGISTICS", "Flight Logistics Card"),
        ("15 kg Check-in Baggage", "Baggage Allowance"),
        ("Mandatory Photo ID", "Aadhaar / ID Checklist"),
        ("OPTION A: LAND PACKAGE ONLY", "Dual Pricing Option A"),
        ("OPTION B: FULL INCLUSIVE", "Dual Pricing Option B"),
        ("8500", "Land AP Price"),
        ("18000", "Flight Inclusive Combined Price"),
        ("happy journey", "Footer")
    ]
    for pattern, desc in checks:
        found = pattern in html_content
        print(f"     {'[OK]' if found else '[FAIL]'} {desc}: '{pattern}'")
        assert found, f"Missing pattern: {pattern}"

    print("\n================================================================================")
    print("      ALL TESTS & SIMULATIONS PASSED WITH 100% SUCCESS!                        ")
    print("================================================================================")

if __name__ == '__main__':
    run_simulation()
