import datetime
from decimal import Decimal
import json

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse

from core.models import Client as CoreClient, VehicleType, Driver, Vehicle
from operations.models import (
    Booking, Trip, TripMilestoneEvent, EmergencyIncidentAlert
)
from finance.models import TripExpense


class Phase3OperationsDispatchLifecycleTests(TestCase):
    """
    End-to-End Master Backend Test Suite for Phase 3:
    Operations Booking, Dispatch Engine, 7-Milestone Lifecycle & Driver Digital Twin.
    """

    def setUp(self):
        self.user = User.objects.create_superuser(
            username='phase3_admin',
            email='admin@travelerp.com',
            password='password123'
        )
        self.client = Client()
        self.client.force_login(self.user)

        self.party = CoreClient.objects.create(
            name='Cognizant Global Transport',
            phone='9840011223',
            email='trips@cognizant.com'
        )

        self.vehicle_type = VehicleType.objects.create(
            name='Toyota Innova Crysta Phase3',
            seating_capacity=7,
            default_day_rate=Decimal('3500.00'),
            default_km_rate=Decimal('16.00')
        )

        self.vehicle = Vehicle.objects.create(
            registration_number='TN-01-OP-5555',
            vehicle_type=self.vehicle_type,
            status='available',
            current_km=48000
        )

        self.standby_vehicle = Vehicle.objects.create(
            registration_number='TN-01-ST-9999',
            vehicle_type=self.vehicle_type,
            status='available',
            current_km=31000
        )

        self.driver = Driver.objects.create(
            name='Muthu Kumar',
            phone='9842511888',
            status='active'
        )

        self.standby_driver = Driver.objects.create(
            name='Dinesh Karthik',
            phone='9842511777',
            status='active'
        )

    # -------------------------------------------------------------------------
    # 1. Booking Lifecycle & Auto-Numbering
    # -------------------------------------------------------------------------

    def test_booking_creation_and_auto_numbering(self):
        """Test Booking model auto-generates BK-XXXX sequence and validates dates."""
        booking = Booking.objects.create(
            party=self.party,
            guest_name='Mr. Venkatesh Iyer',
            guest_phone='9840011223',
            pickup_location='Chennai Airport T1',
            destination='Mahabalipuram & Pondicherry',
            pickup_date=datetime.date(2026, 12, 1),
            pickup_time=datetime.time(8, 30),
            drop_date=datetime.date(2026, 12, 3),
            journey_type='outstation',
            vehicle_type=self.vehicle_type,
            expected_km=350,
            quoted_price=Decimal('16500.00'),
            status='confirmed'
        )
        self.assertTrue(booking.booking_number.startswith('BK-'))
        self.assertEqual(booking.status, 'confirmed')

        # Test date validation: drop date cannot be before pickup date
        invalid_booking = Booking(
            party=self.party,
            guest_name='Test Invalid',
            pickup_location='Chennai',
            destination='Salem',
            pickup_date=datetime.date(2026, 12, 10),
            drop_date=datetime.date(2026, 12, 8),
            pickup_time=datetime.time(8, 0),
            journey_type='outstation'
        )
        with self.assertRaises(ValidationError):
            invalid_booking.clean()

    def test_booking_views_rendering(self):
        """Test HTTP 200 responses for booking list and detail views."""
        booking = Booking.objects.create(
            party=self.party,
            guest_name='Vignesh Shivan',
            pickup_location='Coimbatore',
            destination='Ooty',
            pickup_date=datetime.date(2026, 11, 25),
            pickup_time=datetime.time(7, 0),
            journey_type='outstation',
            vehicle_type=self.vehicle_type
        )
        # List view
        res_list = self.client.get('/bookings/')
        self.assertEqual(res_list.status_code, 200)

        # Detail view
        res_detail = self.client.get(f'/bookings/{booking.id}/')
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, 'Vignesh Shivan')

    # -------------------------------------------------------------------------
    # 2. Trip Lifecycle, Status Transitions & Printable Documents
    # -------------------------------------------------------------------------

    def test_trip_provisioning_and_status_transitions(self):
        """Test Trip creation from booking, auto-PIN generation, and printable sheets."""
        booking = Booking.objects.create(
            party=self.party,
            guest_name='Suresh Raina',
            guest_phone='9840077889',
            pickup_location='Madurai Junction',
            destination='Rameswaram & Dhanushkodi',
            pickup_date=datetime.date(2026, 12, 5),
            pickup_time=datetime.time(6, 0),
            journey_type='outstation',
            vehicle_type=self.vehicle_type,
            quoted_price=Decimal('19500.00'),
            status='confirmed'
        )

        trip = Trip.objects.create(
            booking=booking,
            party=self.party,
            guest_name='Suresh Raina',
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=datetime.date(2026, 12, 5),
            start_time=datetime.time(6, 0),
            end_date=datetime.date(2026, 12, 7),
            billing_model='fixed',
            fixed_amount=Decimal('19500.00'),
            status='assigned'
        )

        self.assertTrue(trip.trip_id.startswith('TR-'))
        self.assertEqual(len(trip.pickup_pin), 4)

        # 1. Trip Detail View
        res_detail = self.client.get(f'/trips/{trip.id}/')
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, 'Suresh Raina')

        # 2. Printable Trip Sheet
        res_sheet = self.client.get(f'/trips/{trip.id}/trip-sheet/')
        self.assertEqual(res_sheet.status_code, 200)
        self.assertContains(res_sheet, trip.trip_id)

        # 3. Customer Confirmation Preview
        res_conf = self.client.get(f'/trips/{trip.id}/customer-confirmation/')
        self.assertEqual(res_conf.status_code, 200)
        self.assertContains(res_conf, 'Suresh Raina')

        # 4. Status Update API
        status_url = f'/trips/{trip.id}/status/'
        res_status = self.client.post(status_url, {'status': 'driver_confirmed'})
        self.assertEqual(res_status.status_code, 302)
        trip.refresh_from_db()
        self.assertEqual(trip.status, 'driver_confirmed')

    # -------------------------------------------------------------------------
    # 3. Emergency Incident Alert & Standby Vehicle Dispatch
    # -------------------------------------------------------------------------

    def test_emergency_incident_and_standby_dispatch(self):
        """Test emergency incident creation and 1-click standby vehicle replacement."""
        trip = Trip.objects.create(
            party=self.party,
            guest_name='Corporate Delegate Group',
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=timezone.now().date(),
            status='started'
        )

        incident = EmergencyIncidentAlert.objects.create(
            incident_type='breakdown',
            severity='critical',
            vehicle=self.vehicle,
            driver=self.driver,
            trip=trip,
            location_address='NH44 Highway near Krishnagiri Toll Plaza',
            passenger_count=6,
            passengers_safety_status='all_safe',
            description='Clutch plate failure on highway. Vehicle immobilized.',
            status='reported'
        )
        self.assertTrue(incident.incident_id.startswith('INC-'))

        # Dispatch Standby Vehicle & Driver
        dispatch_url = f'/incidents/{incident.id}/dispatch-standby/'
        payload = {
            'standby_vehicle_id': self.standby_vehicle.id,
            'standby_driver_id': self.standby_driver.id,
            'eta_minutes': 25,
            'notes': 'Standby Innova dispatched from Hosur depot with senior chauffeur.'
        }
        res_dispatch = self.client.post(
            dispatch_url,
            data=payload,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(res_dispatch.status_code, 200)
        data = res_dispatch.json()
        self.assertEqual(data['status'], 'success')

        incident.refresh_from_db()
        self.assertEqual(incident.status, 'standby_dispatched')
        self.assertEqual(incident.standby_vehicle, self.standby_vehicle)
        self.assertEqual(incident.standby_driver, self.standby_driver)
        self.assertEqual(incident.standby_eta_minutes, 25)

    # -------------------------------------------------------------------------
    # 4. 7-Milestone Tour Lifecycle Digital Twin
    # -------------------------------------------------------------------------

    def test_7_milestone_tour_lifecycle_progression(self):
        """Test step-by-step advancement through all 7 tour milestones."""
        trip = Trip.objects.create(
            party=self.party,
            guest_name='Dr. Radhakrishnan',
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=timezone.now().date(),
            status='assigned'
        )
        correct_pin = trip.pickup_pin

        # Cockpit view renders 200
        res_cockpit = self.client.get(f'/trip/{trip.id}/lifecycle/')
        self.assertEqual(res_cockpit.status_code, 200)
        self.assertContains(res_cockpit, '7-Milestone Tour Lifecycle')

        advance_url = reverse('api-trip-milestone-advance', kwargs={'trip_id': trip.id})

        # Milestone 1: Car Pickup
        p1 = {'milestone': 'car_pickup', 'odometer': 48000, 'notes': 'Starting from Chennai garage.'}
        r1 = self.client.post(advance_url, data=json.dumps(p1), content_type='application/json')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()['status'], 'success')

        # Milestone 2: Driver Reached
        p2 = {'milestone': 'driver_reached', 'notes': 'Driver reached airport pickup point.'}
        r2 = self.client.post(advance_url, data=json.dumps(p2), content_type='application/json')
        self.assertEqual(r2.status_code, 200)

        # Milestone 3: Guest Pickup - Invalid OTP PIN rejected
        p3_bad = {'milestone': 'guest_pickup', 'pickup_pin': '0000'}
        r3_bad = self.client.post(advance_url, data=json.dumps(p3_bad), content_type='application/json')
        self.assertEqual(r3_bad.status_code, 400)
        self.assertIn('Invalid', r3_bad.json()['message'])

        # Milestone 3: Guest Pickup - Valid PIN accepted
        p3_good = {'milestone': 'guest_pickup', 'pickup_pin': correct_pin, 'notes': 'Guest verified via secure PIN.'}
        r3_good = self.client.post(advance_url, data=json.dumps(p3_good), content_type='application/json')
        self.assertEqual(r3_good.status_code, 200)

        # Milestone 4: On Trip
        p4 = {'milestone': 'on_trip', 'notes': 'En route on ECR scenic highway.'}
        r4 = self.client.post(advance_url, data=json.dumps(p4), content_type='application/json')
        self.assertEqual(r4.status_code, 200)

        # Milestone 5: Guest Drop
        p5 = {'milestone': 'guest_drop', 'notes': 'Guest safely dropped at resort.'}
        r5 = self.client.post(advance_url, data=json.dumps(p5), content_type='application/json')
        self.assertEqual(r5.status_code, 200)

        # Milestone 6: Quick Expense & Photo
        exp_url = reverse('api-trip-quick-expense', kwargs={'trip_id': trip.id})
        p_exp = {'expense_type': 'toll', 'amount': '350.00', 'notes': 'ECR Fastag Toll deduction'}
        r_exp = self.client.post(exp_url, data=json.dumps(p_exp), content_type='application/json')
        self.assertEqual(r_exp.status_code, 200)
        self.assertEqual(TripExpense.objects.filter(trip=trip).count(), 1)

        p6 = {'milestone': 'expenses_photo', 'notes': 'Toll Fastag receipt reconciled.'}
        r6 = self.client.post(advance_url, data=json.dumps(p6), content_type='application/json')
        self.assertEqual(r6.status_code, 200)

        # Milestone 7: Car Drop (Trip Completed)
        p7 = {'milestone': 'car_drop', 'odometer': 48350, 'notes': 'Vehicle parked safely at depot.'}
        r7 = self.client.post(advance_url, data=json.dumps(p7), content_type='application/json')
        self.assertEqual(r7.status_code, 200)

        trip.refresh_from_db()
        self.assertEqual(trip.status, 'completed')
        self.assertEqual(trip.closing_km, 48350)
        self.assertEqual(trip.milestone_events.count(), 7)

        # Milestones status API
        status_url = reverse('api-trip-milestones-status', kwargs={'trip_id': trip.id})
        res_m_status = self.client.get(status_url)
        self.assertEqual(res_m_status.status_code, 200)
        self.assertEqual(res_m_status.json()['completed_count'], 7)

    # -------------------------------------------------------------------------
    # 5. Driver Portal, Digital Handover & PWA Assets
    # -------------------------------------------------------------------------

    def test_driver_handover_portal_and_sos(self):
        """Test Driver Handover view, SOS alert trigger, and PWA manifest assets."""
        trip = Trip.objects.create(
            party=self.party,
            guest_name='Kishore Kumar',
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=timezone.now().date(),
            status='assigned'
        )

        # 1. Driver Handover View
        res_handover = self.client.get(f'/trip/{trip.id}/handover/')
        self.assertEqual(res_handover.status_code, 200)

        # 2. Driver Handover SOS trigger
        res_sos = self.client.post(f'/trip/{trip.id}/handover/sos/', {'latitude': 13.0827, 'longitude': 80.2707})
        self.assertIn(res_sos.status_code, [200, 302])

        # 3. PWA manifest and service worker
        res_manifest = self.client.get('/manifest.json')
        self.assertEqual(res_manifest.status_code, 200)

        res_sw = self.client.get('/sw.js')
        self.assertEqual(res_sw.status_code, 200)

    # -------------------------------------------------------------------------
    # 6. Passenger Live Tracking Portal
    # -------------------------------------------------------------------------

    def test_passenger_live_tracking_portal(self):
        """Test passenger live tracking view and live telemetry API endpoint."""
        trip = Trip.objects.create(
            party=self.party,
            guest_name='Sunil Gavaskar',
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=timezone.now().date(),
            status='started'
        )
        self.assertIsNotNone(trip.tracking_token)

        # Tracking HTML view
        res_track = self.client.get(f'/track/{trip.tracking_token}/')
        self.assertEqual(res_track.status_code, 200)
        self.assertContains(res_track, 'Sunil Gavaskar')

        # Live telemetry API
        res_live = self.client.get(f'/api/track/{trip.tracking_token}/live/')
        self.assertEqual(res_live.status_code, 200)
        data = res_live.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['trip_status'], 'started')
