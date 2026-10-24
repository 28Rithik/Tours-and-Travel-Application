"""
Automated Verification Suite: Interstate State Border Entry Tax & Eco-Sensitive Zone e-Pass Sentry
Tests Section 88 MV Act Permits, Kerala ₹200 Reciprocal Rule, Karnataka/AP Border Taxes,
AITP National Waivers, and Madras High Court / TNeGA Hill Station e-Passes (Nilgiris / Kodai / Valparai).
"""

from decimal import Decimal
from datetime import date, time, timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import Vehicle, VehicleType, Driver, Party, Client as ClientModel
from operations.models import Trip, Booking, InterstateBorderPermit, EcoSensitiveZoneEPass
from operations.border_permit_sentry import (
    audit_trip_border_permit,
    audit_trip_hill_epass,
    detect_target_state,
    detect_hill_station_epass_zone,
    STATUTORY_BORDER_TAX_MATRIX,
    ECO_SENSITIVE_ZONES_CONFIG
)

User = get_user_model()


class InterstatePermitAndEPassTestSuite(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='admin_permits',
            password='testpassword123',
            email='admin@sivagayathiritravels.com'
        )
        self.client.force_login(self.user)

        self.party = ClientModel.objects.create(
            name='Cognizant Technology Solutions',
            phone='9876543210'
        )

        self.v_type_sedan = VehicleType.objects.create(name='Sedan Dzire AC')
        self.v_type_innova = VehicleType.objects.create(name='Innova Crysta MPV')
        self.v_type_tempo = VehicleType.objects.create(name='Tempo Traveller 14 Seater')
        self.v_type_coach = VehicleType.objects.create(name='Luxury Pushback Coach 45 Seater')

        # Vehicle 1: Innova Crysta (Motor Cab, Contract Carriage, Tourist Permit)
        self.veh_innova = Vehicle.objects.create(
            registration_number='TN 38 BZ 1001',
            vehicle_type=self.v_type_innova,
            seating_capacity=7,
            rto_permit_category='motor_cab',
            primary_permit_type='contract_carriage',
            has_contract_carriage_permit=True,
            has_tourist_permit=True,
            permit_number='TN/CB/CC/2026/1001',
            permit_expiry=date.today() + timedelta(days=200),
            has_aitp=False
        )

        # Vehicle 2: Luxury Coach with All India Tourist Permit (AITP)
        self.veh_coach_aitp = Vehicle.objects.create(
            registration_number='TN 38 CZ 9999',
            vehicle_type=self.v_type_coach,
            seating_capacity=45,
            rto_permit_category='omnibus',
            primary_permit_type='tourist_permit',
            has_contract_carriage_permit=True,
            has_tourist_permit=True,
            permit_number='TN/CB/OM/2026/9999',
            permit_expiry=date.today() + timedelta(days=300),
            has_aitp=True,
            aitp_permit_number='AITP/TN/2026/88100',
            aitp_expiry=date.today() + timedelta(days=150)
        )

        self.driver = Driver.objects.create(
            name='K. Murugan',
            phone='9843210001'
        )

    def test_01_vehicle_rto_permits_and_aitp_validity(self):
        """Validates vehicle statutory RTO permit categorization and AITP helper."""
        self.assertEqual(self.veh_innova.rto_permit_category, 'motor_cab')
        self.assertTrue(self.veh_innova.has_contract_carriage_permit)
        self.assertTrue(self.veh_innova.has_tourist_permit)
        self.assertFalse(self.veh_innova.has_aitp)
        self.assertFalse(self.veh_innova.is_aitp_valid())

        self.assertEqual(self.veh_coach_aitp.rto_permit_category, 'omnibus')
        self.assertTrue(self.veh_coach_aitp.has_aitp)
        self.assertTrue(self.veh_coach_aitp.is_aitp_valid())

    def test_02_detect_target_states_and_hill_zones(self):
        """Validates corridor detection for interstate and hill e-pass destinations."""
        # Interstate detection
        self.assertEqual(detect_target_state('Munnar Hill Resort, Kerala'), 'Kerala')
        self.assertEqual(detect_target_state('Bangalore Electronic City, Karnataka'), 'Karnataka')
        self.assertEqual(detect_target_state('Tirupati Balaji Temple, Andhra Pradesh'), 'Andhra Pradesh')
        self.assertEqual(detect_target_state('White Town, Pondicherry'), 'Puducherry')
        self.assertIsNone(detect_target_state('Madurai Meenakshi Temple, Tamil Nadu'))

        # Hill Station e-pass detection
        self.assertEqual(detect_hill_station_epass_zone('Ooty Botanical Garden, Nilgiris'), 'nilgiris')
        self.assertEqual(detect_hill_station_epass_zone('Coonoor Tea Estate, Nilgiris'), 'nilgiris')
        self.assertEqual(detect_hill_station_epass_zone('Kotagiri Kodanad Viewpoint'), 'nilgiris')
        self.assertEqual(detect_hill_station_epass_zone('Kodaikanal Lake & Bryant Park'), 'kodaikanal')
        self.assertEqual(detect_hill_station_epass_zone('Valparai Sholayar Dam & Tea Estate'), 'valparai')
        self.assertIsNone(detect_hill_station_epass_zone('Coimbatore Town Hall'))

    def test_03_kerala_reciprocal_permit_fee_only_rule(self):
        """
        Validates the user's rule: For Kerala, commercial vehicles pay ONLY
        the Kerala entry permit fee (₹200), and ₹0 State Border Road Tax.
        """
        booking_kl = Booking.objects.create(
            party=self.party,
            guest_name='Ananya Iyer',
            pickup_location='Coimbatore Gandhipuram',
            destination='Munnar Tea Valley, Kerala',
            pickup_date=date.today(),
            pickup_time=time(6, 0),
            journey_type='outstation',
            drop_date=date.today() + timedelta(days=3)
        )
        trip_kl = Trip.objects.create(
            booking=booking_kl,
            vehicle=self.veh_innova,
            driver=self.driver,
            start_date=timezone.localdate(),
            end_date=timezone.localdate() + timedelta(days=3),
            status='assigned'
        )

        audit = audit_trip_border_permit(trip_kl)
        self.assertTrue(audit['is_interstate'])
        self.assertEqual(audit['target_state'], 'Kerala')
        self.assertEqual(audit['state_permit_fee'], Decimal('200.00'))
        self.assertEqual(audit['border_road_tax'], Decimal('0.00'))
        self.assertEqual(audit['required_tax'], Decimal('200.00'))
        self.assertEqual(audit['status'], 'pending_payment')
        self.assertIn('Walayar', audit['checkpost'])

    def test_04_karnataka_permit_plus_border_tax_rule(self):
        """
        Validates the user's rule: For Karnataka, vehicles pay the state permit fee (₹200)
        WITH state border road tax (e.g. ₹900 for Innova Crysta SUV = ₹1,100).
        """
        booking_ka = Booking.objects.create(
            party=self.party,
            guest_name='Siddharth Rao',
            pickup_location='Hosur Industrial Area',
            destination='Bangalore Whitefield IT Park, Karnataka',
            pickup_date=date.today(),
            pickup_time=time(7, 30),
            journey_type='outstation',
            drop_date=date.today() + timedelta(days=2)
        )
        trip_ka = Trip.objects.create(
            booking=booking_ka,
            vehicle=self.veh_innova,
            driver=self.driver,
            start_date=timezone.localdate(),
            end_date=timezone.localdate() + timedelta(days=2),
            status='assigned'
        )

        audit = audit_trip_border_permit(trip_ka)
        self.assertTrue(audit['is_interstate'])
        self.assertEqual(audit['target_state'], 'Karnataka')
        self.assertEqual(audit['state_permit_fee'], Decimal('200.00'))
        self.assertEqual(audit['border_road_tax'], Decimal('900.00'))
        self.assertEqual(audit['required_tax'], Decimal('1100.00'))
        self.assertIn('Attibele', audit['checkpost'])

    def test_05_aitp_national_permit_border_tax_exemption(self):
        """
        Validates that vehicles with active All India Tourist Permit (AITP)
        are completely exempt from border road taxes across all interstate corridors.
        """
        booking_ka_coach = Booking.objects.create(
            party=self.party,
            guest_name='Cognizant Annual Corporate Outing',
            pickup_location='Chennai Tidel Park',
            destination='Mysore Heritage Palace, Karnataka',
            pickup_date=date.today(),
            pickup_time=time(5, 0),
            journey_type='outstation',
            drop_date=date.today() + timedelta(days=4)
        )
        trip_coach = Trip.objects.create(
            booking=booking_ka_coach,
            vehicle=self.veh_coach_aitp,
            driver=self.driver,
            start_date=timezone.localdate(),
            end_date=timezone.localdate() + timedelta(days=4),
            status='assigned'
        )

        audit = audit_trip_border_permit(trip_coach)
        self.assertTrue(audit['is_interstate'])
        self.assertTrue(audit['is_aitp_exempt'])
        self.assertEqual(audit['required_tax'], Decimal('0.00'))
        self.assertEqual(audit['status'], 'valid')
        self.assertIn('AITP National Authorization', audit['status_label'])

    def test_06_eco_sensitive_zone_hill_epass_nilgiris_and_kodai(self):
        """
        Validates Madras High Court mandated TNeGA e-pass surveillance for
        Nilgiris (Ooty / Coonoor / Kotagiri) and Kodaikanal.
        """
        booking_ooty = Booking.objects.create(
            party=self.party,
            guest_name='Praveen Kumar',
            pickup_location='Mettupalayam Railway Station',
            destination='Ooty Lake & Coonoor Sim Park, Nilgiris',
            pickup_date=date.today(),
            pickup_time=time(8, 0),
            journey_type='outstation',
            drop_date=date.today() + timedelta(days=2)
        )
        trip_ooty = Trip.objects.create(
            booking=booking_ooty,
            vehicle=self.veh_innova,
            driver=self.driver,
            start_date=timezone.localdate(),
            end_date=timezone.localdate() + timedelta(days=2),
            status='assigned'
        )

        audit = audit_trip_hill_epass(trip_ooty)
        self.assertTrue(audit['requires_epass'])
        self.assertEqual(audit['zone_key'], 'nilgiris')
        self.assertIn('Burliyar', audit['default_checkpost'])
        self.assertEqual(audit['status'], 'missing')

        # Now issue an e-pass for this vehicle and re-audit
        epass = EcoSensitiveZoneEPass.objects.create(
            trip=trip_ooty,
            vehicle=self.veh_innova,
            driver=self.driver,
            zone='nilgiris',
            epass_number='TNEGA-NIL-2026-TEST01',
            entry_date=timezone.localdate(),
            exit_date=timezone.localdate() + timedelta(days=3),
            num_tourists=5,
            hotel_name='Sterling Ooty Elk Hill',
            hotel_booking_ref='ST-2026-88',
            checkpost_name='Burliyar Checkpost (Mettupalayam - Coonoor)',
            qr_code_token='TNEGA-TEST-TOKEN',
            status='active'
        )

        audit_after = audit_trip_hill_epass(trip_ooty)
        self.assertEqual(audit_after['status'], 'active')
        self.assertIn('TNEGA-NIL-2026-TEST01', audit_after['status_label'])

    def test_07_border_permit_and_epass_studio_view_and_apis(self):
        """Tests HTTP endpoints for Border Permit Studio, Parivahan payment, and e-Pass generation."""
        # 1. Studio Page
        resp = self.client.get('/operations/border-permits/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Interstate Border Road Tax')
        self.assertContains(resp, 'Eco-Sensitive Hill e-Passes')
        self.assertContains(resp, 'Walayar')

        # 2. Border Permit Payment API
        pay_payload = {
            'vehicle_id': self.veh_innova.id,
            'target_state': 'Kerala',
            'checkpost_name': 'Walayar Check-post (NH-544 Palakkad)',
            'state_permit_fee': '200.00',
            'border_road_tax': '0.00',
            'receipt_number': 'KL-TEST-REC-2026',
            'validity_days': 7,
        }
        resp_pay = self.client.post('/api/operations/border-permits/pay/', pay_payload, content_type='application/json')
        self.assertEqual(resp_pay.status_code, 200)
        pay_json = resp_pay.json()
        self.assertEqual(pay_json['status'], 'success')
        self.assertEqual(pay_json['tax_amount'], 200.0)

        # 3. Hill e-Pass Issue API
        epass_payload = {
            'vehicle_id': self.veh_innova.id,
            'zone': 'kodaikanal',
            'hotel_name': 'Tamara Kodai Resort',
            'hotel_booking_ref': 'BK-KODAI-91',
            'num_tourists': 4,
            'checkpost_name': 'Silver Cascade Checkpost',
        }
        resp_epass = self.client.post('/api/operations/epass/issue/', epass_payload, content_type='application/json')
        self.assertEqual(resp_epass.status_code, 200)
        epass_json = resp_epass.json()
        self.assertEqual(epass_json['status'], 'success')
        self.assertIn('TNEGA-KOD', epass_json['epass_number'])

        # 4. Checkpost Verify API
        epass_id = epass_json['epass_id']
        resp_verify = self.client.post(f'/api/operations/epass/verify/{epass_id}/')
        self.assertEqual(resp_verify.status_code, 200)
        self.assertEqual(resp_verify.json()['status'], 'success')
