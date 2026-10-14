"""
Automated Test Suite for Regional Petty Cash Float Scoping & Inter-Depot Asset Relocation Workflow.
Validates:
1. Petty Cash Regional Float Isolation (Coimbatore vs. Chennai HQ accounts)
2. Cross-Depot Disbursement Fencing (Regional Cashier blocked from non-depot vaults)
3. Inter-Depot Transfer Creation, Validation & Role Authorization
4. Asset Relocation Receipt & Automatic vehicle base_depot Update
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from decimal import Decimal
import datetime
import json

from core.models import Vehicle, Driver, StaffProfile, VehicleType, InterDepotTransferLog
from finance.models import PettyCashAccount, PettyCashTransaction
from operations.models import Trip, Booking, Client as ClientParty
from core.depot_scoping import (
    DEPOT_CHENNAI, DEPOT_COIMBATORE, DEPOT_MADURAI, DEPOT_BENGALURU,
)


class InterDepotAndPettyCashTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Base Setup: VehicleType
        self.vtype, _ = VehicleType.objects.get_or_create(
            name='Executive Coach',
            defaults={'seating_capacity': 35}
        )

        # 2. Users & Staff Profiles
        # Super Admin at Chennai HQ
        self.admin_user, _ = User.objects.get_or_create(
            username='test_admin_central',
            defaults={'is_staff': True, 'is_superuser': True, 'email': 'central_admin@test.com'}
        )
        self.admin_user.set_password('pass123')
        self.admin_user.save()
        self.prof_admin, _ = StaffProfile.objects.get_or_create(
            user=self.admin_user,
            defaults={
                'role': 'admin',
                'employee_id': 'TST-HQ-01',
                'branch': DEPOT_CHENNAI,
                'approval_limit_inr': Decimal('5000000.00'),
            }
        )

        # Regional Operations Dispatcher at Coimbatore Hub
        self.cbe_ops_user, _ = User.objects.get_or_create(
            username='test_cbe_dispatcher',
            defaults={'is_staff': True, 'is_superuser': False, 'email': 'cbe_ops@test.com'}
        )
        self.cbe_ops_user.set_password('pass123')
        self.cbe_ops_user.save()
        self.prof_cbe_ops, _ = StaffProfile.objects.get_or_create(
            user=self.cbe_ops_user,
            defaults={
                'role': 'operations',
                'employee_id': 'TST-CBE-OPS',
                'branch': DEPOT_COIMBATORE,
                'approval_limit_inr': Decimal('100000.00'),
            }
        )

        # Regional Treasury Cashier at Coimbatore Hub
        self.cbe_cashier_user, _ = User.objects.get_or_create(
            username='test_cbe_cashier',
            defaults={'is_staff': True, 'is_superuser': False, 'email': 'cbe_cash@test.com'}
        )
        self.cbe_cashier_user.set_password('pass123')
        self.cbe_cashier_user.save()
        self.prof_cbe_cashier, _ = StaffProfile.objects.get_or_create(
            user=self.cbe_cashier_user,
            defaults={
                'role': 'treasury_petty_cashier',
                'employee_id': 'TST-CBE-CSH',
                'branch': DEPOT_COIMBATORE,
                'approval_limit_inr': Decimal('50000.00'),
            }
        )

        # Regional Operations Dispatcher at Chennai HQ
        self.chn_ops_user, _ = User.objects.get_or_create(
            username='test_chn_dispatcher',
            defaults={'is_staff': True, 'is_superuser': False, 'email': 'chn_ops@test.com'}
        )
        self.chn_ops_user.set_password('pass123')
        self.chn_ops_user.save()
        self.prof_chn_ops, _ = StaffProfile.objects.get_or_create(
            user=self.chn_ops_user,
            defaults={
                'role': 'operations',
                'employee_id': 'TST-CHN-OPS',
                'branch': DEPOT_CHENNAI,
                'approval_limit_inr': Decimal('150000.00'),
            }
        )

        # 3. Regional Petty Cash Accounts
        self.account_chennai = PettyCashAccount.objects.create(
            account_name='Central Imprest Vault',
            base_depot=DEPOT_CHENNAI,
            account_type='branch',
            allocated_limit=Decimal('100000.00'),
            opening_balance=Decimal('85000.00'),
            current_balance=Decimal('85000.00'),
            warning_threshold=Decimal('15000.00'),
            is_active=True,
        )

        self.account_coimbatore = PettyCashAccount.objects.create(
            account_name='Coimbatore Workshop Float',
            base_depot=DEPOT_COIMBATORE,
            account_type='branch',
            allocated_limit=Decimal('50000.00'),
            opening_balance=Decimal('35000.00'),
            current_balance=Decimal('35000.00'),
            warning_threshold=Decimal('10000.00'),
            is_active=True,
        )

        # 4. Regional Fleet Vehicles
        self.vehicle_cbe = Vehicle.objects.create(
            registration_number='TN-38-BZ-9901',
            brand='Toyota',
            model='Innova Crysta',
            vehicle_type=self.vtype,
            seating_capacity=7,
            base_depot=DEPOT_COIMBATORE,
            status='available',
            current_km=42000,
        )

        self.vehicle_chn = Vehicle.objects.create(
            registration_number='TN-01-AB-1102',
            brand='Volvo',
            model='B11R Multi-Axle',
            vehicle_type=self.vtype,
            seating_capacity=45,
            base_depot=DEPOT_CHENNAI,
            status='available',
            current_km=78000,
        )

        # Driver
        self.driver_cbe = Driver.objects.create(
            name='Karthik Murugan',
            phone='9842100001',
            base_depot=DEPOT_COIMBATORE,
        )

    # =========================================================================
    # Part 1: Regional Petty Cash Float Isolation Tests
    # =========================================================================

    def test_01_regional_petty_cash_studio_scoping(self):
        """Coimbatore cashier only sees Coimbatore accounts; Admin sees consolidated."""
        # 1. Coimbatore cashier view
        self.client.login(username='test_cbe_cashier', password='pass123')
        resp = self.client.get('/finance/petty-cash/')
        self.assertEqual(resp.status_code, 200)
        accounts = list(resp.context['accounts'])
        self.assertIn(self.account_coimbatore, accounts)
        self.assertNotIn(self.account_chennai, accounts)
        self.assertEqual(resp.context['can_change_depot'], False)
        self.assertEqual(resp.context['current_depot'], DEPOT_COIMBATORE)

        # 2. Super admin consolidated view
        self.client.login(username='test_admin_central', password='pass123')
        resp_admin = self.client.get('/finance/petty-cash/')
        self.assertEqual(resp_admin.status_code, 200)
        admin_accounts = list(resp_admin.context['accounts'])
        self.assertIn(self.account_coimbatore, admin_accounts)
        self.assertIn(self.account_chennai, admin_accounts)
        self.assertEqual(resp_admin.context['can_change_depot'], True)

        # 3. Super admin filtered by depot
        resp_cbe = self.client.get(f'/finance/petty-cash/?depot={DEPOT_COIMBATORE}')
        cbe_only = list(resp_cbe.context['accounts'])
        self.assertIn(self.account_coimbatore, cbe_only)
        self.assertNotIn(self.account_chennai, cbe_only)

    def test_02_petty_cash_disbursement_depot_fencing(self):
        """Regional cashier is forbidden from disbursing money from another depot's float."""
        self.client.login(username='test_cbe_cashier', password='pass123')

        # Attempt to disburse from Chennai Central HQ account
        disburse_payload = {
            'account_id': self.account_chennai.id,
            'amount': 2500,
            'category': 'fuel',
            'recipient_or_vendor': 'Fuel Station',
            'notes': 'Unauthorized cross-depot disbursement test',
        }
        resp = self.client.post(
            '/finance/api/petty-cash/disburse/',
            data=json.dumps(disburse_payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 403)
        data = resp.json()
        self.assertEqual(data.get('status'), 'error')
        self.assertIn('Unauthorized', data.get('message', ''))

        # Legitimate disbursement from Coimbatore account succeeds
        legit_payload = {
            'account_id': self.account_coimbatore.id,
            'amount': 1500,
            'category': 'toll_parking',
            'recipient_or_vendor': 'NHAI Fastag',
            'notes': 'Authorized Coimbatore toll reimbursement',
        }
        resp_ok = self.client.post(
            '/finance/api/petty-cash/disburse/',
            data=json.dumps(legit_payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp_ok.status_code, 200)
        data_ok = resp_ok.json()
        self.assertEqual(data_ok.get('status'), 'success')

        # Verify account balance deducted
        self.account_coimbatore.refresh_from_db()
        self.assertEqual(self.account_coimbatore.current_balance, Decimal('33500.00'))

    # =========================================================================
    # Part 2: Inter-Depot Asset Relocation Workflow Tests
    # =========================================================================

    def test_03_transfer_request_validation_and_fencing(self):
        """Validates cross-depot dispatch authority, same-depot errors, and creation."""
        self.client.login(username='test_cbe_dispatcher', password='pass123')

        # 1. Coimbatore dispatcher cannot dispatch Chennai's vehicle
        unauthorized_payload = {
            'vehicle_id': self.vehicle_chn.id,
            'destination_depot': DEPOT_COIMBATORE,
            'reason': 'fleet_rebalance',
        }
        resp_unauth = self.client.post(
            '/api/fleet/transfer/request/',
            data=json.dumps(unauthorized_payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp_unauth.status_code, 403)

        # 2. Cannot transfer to the same depot
        same_depot_payload = {
            'vehicle_id': self.vehicle_cbe.id,
            'destination_depot': DEPOT_COIMBATORE,
            'reason': 'fleet_rebalance',
        }
        resp_same = self.client.post(
            '/api/fleet/transfer/request/',
            data=json.dumps(same_depot_payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp_same.status_code, 400)
        self.assertIn('already stationed at', resp_same.json().get('message', ''))

        # 3. Successful transfer creation: CBE -> CHN for seasonal peak
        valid_payload = {
            'vehicle_id': self.vehicle_cbe.id,
            'destination_depot': DEPOT_CHENNAI,
            'reason': 'seasonal_peak',
            'transfer_driver_id': self.driver_cbe.id,
            'odometer_at_dispatch': 42050,
            'dispatch_immediately': True,
            'notes': 'Reallocated for Ooty summer seasonal tourist influx.',
        }
        resp_ok = self.client.post(
            '/api/fleet/transfer/request/',
            data=json.dumps(valid_payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp_ok.status_code, 200)
        data = resp_ok.json()
        self.assertEqual(data.get('status'), 'success')
        transfer_id = data['transfer']['transfer_id']

        # Verify database record
        transfer = InterDepotTransferLog.objects.get(transfer_id=transfer_id)
        self.assertEqual(transfer.vehicle, self.vehicle_cbe)
        self.assertEqual(transfer.origin_depot, DEPOT_COIMBATORE)
        self.assertEqual(transfer.destination_depot, DEPOT_CHENNAI)
        self.assertEqual(transfer.status, 'in_transit')
        self.assertEqual(transfer.requested_by, self.cbe_ops_user)
        self.assertEqual(transfer.odometer_at_dispatch, 42050)

    def test_04_cannot_transfer_vehicle_on_active_trip(self):
        """Vehicles currently allocated to active trips cannot be relocated."""
        client_party = ClientParty.objects.create(name='Test Corporate Client')
        booking = Booking.objects.create(
            party=client_party,
            guest_name='VIP Guest',
            pickup_date=datetime.date.today(),
            pickup_time=datetime.time(9, 0),
            pickup_location='Coimbatore Airport',
            destination='Ooty',
        )
        # Create active trip with date objects
        trip = Trip.objects.create(
            booking=booking,
            party=client_party,
            vehicle=self.vehicle_cbe,
            driver=self.driver_cbe,
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=2),
            status='started',
        )

        self.client.login(username='test_cbe_dispatcher', password='pass123')
        payload = {
            'vehicle_id': self.vehicle_cbe.id,
            'destination_depot': DEPOT_CHENNAI,
            'reason': 'seasonal_peak',
        }
        resp = self.client.post(
            '/api/fleet/transfer/request/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('currently allocated to active trip', resp.json().get('message', ''))

    def test_05_receive_transfer_and_relocate_vehicle(self):
        """Authorized destination custodian receives vehicle, updating base_depot and odometer."""
        # Create an in-transit transfer: CBE -> CHN
        transfer = InterDepotTransferLog.objects.create(
            vehicle=self.vehicle_cbe,
            origin_depot=DEPOT_COIMBATORE,
            destination_depot=DEPOT_CHENNAI,
            reason='wedding_contract',
            status='in_transit',
            requested_by=self.cbe_ops_user,
            odometer_at_dispatch=42000,
        )

        # 1. Coimbatore user attempts to receive transfer destined for Chennai -> 403 Forbidden
        self.client.login(username='test_cbe_dispatcher', password='pass123')
        resp_forbidden = self.client.post(
            f'/api/fleet/transfer/{transfer.id}/receive/',
            data=json.dumps({'odometer_at_receipt': 42520}),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp_forbidden.status_code, 403)

        # 2. Chennai dispatcher successfully receives the incoming vehicle
        self.client.login(username='test_chn_dispatcher', password='pass123')
        resp_receive = self.client.post(
            f'/api/fleet/transfer/{transfer.id}/receive/',
            data=json.dumps({
                'odometer_at_receipt': 42540,
                'notes': 'Vehicle inspected, clean condition, parked in Bay 4.',
            }),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp_receive.status_code, 200)
        data = resp_receive.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertEqual(data['transfer']['base_depot'], DEPOT_CHENNAI)
        self.assertEqual(data['transfer']['status'], 'completed')

        # 3. Verify vehicle model update in database
        self.vehicle_cbe.refresh_from_db()
        self.assertEqual(self.vehicle_cbe.base_depot, DEPOT_CHENNAI)
        self.assertEqual(self.vehicle_cbe.current_km, 42540)

        # Verify transfer log update
        transfer.refresh_from_db()
        self.assertEqual(transfer.status, 'completed')
        self.assertIsNotNone(transfer.received_at)
        self.assertEqual(transfer.odometer_at_receipt, 42540)
        self.assertIn('Bay 4', transfer.notes)

    def test_06_depot_transfer_history_scoping(self):
        """Transfer history respects regional scoping."""
        transfer = InterDepotTransferLog.objects.create(
            vehicle=self.vehicle_cbe,
            origin_depot=DEPOT_COIMBATORE,
            destination_depot=DEPOT_CHENNAI,
            reason='breakdown_replacement',
            status='in_transit',
            requested_by=self.cbe_ops_user,
        )

        # Coimbatore user sees this transfer (origin=CBE)
        self.client.login(username='test_cbe_dispatcher', password='pass123')
        resp_cbe = self.client.get('/api/fleet/transfer/history/')
        self.assertEqual(resp_cbe.status_code, 200)
        transfers_cbe = resp_cbe.json().get('transfers', [])
        transfer_ids_cbe = [t['transfer_id'] for t in transfers_cbe]
        self.assertIn(transfer.transfer_id, transfer_ids_cbe)

        # Madurai user does NOT see CBE -> CHN transfer
        madurai_user, _ = User.objects.get_or_create(
            username='test_mdu_dispatcher',
            defaults={'is_staff': True, 'is_superuser': False}
        )
        madurai_user.set_password('pass123')
        madurai_user.save()
        StaffProfile.objects.get_or_create(
            user=madurai_user,
            defaults={'role': 'operations', 'branch': DEPOT_MADURAI, 'employee_id': 'TST-MDU-OPS'}
        )
        self.client.login(username='test_mdu_dispatcher', password='pass123')
        resp_mdu = self.client.get('/api/fleet/transfer/history/')
        self.assertEqual(resp_mdu.status_code, 200)
        transfers_mdu = resp_mdu.json().get('transfers', [])
        transfer_ids_mdu = [t['transfer_id'] for t in transfers_mdu]
        self.assertNotIn(transfer.transfer_id, transfer_ids_mdu)
