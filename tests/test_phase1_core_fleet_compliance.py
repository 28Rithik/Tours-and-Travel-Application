import datetime
from decimal import Decimal
import json

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse

from core.models import (
    Party, Client as CoreClient, Supplier as CoreSupplier,
    VehicleType, Driver, Cleaner, DriverEmploymentPeriod,
    CleanerEmploymentPeriod, Vehicle, RateCard, LicenseClass
)
from core_partners.models import Client as PartnerClient, Supplier as PartnerSupplier, RateCard as PartnerRateCard
from core_crew.models import Driver as CrewDriver, Cleaner as CrewCleaner, LicenseClass as CrewLicenseClass
from suppliers.models import SupplierContract, CommissionRule
from maintenance.models import (
    ComplianceDocument, ServiceReminder, DefectTicket,
    VehicleDamageInspection, VehicleDamageMarker
)
from maintenance.services import (
    check_compliance_expiries,
    verify_trip_dispatch_compliance,
    check_preventive_maintenance_due
)


class Phase1CoreFleetComplianceTests(TestCase):
    """
    End-to-End Master Backend Test Suite for Phase 1:
    Core Master Data, Fleet Assets & Crew Compliance Engine.
    """

    def setUp(self):
        self.user = User.objects.create_superuser(
            username='phase1_admin',
            email='admin@travelerp.com',
            password='password123'
        )
        self.client = Client()
        self.client.force_login(self.user)

        self.today = timezone.localdate()

        # Create basic party entities
        self.corporate_client = CoreClient.objects.create(
            name='Cognizant Technology Solutions',
            party_type='corporate',
            phone='04422334455',
            email='transport@cognizant.com',
            gstin='33AAACC1234D1Z5',
            state_code='33',
            credit_period_days=30
        )

        self.supplier_party = CoreSupplier.objects.create(
            name='Sri Balaji Fleet Suppliers',
            party_type='supplier',
            phone='9840098765',
            email='balajifleet@gmail.com',
            state_code='33'
        )

        self.vehicle_type = VehicleType.objects.create(
            name='Toyota Innova Crysta Phase1',
            seating_capacity=7,
            default_day_rate=Decimal('3500.00'),
            default_km_rate=Decimal('16.00'),
            has_ac=True,
            is_luxury=True
        )

    # -------------------------------------------------------------------------
    # 1. Master Records & Entity Validation
    # -------------------------------------------------------------------------

    def test_party_and_client_models(self):
        """Test party and client models creation, properties, and string representations."""
        self.assertEqual(str(self.corporate_client), 'Cognizant Technology Solutions')
        self.assertEqual(self.corporate_client.party_type, 'corporate')
        self.assertEqual(str(self.supplier_party), 'Sri Balaji Fleet Suppliers')
        self.assertEqual(self.supplier_party.party_type, 'supplier')

    def test_vehicle_type_model_and_api(self):
        """Test VehicleType fields and api_get_vehicle_types endpoint."""
        self.assertEqual(str(self.vehicle_type), 'Toyota Innova Crysta Phase1')
        self.assertEqual(self.vehicle_type.seating_capacity, 7)

        url = reverse('api_get_vehicle_types')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn(str(self.vehicle_type.id), data)
        self.assertEqual(data[str(self.vehicle_type.id)]['default_day_rate'], '3500.00')

    def test_driver_clean_validation_rules(self):
        """Test driver clean() validation for owned, supplier, and temporary drivers."""
        # 1. Owned driver missing Aadhar/Bank/Joining date should raise ValidationError
        owned_driver = Driver(
            name='Murugan K',
            driver_type='owned',
            phone='9842511001'
        )
        with self.assertRaises(ValidationError) as ctx:
            owned_driver.clean()
        self.assertIn('aadhar_number', ctx.exception.message_dict)
        self.assertIn('bank_account_number', ctx.exception.message_dict)
        self.assertIn('joining_date', ctx.exception.message_dict)

        # 2. Owned driver with complete required fields passes
        owned_driver.aadhar_number = '123456789012'
        owned_driver.bank_account_number = 'SBIN000123456789'
        owned_driver.joining_date = self.today - datetime.timedelta(days=100)
        owned_driver.clean()  # Should not raise
        owned_driver.save()
        self.assertEqual(str(owned_driver), 'Murugan K')

        # 3. Supplier driver requires employer_party of type 'supplier'
        supplier_driver = Driver(
            name='Kumar S',
            driver_type='supplier',
            employer_party=self.corporate_client  # wrong type (corporate)
        )
        with self.assertRaises(ValidationError) as ctx:
            supplier_driver.clean()
        self.assertIn('employer_party', ctx.exception.message_dict)

        supplier_driver.employer_party = self.supplier_party
        supplier_driver.clean()  # Should not raise

        # 4. Temporary driver requires upi_id
        temp_driver = Driver(name='Ravi T', driver_type='temporary')
        with self.assertRaises(ValidationError) as ctx:
            temp_driver.clean()
        self.assertIn('upi_id', ctx.exception.message_dict)

    def test_driver_license_status_property(self):
        """Test driver.license_status property accurately reports validity."""
        driver = Driver.objects.create(
            name='Senthil Nathan',
            driver_type='owned',
            aadhar_number='999988887777',
            bank_account_number='HDFC0012345',
            joining_date=self.today - datetime.timedelta(days=365)
        )

        # Case 1: No expiry set
        self.assertEqual(driver.license_status['status'], 'missing')

        # Case 2: Expired license
        driver.license_validity_tr = self.today - datetime.timedelta(days=10)
        self.assertEqual(driver.license_status['status'], 'expired')

        # Case 3: Expiring soon (within 30 days)
        driver.license_validity_tr = self.today + datetime.timedelta(days=15)
        self.assertEqual(driver.license_status['status'], 'expiring_soon')

        # Case 4: Valid (more than 30 days)
        driver.license_validity_tr = self.today + datetime.timedelta(days=180)
        self.assertEqual(driver.license_status['status'], 'valid')

    def test_cleaner_validation_and_clean_rules(self):
        """Test cleaner model validation for can_drive rules and employment periods."""
        cleaner = Cleaner(name='Selvam V', can_drive=True)
        with self.assertRaises(ValidationError) as ctx:
            cleaner.clean()
        self.assertIn('license_number', ctx.exception.message_dict)

        cleaner.license_number = 'TN-52-DRV-0091'
        with self.assertRaises(ValidationError) as ctx2:
            cleaner.clean()
        self.assertIn('license_validity', ctx2.exception.message_dict)

        cleaner.license_validity = self.today + datetime.timedelta(days=200)
        cleaner.clean()
        cleaner.save()
        self.assertEqual(str(cleaner), 'Selvam V')

    def test_vehicle_ownership_validation_and_compliance_sync(self):
        """Test vehicle ownership rules and automatic sync of compliance documents."""
        # 1. Outsourced vehicle must have owner_party
        outsourced_veh = Vehicle(
            registration_number='TN-52-OUT-1001',
            ownership_type='outsourced',
            vehicle_type=self.vehicle_type
        )
        with self.assertRaises(ValidationError) as ctx:
            outsourced_veh.clean()
        self.assertIn('owner_party', ctx.exception.message_dict)

        # 2. Owned vehicle cannot have a supplier owner_party
        owned_veh = Vehicle(
            registration_number='TN-52-OWN-1002',
            ownership_type='owned',
            owner_party=self.supplier_party,
            vehicle_type=self.vehicle_type
        )
        with self.assertRaises(ValidationError) as ctx:
            owned_veh.clean()
        self.assertIn('owner_party', ctx.exception.message_dict)

        # 3. Create valid owned vehicle
        veh = Vehicle.objects.create(
            registration_number='TN-52-AA-9999',
            vehicle_type=self.vehicle_type,
            ownership_type='owned',
            status='available',
            current_km=50000
        )

        # 4. Save ComplianceDocument and verify auto-sync to Vehicle
        comp_doc = ComplianceDocument.objects.create(
            vehicle=veh,
            document_type='insurance',
            document_number='POL-INNOV-8812',
            expiry_date=self.today + datetime.timedelta(days=90),
            insurance_provider='Tata AIG General Insurance',
            coverage_type='comprehensive'
        )
        veh.refresh_from_db()
        self.assertEqual(veh.insurance_expiry, comp_doc.expiry_date)

    def test_vehicle_compliance_status_property(self):
        """Test vehicle.compliance_status property categorization."""
        veh = Vehicle.objects.create(
            registration_number='TN-33-BB-8888',
            vehicle_type=self.vehicle_type,
            status='available',
            insurance_expiry=self.today + datetime.timedelta(days=120),
            fc_expiry=self.today + datetime.timedelta(days=150),
            permit_expiry=self.today + datetime.timedelta(days=200)
        )
        self.assertEqual(veh.compliance_status['status'], 'valid')

        # Expiring soon (<30 days)
        veh.fc_expiry = self.today + datetime.timedelta(days=12)
        self.assertEqual(veh.compliance_status['status'], 'expiring_soon')

        # Expired
        veh.insurance_expiry = self.today - datetime.timedelta(days=5)
        self.assertEqual(veh.compliance_status['status'], 'expired')

    # -------------------------------------------------------------------------
    # 2. Rate Cards & Contract Tariffs
    # -------------------------------------------------------------------------

    def test_rate_card_effective_date_and_overlap_validation(self):
        """Test RateCard model, date logic, and overlapping period prevention."""
        rc1 = RateCard.objects.create(
            party=self.corporate_client,
            vehicle_type=self.vehicle_type,
            effective_from=datetime.date(2026, 1, 1),
            effective_to=datetime.date(2026, 6, 30),
            day_rate=Decimal('3200.00'),
            km_rate=Decimal('15.00'),
            driver_bata=Decimal('400.00')
        )
        self.assertEqual(str(rc1), f'{self.corporate_client} / {self.vehicle_type} / 2026-01-01')

        # Overlapping rate card should raise ValidationError
        rc_overlapping = RateCard(
            party=self.corporate_client,
            vehicle_type=self.vehicle_type,
            effective_from=datetime.date(2026, 3, 1),
            effective_to=datetime.date(2026, 8, 31),
            day_rate=Decimal('3400.00')
        )
        with self.assertRaises(ValidationError):
            rc_overlapping.clean()

        # Non-overlapping future rate card should succeed
        rc2 = RateCard(
            party=self.corporate_client,
            vehicle_type=self.vehicle_type,
            effective_from=datetime.date(2026, 7, 1),
            effective_to=datetime.date(2026, 12, 31),
            day_rate=Decimal('3600.00')
        )
        rc2.clean()
        rc2.save()
        self.assertIsNotNone(rc2.id)

    # -------------------------------------------------------------------------
    # 3. Core Partners, Crew & Suppliers Proxy Models
    # -------------------------------------------------------------------------

    def test_proxy_models_and_supplier_contracts(self):
        """Test core_partners and core_crew proxy models and supplier contracts."""
        # Core partners proxies
        p_client = PartnerClient.objects.filter(id=self.corporate_client.id).first()
        self.assertIsNotNone(p_client)
        self.assertEqual(p_client.name, 'Cognizant Technology Solutions')

        p_supplier = PartnerSupplier.objects.filter(id=self.supplier_party.id).first()
        self.assertIsNotNone(p_supplier)

        # Supplier Contract
        contract = SupplierContract.objects.create(
            supplier=self.supplier_party,
            title='Annual Coach Supply Agreement 2026-2027',
            valid_from=datetime.date(2026, 1, 1),
            valid_to=datetime.date(2026, 12, 31),
            is_active=True
        )
        self.assertIsNotNone(contract.id)
        self.assertTrue(contract.is_active)

        # Commission Rule
        comm = CommissionRule.objects.create(
            agent_name='Yatra Global B2B Desk',
            commission_percentage=Decimal('8.50'),
            is_active=True
        )
        self.assertEqual(comm.commission_percentage, Decimal('8.50'))

    # -------------------------------------------------------------------------
    # 4. Fleet Compliance & Expiration Engine Services
    # -------------------------------------------------------------------------

    def test_check_compliance_expiries_service(self):
        """Test maintenance.services.check_compliance_expiries scanner."""
        # Vehicle 1: Compliant
        Vehicle.objects.create(
            registration_number='TN-01-OK-1111',
            vehicle_type=self.vehicle_type,
            status='available',
            insurance_expiry=self.today + datetime.timedelta(days=180),
            fc_expiry=self.today + datetime.timedelta(days=180)
        )
        # Vehicle 2: Overdue insurance
        Vehicle.objects.create(
            registration_number='TN-01-EXP-2222',
            vehicle_type=self.vehicle_type,
            status='available',
            insurance_expiry=self.today - datetime.timedelta(days=5),
            fc_expiry=self.today + datetime.timedelta(days=180)
        )

        data = check_compliance_expiries(threshold_days=30)
        self.assertIn('expired', data)
        self.assertIn('critical', data)
        self.assertIn('warning', data)
        self.assertGreaterEqual(len(data['expired']), 1)
        self.assertGreaterEqual(data['total_vehicles_scanned'], 2)

    def test_verify_trip_dispatch_compliance_service(self):
        """Test verify_trip_dispatch_compliance safety gate."""
        veh_ok = Vehicle.objects.create(
            registration_number='TN-09-SAFE-01',
            vehicle_type=self.vehicle_type,
            status='available',
            insurance_expiry=self.today + datetime.timedelta(days=60),
            fc_expiry=self.today + datetime.timedelta(days=60),
            permit_expiry=self.today + datetime.timedelta(days=60),
            tax_expiry=self.today + datetime.timedelta(days=60),
            pollution_expiry=self.today + datetime.timedelta(days=60)
        )
        drv_ok = Driver.objects.create(
            name='Karthik P',
            driver_type='owned',
            status='active',
            aadhar_number='555544443333',
            bank_account_number='ICIC0001234',
            joining_date=self.today - datetime.timedelta(days=200),
            license_validity_tr=self.today + datetime.timedelta(days=90)
        )

        # 1. Compliant assignment passes
        trip_start = self.today + datetime.timedelta(days=2)
        trip_end = self.today + datetime.timedelta(days=5)
        is_compliant, violations = verify_trip_dispatch_compliance(veh_ok, drv_ok, trip_start, trip_end)
        self.assertTrue(is_compliant)
        self.assertEqual(len(violations), 0)

        # 2. Expired FC before trip end fails
        veh_ok.fc_expiry = self.today + datetime.timedelta(days=3)  # expires mid-trip
        veh_ok.save()
        is_compliant, violations = verify_trip_dispatch_compliance(veh_ok, drv_ok, trip_start, trip_end)
        self.assertFalse(is_compliant)
        self.assertTrue(any('Fitness Certificate' in v for v in violations))

    def test_check_preventive_maintenance_due_service(self):
        """Test check_preventive_maintenance_due detects odometer thresholds."""
        veh = Vehicle.objects.create(
            registration_number='TN-72-PM-001',
            vehicle_type=self.vehicle_type,
            status='available',
            current_km=60200
        )
        ServiceReminder.objects.create(
            vehicle=veh,
            service_task='Engine Oil & Filter Replacement',
            last_service_km=50000,
            interval_km=10000,  # due_km = 60000 (overdue by 200 km)
            is_active=True
        )

        result = check_preventive_maintenance_due(vehicle_id=veh.id)
        self.assertIn('services_due', result)
        services = result['services_due']
        self.assertGreaterEqual(len(services), 1)
        self.assertEqual(services[0]['status'], 'overdue')
        self.assertEqual(services[0]['task_name'], 'Engine Oil & Filter Replacement')

    # -------------------------------------------------------------------------
    # 5. Maintenance Dashboard & Compliance APIs
    # -------------------------------------------------------------------------

    def test_compliance_dashboard_and_summary_apis(self):
        """Test HTTP responses for compliance dashboard and summary APIs."""
        dash_res = self.client.get('/maintenance/compliance/')
        self.assertEqual(dash_res.status_code, 200)

        api_res = self.client.get('/maintenance/api/compliance-summary/')
        self.assertEqual(api_res.status_code, 200)
        data = api_res.json()
        self.assertIn('compliance_rate', data)
        self.assertIn('expired_count', data)

    # -------------------------------------------------------------------------
    # 6. 2D Vehicle Damage Marker Studio & Print Inspection
    # -------------------------------------------------------------------------

    def test_vehicle_damage_inspection_studio_and_marker_lifecycle(self):
        """Test 2D damage marker studio view, API saving, and printable certificate."""
        veh = Vehicle.objects.create(
            registration_number='TN-11-DM-7777',
            vehicle_type=self.vehicle_type,
            status='available',
            current_km=32000
        )

        # 1. Studio view renders 200
        res = self.client.get('/maintenance/damage-marker/')
        self.assertEqual(res.status_code, 200)

        # 2. Save Inspection with 2D Markers via API
        payload = {
            'vehicle_id': veh.id,
            'inspection_type': 'checkout',
            'vehicle_body_style': 'suv',
            'customer_name': 'Anand Swaminathan',
            'customer_phone': '9840011223',
            'inspector_name': 'Fleet Supervisor Rangarajan',
            'odometer_reading': 32000,
            'fuel_level_percent': 90,
            'security_deposit_held': 10000,
            'notes': 'Pre-departure handover check.',
            'markers': [
                {
                    'marker_number': 1,
                    'damage_type': 'dent',
                    'view_angle': 'front',
                    'panel_zone': 'front_bumper',
                    'x_percent': 45.5,
                    'y_percent': 62.0,
                    'severity': 'moderate',
                    'description': 'Dent on bumper lower lip',
                    'notes': 'Dent on bumper lower lip',
                    'estimated_repair_cost': 4500.00
                },
                {
                    'marker_number': 2,
                    'damage_type': 'scratch',
                    'view_angle': 'left',
                    'panel_zone': 'left_rear_door',
                    'x_percent': 80.2,
                    'y_percent': 33.1,
                    'severity': 'minor',
                    'description': 'Minor scratch on left rear door',
                    'notes': 'Minor scratch on left rear door',
                    'estimated_repair_cost': 1200.00
                }
            ]
        }

        save_res = self.client.post(
            '/maintenance/api/damage-inspection/save/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(save_res.status_code, 200)
        res_data = save_res.json()
        self.assertEqual(res_data['status'], 'success')
        inspection_id = res_data['inspection_id']

        # 3. Fetch inspection detail via API
        detail_res = self.client.get(f'/maintenance/api/damage-inspection/{inspection_id}/')
        self.assertEqual(detail_res.status_code, 200)
        detail_data = detail_res.json()
        self.assertEqual(len(detail_data['markers']), 2)

        # 4. Render printable handover certificate
        print_res = self.client.get(f'/maintenance/damage-inspection/{inspection_id}/print/')
        self.assertEqual(print_res.status_code, 200)
        self.assertContains(print_res, 'Anand Swaminathan')
        self.assertContains(print_res, 'TN-11-DM-7777')
        self.assertContains(print_res, 'Dent on bumper lower lip')
