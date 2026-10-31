from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from core.models import StaffProfile

User = get_user_model()


class RbacRoleVerificationTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Admin / Superuser
        self.admin_user, _ = User.objects.get_or_create(username='admin_boss', defaults={'is_superuser': True, 'is_staff': True})
        self.admin_user.is_superuser = True
        self.admin_user.is_staff = True
        self.admin_user.save()
        StaffProfile.objects.update_or_create(
            user=self.admin_user,
            defaults={'role': 'admin', 'department': 'Executive Management', 'branch': 'Chennai Central HQ', 'employee_id': 'SGT-TEST-ADM01'}
        )

        # 2. Fleet Manager
        self.fleet_user, _ = User.objects.get_or_create(username='fleet_lead', defaults={'is_staff': True})
        self.fleet_user.is_superuser = False
        self.fleet_user.save()
        StaffProfile.objects.update_or_create(
            user=self.fleet_user,
            defaults={'role': 'fleet_manager', 'department': 'Fleet Operations', 'branch': 'Coimbatore Hub', 'employee_id': 'SGT-TEST-FLT02'}
        )

        # 3. Booking Manager
        self.booking_user, _ = User.objects.get_or_create(username='booking_lead', defaults={'is_staff': True})
        self.booking_user.is_superuser = False
        self.booking_user.save()
        StaffProfile.objects.update_or_create(
            user=self.booking_user,
            defaults={'role': 'booking_manager', 'department': 'Commercial & Tours', 'branch': 'Madurai Depo', 'employee_id': 'SGT-TEST-BKG03'}
        )

        # 4. Finance Team
        self.finance_user, _ = User.objects.get_or_create(username='finance_auditor', defaults={'is_staff': True})
        self.finance_user.is_superuser = False
        self.finance_user.save()
        StaffProfile.objects.update_or_create(
            user=self.finance_user,
            defaults={'role': 'finance_controller', 'department': 'Accounts & Treasury', 'branch': 'Chennai Central HQ', 'employee_id': 'SGT-TEST-FIN04'}
        )

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
        # Check all role sections are present
        self.assertIn('Fleet Readiness &amp; Radar', content)
        self.assertIn('Dispatch Queue &amp; Leads', content)
        self.assertIn('Monthly Financial Pulse', content)

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
        self.assertIn('Fleet Readiness &amp; Radar', content)
        self.assertIn('Open Live Fleet Radar', content)

        # Finance and Sales sections must be filtered out
        self.assertNotIn('Monthly Financial Pulse', content)
        self.assertNotIn('Dispatch Queue &amp; Leads', content)

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
        self.assertIn('Dispatch Queue &amp; Leads', content)
        self.assertIn('Open Query Tracker 2.0', content)

        # Fleet and Finance sections must be filtered out
        self.assertNotIn('Fleet Readiness &amp; Radar', content)
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
        self.assertIn('Monthly Financial Pulse', content)
        self.assertIn('Client Statements &amp; Ledger', content)

        # Fleet maintenance and sales lead pipeline must be filtered out
        self.assertNotIn('Fleet Readiness &amp; Radar', content)
        self.assertNotIn('Dispatch Queue &amp; Leads', content)
