"""
tests/test_phase9_geofence_and_alarms.py

Comprehensive Automated Test Suite for Phase 9:
Real-Time Geofence Breach Daemon & Automated Emergency Incident Alarms.

Tests:
1. Restricted zone perimeter intrusion detection and critical incident creation.
2. Zone over-speeding detection and driver behavior penalty log creation.
3. Route corridor deviation detection (> 2.5 km off-route).
4. Alert deduplication / throttling window (prevents alert storms).
5. Automated outbound WhatsApp alarm message generation.
6. Dispatcher incident acknowledgment API endpoint.
7. Active geofence alarms feed API endpoint.
8. Background daemon management command single-shot run.
"""

from decimal import Decimal
from datetime import date, time, timedelta

from django.test import TestCase, Client
from django.utils import timezone
from django.core.management import call_command
from django.contrib.auth.models import User

from core.models import Vehicle, Driver, Client as PartyClient, VehicleType
from operations.models import (
    Trip,
    Booking,
    VehicleTelematicsPing,
    GeofenceZone,
    DriverBehaviorLog,
    EmergencyIncidentAlert,
    WhatsAppBotMessage,
)
from operations.geofence_engine import GeofenceSafetyEngine


class Phase9GeofenceAndAlarmsTests(TestCase):
    def setUp(self):
        self.vtype, _ = VehicleType.objects.get_or_create(name='Luxury Coach')
        self.client_obj = PartyClient.objects.create(name='Tech Park IT Corp', phone='9842100099')

        self.driver = Driver.objects.create(
            name='Karthik Murugan',
            phone='+919842111222',
            license_number='TN38-2019-001234'
        )

        self.vehicle = Vehicle.objects.create(
            registration_number='TN-38-GEOFENCE-01',
            model='Force Urbania Luxury',
            vehicle_type=self.vtype,
            default_driver=self.driver,
            seating_capacity=14,
            current_km=35000,
            status='available'
        )

        self.booking = Booking.objects.create(
            party=self.client_obj,
            pickup_date=date.today(),
            pickup_time=time(8, 30),
            pickup_location='Coimbatore HQ Depot',
            destination='Ooty Botanical Garden',
            journey_type='round_trip',
            vehicle_type=self.vtype,
            guest_name='Corporate Delegate Team'
        )

        self.trip = Trip.objects.create(
            booking=self.booking,
            party=self.client_obj,
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=date.today(),
            end_date=date.today(),
            status='started'
        )

        # Test Restricted Zone (Orvakkal Industrial Area)
        self.restricted_zone = GeofenceZone.objects.create(
            name='Orvakkal High Risk Restricted Zone',
            zone_type='restricted_zone',
            latitude=Decimal('11.0250000'),
            longitude=Decimal('76.9600000'),
            radius_meters=600,
            speed_limit_kmh=30,
            alert_on_entry=True,
            alert_on_exit=True,
            is_active=True
        )

        # Test School Campus Zone
        self.school_zone = GeofenceZone.objects.create(
            name='PSG Tech Campus Safety Perimeter',
            zone_type='school',
            latitude=Decimal('11.0200000'),
            longitude=Decimal('77.0000000'),
            radius_meters=500,
            speed_limit_kmh=25,
            is_active=True
        )

        # Staff User for Dispatcher APIs
        self.staff_user = User.objects.create_user(
            username='duty_dispatcher',
            password='DispatcherPassword123!',
            is_staff=True
        )
        self.client = Client()

    def test_restricted_zone_intrusion_triggers_critical_incident(self):
        """
        Injecting a ping inside a restricted zone perimeter must auto-raise:
        1. A critical DriverBehaviorLog.
        2. A critical EmergencyIncidentAlert.
        3. An outbound WhatsAppBotMessage alert to the control room.
        """
        ping = VehicleTelematicsPing.objects.create(
            vehicle=self.vehicle,
            trip=self.trip,
            timestamp=timezone.now(),
            latitude=Decimal('11.0251000'),  # Inside restricted zone (~15m from center)
            longitude=Decimal('76.9601000'),
            speed_kmh=Decimal('42.0'),
            ignition_on=True
        )

        result = GeofenceSafetyEngine.evaluate_ping(ping)
        self.assertEqual(result['status'], 'evaluated')
        self.assertGreaterEqual(result['violations_count'], 1)
        self.assertIsNotNone(result['incident_created_id'])
        self.assertTrue(result['whatsapp_sent'])

        # Verify DriverBehaviorLog
        log = DriverBehaviorLog.objects.filter(
            vehicle=self.vehicle,
            event_type='geofence_breach',
            severity='critical'
        ).first()
        self.assertIsNotNone(log)
        self.assertIn('Orvakkal High Risk Restricted Zone', log.notes)
        self.assertEqual(log.penalty_points, 20)

        # Verify EmergencyIncidentAlert
        incident = EmergencyIncidentAlert.objects.filter(
            incident_id=result['incident_created_id']
        ).first()
        self.assertIsNotNone(incident)
        self.assertEqual(incident.incident_type, 'geofence_breach')
        self.assertEqual(incident.severity, 'critical')
        self.assertEqual(incident.status, 'reported')
        self.assertEqual(incident.vehicle, self.vehicle)

        # Verify WhatsApp Alert
        msg = WhatsAppBotMessage.objects.filter(
            trip=self.trip,
            intent='geofence_breach_alert'
        ).first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.message_direction, 'outbound')
        self.assertIn('RESTRICTED ZONE INTRUSION', msg.message_body)
        self.assertIn(self.vehicle.registration_number, msg.message_body)

    def test_zone_severe_overspeeding_triggers_incident_and_scorecard_deduction(self):
        """
        Speeding > 25 km/h above the zone limit inside a sensitive zone (PSG Campus, limit 25 km/h)
        must log a critical infraction and escalate to an EmergencyIncidentAlert.
        """
        ping = VehicleTelematicsPing.objects.create(
            vehicle=self.vehicle,
            trip=self.trip,
            timestamp=timezone.now(),
            latitude=Decimal('11.0201000'),  # Inside school zone
            longitude=Decimal('77.0001000'),
            speed_kmh=Decimal('58.0'),       # 33 km/h above limit (25)
            ignition_on=True
        )

        result = GeofenceSafetyEngine.evaluate_ping(ping)
        self.assertGreaterEqual(result['violations_count'], 1)

        # Verify DriverBehaviorLog
        log = DriverBehaviorLog.objects.filter(
            vehicle=self.vehicle,
            event_type='overspeeding',
            severity='critical'
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(float(log.recorded_speed_kmh), 58.0)
        self.assertEqual(log.penalty_points, 15)

        # Verify escalation to EmergencyIncidentAlert
        incident = EmergencyIncidentAlert.objects.filter(
            vehicle=self.vehicle,
            incident_type='overspeed_violation'
        ).first()
        self.assertIsNotNone(incident)
        self.assertEqual(incident.severity, 'high')

    def test_route_corridor_deviation_detection(self):
        """
        When a vehicle assigned to Coimbatore -> Ooty deviates > 2.5 km off-route,
        the corridor watchdog must log a corridor deviation event.
        """
        # Inject coordinates 15 km away from Coimbatore -> Ooty axis
        ping = VehicleTelematicsPing.objects.create(
            vehicle=self.vehicle,
            trip=self.trip,
            timestamp=timezone.now(),
            latitude=Decimal('10.8500000'),  # Far south toward Pollachi
            longitude=Decimal('76.8500000'),
            speed_kmh=Decimal('65.0'),
            ignition_on=True
        )

        result = GeofenceSafetyEngine.evaluate_ping(ping)
        self.assertGreaterEqual(result['violations_count'], 1)

        log = DriverBehaviorLog.objects.filter(
            vehicle=self.vehicle,
            notes__icontains='Route Corridor Deviation'
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.event_type, 'geofence_breach')
        self.assertEqual(log.severity, 'high')

    def test_alert_throttling_prevents_duplicate_incident_storms(self):
        """
        Subsequent pings within the 15-minute cooldown window should not spam
        duplicate EmergencyIncidentAlert tickets for the same violation.
        """
        ping1 = VehicleTelematicsPing.objects.create(
            vehicle=self.vehicle,
            trip=self.trip,
            timestamp=timezone.now(),
            latitude=Decimal('11.0251000'),
            longitude=Decimal('76.9601000'),
            speed_kmh=Decimal('35.0')
        )
        res1 = GeofenceSafetyEngine.evaluate_ping(ping1)
        self.assertIsNotNone(res1['incident_created_id'])
        incident_count_1 = EmergencyIncidentAlert.objects.filter(vehicle=self.vehicle).count()

        # Immediate second ping 10 seconds later
        ping2 = VehicleTelematicsPing.objects.create(
            vehicle=self.vehicle,
            trip=self.trip,
            timestamp=timezone.now() + timedelta(seconds=10),
            latitude=Decimal('11.0251200'),
            longitude=Decimal('76.9601100'),
            speed_kmh=Decimal('36.0')
        )
        res2 = GeofenceSafetyEngine.evaluate_ping(ping2)

        # Should be throttled
        self.assertEqual(res2['violations'][0]['status'], 'throttled')
        incident_count_2 = EmergencyIncidentAlert.objects.filter(vehicle=self.vehicle).count()
        self.assertEqual(incident_count_1, incident_count_2)

    def test_dispatcher_incident_acknowledgment_api(self):
        """
        POST to /api/incidents/<id>/acknowledge/ must transition incident to 'acknowledged'
        and record dispatcher resolution notes.
        """
        incident = EmergencyIncidentAlert.objects.create(
            incident_type='geofence_breach',
            severity='critical',
            vehicle=self.vehicle,
            driver=self.driver,
            trip=self.trip,
            status='reported',
            description='Test intrusion alert'
        )

        self.client.force_login(self.staff_user)
        response = self.client.post(
            f'/api/incidents/{incident.incident_id}/acknowledge/',
            data={'notes': 'Confirmed with driver; vehicle rerouting back to permitted corridor.'},
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['new_status'], 'acknowledged')

        incident.refresh_from_db()
        self.assertEqual(incident.status, 'acknowledged')
        self.assertIn('duty_dispatcher', incident.resolution_notes)

    def test_active_geofence_alarms_api(self):
        """
        GET to /api/fleet/geofence-alarms/ must return active alarms and unresolved incidents.
        """
        EmergencyIncidentAlert.objects.create(
            incident_type='geofence_breach',
            severity='critical',
            vehicle=self.vehicle,
            driver=self.driver,
            status='reported',
            description='Active live breach'
        )

        self.client.force_login(self.staff_user)
        response = self.client.get('/api/fleet/geofence-alarms/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['has_active_alarm'])
        self.assertGreaterEqual(data['active_count'], 1)
        self.assertEqual(data['incidents'][0]['vehicle_reg'], self.vehicle.registration_number)

    def test_background_daemon_single_shot_run(self):
        """
        Management command run_geofence_daemon with --once flag must execute
        a full evaluation cycle across vehicles and terminate cleanly.
        """
        VehicleTelematicsPing.objects.create(
            vehicle=self.vehicle,
            trip=self.trip,
            timestamp=timezone.now(),
            latitude=Decimal('11.0168000'),
            longitude=Decimal('76.9558000'),
            speed_kmh=Decimal('15.0')
        )

        # Execute management command
        call_command('run_geofence_daemon', once=True)
        # Verify no unhandled exception occurred and execution completed
