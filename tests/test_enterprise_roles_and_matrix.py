from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from core.models import StaffProfile, Driver, Party, Vehicle


class EnterpriseRolesAndMatrixTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Ensure groups exist
        cls.admin_group, _ = Group.objects.get_or_create(name='Super_Admins')
        cls.mgr_group, _ = Group.objects.get_or_create(name='General_Managers')
        cls.sales_exec_group, _ = Group.objects.get_or_create(name='Sales_Executives')
        cls.corp_sales_group, _ = Group.objects.get_or_create(name='Corporate_Sales')
        cls.ops_group, _ = Group.objects.get_or_create(name='Operations_Dispatch')
        cls.acct_group, _ = Group.objects.get_or_create(name='Accounts_Finance')
        cls.driver_group, _ = Group.objects.get_or_create(name='Chauffeur_Drivers')
        cls.support_group, _ = Group.objects.get_or_create(name='Guest_Support')

        # Create demo staff users
        cls.admin_user = User.objects.create_user(
            username='admin_rajesh_test', email='rajesh@test.in', password='pass',
            first_name='Rajesh', last_name='Kannan', is_staff=True, is_superuser=True
        )
        cls.admin_profile = StaffProfile.objects.create(
            user=cls.admin_user, role='admin', employee_id='TST-EXEC-01',
            branch='Chennai HQ', department='Executive', approval_limit_inr=Decimal('2500000.00')
        )

        cls.mgr_user = User.objects.create_user(
            username='mgr_vikram_test', email='vikram@test.in', password='pass',
            first_name='Vikram', last_name='Sundaram', is_staff=True
        )
        cls.mgr_user.groups.add(cls.mgr_group)
        cls.mgr_profile = StaffProfile.objects.create(
            user=cls.mgr_user, role='manager', employee_id='TST-MGR-02',
            branch='Coimbatore Hub', department='Regional Ops', approval_limit_inr=Decimal('500000.00')
        )

        cls.sales_user = User.objects.create_user(
            username='sales_priya_test', email='priya@test.in', password='pass',
            first_name='Priya', last_name='Natarajan', is_staff=True
        )
        cls.sales_user.groups.add(cls.sales_exec_group)
        cls.sales_profile = StaffProfile.objects.create(
            user=cls.sales_user, role='sales_executive', employee_id='TST-SLS-03',
            branch='Chennai HQ', department='Sales', monthly_sales_target_inr=Decimal('1500000.00')
        )

        cls.ops_user = User.objects.create_user(
            username='ops_suresh_test', email='suresh@test.in', password='pass',
            first_name='Suresh', last_name='Balaji', is_staff=True
        )
        cls.ops_user.groups.add(cls.ops_group)
        cls.ops_profile = StaffProfile.objects.create(
            user=cls.ops_user, role='operations', employee_id='TST-OPS-04',
            branch='Coimbatore Hub', department='Fleet Ops', approval_limit_inr=Decimal('100000.00')
        )

        cls.acct_user = User.objects.create_user(
            username='acct_meena_test', email='meena@test.in', password='pass',
            first_name='Meenakshi', last_name='Raman', is_staff=True
        )
        cls.acct_user.groups.add(cls.acct_group)
        cls.acct_profile = StaffProfile.objects.create(
            user=cls.acct_user, role='operation_account', employee_id='TST-FIN-05',
            branch='Chennai HQ', department='Accounts', approval_limit_inr=Decimal('250000.00')
        )

        cls.driver_user = User.objects.create_user(
            username='driver_muthu_test', email='muthu@test.in', password='pass',
            first_name='Muthukumar', last_name='S', is_staff=True
        )
        cls.driver_user.groups.add(cls.driver_group)
        cls.driver_profile = StaffProfile.objects.create(
            user=cls.driver_user, role='driver', employee_id='TST-DRV-06',
            branch='Madurai Depo', department='Field Ops'
        )

    def setUp(self):
        self.client = Client()

    def test_01_staff_profile_model_and_role_choices(self):
        """Verify StaffProfile model properties, badges, and choices."""
        self.assertEqual(self.admin_profile.role_badge_color, '#e11d48')
        self.assertEqual(self.sales_profile.role_badge_color, '#10b981')
        self.assertEqual(self.ops_profile.role_badge_color, '#0284c7')
        self.assertEqual(self.acct_profile.role_badge_color, '#d97706')
        self.assertEqual(self.driver_profile.role_badge_color, '#f97316')
        self.assertEqual(self.mgr_profile.role_badge_color, '#8b5cf6')

        self.assertEqual(self.admin_profile.display_name, 'Rajesh Kannan')
        self.assertIn('TST-EXEC-01', str(self.admin_profile))

    def test_02_rbac_context_processor(self):
        """Verify rbac_context provides correct role flags and demo personas."""
        from travelerp.context_processors import rbac_context

        # Authenticate as Sales Executive
        self.client.force_login(self.sales_user)
        request = self.client.get('/dashboard/').wsgi_request

        ctx = rbac_context(request)
        self.assertTrue(ctx['is_sales_executive'])
        self.assertTrue(ctx['is_sales'])
        self.assertFalse(ctx['is_admin'])
        self.assertEqual(ctx['user_role_code'], 'sales_executive')
        self.assertEqual(ctx['user_employee_id'], 'TST-SLS-03')
        self.assertGreaterEqual(len(ctx['demo_personas']), 8)

    def test_03_switch_persona_endpoint(self):
        """Verify 1-click persona switcher seamlessly changes active user session."""
        self.client.force_login(self.admin_user)
        
        # Switch to Priya Natarajan (Sales)
        response = self.client.get(
            reverse('auth-switch-persona', kwargs={'username': 'sales_priya_test'}),
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'].username, 'sales_priya_test')

        # Switch to Suresh Balaji (Operations)
        response2 = self.client.get(
            reverse('auth-switch-persona', kwargs={'username': 'ops_suresh_test'}),
            follow=True
        )
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.context['user'].username, 'ops_suresh_test')

    def test_04_staff_roles_matrix_view_renders_cleanly(self):
        """Verify Staff Directory & RBAC Matrix view loads with 200 OK."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('staff-roles-matrix'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff_roles_matrix.html')
        self.assertContains(response, 'Staff Directory &amp; RBAC Clearance Matrix')
        self.assertContains(response, 'Departmental Capability Clearance Matrix')
        self.assertContains(response, 'Operational Audit Log')

    def test_05_role_tailored_dashboard_rendering(self):
        """Verify that dashboard renders role-tailored workspace ribbons for each user."""
        # 1. Sales Executive Dashboard
        self.client.force_login(self.sales_user)
        resp_sales = self.client.get(reverse('dashboard'))
        self.assertEqual(resp_sales.status_code, 200)
        self.assertContains(resp_sales, 'Monthly Sales Target Progress')

        # 2. Operations Dashboard
        self.client.force_login(self.ops_user)
        resp_ops = self.client.get(reverse('dashboard'))
        self.assertEqual(resp_ops.status_code, 200)
        self.assertContains(resp_ops, 'Open Fleet Radar')

        # 3. Accounts & Billing Dashboard
        self.client.force_login(self.acct_user)
        resp_acct = self.client.get(reverse('dashboard'))
        self.assertEqual(resp_acct.status_code, 200)
        self.assertContains(resp_acct, 'Tax Invoicing &amp; Receivables')

        # 4. General Manager Approvals Dashboard
        self.client.force_login(self.mgr_user)
        resp_mgr = self.client.get(reverse('dashboard'))
        self.assertEqual(resp_mgr.status_code, 200)
        self.assertContains(resp_mgr, 'Pending Executive Approvals Queue')

        # 5. Field Chauffeur Tour Cockpit
        self.client.force_login(self.driver_user)
        resp_driver = self.client.get(reverse('dashboard'))
        self.assertEqual(resp_driver.status_code, 200)
        self.assertContains(resp_driver, 'Current Assigned Chauffeur Duty')
