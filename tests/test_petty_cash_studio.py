from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
import json

from core.models import Driver, Vehicle, VehicleType, Party
from operations.models import Trip, Booking
from finance.models import PettyCashAccount, PettyCashTransaction


class PettyCashStudioTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='cashier_admin',
            email='cashier@example.com',
            password='password123'
        )
        self.client.login(username='cashier_admin', password='password123')

        self.party = Party.objects.create(name='Global Logistics', party_type='customer')
        self.driver = Driver.objects.create(name='Prakash Rajan', phone='9842511223', status='active')

        self.account = PettyCashAccount.objects.create(
            account_name='Coimbatore Depot Cash Box',
            account_type='branch',
            allocated_limit=Decimal('25000.00'),
            current_balance=Decimal('10000.00'),
            warning_threshold=Decimal('2000.00')
        )

        self.driver_account = PettyCashAccount.objects.create(
            account_name=f'Driver Float - {self.driver.name}',
            account_type='driver',
            holder_driver=self.driver,
            allocated_limit=Decimal('10000.00'),
            current_balance=Decimal('5000.00'),
            warning_threshold=Decimal('1500.00')
        )

        from datetime import date
        self.trip = Trip.objects.create(
            trip_id='TR-CASH-001',
            party=self.party,
            guest_name='Mr. Sundaram',
            driver=self.driver,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 2),
            status='started',
            fixed_amount=25000,
        )

    def test_account_creation_and_balance_logic(self):
        """Test petty cash account creation and running balance recalculation."""
        self.assertEqual(self.account.current_balance, Decimal('10000.00'))
        self.assertFalse(self.account.is_low_balance)

        # Create an expense
        txn = PettyCashTransaction.objects.create(
            account=self.account,
            transaction_type='expense',
            category='toll_parking',
            amount=Decimal('8500.00'),
            status='approved'
        )
        self.assertTrue(txn.voucher_number.startswith('PCV-'))
        
        # After 8500 expense, balance should be 10000 - 8500 = 1500 <= warning_threshold (2000)
        self.account.refresh_from_db()
        self.assertTrue(self.account.is_low_balance)

    def test_api_petty_cash_topup(self):
        """Test API endpoint to top-up an active float."""
        url = reverse('api-petty-cash-topup')
        payload = {
            'account_id': self.account.id,
            'amount': '5000.00',
            'notes': 'Weekly safe replenishment',
            'reference_number': 'REF-SAFE-99',
        }
        response = self.client.post(url, data=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['new_balance'], 15000.0)

        # Verify transaction created
        topup_txn = self.account.transactions.filter(transaction_type='top_up').first()
        self.assertIsNotNone(topup_txn)
        self.assertEqual(topup_txn.amount, Decimal('5000.00'))

    def test_api_petty_cash_disburse(self):
        """Test API endpoint to log out-of-pocket expense."""
        url = reverse('api-petty-cash-disburse')
        payload = {
            'account_id': self.driver_account.id,
            'amount': '750.00',
            'category': 'toll_parking',
            'recipient_or_vendor': 'L&T Toll Plaza NH44',
            'notes': 'Fastag cash barrier recharge',
            'trip_id': self.trip.id,
        }
        response = self.client.post(url, data=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')

        # Check account balance decreased: 5000 - 750 = 4250
        self.driver_account.refresh_from_db()
        self.assertEqual(self.driver_account.current_balance, Decimal('4250.00'))

        # Check transaction attributes
        txn = PettyCashTransaction.objects.get(voucher_number=data['voucher_number'])
        self.assertEqual(txn.trip, self.trip)
        self.assertEqual(txn.recipient_or_vendor, 'L&T Toll Plaza NH44')

    def test_api_petty_cash_audit_action(self):
        """Test 1-click audit approval or rejection of a voucher."""
        txn = PettyCashTransaction.objects.create(
            account=self.driver_account,
            transaction_type='expense',
            category='fuel',
            amount=Decimal('1200.00'),
            status='submitted',
            notes='Emergency diesel can purchase'
        )

        url = reverse('api-petty-cash-audit-action', args=[txn.id])
        
        # Test approval
        response = self.client.post(
            url,
            data=json.dumps({'action': 'approve', 'audit_notes': 'Verified fuel receipt'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['new_status'], 'approved')

        txn.refresh_from_db()
        self.assertEqual(txn.status, 'approved')
        self.assertEqual(txn.authorized_by, self.user)

    def test_api_petty_cash_stats(self):
        """Test stats endpoint returns aggregate circulation figures."""
        url = reverse('api-petty-cash-stats')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('total_circulation', data)
        self.assertIn('today_disbursed', data)
        self.assertIn('pending_audits', data)

    def test_admin_petty_cash_studio_view_renders_200(self):
        """Test cashier petty cash studio page renders HTTP 200."""
        url = reverse('admin-petty-cash-studio')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Petty Cash Float Register')
        self.assertContains(response, 'Coimbatore Depot Cash Box')

    def test_driver_mobile_wallet_view_renders_200(self):
        """Test driver mobile wallet view renders HTTP 200."""
        url = reverse('driver-mobile-wallet')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Driver Cash Float Wallet')
