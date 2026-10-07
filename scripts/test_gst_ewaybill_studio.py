import os
import sys

# Ensure UTF-8 stdout on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import json
from decimal import Decimal
import django

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import Party, Vehicle, Driver
from operations.models import Trip, Booking
from finance.models import (
    CorporateGSTInvoice,
    InvoiceLineItem,
    EWayBill,
    Account,
    JournalEntry,
    JournalItem,
)
from finance.gst_engine import (
    INDIAN_GST_STATES,
    TRANSPORT_SAC_CODES,
    calculate_invoice_taxes,
    validate_gstin,
    generate_b2b_qr_code,
    generate_nic_eway_bill_json,
    validate_nic_eway_bill_payload,
    post_invoice_to_general_ledger,
    get_multistate_gst_audit_summary,
    get_state_name,
)

User = get_user_model()


def run_tests():
    print("=" * 80)
    print("[*] CORPORATE GST B2B INVOICING & NIC E-WAY BILL STUDIO -- AUTOMATED TEST SUITE")
    print("=" * 80)

    checks_passed = 0
    total_checks = 0

    def assert_check(condition, label):
        nonlocal checks_passed, total_checks
        total_checks += 1
        if condition:
            checks_passed += 1
            print(f"  [PASS] {label}")
        else:
            print(f"  [FAIL] {label}")
            sys.exit(1)

    # --------------------------------------------------------------------------
    # STAGE 1: GST Calculation Engine
    # --------------------------------------------------------------------------
    print("\n--- [STAGE 1] Testing GST Calculation Engine ---")
    
    # 1. Intra-State (TN to TN @ 5%)
    res_intra = calculate_invoice_taxes(Decimal('10000.00'), Decimal('5.00'), supplier_state='33', recipient_state='33')
    assert_check(res_intra['supply_type'] == 'intra_state', "Intra-state classified correctly for TN to TN")
    assert_check(res_intra['cgst_rate'] == Decimal('2.50'), "CGST rate is 2.5%")
    assert_check(res_intra['sgst_rate'] == Decimal('2.50'), "SGST rate is 2.5%")
    assert_check(res_intra['igst_amount'] == Decimal('0.00'), "IGST is 0 for intra-state")
    assert_check(res_intra['cgst_amount'] == Decimal('250.00'), "CGST amount is ₹250.00")
    assert_check(res_intra['sgst_amount'] == Decimal('250.00'), "SGST amount is ₹250.00")
    assert_check(res_intra['total_invoice_value'] == Decimal('10500.00'), "Total invoice value is ₹10,500.00")

    # 2. Inter-State (TN to KA @ 5%)
    res_inter = calculate_invoice_taxes(Decimal('10000.00'), Decimal('5.00'), supplier_state='33', recipient_state='29')
    assert_check(res_inter['supply_type'] == 'inter_state', "Inter-state classified correctly for TN to KA")
    assert_check(res_inter['cgst_amount'] == Decimal('0.00'), "CGST is 0 for inter-state")
    assert_check(res_inter['sgst_amount'] == Decimal('0.00'), "SGST is 0 for inter-state")
    assert_check(res_inter['igst_amount'] == Decimal('500.00'), "IGST amount is ₹500.00")
    assert_check(res_inter['total_invoice_value'] == Decimal('10500.00'), "Total invoice value is ₹10,500.00")

    # 3. Round-Off Precision
    res_round = calculate_invoice_taxes(Decimal('333.33'), Decimal('5.00'), supplier_state='33', recipient_state='33')
    assert_check(res_round['total_invoice_value'] == Decimal('350.00'), "Round off correctly rounded ₹349.9965 to ₹350.00")
    assert_check(res_round['round_off'] != 0, "Round off difference captured")

    # --------------------------------------------------------------------------
    # STAGE 2: GSTIN Anomaly Detector & Validation
    # --------------------------------------------------------------------------
    print("\n--- [STAGE 2] Testing GSTIN Validation & Anomaly Detection ---")
    
    valid_tn_gstin = "33AAAAA0000A1Z5"
    is_valid, msg = validate_gstin(valid_tn_gstin, expected_state_code='33')
    assert_check(is_valid, f"Valid TN GSTIN accepted: {valid_tn_gstin}")

    valid_ka_gstin = "29BBBBB1111B1Z2"
    is_valid, msg = validate_gstin(valid_ka_gstin, expected_state_code='29')
    assert_check(is_valid, f"Valid KA GSTIN accepted: {valid_ka_gstin}")

    # State mismatch
    is_valid, msg = validate_gstin(valid_ka_gstin, expected_state_code='33')
    assert_check(not is_valid and "mismatch" in msg.lower(), "Flagged state code mismatch when KA GSTIN used for TN")

    # Invalid format
    is_valid, msg = validate_gstin("INVALID_GSTIN_123")
    assert_check(not is_valid, "Flagged invalid format GSTIN")

    # --------------------------------------------------------------------------
    # STAGE 3: Corporate GST Invoice & E-Way Bill Model Creation
    # --------------------------------------------------------------------------
    print("\n--- [STAGE 3] Testing Invoice & E-Way Bill Creation ---")

    admin_user, _ = User.objects.get_or_create(username='admin', defaults={'is_staff': True, 'is_superuser': True})
    party, _ = Party.objects.get_or_create(
        name="Wipro Technologies Bengaluru",
        defaults={
            'party_type': 'corporate',
            'phone': '9845011223',
            'email': 'transport@wipro.com',
            'gstin': '29AAAAW1234A1Z8',
            'state_code': '29',
            'address': 'Sarjapur Road, Doddakannelli, Bengaluru, Karnataka 560035',
        }
    )

    vehicle, _ = Vehicle.objects.get_or_create(
        registration_number="KA01MJ8888",
        defaults={'brand': 'Toyota', 'model': 'Innova Crysta', 'seating_capacity': 7}
    )

    invoice = CorporateGSTInvoice.objects.create(
        party=party,
        invoice_type='regular_b2b',
        supplier_legal_name="Siva Gayathiri Tours & Travels",
        supplier_trade_name="Sivagayathiri Travels",
        supplier_gstin="33AAAAA0000A1Z5",
        supplier_state_code="33",
        supplier_address="12/4, Gandhi Road, Chennai, Tamil Nadu - 600001",
        supplier_pincode="600001",
        recipient_legal_name=party.name,
        recipient_trade_name=party.name,
        recipient_gstin=party.gstin,
        recipient_state_code='29',
        recipient_address=party.address,
        recipient_pincode="560035",
        place_of_supply="29-Karnataka",
        sac_code="996601",
        taxable_value=Decimal('15000.00'),
        gst_rate_percent=Decimal('5.00'),
    )

    assert_check(invoice.invoice_number.startswith("SGT/"), f"Generated official invoice serial: {invoice.invoice_number}")
    assert_check(invoice.supply_type == 'inter_state', "Inter-state supply resolved automatically (TN to KA)")
    assert_check(invoice.igst_amount == Decimal('750.00'), f"IGST computed correctly: ₹{invoice.igst_amount}")
    assert_check(invoice.total_invoice_value == Decimal('15750.00'), f"Total invoice value correct: ₹{invoice.total_invoice_value}")

    # Create line item
    line_item = InvoiceLineItem.objects.create(
        invoice=invoice,
        item_description="Sarjapur Tech Park Executive Commute",
        sac_code="996601",
        vehicle=vehicle,
        quantity=Decimal('1.00'),
        unit="TRIP",
        rate=Decimal('15000.00'),
        taxable_amount=Decimal('15000.00'),
        igst_amount=Decimal('750.00'),
        total_amount=Decimal('15750.00')
    )
    assert_check(line_item.pk is not None, "InvoiceLineItem created successfully")

    # --------------------------------------------------------------------------
    # STAGE 4: B2B QR Code Stamping
    # --------------------------------------------------------------------------
    print("\n--- [STAGE 4] Testing B2B QR Code Stamping ---")
    
    qr_payload, svg_str, png_uri = generate_b2b_qr_code(invoice)
    assert_check("GSTIN_SUP:33AAAAA0000A1Z5" in qr_payload, "Supplier GSTIN encoded in QR payload")
    assert_check("GSTIN_REC:29AAAAW1234A1Z8" in qr_payload, "Recipient GSTIN encoded in QR payload")
    assert_check("IRN:" in qr_payload, "Digital IRN hash fingerprint encoded in QR")
    assert_check("<svg" in svg_str and "</svg>" in svg_str, "Vector SVG QR code generated")
    assert_check(png_uri.startswith("data:image/png;base64,"), "Base64 PNG QR code generated")

    invoice.qr_code_data = qr_payload
    invoice.qr_code_svg = svg_str
    invoice.save(update_fields=['qr_code_data', 'qr_code_svg'])

    # --------------------------------------------------------------------------
    # STAGE 5: NIC E-Way Bill Schema Generation & Validation
    # --------------------------------------------------------------------------
    print("\n--- [STAGE 5] Testing NIC E-Way Bill Schema v1.04 ---")

    nic_payload = generate_nic_eway_bill_json(
        invoice_obj=invoice,
        trans_distance_km=360
    )

    is_valid, errors = validate_nic_eway_bill_payload(nic_payload)
    assert_check(is_valid, f"NIC JSON payload 100% Schema Valid: {errors}")
    assert_check(nic_payload['supplyType'] == 'O', "supplyType is Outward ('O')")
    assert_check(nic_payload['docType'] == 'INV', "docType is Tax Invoice ('INV')")
    assert_check(nic_payload['actFromStateCode'] == 33, "actFromStateCode is Tamil Nadu (33)")
    assert_check(nic_payload['actToStateCode'] == 29, "actToStateCode is Karnataka (29)")
    assert_check(nic_payload['transDistance'] == 360, "transDistance is 360 KM")
    assert_check(len(nic_payload['itemList']) == 1, "Item list contains line item")

    # Create EWayBill model instance
    ewb = EWayBill.objects.create(
        invoice=invoice,
        vehicle_number="KA01MJ8888",
        trans_distance_km=360,
        nic_payload_json=nic_payload,
        status='active'
    )
    assert_check(len(ewb.eway_bill_number) == 12, f"Official 12-digit E-Way Bill number generated: {ewb.eway_bill_number}")
    assert_check(ewb.valid_until > timezone.now(), f"Validity period computed per Rule 138(10): {ewb.valid_until}")

    # --------------------------------------------------------------------------
    # STAGE 6: General Ledger Double-Entry Posting
    # --------------------------------------------------------------------------
    print("\n--- [STAGE 6] Testing Double-Entry General Ledger Auto-Posting ---")

    je = post_invoice_to_general_ledger(invoice)
    assert_check(je is not None, f"Journal Entry #{je.entry_number} generated")
    assert_check(je.is_balanced, f"Journal Entry balanced: DR ₹{je.total_debit} == CR ₹{je.total_credit}")
    assert_check(je.total_debit == Decimal('15750.00'), "Debit Accounts Receivable for Gross Invoice Value (₹15,750.00)")
    assert_check(je.total_credit == Decimal('15750.00'), "Credit Revenue (₹15,000) + Output IGST (₹750)")

    # --------------------------------------------------------------------------
    # STAGE 7: Multi-State GST Audit & GSTR-1 Reconciliation
    # --------------------------------------------------------------------------
    print("\n--- [STAGE 7] Testing Multi-State GST Audit Summary ---")

    summary = get_multistate_gst_audit_summary()
    assert_check(summary['total_invoices'] >= 1, f"Audit tracked {summary['total_invoices']} invoices")
    assert_check(summary['total_taxable'] >= Decimal('15000.00'), "Audit accurately aggregates taxable turnover")
    assert_check(len(summary['state_breakdown']) >= 1, f"State breakdown categorized {len(summary['state_breakdown'])} state(s)")

    # --------------------------------------------------------------------------
    # STAGE 8: HTTP Views & API Verification
    # --------------------------------------------------------------------------
    print("\n--- [STAGE 8] Testing HTTP Endpoints & Web APIs ---")

    client = Client()
    client.force_login(admin_user)

    # 1. Unfold Admin GST Studio View
    resp_studio = client.get('/admin/finance/gst-studio/')
    assert_check(resp_studio.status_code == 200, "Unfold GST Studio View returns HTTP 200 OK")
    assert_check(b"Corporate GST B2B Invoicing" in resp_studio.content, "Studio contains main title")
    assert_check(b"1-Click Generator Workbench" in resp_studio.content, "Studio contains workbench tab")

    # 2. 1-Click Generator API
    resp_api = client.post(
        '/api/finance/generate-invoice-ewaybill/',
        data=json.dumps({
            'party_id': party.pk,
            'taxable_value': '12000.00',
            'gst_rate_percent': '5.00',
            'sac_code': '996601',
            'recipient_state_code': '33',  # Intra-state
            'vehicle_number': 'TN09AB1234',
            'trans_distance_km': 60,
            'is_reverse_charge': False,
            'auto_generate_eway': True,
        }),
        content_type='application/json'
    )
    assert_check(resp_api.status_code == 200, "Generate Invoice API returns HTTP 200 OK")
    api_data = resp_api.json()
    assert_check(api_data.get('success') is True, "API reported success=True")
    new_inv_id = api_data.get('invoice_id')
    assert_check(new_inv_id is not None, f"Created new invoice ID: {new_inv_id}")

    # 3. NIC JSON Download API
    resp_json = client.get(f'/api/finance/invoice/{new_inv_id}/eway-json/')
    assert_check(resp_json.status_code == 200, "NIC JSON download endpoint returns HTTP 200 OK")
    assert_check(resp_json['Content-Type'] == 'application/json', "Content-Type is application/json")
    exported_payload = json.loads(resp_json.content.decode('utf-8'))
    is_valid_export, export_errs = validate_nic_eway_bill_payload(exported_payload)
    assert_check(is_valid_export, f"Downloaded NIC JSON passes 100% schema validation: {export_errs}")

    # 4. Printable Rule 46 Tax Invoice View
    resp_print = client.get(f'/finance/invoice/{new_inv_id}/view/')
    assert_check(resp_print.status_code == 200, "Printable Tax Invoice view returns HTTP 200 OK")
    assert_check(b"TAX INVOICE" in resp_print.content, "Tax Invoice banner present")
    assert_check(b"GST Rule 46 QR Stamp" in resp_print.content, "QR Stamp present on invoice")

    print("\n" + "=" * 80)
    print(f"[*] ALL CHECKS PASSED: {checks_passed} / {total_checks} (100% SUCCESS!)")
    print("=" * 80)


if __name__ == '__main__':
    run_tests()
