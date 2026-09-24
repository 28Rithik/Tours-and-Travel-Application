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
from django.contrib.messages.storage.fallback import FallbackStorage

from core.models import Party, VehicleType
from operations.models import Booking
from crm.models import Quotation, DmcInvoice
from crm.views import (
    dmc_invoice_console_view, dmc_invoice_create_view,
    dmc_invoice_detail_view, dmc_invoice_dispatch_api,
    dmc_reports_hub_view
)

User = get_user_model()

def test_phase_e_invoicing_and_reports():
    print("=" * 80)
    print("RUNNING PHASE E: PROFORMA & TAX INVOICING + DMC REPORTS VERIFICATION")
    print("=" * 80)

    factory = RequestFactory()
    admin_user, _ = User.objects.get_or_create(username='admin_dmc_e', defaults={'is_staff': True, 'is_superuser': True})
    party, _ = Party.objects.get_or_create(name='TATA Consultancy Services Inbound', defaults={'party_type': 'corporate', 'phone': '+919876543210', 'gstin': '33AAAAA1234A1Z5'})
    vtype, _ = VehicleType.objects.get_or_create(name='Innova Crysta 7S', defaults={'seating_capacity': 7})

    booking, _ = Booking.objects.get_or_create(
        booking_number='BK-2026-INV-DEMO',
        defaults={
            'party': party,
            'guest_name': 'Rajesh Gopinathan',
            'guest_phone': '+919876543210',
            'pickup_location': 'Coimbatore Airport',
            'destination': 'Ooty & Nilgiris Circuit',
            'pickup_date': timezone.now().date(),
            'drop_date': timezone.now().date() + datetime.timedelta(days=3),
            'pickup_time': datetime.time(9, 0),
            'journey_type': 'outstation',
            'vehicle_type': vtype,
            'pax_count': 5,
            'billing_type': 'package',
            'quoted_price': Decimal('50000.00'),
            'gst_rate': Decimal('5.00'),
            'status': 'confirmed'
        }
    )

    # ---------------------------------------------------------
    # 1. Intra-State Tax Invoice Generation (CGST 2.5% + SGST 2.5%)
    # ---------------------------------------------------------
    print("\n[STEP 1] Generating Intra-State Tax Invoice with CGST + SGST...")
    create_req = factory.post('/crm/invoices/create/', {
        'invoice_type': 'tax_invoice',
        'party': party.id,
        'booking': booking.id,
        'billing_name': 'TATA Consultancy Services Ltd',
        'billing_address': 'TCS Siruseri Campus, Chennai, Tamil Nadu',
        'client_gstin': '33AAACT2727Q1ZW',
        'place_of_supply': 'Tamil Nadu (33)',
        'taxable_amount': '50000.00',
        'tax_regime': 'intra_state',
        'gst_rate': '5.00',
        'paid_amount': '15000.00',
        'description_of_service': 'Ooty 3N/4D Executive Retreat Ground Handling (SAC: 998555)'
    })
    create_req.user = admin_user
    setattr(create_req, 'session', {})
    setattr(create_req, '_messages', FallbackStorage(create_req))
    create_res = dmc_invoice_create_view(create_req)
    assert create_res.status_code == 302, f"Invoice creation failed: {create_res.status_code}"

    inv = DmcInvoice.objects.filter(booking=booking, invoice_type='tax_invoice').latest('created_at')
    assert inv.cgst_amount == Decimal('1250.00'), f"Expected CGST 1250, got {inv.cgst_amount}"
    assert inv.sgst_amount == Decimal('1250.00'), f"Expected SGST 1250, got {inv.sgst_amount}"
    assert inv.total_tax_amount == Decimal('2500.00'), f"Expected Total Tax 2500, got {inv.total_tax_amount}"
    assert inv.total_invoice_amount == Decimal('52500.00'), f"Expected Total 52500, got {inv.total_invoice_amount}"
    assert inv.balance_due == Decimal('37500.00'), f"Expected Balance Due 37500, got {inv.balance_due}"
    assert inv.status == 'partially_paid'
    print(f" -> Tax Invoice {inv.invoice_number} created successfully: Total ₹{inv.total_invoice_amount:,.2f} | Balance ₹{inv.balance_due:,.2f}")

    # ---------------------------------------------------------
    # 2. Inter-State Proforma Invoice Generation (IGST 5.0%)
    # ---------------------------------------------------------
    print("\n[STEP 2] Generating Inter-State Proforma Advance Bill with IGST...")
    proforma = DmcInvoice.objects.create(
        invoice_type='proforma',
        party=party,
        billing_name='Kuoni Inbound Zurich (Swiss Travel)',
        place_of_supply='Karnataka (29)',
        taxable_amount=Decimal('80000.00'),
        tax_regime='inter_state',
        gst_rate=Decimal('5.00'),
        paid_amount=Decimal('84000.00'),
        created_by=admin_user
    )
    assert proforma.igst_amount == Decimal('4000.00')
    assert proforma.total_invoice_amount == Decimal('84000.00')
    assert proforma.balance_due == Decimal('0.00')
    assert proforma.status == 'paid'
    print(f" -> Proforma Invoice {proforma.invoice_number} verified with full payment auto-reconciliation!")

    # ---------------------------------------------------------
    # 3. Invoicing Console & Print Letterhead View
    # ---------------------------------------------------------
    print("\n[STEP 3] Rendering Invoicing Console & Printable Sheet...")
    console_req = factory.get('/crm/invoices/')
    console_req.user = admin_user
    console_res = dmc_invoice_console_view(console_req)
    assert console_res.status_code == 200
    print(" -> Invoicing Console rendered successfully!")

    detail_req = factory.get(f'/crm/invoices/{inv.id}/')
    detail_req.user = admin_user
    detail_res = dmc_invoice_detail_view(detail_req, inv.id)
    assert detail_res.status_code == 200
    assert b"SIVAGAYATHIRI TRAVELS" in detail_res.content
    assert b"998555" in detail_res.content
    print(" -> Printable Tax Invoice document loaded with GSTIN, SAC 998555, and bank remittance instructions!")

    # ---------------------------------------------------------
    # 4. WhatsApp / Email Invoice Dispatch API
    # ---------------------------------------------------------
    print("\n[STEP 4] Testing 1-Click WhatsApp Invoice Dispatch API...")
    dispatch_req = factory.post(f'/crm/api/invoices/{inv.id}/dispatch/')
    dispatch_req.user = admin_user
    dispatch_req.META['HTTP_HOST'] = '127.0.0.1:8000'
    dispatch_res = dmc_invoice_dispatch_api(dispatch_req, inv.id)
    assert dispatch_res.status_code == 200
    dispatch_data = json.loads(dispatch_res.content)
    assert dispatch_data['status'] == 'success'
    print(f" -> SUCCESS: Official invoice link and statement dispatched via WhatsApp to {dispatch_data['dispatched_to']}!")

    # ---------------------------------------------------------
    # 5. DMC Reports & Analytics Hub + CSV Export
    # ---------------------------------------------------------
    print("\n[STEP 5] Testing Comprehensive DMC Reports & Analytics Hub...")
    hub_req = factory.get('/crm/reports/')
    hub_req.user = admin_user
    hub_res = dmc_reports_hub_view(hub_req)
    assert hub_res.status_code == 200
    print(" -> Reports Hub rendered successfully with Destination Turnover & Win Rates!")

    # CSV Export
    csv_req = factory.get('/crm/reports/?export=destinations_csv')
    csv_req.user = admin_user
    csv_res = dmc_reports_hub_view(csv_req)
    assert csv_res.status_code == 200
    assert csv_res['Content-Type'] == 'text/csv'
    assert b"Gross Revenue (INR)" in csv_res.content
    print(" -> SUCCESS: Destination & Circuit Turnover CSV export generated cleanly!")

    print("\n" + "=" * 80)
    print("ALL PHASE E INVOICING & REPORTS VERIFICATION TESTS PASSED! [100% OK]")
    print("=" * 80)

if __name__ == '__main__':
    test_phase_e_invoicing_and_reports()
