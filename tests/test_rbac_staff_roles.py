from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from core.models import Vehicle, Driver, Party


class RbacRoleVerificationTests(TestCase):
    """
    Automated test suite verifying Phase 2: Role-Based Access Control (RBAC).
    Verifies:
      1. Existence and membership of Fleet_Managers, Booking_Managers, Finance_Team groups.
      2. Role context processor injects appropriate role flags and badges.
      3. Sidebar sections filter according to staff clearance.
      4. Dashboard KPIs adapt to the authenticated role.
    """

    @classmethod
    def setUpTestData(cls):
        # Ensure groups exist
        cls.fleet_group, _ = Group.objects.get_or_create(name='Fleet_Managers')
        cls.booking_group, _ = Group.objects.get_or_create(name='Booking_Managers')
        cls.finance_group, _ = Group.objects.get_or_create(name='Finance_Team')

        # Create test users
        cls.admin_user = User.objects.create_superuser('test_admin_rbac', 'admin@rbac.in', 'pass123')
        
        cls.fleet_user = User.objects.create_user('test_fleet_rbac', 'fleet@rbac.in', 'pass123', is_staff=True)
        cls.fleet_user.groups.add(cls.fleet_group)

        cls.booking_user = User.objects.create_user('test_booking_rbac', 'booking@rbac.in', 'pass123', is_staff=True)
        cls.booking_user.groups.add(cls.booking_group)

        cls.finance_user = User.objects.create_user('test_finance_rbac', 'fin@rbac.in', 'pass123', is_staff=True)
        cls.finance_user.groups.add(cls.finance_group)

    def setUp(self):
        self.client = Client()

    def test_01_admin_superuser_full_clearance(self):
        """Superuser should see all sections, all KPIs, and Superuser Admin badge."""
        self.client.force_login(self.admin_user)
        resp = self.client.get('/dashboard/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context['is_superuser'])
        self.assertTrue(resp.context['is_fleet_manager'])
        self.assertTrue(resp.context['is_booking_manager'])
        self.assertTrue(resp.context['is_finance_user'])
        self.assertEqual(resp.context['user_role_label'], 'Superuser Admin')

        content = resp.content.decode('utf-8')
        # Check all sidebar sections are present
        self.assertIn('Fleet &amp; Telematics', content)
        self.assertIn('Sales &amp; CRM', content)
        self.assertIn('Finance &amp; Billing', content)
        self.assertIn('Administration', content)

    def test_02_fleet_manager_clearance(self):
        """Fleet Manager should see only Fleet & Telematics, no confidential financial figures."""
        self.client.force_login(self.fleet_user)
        resp = self.client.get('/dashboard/')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['is_superuser'])
        self.assertTrue(resp.context['is_fleet_manager'])
        self.assertFalse(resp.context['is_booking_manager'])
        self.assertFalse(resp.context['is_finance_user'])
        self.assertEqual(resp.context['user_role_label'], 'Fleet Manager')

        content = resp.content.decode('utf-8')
        # Fleet sections must be visible
        self.assertIn('Fleet &amp; Telematics', content)
        self.assertIn('Fleet Readiness &amp; Radar', content)
        self.assertIn('Live Fleet Map', content)
        
        # Finance and Sales sections must be filtered out
        self.assertNotIn('Finance &amp; Billing', content)
        self.assertNotIn('Monthly Financial Pulse', content)
        self.assertNotIn('Quotation Studio', content)

    def test_03_booking_manager_clearance(self):
        """Booking Manager should see Sales & CRM, not Fleet maintenance or sensitive accounting."""
        self.client.force_login(self.booking_user)
        resp = self.client.get('/dashboard/')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['is_superuser'])
        self.assertFalse(resp.context['is_fleet_manager'])
        self.assertTrue(resp.context['is_booking_manager'])
        self.assertFalse(resp.context['is_finance_user'])

        content = resp.content.decode('utf-8')
        # Sales sections must be visible
        self.assertIn('Sales &amp; CRM', content)
        self.assertIn('Dispatch Queue &amp; Leads', content)
        self.assertIn('Query Tracker 2.0', content)

        # Fleet and Finance sections must be filtered out
        self.assertNotIn('Fleet &amp; Telematics', content)
        self.assertNotIn('Finance &amp; Billing', content)
        self.assertNotIn('Monthly Financial Pulse', content)

    def test_04_finance_team_clearance(self):
        """Finance Team should see Invoices, Ledgers, and Monthly Financial Pulse."""
        self.client.force_login(self.finance_user)
        resp = self.client.get('/dashboard/')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['is_superuser'])
        self.assertFalse(resp.context['is_fleet_manager'])
        self.assertFalse(resp.context['is_booking_manager'])
        self.assertTrue(resp.context['is_finance_user'])

        content = resp.content.decode('utf-8')
        # Finance sections must be visible
        self.assertIn('Finance &amp; Billing', content)
        self.assertIn('Monthly Financial Pulse', content)
        self.assertIn('Statements &amp; Ledgers', content)

        # Fleet maintenance and sales lead pipeline must be filtered out
        self.assertNotIn('Fleet &amp; Telematics', content)
        self.assertNotIn('Sales &amp; CRM', content)
