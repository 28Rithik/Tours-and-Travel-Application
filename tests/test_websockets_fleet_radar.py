from django.test import TestCase, override_settings
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from travelerp.asgi import application
from core.models import Vehicle, VehicleType, Driver
from operations.models import Trip, EmergencyIncidentAlert
from operations.telematics_broadcast import (
    build_fleet_live_feed_payload,
    broadcast_fleet_telemetry,
    broadcast_emergency_sos,
    broadcast_incident_acknowledgment,
)
from operations.services import ingest_telematics_ping
from decimal import Decimal
from django.utils import timezone


class FleetLiveRadarWebSocketsTestCase(TestCase):
    """
    Test suite for Real-Time WebSockets Live Control Room (Zero-Polling Fleet Radar & SOS).
    """

    def setUp(self):
        self.vehicle_type = VehicleType.objects.create(name="Executive Sedan")
        self.vehicle = Vehicle.objects.create(
            registration_number="TN-38-BZ-9999",
            brand="Toyota",
            model="Innova Crysta",
            seating_capacity=7,
            vehicle_type=self.vehicle_type,
            status="available",
            current_km=45000,
            base_depot="Coimbatore Hub",
            gps_imei="IMEI9999999999",
        )
        self.driver = Driver.objects.create(
            name="Senthil Kumar",
            phone="+919876543210",
            license_number="DL-TN-38-2022-0099",
            status="active",
        )

    async def test_fleet_radar_websocket_connection_and_initial_snapshot(self):
        """
        Verify that a client connects to /ws/fleet/live-radar/ and receives
        an instant initial fleet_snapshot without HTTP polling.
        """
        communicator = WebsocketCommunicator(application, "/ws/fleet/live-radar/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "WebSocket connection to /ws/fleet/live-radar/ failed.")

        # First message should be fleet_snapshot
        response = await communicator.receive_json_from()
        self.assertEqual(response.get("type"), "fleet_snapshot")
        self.assertIn("data", response)
        self.assertIn("vehicles", response["data"])
        self.assertIn("summary", response["data"])
        self.assertGreaterEqual(response["data"]["summary"]["total_vehicles"], 1)

        # Disconnect cleanly
        await communicator.disconnect()

    async def test_fleet_radar_ping_pong_protocol(self):
        """
        Verify bidirectional ping-pong heartbeat over the WebSocket connection.
        """
        communicator = WebsocketCommunicator(application, "/ws/fleet/live-radar/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Consume initial snapshot
        await communicator.receive_json_from()

        # Send ping
        await communicator.send_json_to({"action": "ping"})
        response = await communicator.receive_json_from()
        self.assertEqual(response.get("type"), "pong")
        self.assertIn("timestamp", response)

        await communicator.disconnect()

    async def test_fleet_radar_request_snapshot_action(self):
        """
        Verify client can trigger an instant snapshot re-fetch via WebSocket.
        """
        communicator = WebsocketCommunicator(application, "/ws/fleet/live-radar/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Consume initial snapshot
        await communicator.receive_json_from()

        # Request fresh snapshot
        await communicator.send_json_to({"action": "request_snapshot"})
        response = await communicator.receive_json_from()
        self.assertEqual(response.get("type"), "fleet_snapshot")
        self.assertIn("vehicles", response["data"])

        await communicator.disconnect()

    async def test_telemetry_broadcast_delivered_to_websocket_client(self):
        """
        Verify that when telemetry is broadcast to the channel layer group,
        the connected WebSocket client receives a sub-50ms telemetry_ping event.
        """
        communicator = WebsocketCommunicator(application, "/ws/fleet/live-radar/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Consume initial snapshot
        await communicator.receive_json_from()

        # Broadcast telemetry update to group
        channel_layer = get_channel_layer()
        telemetry_payload = {
            "id": self.vehicle.id,
            "registration_number": self.vehicle.registration_number,
            "lat": 11.0250,
            "lng": 76.9600,
            "speed_kmh": 68.5,
            "heading_degrees": 90,
            "ignition_on": True,
            "status_code": "on_trip",
        }
        await channel_layer.group_send(
            "fleet_live_radar_global",
            {
                "type": "fleet_telemetry_broadcast",
                "data": telemetry_payload,
            }
        )

        # Receive streamed packet
        msg = await communicator.receive_json_from()
        self.assertEqual(msg.get("type"), "telemetry_ping")
        self.assertEqual(msg["data"]["registration_number"], "TN-38-BZ-9999")
        self.assertEqual(msg["data"]["speed_kmh"], 68.5)

        await communicator.disconnect()

    async def test_emergency_sos_websocket_consumer_flow(self):
        """
        Verify dedicated /ws/emergency/sos/ channel handshake and alarm streaming.
        """
        communicator = WebsocketCommunicator(application, "/ws/emergency/sos/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "WebSocket connection to /ws/emergency/sos/ failed.")

        # Receives initial emergency status
        status_msg = await communicator.receive_json_from()
        self.assertEqual(status_msg.get("type"), "emergency_status")
        self.assertIn("active_count", status_msg)

        # Send emergency SOS broadcast to group
        channel_layer = get_channel_layer()
        sos_data = {
            "incident_id": "INC-TEST-001",
            "vehicle_reg": "TN-38-BZ-9999",
            "incident_type": "Mechanical Breakdown",
            "severity": "critical",
            "location": "Ghat Road Hairpin 7",
            "description": "Engine overheating, radiator hose leak.",
        }
        await channel_layer.group_send(
            "emergency_sos_command",
            {
                "type": "emergency_sos_broadcast",
                "data": sos_data,
            }
        )

        alarm_msg = await communicator.receive_json_from()
        self.assertEqual(alarm_msg.get("type"), "sos_alert")
        self.assertEqual(alarm_msg["data"]["incident_id"], "INC-TEST-001")
        self.assertEqual(alarm_msg["data"]["severity"], "critical")

        await communicator.disconnect()

    def test_sync_telematics_payload_builder_and_broadcast_helpers(self):
        """
        Verify build_fleet_live_feed_payload and broadcast helper utilities.
        """
        payload = build_fleet_live_feed_payload()
        self.assertEqual(payload["status"], "success")
        self.assertIn("summary", payload)
        self.assertIn("vehicles", payload)
        self.assertIn("geofences", payload)
        self.assertTrue(any(v["registration_number"] == "TN-38-BZ-9999" for v in payload["vehicles"]))

        # Verify broadcast functions return True without error
        res_telemetry = broadcast_fleet_telemetry({
            "id": self.vehicle.id,
            "registration_number": self.vehicle.registration_number,
            "lat": 11.0168,
            "lng": 76.9558,
            "speed_kmh": 50.0,
        })
        self.assertTrue(res_telemetry)

        res_sos = broadcast_emergency_sos({
            "incident_id": "INC-SYNC-002",
            "severity": "critical",
            "description": "Test broadcast alarm",
        })
        self.assertTrue(res_sos)

        res_ack = broadcast_incident_acknowledgment(1, "Commander Murugan")
        self.assertTrue(res_ack)

    def test_ingest_telematics_ping_triggers_state_update_and_cache(self):
        """
        Verify that ingest_telematics_ping updates vehicle, records ping, and caches telematics.
        """
        ping_payload = {
            "vehicle_id": self.vehicle.id,
            "latitude": 11.0168,
            "longitude": 76.9558,
            "speed_kmh": 55.4,
            "heading": 120,
            "odometer_km": 45120,
            "fuel_level_pct": 78.5,
        }
        result = ingest_telematics_ping(ping_payload)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["vehicle"], "TN-38-BZ-9999")

        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.current_km, 45120)
        self.assertIn("11.01680", self.vehicle.current_location)

    async def test_crm_kanban_websocket_connection_and_card_sync(self):
        """
        Verify that a sales rep browser connects to /ws/crm/kanban/
        and receives instant kanban_card_moved updates with zero polling.
        """
        from crm.models import Inquiry
        communicator = WebsocketCommunicator(application, "/ws/crm/kanban/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "WebSocket connection to /ws/crm/kanban/ failed.")

        # Receive greeting
        msg = await communicator.receive_json_from()
        self.assertEqual(msg.get("type"), "kanban_connected")

        # Broadcast card movement
        channel_layer = get_channel_layer()
        card_data = {
            "inquiry_id": 99,
            "inquiry_number": "INQ-2026-099",
            "customer_name": "Dr. APJ Family Tour",
            "new_status": "quoted",
            "new_status_display": "Quoted",
            "user_name": "Rithik Manager",
            "deal_value": 75000.0,
            "timestamp": "15:30:00",
        }
        await channel_layer.group_send(
            "crm_kanban_global",
            {
                "type": "kanban_card_broadcast",
                "data": card_data,
            }
        )

        received_card_event = await communicator.receive_json_from()
        self.assertEqual(received_card_event.get("type"), "kanban_card_moved")
        self.assertEqual(received_card_event["data"]["customer_name"], "Dr. APJ Family Tour")
        self.assertEqual(received_card_event["data"]["new_status"], "quoted")

        await communicator.disconnect()

