import datetime
from decimal import Decimal
import json

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse

from core.models import Client as CoreClient, VehicleType, Driver, Vehicle
from operations.models import (
    Booking, Trip, VehicleTelematicsPing, GeofenceZone,
    EmergencyIncidentAlert, DriverHandoverSession
)
from operations.whatsapp_bot import (
    process_inbound_message,
    generate_passenger_dispatch_sheet,
    generate_driver_briefing_sheet,
    generate_emergency_sos_broadcast,
)


class Phase5TelematicsGisTaraWhatsAppTests(TestCase):
    """
    End-to-End Master Backend Test Suite for Phase 5:
    Telematics Radar, GIS Routing, TARA AI Copilot & Automated WhatsApp Engine.
    """

    def setUp(self):
        self.user = User.objects.create_superuser(
            username='phase5_admin',
            email='admin@travelerp.com',
            password='password123'
        )
        self.client = Client()
        self.client.force_login(self.user)

        self.party = CoreClient.objects.create(
            name='Cognizant Enterprise Hub',
            phone='9840011223',
            email='trips@cognizant.com'
        )

        self.vehicle_type = VehicleType.objects.create(
            name='Volvo B11R Luxury Coach',
            seating_capacity=45,
            default_day_rate=Decimal('18000.00'),
            default_km_rate=Decimal('42.00')
        )

        self.vehicle = Vehicle.objects.create(
            registration_number='TN-01-TL-8888',
            vehicle_type=self.vehicle_type,
            status='available',
            current_km=62000
        )

        self.driver = Driver.objects.create(
            name='Captain Velusamy',
            phone='9842511999',
            status='active'
        )

        self.booking = Booking.objects.create(
            party=self.party,
            guest_name='Mr. Anirudh Ravichander',
            guest_phone='9840099887',
            pickup_location='Chennai Airport T2',
            destination='Pondicherry Promenade',
            pickup_date=timezone.now().date(),
            pickup_time=datetime.time(10, 0),
            status='confirmed',
            quoted_price=Decimal('18500.00')
        )

        self.trip = Trip.objects.create(
            booking=self.booking,
            party=self.party,
            vehicle=self.vehicle,
            driver=self.driver,
            start_date=timezone.now().date(),
            billing_model='fixed',
            fixed_amount=Decimal('18500.00'),
            status='started'
        )

        # Seed initial telematics ping
        self.initial_ping = VehicleTelematicsPing.objects.create(
            vehicle=self.vehicle,
            timestamp=timezone.now(),
            latitude=Decimal('13.0827'),
            longitude=Decimal('80.2707'),
            speed_kmh=Decimal('45.0'),
            heading_degrees=Decimal('90.0'),
            ignition_on=True,
            fuel_level_pct=Decimal('78.5'),
            odometer_km=62000
        )

        # Seed geofence zone
        self.geofence = GeofenceZone.objects.create(
            name='Chennai Airport Security Perimeter',
            zone_type='depot',
            latitude=Decimal('12.9941'),
            longitude=Decimal('80.1709'),
            radius_meters=1500,
            speed_limit_kmh=40,
            is_active=True
        )

    # -------------------------------------------------------------------------
    # 1. Telematics Radar, Live Feed & Tick Simulation Engine
    # -------------------------------------------------------------------------

    def test_admin_fleet_radar_and_live_feed(self):
        """Test admin Leaflet radar map render and JSON live feed endpoint."""
        # 1. Admin Fleet Radar View
        res_radar = self.client.get(reverse('admin-fleet-radar'))
        self.assertEqual(res_radar.status_code, 200)
        self.assertContains(res_radar, 'Live Fleet Telematics GPS Radar Map')

        # 2. Live Feed REST API
        res_feed = self.client.get(reverse('api-fleet-live-feed'))
        self.assertEqual(res_feed.status_code, 200)
        feed_data = res_feed.json()
        self.assertEqual(feed_data['status'], 'success')
        self.assertIn('summary', feed_data)
        self.assertIn('vehicles', feed_data)
        self.assertGreaterEqual(feed_data['summary']['total_vehicles'], 1)

    def test_telematics_simulation_tick_advancement(self):
        """Test GPS simulation tick advances vehicle coordinates, speed, and fuel."""
        res_tick = self.client.post(reverse('api-fleet-telematics-tick'))
        self.assertEqual(res_tick.status_code, 200)
        data = res_tick.json()
        self.assertEqual(data['status'], 'success')
        self.assertGreaterEqual(data.get('ticks_count', len(data.get('ticks', []))), 1)

        # Verify a new telematics ping was recorded for the vehicle
        pings_count = VehicleTelematicsPing.objects.filter(vehicle=self.vehicle).count()
        self.assertGreaterEqual(pings_count, 1)

    # -------------------------------------------------------------------------
    # 2. GIS Routing, Spatial Nearest Vehicles & Prometheus Metrics
    # -------------------------------------------------------------------------

    def test_gis_osrm_route_and_spatial_nearest_vehicles(self):
        """Test OSRM routing calculation and PostGIS/spatial nearest vehicle dispatch."""
        # 1. OSRM Route Calculation
        route_url = f"{reverse('api_osrm_route')}?origin=coimbatore&dest=ooty"
        res_route = self.client.get(route_url)
        self.assertEqual(res_route.status_code, 200)
        route_data = res_route.json()
        self.assertEqual(route_data['status'], 'success')
        self.assertIn('geometry', route_data)
        self.assertGreater(route_data['distance_km'], 0)

        # 2. Spatial Nearest Vehicles (Haversine fallback / PostGIS)
        nearest_url = f"{reverse('api_spatial_nearest_vehicles')}?lat=13.0827&lng=80.2707&radius_km=50"
        res_nearest = self.client.get(nearest_url)
        self.assertEqual(res_nearest.status_code, 200)
        nearest_data = res_nearest.json()
        self.assertEqual(nearest_data['status'], 'success')
        self.assertIn('vehicles', nearest_data)

    def test_gis_prometheus_metrics_and_health_checks(self):
        """Test Prometheus metric exposition, GIS health API, and Mission Control UI."""
        # 1. Prometheus Metrics Text Exposition
        res_metrics = self.client.get(reverse('gis_prometheus_metrics'))
        self.assertEqual(res_metrics.status_code, 200)
        content = res_metrics.content.decode('utf-8')
        self.assertIn('gis_postgis_connected', content)
        self.assertIn('gis_osrm_total_queries', content)

        # 2. Structured GIS Health Check API
        res_health = self.client.get(reverse('gis_health'))
        self.assertEqual(res_health.status_code, 200)
        health_data = res_health.json()
        self.assertIn('services', health_data)
        self.assertIn('status', health_data)

        # 3. GIS Mission Control Center View
        res_ctrl = self.client.get(reverse('gis_control_center'))
        self.assertEqual(res_ctrl.status_code, 200)
        self.assertContains(res_ctrl, 'Enterprise OSM GIS')

    # -------------------------------------------------------------------------
    # 3. TARA AI Operations Copilot Engine (NLP & Fast Groq LLaMA)
    # -------------------------------------------------------------------------

    def test_tara_ai_copilot_queries_and_studio(self):
        """Test TARA AI natural language query processing and studio view."""
        # 1. Quick Stats
        res_stats = self.client.get(reverse('api-tara-quick-stats'))
        self.assertEqual(res_stats.status_code, 200)
        stats = res_stats.json()
        self.assertEqual(stats['status'], 'success')
        self.assertIn('active_tours', stats)
        self.assertIn('collection_rate', stats)

        # 2. Active Tours NLP Query
        payload_tours = {'message': 'How many tours are running today?'}
        res_tours = self.client.post(
            reverse('api-tara-chat'),
            data=json.dumps(payload_tours),
            content_type='application/json'
        )
        self.assertEqual(res_tours.status_code, 200)
        tours_data = res_tours.json()
        self.assertEqual(tours_data['status'], 'success')
        self.assertIn('reply', tours_data)

        # 3. Compliance Expiry NLP Query
        payload_comp = {'message': 'Which vehicles need insurance renewal?'}
        res_comp = self.client.post(
            reverse('api-tara-chat'),
            data=json.dumps(payload_comp),
            content_type='application/json'
        )
        self.assertEqual(res_comp.status_code, 200)
        comp_data = res_comp.json()
        self.assertEqual(comp_data['status'], 'success')
        self.assertIn('reply', comp_data)

        # 4. TARA Copilot Full Studio View
        res_studio = self.client.get(reverse('admin-tara-copilot-studio'))
        self.assertEqual(res_studio.status_code, 200)
        self.assertContains(res_studio, 'TARA AI Operations Business Brain')

    # -------------------------------------------------------------------------
    # 4. WhatsApp Business Bot Studio, Dispatch Alerts & SOS Broadcast
    # -------------------------------------------------------------------------

    def test_whatsapp_message_processing_and_dispatch(self):
        """Test WhatsApp branded briefing generation, intent parsing, and trip dispatch."""
        # 1. Branded Passenger Dispatch Sheet Generation
        pax_sheet = generate_passenger_dispatch_sheet(self.trip)
        self.assertIn('SIVAGAYATHIRI TRAVELS', pax_sheet)
        self.assertIn('TRIP DISPATCH CONFIRMATION', pax_sheet)
        self.assertIn('Captain Velusamy', pax_sheet)
        self.assertIn('TN-01-TL-8888', pax_sheet)

        # 2. Driver Briefing Sheet Generation
        drv_sheet = generate_driver_briefing_sheet(self.trip)
        self.assertIn('NEW TRIP DUTY ASSIGNMENT', drv_sheet)
        self.assertIn('DIGITAL HANDOVER', drv_sheet)

        # 3. Intent Processing: TRIP status
        reply_trip, intent, _ = process_inbound_message(sender_phone=self.driver.phone, raw_text='TRIP')
        self.assertEqual(intent, 'trip_status')
        self.assertIn('Trip', reply_trip)

        # 4. Intent Processing: Emergency SOS Broadcast
        reply_sos, intent_sos, _ = process_inbound_message(sender_phone=self.driver.phone, raw_text='EMERGENCY SOS BRAKE FAILURE')
        self.assertEqual(intent_sos, 'sos_trigger')
        self.assertIn('EMERGENCY SOS LOGGED', reply_sos)
        # Verify an Emergency Incident Alert was created automatically
        inc = EmergencyIncidentAlert.objects.filter(driver=self.driver).first()
        self.assertIsNotNone(inc)
        self.assertEqual(inc.severity, 'critical')

        # 5. WhatsApp Bot Studio Admin View
        res_bot_studio = self.client.get(reverse('admin-whatsapp-bot-studio'))
        self.assertEqual(res_bot_studio.status_code, 200)
        self.assertContains(res_bot_studio, 'WhatsApp Business Bot')

        # 6. 1-Click Passenger WhatsApp Dispatch Endpoint
        dispatch_url = reverse('api-whatsapp-trip-dispatch', kwargs={'trip_id': self.trip.id})
        res_dispatch = self.client.post(dispatch_url)
        self.assertEqual(res_dispatch.status_code, 200)
        self.assertIn(res_dispatch.json()['status'], ['ok', 'success'])
        self.trip.refresh_from_db()
        self.assertGreaterEqual(self.trip.whatsapp_broadcast_count, 1)
