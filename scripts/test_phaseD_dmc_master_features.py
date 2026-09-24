import os
import sys
import django
from decimal import Decimal
import datetime
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from core.models import Party, VehicleType
from operations.models import Booking
from finance.models import Payment
from crm.models import (
    SupplierProfile, FlightMaster, DmcDocument,
    TravelComplaint, SupplierPaymentRequisition, PartnerProfile
)
from crm.views import (
    api_master_data_lookup, dmc_documents_view, dmc_document_upload_api,
    complaints_console_view, complaint_lodge_view, complaint_resolve_api,
    payment_requisition_console_view, payment_requisition_create_view,
    payment_requisition_status_api, client_pending_payments_report_view,
    send_client_payment_reminder_api
)

User = get_user_model()

def test_phase_d_features():
    print("=" * 80)
    print("RUNNING DMC PHASE D ENTERPRISE VERIFICATION SUITE")
    print("=" * 80)

    factory = RequestFactory()
    admin_user, _ = User.objects.get_or_create(username='admin_dmc_test', defaults={'is_staff': True, 'is_superuser': True})

    # ---------------------------------------------------------
    # 1. Flight Master Data & Lookup
    # ---------------------------------------------------------
    print("\n[STEP 1] Testing Flight Master Data & Dynamic Schedules...")
    flight, _ = FlightMaster.objects.get_or_create(
        flight_number='6E-542',
        defaults={
            'airline': 'IndiGo Airlines',
            'origin_airport': 'CJB (Coimbatore)',
            'destination_airport': 'DEL (New Delhi)',
            'departure_time': datetime.time(6, 30),
            'arrival_time': datetime.time(9, 45),
            'operating_days': 'Daily',
            'cabin_class': 'economy',
            'baggage_allowance': '15 KG Check-in + 7 KG Cabin',
            'is_active': True
        }
    )
    print(f" -> Flight schedule registered: {flight}")

    req = factory.get('/crm/api/master-data/lookup/?query=Coimbatore')
    req.user = admin_user
    res = api_master_data_lookup(req)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = json.loads(res.content)
    assert 'flights' in data, "Flights key missing from master data lookup"
    assert any(f['flight_number'] == '6E-542' for f in data['flights']), "Flight 6E-542 not returned in search!"
    print(" -> SUCCESS: Master data API returned active flight schedules!")

    # ---------------------------------------------------------
    # 2. Document Management Vault
    # ---------------------------------------------------------
    print("\n[STEP 2] Testing Enterprise Document Vault Upload & Retrieval...")
    test_file = SimpleUploadedFile("ooty_package_brochure_2026.pdf", b"%PDF-1.4 dummy pdf binary stream", content_type="application/pdf")
    
    upload_req = factory.post('/crm/api/documents/upload/', {
        'title': 'Ooty 3N/4D Luxury Summer Brochure 2026',
        'category': 'brochure',
        'description': 'Official DMC luxury brochure featuring Nilgiri Mountain Railway',
        'document_file': test_file
    })
    upload_req.user = admin_user
    upload_res = dmc_document_upload_api(upload_req)
    assert upload_res.status_code == 200, f"Upload API failed: {upload_res.content}"
    upload_data = json.loads(upload_res.content)
    assert upload_data['status'] == 'success'
    doc_id = upload_data['document_id']
    print(f" -> Document #{doc_id} uploaded successfully: {upload_data['title']}")

    # Vault View
    view_req = factory.get('/crm/documents/?category=brochure')
    view_req.user = admin_user
    view_res = dmc_documents_view(view_req)
    assert view_res.status_code == 200
    print(" -> SUCCESS: Document Vault console rendered with category filters!")

    # ---------------------------------------------------------
    # 3. Complaint & Service Quality Management
    # ---------------------------------------------------------
    print("\n[STEP 3] Testing Grievance Lodging & Quality Audit...")
    supplier_party, _ = Party.objects.get_or_create(name='Sterling Ooty Fern Hill', defaults={'party_type': 'supplier'})
    supplier, _ = SupplierProfile.objects.get_or_create(
        party=supplier_party,
        defaults={'trade_name': 'Sterling Ooty Resort', 'destination_city': 'Ooty'}
    )

    lodge_req = factory.post('/crm/complaints/lodge/', {
        'complainant_name': 'Dr. Ramanathan Sundaram',
        'complainant_phone': '+91 98401 22334',
        'complainant_type': 'b2c_traveler',
        'category': 'hotel_quality',
        'severity': 'high',
        'issue_description': 'Hot water boiler malfunctioned at resort during chilly morning.',
        'supplier_involved': supplier.id
    })
    lodge_req.user = admin_user
    from django.contrib.messages.storage.fallback import FallbackStorage
    setattr(lodge_req, 'session', {})
    setattr(lodge_req, '_messages', FallbackStorage(lodge_req))
    lodge_res = complaint_lodge_view(lodge_req)
    assert lodge_res.status_code == 302

    complaint = TravelComplaint.objects.filter(complainant_name='Dr. Ramanathan Sundaram').latest('lodged_at')
    print(f" -> Complaint registered: {complaint.complaint_number} (Severity: {complaint.severity})")

    # Resolve Complaint with Supplier Rating Audit
    resolve_req = factory.post(f'/crm/api/complaints/{complaint.id}/resolve/', {
        'status': 'resolved',
        'investigation_remarks': 'Maintenance team repaired boiler heating element by 11:00 AM.',
        'resolution_notes': 'Complimentary buffet dinner provided to traveler family.',
        'supplier_rating': '4'
    })
    resolve_req.user = admin_user
    resolve_res = complaint_resolve_api(resolve_req, complaint.id)
    assert resolve_res.status_code == 200
    complaint.refresh_from_db()
    assert complaint.status == 'resolved'
    assert complaint.supplier_rating_awarded == 4
    print(f" -> SUCCESS: Complaint {complaint.complaint_number} resolved with 4-star supplier audit!")

    # ---------------------------------------------------------
    # 4. Supplier Payment Requisition & Margin Spread
    # ---------------------------------------------------------
    print("\n[STEP 4] Testing Accounts Payable Requisitions & Profit Margins...")
    create_req = factory.post('/crm/requisitions/create/', {
        'supplier': supplier.id,
        'amount_requested': '35000.00',
        'payment_type': 'advance',
        'cost_to_company': '35000.00',
        'cost_to_client': '52000.00',
        'invoice_number': 'STR-OOTY-998',
        'notes': '50% room block advance for October group tour'
    })
    create_req.user = admin_user
    setattr(create_req, 'session', {})
    setattr(create_req, '_messages', FallbackStorage(create_req))
    create_res = payment_requisition_create_view(create_req)
    assert create_res.status_code == 302

    req_obj = SupplierPaymentRequisition.objects.filter(invoice_number='STR-OOTY-998').latest('created_at')
    assert req_obj.gross_margin == Decimal('17000.00')
    print(f" -> Requisition created: {req_obj.requisition_number} (Buy: ₹{req_obj.cost_to_company}, Sell: ₹{req_obj.cost_to_client}, Margin: ₹{req_obj.gross_margin})")

    # Approve
    status_req = factory.post(f'/crm/api/requisitions/{req_obj.id}/update-status/', {'action': 'approve'})
    status_req.user = admin_user
    status_res = payment_requisition_status_api(status_req, req_obj.id)
    assert status_res.status_code == 200
    req_obj.refresh_from_db()
    assert req_obj.status == 'approved'
    print(f" -> Requisition {req_obj.requisition_number} status updated to: {req_obj.status}")

    # Disburse
    disburse_req = factory.post(f'/crm/api/requisitions/{req_obj.id}/update-status/', {
        'action': 'disburse',
        'transaction_reference': 'UTR202609249901'
    })
    disburse_req.user = admin_user
    disburse_res = payment_requisition_status_api(disburse_req, req_obj.id)
    assert disburse_res.status_code == 200
    req_obj.refresh_from_db()
    assert req_obj.status == 'disbursed'
    assert req_obj.transaction_reference == 'UTR202609249901'
    print(f" -> SUCCESS: Requisition disbursed with UTR {req_obj.transaction_reference}!")

    # ---------------------------------------------------------
    # 5. Client Pending Payments Aging & WhatsApp Reminders
    # ---------------------------------------------------------
    print("\n[STEP 5] Testing Client Pending Payment Aging & WhatsApp Balance Dispatch...")
    vtype, _ = VehicleType.objects.get_or_create(name='Innova Crysta 7S', defaults={'seating_capacity': 7})
    client_party, _ = Party.objects.get_or_create(name='Vikramaditya Hegde', defaults={'party_type': 'customer', 'phone': '+919988776655'})
    
    test_booking, _ = Booking.objects.get_or_create(
        booking_number='BK-2026-TEST-OVERDUE',
        defaults={
            'party': client_party,
            'guest_name': 'Vikramaditya Hegde',
            'guest_phone': '+919988776655',
            'pickup_location': 'Coimbatore Airport',
            'destination': 'Ooty & Coonoor Tour',
            'pickup_date': timezone.now().date() - datetime.timedelta(days=45),
            'drop_date': timezone.now().date() - datetime.timedelta(days=42),
            'pickup_time': datetime.time(8, 0),
            'journey_type': 'outstation',
            'vehicle_type': vtype,
            'pax_count': 4,
            'billing_type': 'package',
            'quoted_price': Decimal('48000.00'),
            'gst_rate': Decimal('5.00'),
            'status': 'confirmed'
        }
    )

    # Record partial receipt of 20,000 leaving 28,000 overdue
    Payment.objects.get_or_create(
        booking=test_booking,
        payment_type='customer_receipt',
        defaults={
            'amount': Decimal('20000.00'),
            'payment_mode': 'bank_transfer',
            'date': timezone.now().date() - datetime.timedelta(days=45),
            'party': client_party,
        }
    )

    # Aging report view
    aging_req = factory.get('/crm/reports/client-pending-payments/')
    aging_req.user = admin_user
    aging_res = client_pending_payments_report_view(aging_req)
    assert aging_res.status_code == 200
    print(" -> SUCCESS: Client Pending Payment Aging Report rendered successfully!")

    # Dispatch WhatsApp balance reminder
    reminder_req = factory.post('/crm/api/reports/send-payment-reminder/', {'booking_id': test_booking.id})
    reminder_req.user = admin_user
    reminder_res = send_client_payment_reminder_api(reminder_req)
    assert reminder_res.status_code == 200
    rem_data = json.loads(reminder_res.content)
    assert rem_data['status'] == 'success'
    assert rem_data['balance'] == 28000.0
    print(f" -> SUCCESS: WhatsApp balance reminder triggered for booking {rem_data['booking_number']} (Balance: ₹{rem_data['balance']:,.2f}) to {rem_data['dispatched_to']}!")

    print("\n" + "=" * 80)
    print("ALL DMC ENTERPRISE MASTER & OPERATIONS TESTS PASSED COMPLETELY! [100% OK]")
    print("=" * 80)

if __name__ == '__main__':
    test_phase_d_features()
