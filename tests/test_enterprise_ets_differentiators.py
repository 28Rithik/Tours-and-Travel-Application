"""
Automated Test Suite for Enterprise Employee Transportation System (ETS) Differentiators:
1. Airport-Style Transport Command Center & Fleet Telemetry.
2. Autonomous Alternate Transport Recovery (Breakdown Rescue).
3. Dynamic Seat Marketplace & Commuter Trust Scorecard.
4. Silent SOS & Stealth Emergency Pipeline.
5. Corporate Lost & Found Property Registry.
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import Vehicle, VehicleType, Driver, Party, Client as CorporateClient, StaffProfile
from fleet_contracts.models import (
    TransportContract, Route, RouteStop, Shift,
    CommuterManifest, ContractTripLog, NightSafetyEscortLog
)
from fleet_commute.models import (
    CommuteIncident, SeatMarketplaceRelease, CommuterTrustScore, LostAndFoundItem
)
from fleet_commute.services import (
    get_airport_control_center_metrics,
    find_alternate_recovery_vehicles,
    dispatch_alternate_recovery,
    process_seat_marketplace_release,
    trigger_silent_sos,
)

User = get_user_model()


class EnterpriseETSSuitesTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='ets_admin',
            email='ets_admin@sivagayathiri.com',
            password='Password123!'
        )
        StaffProfile.objects.update_or_create(
            user=self.admin_user,
            defaults={
                'role': 'admin',
                'employee_id': 'SGT-ETS-ADM01',
                'branch': 'Coimbatore Central HQ'
            }
        )
        self.client.force_login(self.admin_user)

        # Corporate Client & Contract
        self.corp_party = CorporateClient.objects.create(
            name='Cognizant Technology Solutions',
            party_type='corporate',
            phone='04222666777',
            email='mobility@cognizant.com'
        )
        self.contract = TransportContract.objects.create(
            customer=self.corp_party,
            name='CTS Coimbatore MEPZ Campus Shuttle',
            start_date=timezone.localdate(),
            end_date=timezone.localdate() + timezone.timedelta(days=365),
            status='active',
            billing_model='fixed_monthly'
        )

        # Route & Shift
        self.route = Route.objects.create(
            contract=self.contract,
            name='Saravanampatti to CTS Campus via Peelamedu',
            origin='Saravanampatti',
            destination='CTS Campus',
            distance_km=25
        )
        self.stop = RouteStop.objects.create(
            route=self.route,
            name='Peelamedu Signal Nodal Stop',
            stop_order=1
        )
        self.shift = Shift.objects.create(
            route=self.route,
            shift_name='Morning General 08:30 Shift',
            direction='pickup',
            timing='08:30:00'
        )

        # Vehicles & Driver
        self.v_type = VehicleType.objects.create(name='32 Seater Urbania', seating_capacity=32)
        self.vehicle = Vehicle.objects.create(
            registration_number='TN-38-ETS-1001',
            vehicle_type=self.v_type,
            seating_capacity=32,
            base_depot='Coimbatore Central HQ',
            status='assigned'
        )
        self.standby_vehicle = Vehicle.objects.create(
            registration_number='TN-38-ETS-RESCUE-01',
            vehicle_type=self.v_type,
            seating_capacity=32,
            base_depot='Coimbatore Central HQ',
            status='available'
        )
        self.driver = Driver.objects.create(
            name='K. Karuppasamy',
            phone='9842511223',
            status='active'
        )
        self.standby_driver = Driver.objects.create(
            name='M. Muthuvel',
            phone='9842599887',
            status='active'
        )

        # Commuters
        self.commuter_1 = CommuterManifest.objects.create(
            contract=self.contract,
            commuter_id='CTS-EMP-8812',
            name='Ananya Sundaram',
            gender='female',
            phone='9840112233',
            boarding_stop=self.stop,
            is_active=True
        )
        self.commuter_2 = CommuterManifest.objects.create(
            contract=self.contract,
            commuter_id='CTS-EMP-9943',
            name='Vigneshwaran P',
            gender='male',
            phone='9840998877',
            boarding_stop=self.stop,
            is_active=True
        )

        # Trip Log
        self.trip = ContractTripLog.objects.create(
            shift=self.shift,
            date=timezone.localdate(),
            vehicle=self.vehicle,
            driver=self.driver,
            status='en_route',
            passenger_count=18,
            driver_bata=Decimal('450.00'),
            toll_parking_charges=Decimal('120.00'),
            delay_minutes=0
        )

    def test_01_airport_command_center_telemetry(self):
        """Test airport control room metrics: green/yellow/red, OTP %, seat occupancy %."""
        metrics = get_airport_control_center_metrics(contract_id=self.contract.id)
        
        self.assertEqual(metrics['total_trips'], 1)
        self.assertEqual(metrics['green_count'], 1)
        self.assertEqual(metrics['yellow_count'], 0)
        self.assertEqual(metrics['red_count'], 0)
        self.assertEqual(metrics['total_passengers'], 18)
        self.assertGreater(metrics['otp_pct'], 90.0)
        self.assertGreater(metrics['occupancy_pct'], 50.0)
        self.assertGreater(metrics['cost_per_commuter'], 0.0)

        # Check view endpoint
        url = reverse('fleet_commute:transport_command_center')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Transport Command Center')
        self.assertContains(resp, 'TN-38-ETS-1001')
        self.assertContains(resp, 'K. Karuppasamy')

    def test_02_autonomous_alternate_transport_recovery(self):
        """Test breakdown triage, standby fleet discovery, and 1-click rescue authorization."""
        # 1. Create breakdown incident
        incident = CommuteIncident.objects.create(
            incident_id='INC-ETS-TEST-01',
            incident_type='breakdown',
            severity='critical',
            status='reported',
            trip=self.trip,
            vehicle=self.vehicle,
            driver=self.driver,
            location_name='Near Peelamedu Flyover Hairpin',
            passengers_affected=18,
            description='Alternator failure, vehicle immobilized'
        )

        # 2. Discover alternate rescue fleet
        candidates = find_alternate_recovery_vehicles(incident)
        self.assertGreaterEqual(len(candidates), 1)
        top_rescue = candidates[0]
        self.assertEqual(top_rescue['registration_number'], 'TN-38-ETS-RESCUE-01')
        self.assertGreaterEqual(top_rescue['seating_capacity'], 18)
        self.assertGreater(top_rescue['eta_minutes'], 0)

        # 3. Authorize autonomous rescue dispatch
        result = dispatch_alternate_recovery(
            incident=incident,
            rescue_vehicle_id=self.standby_vehicle.id,
            rescue_driver_id=self.standby_driver.id,
            authorized_by=self.admin_user
        )
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['rescue_vehicle'], 'TN-38-ETS-RESCUE-01')
        self.assertEqual(result['reallocated_passengers'], 18)

        # Verify state
        incident.refresh_from_db()
        self.assertEqual(incident.status, 'rescue_dispatched')
        self.assertEqual(incident.rescue_vehicle, self.standby_vehicle)
        self.assertEqual(len(incident.action_log), 1)
        self.assertEqual(incident.action_log[0]['action'], 'ALTERNATE_RECOVERY_DISPATCHED')

        # Verify trip marked as replacement
        self.trip.refresh_from_db()
        self.assertTrue(self.trip.is_replacement_vehicle)

    def test_03_dynamic_seat_marketplace_and_trust_score(self):
        """Test employee seat surrender and dynamic waitlist reallocation."""
        result = process_seat_marketplace_release(
            commuter=self.commuter_1,
            reason='work_from_home',
            trip=self.trip
        )
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['matched_waitlist'])
        self.assertEqual(result['claimed_by'], self.commuter_2.name)

        # Check Trust Score
        trust_score = CommuterTrustScore.objects.get(commuter=self.commuter_1)
        self.assertGreaterEqual(trust_score.score, Decimal('90.00'))
        self.assertEqual(trust_score.tier, 'gold')
        self.assertFalse(trust_score.is_restricted)

    def test_04_silent_sos_pipeline(self):
        """Test discrete silent SOS trigger without provokative UI feedback."""
        incident = trigger_silent_sos(
            commuter=self.commuter_1,
            trip=self.trip,
            latitude=11.0250,
            longitude=76.9600,
            location_name='Avinashi Road Signal Junction'
        )
        self.assertTrue(incident.is_silent_sos)
        self.assertEqual(incident.severity, 'critical')
        self.assertEqual(incident.status, 'reported')
        self.assertEqual(incident.incident_type, 'safety_concern')
        self.assertIn('SILENT DISTRESS SOS', incident.description)

        # Test AJAX API endpoint
        url = reverse('fleet_commute:api_commute_silent_sos')
        resp = self.client.post(
            url,
            data={'commuter_id': self.commuter_1.commuter_id, 'trip_id': self.trip.id, 'lat': 11.025, 'lng': 76.96},
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['is_stealth'])
        self.assertIn('Synchronized', data['screen_notice'])

    def test_05_lost_and_found_custody_lifecycle(self):
        """Test chain of custody: reported -> driver verified -> security desk -> returned."""
        item = LostAndFoundItem.objects.create(
            reference_no='LF-2026-TEST01',
            item_category='laptop',
            item_name='Lenovo ThinkPad X1 Carbon (Grey sleeve)',
            commuter=self.commuter_1,
            trip=self.trip,
            vehicle=self.vehicle,
            driver=self.driver,
            status='reported'
        )

        # Advance to Driver Verified
        url = reverse('fleet_commute:api_lost_and_found_update', args=[item.id])
        resp = self.client.post(url, {'status': 'driver_verified'})
        self.assertEqual(resp.status_code, 200)

        # Advance to Security Desk Custody
        resp2 = self.client.post(url, {
            'status': 'security_custody',
            'security_officer_name': 'Inspector R. Rajan'
        })
        self.assertEqual(resp2.status_code, 200)

        # Claimed and Returned with signature acknowledgement
        resp3 = self.client.post(url, {'status': 'claimed_and_returned'})
        self.assertEqual(resp3.status_code, 200)

        item.refresh_from_db()
        self.assertEqual(item.status, 'claimed_and_returned')
        self.assertTrue(item.claimant_signature_ack)
        self.assertIsNotNone(item.returned_at)
        self.assertEqual(item.security_officer_name, 'Inspector R. Rajan')

    def test_06_http_views_and_api_endpoints(self):
        """Verify command center, incident desk, and lost & found views render HTTP 200."""
        # 1. Transport Command Center
        resp1 = self.client.get(reverse('fleet_commute:transport_command_center'))
        self.assertEqual(resp1.status_code, 200)
        self.assertContains(resp1, 'Transport Command Center')

        # 2. Incident Command Desk
        resp2 = self.client.get(reverse('fleet_commute:incident_command_center'))
        self.assertEqual(resp2.status_code, 200)
        self.assertContains(resp2, 'Incident Command Desk')

        # 3. Lost & Found Studio
        resp3 = self.client.get(reverse('fleet_commute:lost_and_found_studio'))
        self.assertEqual(resp3.status_code, 200)
        self.assertContains(resp3, 'Lost &amp; Found Registry')

        # 4. JSON Command Center Stats API
        resp4 = self.client.get(reverse('fleet_commute:api_commute_command_center_stats'))
        self.assertEqual(resp4.status_code, 200)
        self.assertEqual(resp4.json()['status'], 'success')
