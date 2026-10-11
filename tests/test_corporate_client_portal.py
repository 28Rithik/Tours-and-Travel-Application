import io
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import Client as CorporateCustomer
from fleet_contracts.models import (
    TransportContract, CommuterManifest,
    ContractSLAPenalty, ContractMonthlyInvoice
)
from fleet_commute.models import (
    EnterpriseSSOConfig, CorporateAuthAuditLog, CorporateUserRole
)

User = get_user_model()


class CorporateClientPortalTests(TestCase):
    def setUp(self):
        # 1. Create two separate corporate client customers (multi-tenancy)
        self.customer_a = CorporateCustomer.objects.create(
            name="Cognizant Technology Solutions",
            email="transport@cognizant.com"
        )
        self.customer_b = CorporateCustomer.objects.create(
            name="Infosys Limited",
            email="mobility@infosys.com"
        )

        # 2. Create contracts for both customers
        today = timezone.now().date()
        self.contract_a = TransportContract.objects.create(
            name="Cognizant MEPZ Campus Commute 2026-27",
            customer=self.customer_a,
            start_date=today,
            end_date=today.replace(year=today.year + 1),
            status="active",
            committed_vehicle_count=15
        )
        self.contract_b = TransportContract.objects.create(
            name="Infosys Mahindra World City Commute 2026-27",
            customer=self.customer_b,
            start_date=today,
            end_date=today.replace(year=today.year + 1),
            status="active",
            committed_vehicle_count=20
        )

        # 3. Create sample commuter for Customer A
        self.commuter_a = CommuterManifest.objects.create(
            contract=self.contract_a,
            commuter_id="CTS9901",
            name="Divya Sundaram",
            gender="female",
            phone="9840112345",
            department_or_grade="Digital Business Operations",
            requires_night_escort=True,
            is_active=True
        )

        # 4. Create sample SLA Penalty for Contract A
        self.sla_penalty = ContractSLAPenalty.objects.create(
            contract=self.contract_a,
            date=today,
            penalty_type="shift_delay",
            penalty_amount=500.00,
            description="Morning pickup delayed by 18 minutes due to route diversion.",
            waived=False
        )

        # 5. Create users
        self.admin_user = User.objects.create_superuser(
            username="admin_operator",
            password="adminpassword123",
            email="admin@travelerp.com"
        )
        self.client_user_a = User.objects.create_user(
            username="cognizant_hr",
            password="hrpassword123",
            email="hr@cognizant.com"
        )
        # Link client_user_a to customer_a via CustomerAccount
        from customer_portal.models import CustomerAccount
        CustomerAccount.objects.create(
            user=self.client_user_a,
            client_record=self.customer_a
        )

    def test_portal_index_view(self):
        """Portal index should list active contracts in clean white UI."""
        client = Client()
        response = client.get(reverse('fleet_commute:client_portal_index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cognizant MEPZ Campus Commute")
        self.assertContains(response, "Infosys Mahindra World City Commute")

    def test_portal_index_alias_route(self):
        """Root alias /client/portal/ should also return 200."""
        client = Client()
        response = client.get(reverse('client_portal_root_index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Corporate Client B2B Portals Directory")

    def test_client_portal_view(self):
        """Dedicated client portal view should load all tabs and commuter manifest."""
        client = Client()
        response = client.get(reverse('fleet_commute:client_transparency_portal', args=[self.contract_a.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Divya Sundaram")
        self.assertContains(response, "CTS9901")
        self.assertContains(response, "Live Shift Fleet Radar")
        self.assertContains(response, "Scope 3 ESG Sustainability")

    def test_multi_tenant_isolation_forbidden(self):
        """A user linked to Customer A attempting to access Customer B's contract should receive HTTP 403."""
        client = Client()
        client.force_login(self.client_user_a)
        # Attempt to access Contract B (Infosys) while logged in as Cognizant
        response = client.get(reverse('fleet_commute:client_transparency_portal', args=[self.contract_b.id]))
        self.assertEqual(response.status_code, 403)

    def test_telematics_live_fleet_api(self):
        """Live fleet telematics API returns JSON with vehicles and geofence."""
        client = Client()
        response = client.get(reverse('fleet_commute:api_client_portal_live_fleet', args=[self.contract_a.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertGreaterEqual(len(data['vehicles']), 1)
        self.assertIn('campus_location', data)
        self.assertIn('shift_progress', data)

    def test_api_client_roster_add(self):
        """Corporate HR can self-service add a commuter."""
        client = Client()
        post_data = {
            'commuter_id': 'CTS9902',
            'name': 'Rahul Nair',
            'gender': 'male',
            'phone': '9840223456',
            'department': 'Cloud Architecture',
            'pickup_address': 'Navalur Toll Gate, OMR',
            'requires_night_escort': 'false'
        }
        response = client.post(reverse('fleet_commute:api_client_roster_add', args=[self.contract_a.id]), post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CommuterManifest.objects.filter(contract=self.contract_a, commuter_id='CTS9902').exists())

    def test_api_client_roster_swap(self):
        """Corporate HR can toggle commuter active status."""
        client = Client()
        response = client.post(
            reverse('fleet_commute:api_client_roster_swap', args=[self.contract_a.id]),
            {'commuter_pk': self.commuter_a.id, 'is_active': 'false'}
        )
        self.assertEqual(response.status_code, 200)
        self.commuter_a.refresh_from_db()
        self.assertFalse(self.commuter_a.is_active)

    def test_api_client_roster_import_csv(self):
        """Corporate HR can bulk import commuters via CSV."""
        client = Client()
        csv_content = (
            "Employee_ID,Name,Gender,Phone,Department,Pickup_Address,Requires_Night_Escort\n"
            "CTS8801,Meera Nambiar,Female,9840999888,AI Lab,Siruseri Sipcot Gate,Yes\n"
            "CTS8802,Vignesh Raman,Male,9840999777,DevOps,Perungudi Bus Stop,No\n"
        )
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = "bulk_roster.csv"

        response = client.post(
            reverse('fleet_commute:api_client_roster_import_csv', args=[self.contract_a.id]),
            {'roster_csv': csv_file}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CommuterManifest.objects.filter(contract=self.contract_a, commuter_id='CTS8801').exists())
        self.assertTrue(CommuterManifest.objects.filter(contract=self.contract_a, commuter_id='CTS8802').exists())

    def test_client_roster_export_csv(self):
        """Exporting roster returns CSV attachment."""
        client = Client()
        response = client.get(reverse('fleet_commute:client_roster_export_csv', args=[self.contract_a.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn("Divya Sundaram", response.content.decode('utf-8'))

    def test_api_client_dispute_sla_penalty(self):
        """Corporate client filing an SLA dispute updates penalty waiver notes."""
        client = Client()
        response = client.post(
            reverse('fleet_commute:api_client_dispute_sla_penalty', args=[self.contract_a.id]),
            {'penalty_id': self.sla_penalty.id, 'dispute_notes': 'Delay due to flash rainfall and OMR waterlogging.'}
        )
        self.assertEqual(response.status_code, 200)
        self.sla_penalty.refresh_from_db()
        self.assertIn("[CLIENT DISPUTE]", self.sla_penalty.waiver_reason)
        self.assertIn("waterlogging", self.sla_penalty.waiver_reason)

    def test_client_esg_certificate_view(self):
        """ESG certificate view renders with metric ton calculations."""
        client = Client()
        response = client.get(reverse('fleet_commute:client_esg_certificate', args=[self.contract_a.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CERTIFICATE OF SUSTAINABLE COMMUTE IMPACT")
        self.assertContains(response, self.contract_a.customer.name)

    def test_client_portal_login_page_renders(self):
        """Corporate client login screen loads with 200 and white B2B portal layout."""
        client = Client()
        response = client.get(reverse('client_portal_root_login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Corporate Client Commute Portal")
        self.assertContains(response, "Corporate Credentials")
        self.assertContains(response, "1-Click Corporate Tenant Access")

    def test_client_portal_quick_tenant_login(self):
        """Quick tenant sign-in sets session and redirects to contract portal."""
        client = Client()
        post_data = {
            'action': 'quick_tenant',
            'contract_id': self.contract_a.id,
            'customer_id': self.customer_a.id
        }
        response = client.post(reverse('client_portal_root_login'), post_data)
        self.assertRedirects(response, reverse('fleet_commute:client_transparency_portal', args=[self.contract_a.id]))
        self.assertEqual(client.session.get('corporate_customer_id'), self.customer_a.id)

    def test_client_portal_logout(self):
        """Logging out flushes corporate session and redirects to login."""
        client = Client()
        # Set session first
        session = client.session
        session['corporate_customer_id'] = self.customer_a.id
        session['corporate_client_name'] = self.customer_a.name
        session.save()

        response = client.get(reverse('client_portal_root_logout'))
        self.assertRedirects(response, reverse('fleet_commute:client_portal_login'))
        self.assertNotIn('corporate_customer_id', client.session)

    def test_client_portal_otp_dispatch(self):
        """Requesting WhatsApp OTP creates a CustomerOTP and logs audit event."""
        from customer_portal.models import CustomerOTP
        from fleet_commute.models import CorporateAuthAuditLog

        client = Client()
        post_data = {
            'action': 'send_otp',
            'phone': '9840112345'
        }
        response = client.post(reverse('client_portal_root_login'), post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "authentication code sent via WhatsApp")
        self.assertTrue(CustomerOTP.objects.filter(phone='9840112345').exists())
        self.assertTrue(CorporateAuthAuditLog.objects.filter(event_type='otp_dispatched').exists())

    def test_client_portal_otp_verification_success(self):
        """Submitting valid OTP logs user in and redirects to contract portal."""
        from customer_portal.models import CustomerOTP
        from fleet_commute.models import CorporateAuthAuditLog
        from datetime import timedelta

        otp = CustomerOTP.objects.create(
            phone='9840112345',
            otp_code='654321',
            expires_at=timezone.now() + timedelta(minutes=10)
        )

        client = Client()
        post_data = {
            'action': 'verify_otp',
            'phone': '9840112345',
            'otp_code': '654321'
        }
        response = client.post(reverse('client_portal_root_login'), post_data)
        self.assertEqual(response.status_code, 302)
        otp.refresh_from_db()
        self.assertTrue(otp.is_verified)
        self.assertTrue(CorporateAuthAuditLog.objects.filter(event_type='otp_verified_success').exists())

    def test_client_portal_otp_verification_failure(self):
        """Submitting wrong OTP shows error and logs failed attempt."""
        from fleet_commute.models import CorporateAuthAuditLog

        client = Client()
        post_data = {
            'action': 'verify_otp',
            'phone': '9840112345',
            'otp_code': '000000'
        }
        response = client.post(reverse('client_portal_root_login'), post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid or expired verification code")
        self.assertTrue(CorporateAuthAuditLog.objects.filter(event_type='otp_verified_failed').exists())

    def test_switch_corporate_role_and_audit_log(self):
        """Corporate user can switch active persona and generates an immutable audit record."""
        from fleet_commute.models import CorporateAuthAuditLog

        client = Client()
        client.force_login(self.client_user_a)

        url = reverse('fleet_commute:api_switch_corporate_role', args=[self.contract_a.id])
        response = client.post(url, {'role': 'safety_auditor'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['active_role'], 'safety_auditor')
        self.assertEqual(client.session.get('corporate_role'), 'safety_auditor')

        # Verify audit log
        log = CorporateAuthAuditLog.objects.filter(event_type='role_switched', client=self.customer_a).latest('timestamp')
        self.assertIn('safety_auditor', log.status_reason)

    def test_unmask_commuter_pii_with_dpdp_audit(self):
        """Authorized transport admin can reveal masked phone and generates statutory DPDP audit log."""
        from fleet_commute.models import CorporateAuthAuditLog

        client = Client()
        client.force_login(self.client_user_a)

        url = reverse('fleet_commute:api_unmask_commuter_pii', args=[self.contract_a.id])
        response = client.post(url, {
            'commuter_pk': self.commuter_a.id,
            'reason': 'Statutory night shift isolated drop verification'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['unmasked_phone'], '9840112345')

        # Verify statutory audit entry
        audit_entry = CorporateAuthAuditLog.objects.filter(event_type='pii_unmasked', client=self.customer_a).latest('timestamp')
        self.assertIn("Statutory night shift", audit_entry.status_reason)
        self.assertIn(self.commuter_a.commuter_id, audit_entry.identifier)

    def test_safety_auditor_pii_unmask_guardrail(self):
        """POSH & Safety Auditor can only unmask female or night escort commuters."""
        male_commuter = CommuterManifest.objects.create(
            contract=self.contract_a,
            commuter_id="CTS1002",
            name="Ramesh Krishnan",
            gender="male",
            phone="9840998877",
            requires_night_escort=False,
            is_active=True
        )

        client = Client()
        client.force_login(self.client_user_a)

        # Switch to safety auditor
        client.post(reverse('fleet_commute:api_switch_corporate_role', args=[self.contract_a.id]), {'role': 'safety_auditor'})

        url = reverse('fleet_commute:api_unmask_commuter_pii', args=[self.contract_a.id])

        # Male general commuter -> 403 Forbidden
        response = client.post(url, {
            'commuter_pk': male_commuter.id,
            'reason': 'Routine check'
        })
        self.assertEqual(response.status_code, 403)
        self.assertIn("Safety Auditors may only unmask", response.json()['message'])

        # Female night commuter -> 200 OK
        response_female = client.post(url, {
            'commuter_pk': self.commuter_a.id,
            'reason': 'POSH night drop audit'
        })
        self.assertEqual(response_female.status_code, 200)
        self.assertEqual(response_female.json()['unmasked_phone'], '9840112345')

    def test_role_rbac_roster_modification_denied_for_finance_and_gate(self):
        """Finance Officer and Gate Security personas are blocked from modifying commuter roster."""
        client = Client()
        client.force_login(self.client_user_a)

        # Switch role to finance_officer
        client.post(reverse('fleet_commute:api_switch_corporate_role', args=[self.contract_a.id]), {'role': 'finance_officer'})

        add_url = reverse('fleet_commute:api_client_roster_add', args=[self.contract_a.id])
        resp_add = client.post(add_url, {
            'commuter_id': 'CTS9999',
            'name': 'Test New Employee',
            'phone': '9840555555'
        })
        self.assertEqual(resp_add.status_code, 403)
        self.assertIn("requires Transport Admin persona", resp_add.json()['message'])

        # Switch to gate_security
        client.post(reverse('fleet_commute:api_switch_corporate_role', args=[self.contract_a.id]), {'role': 'gate_security'})
        swap_url = reverse('fleet_commute:api_client_roster_swap', args=[self.contract_a.id])
        resp_swap = client.post(swap_url, {
            'commuter_pk': self.commuter_a.id,
            'is_active': 'false'
        })
        self.assertEqual(resp_swap.status_code, 403)

    def test_role_rbac_financial_dispute_denied_for_gate_security(self):
        """Gate security cannot dispute SLA penalties or view B2B tax invoice detail."""
        client = Client()
        client.force_login(self.client_user_a)

        # Switch to gate_security
        client.post(reverse('fleet_commute:api_switch_corporate_role', args=[self.contract_a.id]), {'role': 'gate_security'})

        dispute_url = reverse('fleet_commute:api_client_dispute_sla_penalty', args=[self.contract_a.id])
        resp = client.post(dispute_url, {
            'penalty_id': self.sla_penalty.id,
            'dispute_notes': 'Security gate dispute'
        })
        self.assertEqual(resp.status_code, 403)

        # Invoice detail returns 403 PermissionDenied
        today = timezone.now().date()
        invoice = ContractMonthlyInvoice.objects.create(
            contract=self.contract_a,
            invoice_number="INV-CTS-2026-09",
            billing_month=today,
            from_date=today,
            to_date=today,
            total_trips_completed=45,
            total_kms_run=Decimal('1200.00'),
            base_contract_amount=Decimal('150000.00'),
            sla_penalty_deduction=Decimal('500.00'),
            status="generated"
        )
        invoice_url = reverse('fleet_commute:client_invoice_pdf', args=[self.contract_a.id, invoice.id])
        resp_inv = client.get(invoice_url)
        self.assertEqual(resp_inv.status_code, 403)

    def test_ip_allowlist_enforcement(self):
        """When allowed_ip_ranges is configured on CorporateUserRole, outside IPs are blocked."""
        from fleet_commute.models import CorporateUserRole

        CorporateUserRole.objects.create(
            user=self.client_user_a,
            client=self.customer_a,
            role='transport_admin',
            allowed_ip_ranges='192.168.1.0/24',
            is_active=True
        )

        client = Client()
        client.force_login(self.client_user_a)

        portal_url = reverse('fleet_commute:client_transparency_portal', args=[self.contract_a.id])

        # Default IP 127.0.0.1 -> blocked (HTTP 403)
        resp_blocked = client.get(portal_url)
        self.assertEqual(resp_blocked.status_code, 403)

        # Allowed corporate VPN subnet -> 200 OK
        resp_allowed = client.get(portal_url, REMOTE_ADDR='192.168.1.50')
        self.assertEqual(resp_allowed.status_code, 200)

    # ==========================================================================
    # Phase 3 Tests: Enterprise SSO & White-Label Subdomains
    # ==========================================================================
    def test_sso_domain_lookup_api_matched_and_unmatched(self):
        """Domain lookup API returns SSO IdP & brand details for configured corporate domains."""
        sso_cfg = EnterpriseSSOConfig.objects.create(
            client=self.customer_a,
            domain="cognizant.com",
            idp_display_name="Microsoft Entra ID (Azure AD)",
            idp_entity_id="https://sts.windows.net/cognizant-tenant-id/",
            sso_login_url="https://login.microsoftonline.com/cognizant/saml2",
            brand_subdomain_slug="cognizant",
            brand_primary_color="#0033a0",
            brand_logo_url="/static/logos/cognizant.svg",
            campus_branches=[
                {"id": "mepz", "name": "MEPZ Campus"},
                {"id": "siruseri", "name": "Siruseri IT Park"}
            ],
            is_active=True,
            enforce_sso_only=False
        )

        client = Client()
        lookup_url = reverse('fleet_commute:api_sso_domain_lookup')

        # 1. Matched lookup by email
        resp_matched = client.get(lookup_url, {'email': 'ananya.k@cognizant.com'})
        self.assertEqual(resp_matched.status_code, 200)
        data = resp_matched.json()
        self.assertTrue(data['matched'])
        self.assertEqual(data['client_name'], 'Cognizant Technology Solutions')
        self.assertEqual(data['idp_name'], 'Microsoft Entra ID (Azure AD)')
        self.assertEqual(data['brand_slug'], 'cognizant')
        self.assertEqual(data['brand_color'], '#0033a0')
        self.assertIn('sso_initiate_url', data)
        self.assertEqual(len(data['campus_branches']), 2)

        # 2. Matched lookup by naked domain
        resp_domain = client.get(lookup_url, {'domain': 'COGNIZANT.COM'})
        self.assertEqual(resp_domain.status_code, 200)
        self.assertTrue(resp_domain.json()['matched'])

        # 3. Unmatched domain
        resp_unmatched = client.get(lookup_url, {'email': 'unknown@randomcorp.in'})
        self.assertEqual(resp_unmatched.status_code, 200)
        self.assertFalse(resp_unmatched.json()['matched'])

        # 4. Root alias /client/api/sso/lookup-domain/
        resp_alias = client.get(reverse('client_portal_root_sso_domain_lookup'), {'domain': 'cognizant.com'})
        self.assertEqual(resp_alias.status_code, 200)
        self.assertTrue(resp_alias.json()['matched'])

    def test_sso_initiate_redirect_and_audit_log(self):
        """SSO initiate view redirects to IdP/callback and creates sso_redirect audit log."""
        sso_cfg = EnterpriseSSOConfig.objects.create(
            client=self.customer_a,
            domain="cognizant.com",
            idp_display_name="Microsoft Entra ID (Azure AD)",
            sso_login_url="https://login.microsoftonline.com/cognizant/saml2",
            brand_subdomain_slug="cognizant",
            is_active=True
        )

        client = Client()
        initiate_url = reverse('fleet_commute:client_sso_initiate', args=['cognizant'])
        response = client.get(initiate_url + '?saml_mock=1&campus_branch=siruseri')

        # In mock mode, should redirect to callback
        self.assertEqual(response.status_code, 302)
        self.assertIn('callback', response.url)
        self.assertIn('saml_mock=1', response.url)

        # Verify audit log
        audit = CorporateAuthAuditLog.objects.filter(
            client=self.customer_a, event_type='sso_redirect'
        ).first()
        self.assertIsNotNone(audit)
        self.assertIn('Initiated SSO authentication', audit.status_reason)

    def test_sso_callback_jit_provisioning_and_session(self):
        """SSO callback JIT creates user, assigns role, establishes session, and redirects to contract portal."""
        sso_cfg = EnterpriseSSOConfig.objects.create(
            client=self.customer_a,
            domain="cognizant.com",
            idp_display_name="Microsoft Entra ID (Azure AD)",
            brand_subdomain_slug="cognizant",
            is_active=True
        )

        client = Client()
        callback_url = reverse('fleet_commute:client_sso_callback', args=['cognizant'])
        target_email = "ananya.transport@cognizant.com"

        resp = client.get(callback_url, {
            'saml_mock': '1',
            'email': target_email,
            'first_name': 'Ananya',
            'last_name': 'Krishnan',
            'campus_branch': 'mepz_campus'
        })

        # Redirects to client transparency portal for active contract
        self.assertEqual(resp.status_code, 302)
        self.assertIn(str(self.contract_a.id), resp.url)

        # Verify JIT user created
        user = User.objects.filter(username=target_email).first()
        self.assertIsNotNone(user)
        self.assertEqual(user.first_name, 'Ananya')
        self.assertEqual(user.email, target_email)

        # Verify CorporateUserRole provisioned
        corp_role = CorporateUserRole.objects.filter(user=user, client=self.customer_a).first()
        self.assertIsNotNone(corp_role)
        self.assertEqual(corp_role.role, 'transport_admin')

        # Verify Session keys
        self.assertEqual(client.session['corporate_customer_id'], self.customer_a.id)
        self.assertEqual(client.session['corporate_client_name'], self.customer_a.name)
        self.assertEqual(client.session['corporate_contract_id'], self.contract_a.id)
        self.assertTrue(client.session['sso_authenticated'])
        self.assertEqual(client.session['corporate_campus_branch'], 'mepz_campus')

        # Verify audit log
        audit = CorporateAuthAuditLog.objects.filter(
            client=self.customer_a, event_type='sso_login_success'
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.identifier, target_email)

    def test_sso_callback_domain_mismatch_fails(self):
        """SSO callback with domain mismatch is rejected with an audit log."""
        sso_cfg = EnterpriseSSOConfig.objects.create(
            client=self.customer_a,
            domain="cognizant.com",
            brand_subdomain_slug="cognizant",
            is_active=True
        )

        client = Client()
        callback_url = reverse('fleet_commute:client_sso_callback', args=['cognizant'])

        # Attacker tries assertion for another domain
        resp = client.get(callback_url, {
            'saml_mock': '1',
            'email': 'intruder@roguecorp.com'
        })

        self.assertEqual(resp.status_code, 302)
        self.assertIn('client-portal/login', resp.url)

        # Verify failure audit
        audit = CorporateAuthAuditLog.objects.filter(
            client=self.customer_a, event_type='sso_login_failed'
        ).first()
        self.assertIsNotNone(audit)
        self.assertIn('Enterprise domain mismatch', audit.status_reason)

    def test_sso_enforce_sso_only_blocks_password_login(self):
        """When enforce_sso_only is enabled, password sign-in for that domain is blocked."""
        sso_cfg = EnterpriseSSOConfig.objects.create(
            client=self.customer_a,
            domain="cognizant.com",
            idp_display_name="Microsoft Entra ID (Azure AD)",
            brand_subdomain_slug="cognizant",
            is_active=True,
            enforce_sso_only=True
        )

        client = Client()
        login_url = reverse('fleet_commute:client_portal_login')

        # Attempt credentials login with user@cognizant.com
        resp = client.post(login_url, {
            'action': 'credentials',
            'username': 'director@cognizant.com',
            'password': 'anypassword123'
        })

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "requires Single Sign-On (SSO)")
        self.assertContains(resp, "Microsoft Entra ID (Azure AD)")

    def test_white_label_branded_login_view_rendering(self):
        """Branded login view renders client custom colors, campus branches, and SSO button."""
        sso_cfg = EnterpriseSSOConfig.objects.create(
            client=self.customer_a,
            domain="cognizant.com",
            idp_display_name="Microsoft Entra ID (Azure AD)",
            brand_subdomain_slug="cognizant",
            brand_primary_color="#0033a0",
            campus_branches=[
                {"id": "mepz", "name": "MEPZ Campus"},
                {"id": "siruseri", "name": "Siruseri IT Park"}
            ],
            is_active=True,
            enforce_sso_only=True
        )

        client = Client()
        branded_url = reverse('fleet_commute:client_branded_login', args=['cognizant'])
        resp = client.get(branded_url)

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Cognizant Technology Solutions")
        self.assertContains(resp, "MEPZ Campus")
        self.assertContains(resp, "Siruseri IT Park")
        self.assertContains(resp, "#0033a0")
        self.assertContains(resp, "Sign in with Corporate SSO")
        self.assertContains(resp, "SSO Enforced")

    def test_client_portal_logout_clears_sso_session(self):
        """Logout endpoint clears SSO authentication flags, domain, and campus branch from session."""
        client = Client()
        session = client.session
        session['corporate_customer_id'] = self.customer_a.id
        session['corporate_client_name'] = self.customer_a.name
        session['corporate_contract_id'] = self.contract_a.id
        session['sso_authenticated'] = True
        session['sso_domain'] = "cognizant.com"
        session['corporate_campus_branch'] = "siruseri"
        session.save()

        logout_url = reverse('fleet_commute:client_portal_logout')
        resp = client.get(logout_url)

        self.assertEqual(resp.status_code, 302)
        self.assertNotIn('sso_authenticated', client.session)
        self.assertNotIn('sso_domain', client.session)
        self.assertNotIn('corporate_campus_branch', client.session)
        self.assertNotIn('corporate_customer_id', client.session)




