"""
Comprehensive Test Suite for RBAC View-Level Security Decorators & Governance Gates.
Validates:
1. Superuser full pass-through clearance across all modules.
2. Departmental segregation (Finance, Workshop, Sales, Driver).
3. Capability enforcement on GST invoicing, Tally export, Tire Studio, and Compliance.
4. Commercial margin discount override ceiling (<10% requires manager/admin).
5. Financial approval limits and ceiling enforcement on disbursements.
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

from core.models import StaffProfile, Driver, Party, Client as ClientModel, VehicleType
from core.decorators import (
    has_staff_role,
    has_staff_capability,
    get_user_effective_roles,
    CAPABILITY_ROLE_MAP,
)
from finance.models import PettyCashAccount, PettyCashTransaction


class RBACSecurityDecoratorsTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Super Admin
        self.super_admin = User.objects.create_superuser(
            username='admin_director',
            email='director@example.com',
            password='pass123'
        )
        self.super_profile, _ = StaffProfile.objects.get_or_create(
            user=self.super_admin,
            defaults={
                'employee_id': 'SGT-TEST-001',
                'role': 'admin',
                'department': 'Executive Management',
                'branch': 'Chennai Central HQ',
                'approval_limit_inr': Decimal('2500000.00')
            }
        )

        # 2. Branch Manager
        self.manager_user = User.objects.create_user(
            username='mgr_test',
            email='manager@example.com',
            password='pass123'
        )
        self.manager_profile, _ = StaffProfile.objects.get_or_create(
            user=self.manager_user,
            defaults={
                'employee_id': 'SGT-TEST-002',
                'role': 'manager',
                'department': 'Executive Management',
                'branch': 'Coimbatore Hub',
                'approval_limit_inr': Decimal('500000.00')
            }
        )

        # 3. Finance Controller
        self.finance_user = User.objects.create_user(
            username='tax_lead_test',
            email='tax@example.com',
            password='pass123'
        )
        self.finance_profile, _ = StaffProfile.objects.get_or_create(
            user=self.finance_user,
            defaults={
                'employee_id': 'SGT-TEST-003',
                'role': 'finance_controller',
                'department': 'Accounts & Treasury',
                'branch': 'Chennai Central HQ',
                'approval_limit_inr': Decimal('1000000.00')
            }
        )

        # 4. Workshop Manager
        self.workshop_user = User.objects.create_user(
            username='garage_lead_test',
            email='workshop@example.com',
            password='pass123'
        )
        self.workshop_profile, _ = StaffProfile.objects.get_or_create(
            user=self.workshop_user,
            defaults={
                'employee_id': 'SGT-TEST-004',
                'role': 'workshop_manager',
                'department': 'Maintenance & Workshop',
                'branch': 'Madurai Depo',
                'approval_limit_inr': Decimal('150000.00')
            }
        )

        # 5. Sales Executive
        self.sales_user = User.objects.create_user(
            username='sales_rep_test',
            email='sales@example.com',
            password='pass123'
        )
        self.sales_profile, _ = StaffProfile.objects.get_or_create(
            user=self.sales_user,
            defaults={
                'employee_id': 'SGT-TEST-005',
                'role': 'sales_executive',
                'department': 'Commercial & Tours',
                'branch': 'Chennai Central HQ',
                'approval_limit_inr': Decimal('50000.00')
            }
        )

        # 6. Chauffeur / Driver
        self.driver_user = User.objects.create_user(
            username='driver_muthu_test',
            email='driver@example.com',
            password='pass123'
        )
        self.driver_profile, _ = StaffProfile.objects.get_or_create(
            user=self.driver_user,
            defaults={
                'employee_id': 'SGT-TEST-006',
                'role': 'driver',
                'department': 'Fleet Operations',
                'branch': 'Madurai Depo',
                'approval_limit_inr': Decimal('5000.00')
            }
        )

        # 7. Petty Cashier
        self.cashier_user = User.objects.create_user(
            username='cashier_test',
            email='cashier@example.com',
            password='pass123'
        )
        self.cashier_profile, _ = StaffProfile.objects.get_or_create(
            user=self.cashier_user,
            defaults={
                'employee_id': 'SGT-TEST-007',
                'role': 'treasury_petty_cashier',
                'department': 'Accounts & Treasury',
                'branch': 'Coimbatore Hub',
                'approval_limit_inr': Decimal('50000.00')
            }
        )

    def test_effective_roles_and_capability_evaluation(self):
        """Verify role resolution and capability helper checks."""
        # Superuser possesses all roles & capabilities
        self.assertTrue(has_staff_role(self.super_admin, 'admin'))
        self.assertTrue(has_staff_capability(self.super_admin, 'tally_zoho_export'))
        self.assertTrue(has_staff_capability(self.super_admin, 'tire_health_audit'))

        # Finance Controller has finance clearance, but not garage/workshop
        self.assertTrue(has_staff_capability(self.finance_user, 'gst_tax_invoice'))
        self.assertTrue(has_staff_capability(self.finance_user, 'tally_zoho_export'))
        self.assertFalse(has_staff_capability(self.finance_user, 'tire_health_audit'))

        # Workshop Manager has garage clearance, but not accounting/tax
        self.assertTrue(has_staff_capability(self.workshop_user, 'tire_health_audit'))
        self.assertTrue(has_staff_capability(self.workshop_user, 'maintenance_work_orders'))
        self.assertFalse(has_staff_capability(self.workshop_user, 'gst_tax_invoice'))

        # Driver has no finance or quotation clearance
        self.assertFalse(has_staff_capability(self.driver_user, 'gst_tax_invoice'))
        self.assertFalse(has_staff_capability(self.driver_user, 'crm_itinerary_builder'))
        self.assertTrue(has_staff_capability(self.driver_user, 'damage_inspection'))

    def test_view_level_clearance_finance_vs_workshop(self):
        """Validate HTTP 403 on guarded views when accessed by unauthorized personas."""
        # Finance Controller accesses Accounting Export -> HTTP 200
        self.client.force_login(self.finance_user)
        resp = self.client.get('/finance/accounting/')
        self.assertEqual(resp.status_code, 200)

        # Workshop Supervisor accesses Tire Studio -> HTTP 200
        self.client.force_login(self.workshop_user)
        resp = self.client.get('/maintenance/tire-studio/')
        self.assertEqual(resp.status_code, 200)

        # Workshop Supervisor tries accessing Accounting Export -> HTTP 403 PermissionDenied
        resp = self.client.get('/finance/accounting/')
        self.assertEqual(resp.status_code, 403)
        self.assertIn(b"Security Clearance Restricted", resp.content)

        # Finance Controller tries accessing Tire Studio -> HTTP 403 PermissionDenied
        self.client.force_login(self.finance_user)
        resp = self.client.get('/maintenance/tire-studio/')
        self.assertEqual(resp.status_code, 403)
        self.assertIn(b"Clearance Restricted for Capability", resp.content)

    def test_driver_persona_blocked_from_management_portals(self):
        """Chauffeur persona is strictly restricted from administrative studios."""
        self.client.force_login(self.driver_user)

        # Blocked from Accounting Export
        resp = self.client.get('/finance/accounting/')
        self.assertEqual(resp.status_code, 403)

        # Blocked from Tire Studio
        resp = self.client.get('/maintenance/tire-studio/')
        self.assertEqual(resp.status_code, 403)

        # Blocked from Quotation Builder
        resp = self.client.get('/crm/quotations/new/')
        self.assertEqual(resp.status_code, 403)

    def test_commercial_margin_discount_override_floor(self):
        """
        Sales Executive can quote with standard markup (>=10%),
        but markups discounted below 10% raise 403 unless approved by Manager/Director.
        """
        party = ClientModel.objects.create(name='Penta Corp', phone='9840199999', is_active=True)
        vtype = VehicleType.objects.create(name='Toyota Innova Crysta', seating_capacity=7)

        # Sales Executive creates quote with 15% markup -> Success (HTTP 302 redirect to builder)
        self.client.force_login(self.sales_user)
        resp = self.client.post('/crm/quotations/new/', {
            'party': party.id,
            'title': 'Normal Tour Quote',
            'destination': 'Ooty Hill Circuit',
            'start_date': '2026-11-01',
            'end_date': '2026-11-05',
            'markup_percent': '15.00',
            'gst_rate': '5.00',
            'pax_count': 4,
            'vehicle_type': vtype.id,
        })
        self.assertEqual(resp.status_code, 302)

        # Sales Executive attempts to discount markup to 4.50% (<10%) -> Blocked (HTTP 403)
        resp = self.client.post('/crm/quotations/new/', {
            'party': party.id,
            'title': 'Heavily Discounted Quote',
            'destination': 'Ooty Hill Circuit',
            'start_date': '2026-11-01',
            'end_date': '2026-11-05',
            'markup_percent': '4.50',
            'gst_rate': '5.00',
            'pax_count': 4,
            'vehicle_type': vtype.id,
        })
        self.assertEqual(resp.status_code, 403)
        self.assertIn(b"Commercial Margin Waiver Restricted", resp.content)

        # Branch Manager attempts to quote with 4.50% markup -> Allowed (HTTP 302)
        self.client.force_login(self.manager_user)
        resp = self.client.post('/crm/quotations/new/', {
            'party': party.id,
            'title': 'Manager Approved Discount',
            'destination': 'Ooty Hill Circuit',
            'start_date': '2026-11-01',
            'end_date': '2026-11-05',
            'markup_percent': '4.50',
            'gst_rate': '5.00',
            'pax_count': 4,
            'vehicle_type': vtype.id,
        })
        self.assertEqual(resp.status_code, 302)

    def test_petty_cash_disbursement_approval_ceiling(self):
        """
        Cashier has an approval ceiling of ₹50,000.
        Disbursements under ₹50,000 succeed; disbursements exceeding ₹50,000 return 403.
        """
        acc = PettyCashAccount.objects.create(
            account_name='Branch Vault',
            account_type='branch',
            base_depot=self.cashier_profile.branch,
            allocated_limit=Decimal('100000.00'),
            current_balance=Decimal('80000.00'),
            warning_threshold=Decimal('10000.00')
        )

        self.client.force_login(self.cashier_user)

        # Disburse ₹5,000 -> Below ₹50,000 limit -> Success (HTTP 200 JSON)
        resp = self.client.post('/finance/api/petty-cash/disburse/', {
            'account_id': acc.id,
            'amount': '5000.00',
            'category': 'toll_parking',
            'recipient_or_vendor': 'Fastag Highway Tolls',
            'notes': 'Routine highway toll recharge',
        })
        self.assertEqual(resp.status_code, 200)

        # Disburse ₹75,000 -> Exceeds ₹50,000 ceiling -> HTTP 403 Forbidden
        resp = self.client.post('/finance/api/petty-cash/disburse/', {
            'account_id': acc.id,
            'amount': '75000.00',
            'category': 'spot_maintenance',
            'recipient_or_vendor': 'Heavy Diesel Overhaul Workshop',
            'notes': 'Unauthorized emergency gearbox cash',
        })
        self.assertEqual(resp.status_code, 403)
        data = resp.json()
        self.assertEqual(data.get('status'), 'forbidden')
        self.assertIn("Approval Ceiling Exceeded", data.get('error'))
