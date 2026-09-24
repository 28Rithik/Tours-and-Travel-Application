import os
import sys
import datetime
from decimal import Decimal
import django

# Setup environment
sys.stdout.reconfigure(encoding='utf-8')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth.models import User
from django.test import Client as HttpClient
from core.models import Client, VehicleType
from operations.models import Booking
from crm.models import (
    Inquiry, InquiryFollowUp, CommunicationLog,
    HotelMaster, MonumentEntranceMaster, ActivityMaster, GuideChargeMaster,
    Quotation, QuotationDay, QuotationItem
)

def run_tests():
    print("=" * 80)
    print("🚀 PHASE A VALIDATION: CRM QUERY TRACKER 2.0 & DYNAMIC QUOTATION BUILDER")
    print("=" * 80)

    # Setup User & Client
    user, _ = User.objects.get_or_create(username='crm_admin', defaults={'email': 'admin@travelerp.com', 'is_staff': True})
    user.set_password('AdminPass123!')
    user.save()

    client_party, _ = Client.objects.get_or_create(
        name="Southern Escapes Tours & Travels",
        defaults={
            'phone': "9876543210",
            'email': "karthik@southernescapes.com",
            'party_type': 'travel_agency'
        }
    )

    vtype, _ = VehicleType.objects.get_or_create(
        name="Innova Crysta AC",
        defaults={'seating_capacity': 7}
    )

    # --------------------------------------------------------------------------
    # TEST 1: Query Tracker 2.0 & SLA TAT Calculation
    # --------------------------------------------------------------------------
    print("\n[TEST 1] Query Tracker 2.0 & SLA Turnaround Time (TAT) Calculation...")
    now = timezone.now()
    
    # Create Urgent Inquiry (Target TAT = 2 hours)
    inq_urgent = Inquiry.objects.create(
        party=client_party,
        guest_name="Anand Sharma & Family",
        guest_phone="9887766554",
        guest_email="anand.sharma@gmail.com",
        pickup_location="Coimbatore Airport (CJB)",
        destination="Ooty & Coonoor",
        pickup_date=datetime.date.today() + datetime.timedelta(days=10),
        pickup_time=datetime.time(9, 30),
        drop_date=datetime.date.today() + datetime.timedelta(days=13),
        adult_count=4,
        child_count=2,
        priority='urgent',
        source='whatsapp',
        assigned_to=user,
        target_tat_hours=2
    )

    assert inq_urgent.tat_deadline is not None, "TAT deadline must be auto-computed on save."
    expected_deadline_approx = now + datetime.timedelta(hours=2)
    diff_minutes = abs((inq_urgent.tat_deadline - expected_deadline_approx).total_seconds()) / 60
    assert diff_minutes < 5, f"TAT deadline calculation drifted: {diff_minutes} mins"
    assert not inq_urgent.is_overdue, "Brand new inquiry should not be overdue."
    assert inq_urgent.tat_remaining_hours > 0, "Remaining hours should be > 0."

    # Test Follow-up interaction scheduler
    followup = InquiryFollowUp.objects.create(
        inquiry=inq_urgent,
        performed_by=user,
        interaction_type='phone',
        notes="Called guest Anand. Discussed 3-star vs 4-star hotel options in Ooty.",
        next_action="Prepare 3D/2N quote with Sterling Fern Hill",
        is_done=True
    )
    assert inq_urgent.follow_ups.count() >= 1, "Follow-up must be linked to inquiry."
    print("  ✓ SLA TAT deadline automatically calculated (2h for Urgent).")
    print("  ✓ In-pipeline inquiry priority, remaining TAT hours, and follow-up history verified.")

    # --------------------------------------------------------------------------
    # TEST 2: Travel Master Data (Hotels, Monuments, Activities, Guides)
    # --------------------------------------------------------------------------
    print("\n[TEST 2] Travel Master Data Repositories...")
    hotel = HotelMaster.objects.create(
        name="Sterling Fern Hill Resort",
        destination="Ooty",
        star_category="4_star",
        room_type="Classic Valley View Room",
        ep_rate=Decimal('3500.00'),
        cp_rate=Decimal('4200.00'),
        map_rate=Decimal('5400.00'),
        ap_rate=Decimal('6500.00'),
        extra_bed_rate=Decimal('1000.00'),
        peak_surge_percent=Decimal('25.00')
    )
    assert hotel.cp_rate == Decimal('4200.00')

    monument = MonumentEntranceMaster.objects.create(
        name="Government Botanical Garden",
        destination="Ooty",
        domestic_adult_rate=Decimal('50.00'),
        domestic_child_rate=Decimal('30.00'),
        foreigner_adult_rate=Decimal('100.00')
    )
    assert monument.domestic_adult_rate == Decimal('50.00')

    activity = ActivityMaster.objects.create(
        name="Ooty Lake Motor Boating",
        destination="Ooty",
        pricing_type="per_boat_vehicle",
        standard_rate=Decimal('750.00'),
        duration_minutes=30
    )
    assert activity.standard_rate == Decimal('750.00')

    guide = GuideChargeMaster.objects.create(
        destination="Ooty",
        language="english",
        half_day_rate=Decimal('1200.00'),
        full_day_rate=Decimal('2000.00')
    )
    assert guide.full_day_rate == Decimal('2000.00')
    print("  ✓ HotelMaster (EP/CP/MAP/AP rates & peak surge) operational.")
    print("  ✓ MonumentEntranceMaster (Domestic/Foreigner tariff) operational.")
    print("  ✓ ActivityMaster & GuideChargeMaster operational.")

    # --------------------------------------------------------------------------
    # TEST 3: Dynamic Day-by-Day Quotation Builder & Costing Engine
    # --------------------------------------------------------------------------
    print("\n[TEST 3] Dynamic Quotation Costing Engine & Markup Breakdown...")
    quotation = Quotation.objects.create(
        inquiry=inq_urgent,
        party=client_party,
        guest_name="Anand Sharma",
        guest_phone="9887766554",
        guest_email="anand.sharma@gmail.com",
        title="Ooty & Nilgiris Scenic Retreat 3D/2N",
        destination="Ooty",
        start_date=datetime.date.today() + datetime.timedelta(days=10),
        end_date=datetime.date.today() + datetime.timedelta(days=12),
        pax_count=4,
        vehicle_type=vtype,
        vehicle_count=1,
        markup_percent=Decimal('15.00'),
        gst_rate=Decimal('5.00'),
        created_by=user
    )

    assert quotation.duration_days == 3, f"Expected 3 days, got {quotation.duration_days}"
    assert quotation.duration_nights == 2, f"Expected 2 nights, got {quotation.duration_nights}"

    # Day 1
    day1 = QuotationDay.objects.create(
        quotation=quotation,
        day_number=1,
        title="Day 1: Arrival & Ooty Local Sightseeing",
        description="Pick up from Coimbatore Airport, scenic drive to Ooty via Mettupalayam. Visit Botanical Garden & Lake.",
        hotel=hotel,
        hotel_meal_plan='CP',
        overnight_destination="Ooty"
    )

    # Day 2
    day2 = QuotationDay.objects.create(
        quotation=quotation,
        day_number=2,
        title="Day 2: Coonoor & Tea Gardens Tour",
        description="Excursion to Sim's Park, Dolphin's Nose, and Highfield Tea Factory with tea tasting.",
        hotel=hotel,
        hotel_meal_plan='CP',
        overnight_destination="Ooty"
    )

    # Line Items
    # 1. Transport (3 days car hire @ 4500/day = 13500)
    item_trans = QuotationItem.objects.create(
        quotation=quotation,
        day=day1,
        category='transport',
        item_name="Innova Crysta AC Tourist Cab (3 Days Chauffeur Driven)",
        quantity=3,
        unit_cost=Decimal('4500.00'),
        total_cost=Decimal('13500.00')
    )

    # 2. Hotel (2 rooms x 2 nights x 4200 = 16800)
    item_hotel1 = QuotationItem.objects.create(
        quotation=quotation,
        day=day1,
        category='hotel',
        item_name=f"{hotel.name} (2 Rooms - CP Plan - Night 1)",
        quantity=2,
        unit_cost=Decimal('4200.00'),
        total_cost=Decimal('8400.00')
    )
    item_hotel2 = QuotationItem.objects.create(
        quotation=quotation,
        day=day2,
        category='hotel',
        item_name=f"{hotel.name} (2 Rooms - CP Plan - Night 2)",
        quantity=2,
        unit_cost=Decimal('4200.00'),
        total_cost=Decimal('8400.00')
    )

    # 3. Monuments (4 adults x 50 = 200)
    item_monu = QuotationItem.objects.create(
        quotation=quotation,
        day=day1,
        category='monument',
        item_name="Botanical Garden Adult Entry",
        quantity=4,
        unit_cost=Decimal('50.00'),
        total_cost=Decimal('200.00')
    )

    # 4. Activities (1 boat = 750)
    item_act = QuotationItem.objects.create(
        quotation=quotation,
        day=day1,
        category='activity',
        item_name="Ooty Lake Motor Boating",
        quantity=1,
        unit_cost=Decimal('750.00'),
        total_cost=Decimal('750.00')
    )

    # 5. Guide (1 full day guide = 2000)
    item_guide = QuotationItem.objects.create(
        quotation=quotation,
        day=day2,
        category='guide',
        item_name="English Speaking Coonoor Guide",
        quantity=1,
        unit_cost=Decimal('2000.00'),
        total_cost=Decimal('2000.00')
    )

    # Recalculate
    quotation.recalculate_totals()

    # Net cost should be 13500 + 8400 + 8400 + 200 + 750 + 2000 = 33250
    expected_net = Decimal('33250.00')
    assert quotation.net_cost == expected_net, f"Net cost mismatch: got {quotation.net_cost}, expected {expected_net}"

    # Markup 15% on 33250 = 4987.50
    expected_markup = Decimal('4987.50')
    assert quotation.markup_amount == expected_markup, f"Markup mismatch: got {quotation.markup_amount}, expected {expected_markup}"

    # Gross price = 33250 + 4987.50 = 38237.50
    expected_gross = Decimal('38237.50')
    assert quotation.gross_price == expected_gross, f"Gross price mismatch: got {quotation.gross_price}, expected {expected_gross}"

    # GST 5% on 38237.50 = 1911.88
    expected_gst = Decimal('1911.88')
    assert quotation.gst_amount == expected_gst, f"GST mismatch: got {quotation.gst_amount}, expected {expected_gst}"

    # Total quoted price = 38237.50 + 1911.88 = 40149.38
    expected_total = Decimal('40149.38')
    assert quotation.total_quoted_price == expected_total, f"Total mismatch: got {quotation.total_quoted_price}, expected {expected_total}"

    # Per pax price for 4 pax = round(40149.38 / 4, 2)
    expected_per_pax = round(quotation.total_quoted_price / Decimal('4'), 2)
    assert quotation.per_pax_price == expected_per_pax, f"Per pax price mismatch: {quotation.per_pax_price} vs {expected_per_pax}"

    print(f"  ✓ Net Supplier Cost: ₹{quotation.net_cost:,.2f}")
    print(f"  ✓ Agency Markup (15%): ₹{quotation.markup_amount:,.2f}")
    print(f"  ✓ GST (5%): ₹{quotation.gst_amount:,.2f}")
    print(f"  ✓ Total Quoted Price: ₹{quotation.total_quoted_price:,.2f} (₹{quotation.per_pax_price:,.2f}/pax)")

    # --------------------------------------------------------------------------
    # TEST 4: Revision Versioning Engine (Cloning v1 -> v2)
    # --------------------------------------------------------------------------
    print("\n[TEST 4] Quotation Revision Versioning (v1 -> v2)...")
    quotation_v2 = quotation.create_revision()
    assert quotation_v2.version == 2, f"Expected version 2, got {quotation_v2.version}"
    assert '-v2' in quotation_v2.quotation_number, f"Expected -v2 in number, got {quotation_v2.quotation_number}"
    assert quotation_v2.parent_quotation == quotation
    assert quotation_v2.days.count() == 2, "Cloned quote must have 2 days."
    assert quotation_v2.items.count() == 6, "Cloned quote must have 6 items."
    assert quotation_v2.total_quoted_price == quotation.total_quoted_price, "Cloned totals must match original."
    print(f"  ✓ Revision created successfully: {quotation_v2.quotation_number} (v{quotation_v2.version})")
    print(f"  ✓ Preserved {quotation_v2.days.count()} days and {quotation_v2.items.count()} line items.")

    # --------------------------------------------------------------------------
    # TEST 5: 1-Click Conversion to Active Core Booking
    # --------------------------------------------------------------------------
    print("\n[TEST 5] 1-Click Conversion: Quotation -> Active Operations Booking...")
    booking = quotation.convert_to_booking(user=user)
    assert booking is not None, "Booking must be created."
    assert booking.billing_type == 'package', "Booking billing type must be 'package'."
    assert booking.quoted_price == quotation.total_quoted_price, "Booking price must match quotation price."
    assert booking.status == 'confirmed', "Booking must be confirmed upon conversion."
    
    quotation.refresh_from_db()
    assert quotation.status == 'converted', "Quotation status must update to 'converted'."
    assert quotation.booking == booking, "Quotation must link to newly created booking."

    inq_urgent.refresh_from_db()
    assert inq_urgent.status == 'won', f"Inquiry status should be 'won', got {inq_urgent.status}"
    print(f"  ✓ Converted to Booking: #{booking.booking_number} ({booking.guest_name})")
    print(f"  ✓ Booking Amount: ₹{booking.quoted_price:,.2f}")
    print(f"  ✓ Inquiry status automatically updated to 'won'.")

    # --------------------------------------------------------------------------
    # TEST 6: Automated Customer WhatsApp & Email Signals
    # --------------------------------------------------------------------------
    print("\n[TEST 6] Automated Customer Dispatch Signals (WhatsApp / Email)...")
    # Verify acknowledgment communication logged for inq_urgent
    comm = CommunicationLog.objects.filter(client=client_party).first()
    assert comm is not None, "Automated communication log must be created on inquiry save."
    assert comm.comm_type in ['whatsapp', 'email']
    print(f"  ✓ Automated acknowledgment logged: {comm.comm_type} to {comm.client.name}")

    # Mark quotation_v2 as 'sent'
    quotation_v2.status = 'sent'
    quotation_v2.save(update_fields=['status'])
    # Signal triggers proposal link dispatch
    sent_comm = CommunicationLog.objects.filter(client=client_party, message_content__icontains='customized tour proposal').first()
    assert sent_comm is not None, "Proposal dispatch must be logged when quotation is marked as sent."
    print(f"  ✓ Automated proposal dispatch link logged on status 'sent'.")

    # --------------------------------------------------------------------------
    # TEST 7: HTTP Views Validation & Autocomplete Endpoints
    # --------------------------------------------------------------------------
    print("\n[TEST 7] HTTP Endpoints & Client Proposals...")
    http = HttpClient()
    http.force_login(user)

    # 1. Pipeline
    resp = http.get('/crm/queries/')
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert b"Inquiry Pipeline" in resp.content or b"Query Tracker" in resp.content
    print("  ✓ GET /crm/queries/ -> 200 OK (Pipeline View rendered)")

    # 2. Quotation Create
    resp = http.get('/crm/quotations/new/')
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    print("  ✓ GET /crm/quotations/new/ -> 200 OK (Quotation Studio rendered)")

    # 3. Quotation Builder Edit
    resp = http.get(f'/crm/quotations/{quotation.id}/edit/')
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    print(f"  ✓ GET /crm/quotations/{quotation.id}/edit/ -> 200 OK")

    # 4. Quotation Client Proposal Preview
    resp = http.get(f'/crm/quotations/{quotation.id}/preview/')
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert b"Tailor-Made Tour Proposal" in resp.content or b"Sivagayathiri Travels" in resp.content
    print(f"  ✓ GET /crm/quotations/{quotation.id}/preview/ -> 200 OK (Client Proposal Preview rendered)")

    # 5. Master Data Autocomplete API
    resp = http.get('/crm/api/master-data/lookup/?destination=Ooty')
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert 'hotels' in data and 'monuments' in data and 'activities' in data and 'guides' in data
    assert any(h['name'] == hotel.name for h in data['hotels'])
    assert any(m['name'] == monument.name for m in data['monuments'])
    print("  ✓ GET /crm/api/master-data/lookup/?destination=Ooty -> 200 OK (Autocomplete JSON verified)")

    print("\n" + "=" * 80)
    print("🎉 ALL PHASE A VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == '__main__':
    run_tests()
