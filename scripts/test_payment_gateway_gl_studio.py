"""
Comprehensive Automated Test Suite for:
⚡ Dynamic UPI QR & Payment Gateway Studio
⚖️ Double-Entry General Ledger (GL) Auto-Posting Engine
"""

import os
import sys
import json
import django
from decimal import Decimal

# Force Windows PowerShell UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from operations.models import Booking
from core.models import Party
from finance.models import Account, JournalEntry, JournalItem, Payment
from payments_gateway.models import PaymentGatewayConfig, GatewayTransaction, PaymentWebhookEvent
from payments_gateway.upi import (
    build_upi_payment_url,
    generate_upi_qr_svg,
    generate_upi_qr_base64,
    generate_dynamic_upi_package,
)
from payments_gateway.gl_engine import post_gateway_transaction_to_gl, get_or_create_core_accounts

User = get_user_model()


def run_tests():
    print("=" * 80)
    print("⚡ DYNAMIC UPI QR & PAYMENT GATEWAY STUDIO + DOUBLE-ENTRY GL TEST SUITE")
    print("=" * 80)

    # Setup Superuser & Client
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.create_superuser('admin_test', 'admin@example.com', 'adminpass123')
    client = Client()
    client.force_login(user)
    print(f"[*] Authenticated as Superuser: {user.username}\n")

    passed_count = 0
    total_count = 0

    def check(desc, condition):
        nonlocal passed_count, total_count
        total_count += 1
        if condition:
            passed_count += 1
            print(f"  [PASS] {desc}")
        else:
            print(f"  [FAIL] {desc}")
            raise AssertionError(f"Check failed: {desc}")

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 1: NPCI Dynamic UPI Intent & QR Generation
    # ──────────────────────────────────────────────────────────────────────────
    print("--- 1. Testing Dynamic NPCI UPI QR & Intent Engine ---")
    upi_url = build_upi_payment_url(
        vpa='sivagayathiritravels@icici',
        merchant_name='Sivagayathiri Travels',
        amount=Decimal('4250.00'),
        reference_id='BK-UPI-TEST-101',
        note='Tour Advance Payment',
        mcc='4121'
    )
    check("UPI URI starts with 'upi://pay?'", upi_url.startswith('upi://pay?'))
    check("UPI URI contains correct VPA", 'pa=sivagayathiritravels%40icici' in upi_url)
    check("UPI URI contains formatted 2-decimal amount", 'am=4250.00' in upi_url)
    check("UPI URI contains reference ID", 'tr=BK-UPI-TEST-101' in upi_url)
    check("UPI URI currency is INR", 'cu=INR' in upi_url)

    svg_content = generate_upi_qr_svg(upi_url)
    check("SVG vector QR generated", bool(svg_content))
    check("SVG content contains valid <svg tag", '<svg' in svg_content)

    b64_png = generate_upi_qr_base64(upi_url)
    check("Base64 PNG generated", bool(b64_png))
    check("Base64 PNG has valid data URI header", b64_png.startswith('data:image/png;base64,'))

    pkg = generate_dynamic_upi_package(
        amount=Decimal('2500.00'),
        reference_id='BK-PKG-001'
    )
    check("Package contains deep links dictionary", isinstance(pkg['deep_links'], dict))
    check("Package contains Google Pay intent", 'gpay' in pkg['deep_links'])
    check("Package contains PhonePe intent", 'phonepe' in pkg['deep_links'])
    check("Package contains Paytm intent", 'paytm' in pkg['deep_links'])
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 2: Chart of Accounts & Double-Entry Invariants
    # ──────────────────────────────────────────────────────────────────────────
    print("--- 2. Testing Chart of Accounts & General Ledger Math ---")
    accounts = get_or_create_core_accounts()
    check("Core accounts include 1010 Cash", '1010' in accounts)
    check("Core accounts include 1020 Operating Bank", '1020' in accounts)
    check("Core accounts include 1030 Gateway Clearing", '1030' in accounts)
    check("Core accounts include 1100 Accounts Receivable", '1100' in accounts)
    check("Core accounts include 5030 Gateway Charges", '5030' in accounts)

    # Create a manual test journal entry to verify balance invariant
    je = JournalEntry.objects.create(
        date=timezone.now().date(),
        entry_type='general',
        reference_id='TEST-MATH-001',
        narration='Test balance invariant validation'
    )
    JournalItem.objects.create(entry=je, account=accounts['1020'], debit=Decimal('1000.00'), credit=Decimal('0.00'))
    JournalItem.objects.create(entry=je, account=accounts['1100'], debit=Decimal('0.00'), credit=Decimal('1000.00'))

    check("Journal total debit equals 1000.00", je.total_debit == Decimal('1000.00'))
    check("Journal total credit equals 1000.00", je.total_credit == Decimal('1000.00'))
    check("Journal entry is_balanced invariant holds (DR == CR)", je.is_balanced)
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 3: Razorpay Webhook & Automated GL Posting
    # ──────────────────────────────────────────────────────────────────────────
    print("--- 3. Testing Razorpay Webhook Ingestion & GL Posting ---")
    party = Party.objects.filter(party_type='customer').first() or Party.objects.first()
    booking = Booking.objects.filter(party=party).first()

    rzp_ref = booking.booking_number if booking else 'BK-RZP-TEST-99'
    rzp_pid = f"pay_test_suite_{int(timezone.now().timestamp())}"

    rzp_payload = {
        'id': f"evt_rzp_{int(timezone.now().timestamp())}",
        'event': 'payment.captured',
        'payload': {
            'payment': {
                'entity': {
                    'id': rzp_pid,
                    'amount': 600000,  # 6000.00 in paise
                    'fee': 10500,     # 105.00 in paise
                    'tax': 1890,      # 18.90 in paise
                    'notes': {'reference_id': rzp_ref}
                }
            }
        }
    }

    resp = client.post(
        '/payments/webhook/razorpay/',
        data=json.dumps(rzp_payload),
        content_type='application/json'
    )
    check("Razorpay webhook returns 200 OK", resp.status_code == 200)

    rzp_txn = GatewayTransaction.objects.filter(gateway_payment_id=rzp_pid).first()
    check("GatewayTransaction record created", rzp_txn is not None)
    check("Transaction gross amount is 6000.00", rzp_txn.gross_amount == Decimal('6000.00'))
    check("Transaction fee amount parsed correctly (105.00)", rzp_txn.fee_amount == Decimal('105.00'))
    check("Transaction status is 'captured'", rzp_txn.status == 'captured')
    check("Transaction has linked JournalEntry", rzp_txn.journal_entry is not None)
    check("Transaction has linked legacy Payment record", rzp_txn.payment_record is not None)
    check("JournalEntry is balanced (DR == CR)", rzp_txn.journal_entry.is_balanced)
    check("JournalEntry is marked as posted", rzp_txn.journal_entry.is_posted)
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 4: Cashfree Webhook & Automated GL Posting
    # ──────────────────────────────────────────────────────────────────────────
    print("--- 4. Testing Cashfree Webhook Ingestion & GL Posting ---")
    cf_pid = f"cf_test_suite_{int(timezone.now().timestamp())}"
    cf_payload = {
        'type': 'PAYMENT_SUCCESS_WEBHOOK',
        'data': {
            'order': {'order_id': rzp_ref, 'order_amount': 7500.00},
            'payment': {'cf_payment_id': cf_pid, 'payment_amount': 7500.00, 'payment_status': 'SUCCESS'}
        }
    }

    resp_cf = client.post(
        '/payments/webhook/cashfree/',
        data=json.dumps(cf_payload),
        content_type='application/json'
    )
    check("Cashfree webhook returns 200 OK", resp_cf.status_code == 200)
    cf_txn = GatewayTransaction.objects.filter(gateway_payment_id=cf_pid).first()
    check("Cashfree GatewayTransaction created", cf_txn is not None)
    check("Cashfree transaction is captured", cf_txn.status == 'captured')
    check("Cashfree transaction has posted balanced JournalEntry", cf_txn.journal_entry and cf_txn.journal_entry.is_balanced)
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 5: Direct Dynamic UPI 12-Digit UTR Instant Reconciler
    # ──────────────────────────────────────────────────────────────────────────
    print("--- 5. Testing Direct Dynamic UPI Instant UTR Confirmation ---")
    fake_utr = f"4268{int(timezone.now().timestamp()) % 100000000:08d}"
    upi_confirm_payload = {
        'utr_number': fake_utr,
        'amount': '3200.00',
        'booking_id': booking.pk if booking else None,
        'party_id': party.pk if party else None
    }
    resp_upi = client.post(
        '/api/payments/direct-upi/confirm/',
        data=json.dumps(upi_confirm_payload),
        content_type='application/json'
    )
    check("Direct UPI confirmation returns 200 OK", resp_upi.status_code == 200)
    upi_res_data = resp_upi.json()
    check("Response status is 'success'", upi_res_data.get('status') == 'success')
    check("Response contains journal_entry number", bool(upi_res_data.get('journal_entry')))

    upi_txn = GatewayTransaction.objects.filter(gateway_payment_id=fake_utr).first()
    check("Direct UPI transaction created with zero fee", upi_txn and upi_txn.fee_amount == Decimal('0.00'))
    check("Direct UPI transaction posted balanced journal", upi_txn and upi_txn.journal_entry.is_balanced)
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 6: Unfold Admin Payment Studio & APIs
    # ──────────────────────────────────────────────────────────────────────────
    print("--- 6. Testing Unfold Admin Studio UI & REST Endpoints ---")
    resp_admin = client.get('/admin/finance/payment-studio/')
    check("GET /admin/finance/payment-studio/ returns 200 OK", resp_admin.status_code == 200)
    content_admin = resp_admin.content.decode('utf-8')
    check("Admin view renders title", 'Dynamic UPI &amp; Payment Gateway Studio' in content_admin or 'Dynamic UPI & Payment Gateway Studio' in content_admin)
    check("Admin view renders KPI counters", 'Collections Today' in content_admin)
    check("Admin view renders dynamic QR svg container", 'qrSvgContainer' in content_admin)
    check("Admin view renders webhook simulator", 'tab-webhook-sandbox' in content_admin)

    resp_alias = client.get('/admin/payments/studio/')
    check("GET /admin/payments/studio/ alias returns 200 OK", resp_alias.status_code == 200)

    resp_gen = client.get(f'/api/payments/dynamic-upi/generate/?amount=5000.00&booking_id={booking.pk if booking else ""}')
    check("GET /api/payments/dynamic-upi/generate/ returns 200 OK", resp_gen.status_code == 200)
    gen_data = resp_gen.json()
    check("Dynamic UPI API returns SVG", bool(gen_data.get('qr_svg')))
    check("Dynamic UPI API returns deep links", bool(gen_data.get('deep_links')))

    resp_metrics = client.get('/api/payments/studio-metrics/')
    check("GET /api/payments/studio-metrics/ returns 200 OK", resp_metrics.status_code == 200)
    metrics_data = resp_metrics.json()
    check("Metrics returns today_collections", 'today_collections' in metrics_data)
    check("Metrics returns gateway_clearing_bal", 'gateway_clearing_bal' in metrics_data)
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # SECTION 7: Unfold ModelAdmin Compliance Audit
    # ──────────────────────────────────────────────────────────────────────────
    print("--- 7. Auditing ModelAdmin Compliance (100% Unfold) ---")
    from django.contrib import admin as django_admin
    registry = django_admin.site._registry
    for model_cls in [Account, JournalEntry, PaymentGatewayConfig, GatewayTransaction]:
        admin_inst = registry.get(model_cls)
        check(f"{model_cls.__name__} is registered in admin", admin_inst is not None)
        check(f"{model_cls.__name__} admin subclasses UnfoldModelAdmin", isinstance(admin_inst, UnfoldModelAdmin))

    print("\n" + "=" * 80)
    print(f"🏆 ALL {passed_count}/{total_count} CHECKS PASSED (100% SUCCESS)!")
    print("=" * 80)


if __name__ == '__main__':
    run_tests()
