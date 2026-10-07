from django.test import TestCase, Client
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from core.models import Party
from crm.models import DmcInvoice


class Phase4BillingAndInvoicingConsoleTests(TestCase):
    """
    Automated verification suite for Phase 4:
    Enterprise Billing & GST Invoicing Console, Collections Tracking,
    and 1-Click WhatsApp Dispatch with Payment Receipts.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser('finance_admin_test', 'fin@travels.in', 'pass123')

        cls.party = Party.objects.create(
            name='Cognizant Solutions Coimbatore',
            phone='9840112233',
            party_type='corporate',
            gstin='33AAACC1234A1Z5',
            state_code='33',
            address='CHIL SEZ IT Park, Saravanampatti, Coimbatore - 641035'
        )

        cls.tax_inv = DmcInvoice.objects.create(
            invoice_type='tax_invoice',
            party=cls.party,
            billing_name=cls.party.name,
            billing_address=cls.party.address,
            client_gstin=cls.party.gstin,
            place_of_supply='Tamil Nadu (33)',
            taxable_amount=Decimal('40000.00'),
            gst_rate=Decimal('5.00'),
            paid_amount=Decimal('0.00'),
            tax_regime='intra_state',
            status='issued'
        )

        cls.paid_inv = DmcInvoice.objects.create(
            invoice_type='tax_invoice',
            party=cls.party,
            billing_name=cls.party.name,
            billing_address=cls.party.address,
            client_gstin=cls.party.gstin,
            place_of_supply='Tamil Nadu (33)',
            taxable_amount=Decimal('20000.00'),
            gst_rate=Decimal('5.00'),
            paid_amount=Decimal('21000.00'),
            tax_regime='intra_state',
            status='paid'
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def test_01_invoice_console_renders_with_kpis_and_tabs(self):
        """Verifies /crm/invoices/ loads cleanly with KPI matrices and tab counts."""
        resp = self.client.get('/crm/invoices/')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('Invoicing &amp; Collections Console', content)
        self.assertIn('total_billed', resp.context)
        self.assertIn('total_tax', resp.context)
        self.assertIn('total_received', resp.context)
        self.assertIn('total_balance', resp.context)
        self.assertGreaterEqual(resp.context['all_count'], 2)

    def test_02_status_tabs_filtering(self):
        """Verifies tab filtering for unpaid, paid, and tax_invoice."""
        # Unpaid tab
        resp_unpaid = self.client.get('/crm/invoices/?tab=unpaid')
        self.assertEqual(resp_unpaid.status_code, 200)
        self.assertIn(self.tax_inv.invoice_number, resp_unpaid.content.decode('utf-8'))

        # Paid tab
        resp_paid = self.client.get('/crm/invoices/?tab=paid')
        self.assertEqual(resp_paid.status_code, 200)
        self.assertIn(self.paid_inv.invoice_number, resp_paid.content.decode('utf-8'))

    def test_03_create_new_tax_invoice(self):
        """Verifies POST action to create a new compliant tax invoice."""
        resp = self.client.post('/crm/invoices/create/', {
            'invoice_type': 'tax_invoice',
            'party': self.party.id,
            'billing_name': 'Bosch Global Software Tech',
            'client_gstin': '33AAACB9999A1Z1',
            'place_of_supply': 'Tamil Nadu (33)',
            'tax_regime': 'intra_state',
            'taxable_amount': '50000.00',
            'gst_rate': '5.00',
            'paid_amount': '10000.00',
            'description_of_service': 'Executive Chauffeur Transit & Convoy',
        })
        self.assertEqual(resp.status_code, 302)  # Redirects to invoice_detail
        new_inv = DmcInvoice.objects.filter(billing_name='Bosch Global Software Tech').first()
        self.assertIsNotNone(new_inv)
        self.assertEqual(new_inv.taxable_amount, Decimal('50000.00'))
        self.assertEqual(new_inv.total_tax_amount, Decimal('2500.00'))
        self.assertEqual(new_inv.total_invoice_amount, Decimal('52500.00'))
        self.assertEqual(new_inv.balance_due, Decimal('42500.00'))
        self.assertEqual(new_inv.status, 'partially_paid')

    def test_04_record_invoice_payment_receipt(self):
        """Verifies recording customer payment receipt updates balance and marks invoice as paid."""
        # Record full settlement of tax_inv (total = 42000, currently paid = 0)
        resp = self.client.post(
            f'/crm/api/invoices/{self.tax_inv.id}/record-payment/',
            {
                'payment_amount': '42000.00',
                'payment_mode': 'upi',
                'reference_number': 'UPI-REF-TEST-9921'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('status'), 'success')

        self.tax_inv.refresh_from_db()
        self.assertEqual(self.tax_inv.paid_amount, Decimal('42000.00'))
        self.assertEqual(self.tax_inv.balance_due, Decimal('0.00'))
        self.assertEqual(self.tax_inv.status, 'paid')

    def test_05_dispatch_invoice_whatsapp(self):
        """Verifies 1-click WhatsApp dispatch endpoint sends tax invoice summary to client."""
        resp = self.client.post(
            f'/crm/api/invoices/{self.tax_inv.id}/dispatch/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertEqual(data.get('dispatched_to'), self.party.phone)
