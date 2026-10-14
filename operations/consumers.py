import json
import urllib.parse
from typing import Dict, Any, List

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from asgiref.sync import sync_to_async
from django.utils import timezone

from operations.telematics_broadcast import (
    build_fleet_live_feed_payload,
    broadcast_incident_acknowledgment,
)
from operations.models import EmergencyIncidentAlert


class FleetLiveRadarConsumer(AsyncJsonWebsocketConsumer):
    """
    High-Performance Zero-Polling Fleet Radar WebSocket Consumer.
    Streams real-time vehicle GPS positions, headings, speeds, and breadcrumbs directly
    to open dispatcher terminals with sub-50ms latency.
    """

    async def connect(self):
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        params = urllib.parse.parse_qs(query_string)
        self.depot_param = params.get('depot', [None])[0]

        self.global_group = "fleet_live_radar_global"
        await self.channel_layer.group_add(self.global_group, self.channel_name)

        self.depot_group = None
        if self.depot_param and self.depot_param != 'all':
            safe_depot = str(self.depot_param).lower().replace(' ', '_').replace('-', '_')
            self.depot_group = f"fleet_depot_{safe_depot}"
            await self.channel_layer.group_add(self.depot_group, self.channel_name)

        await self.accept()

        # Send initial real-time snapshot immediately on connection handshake
        user = self.scope.get('user')
        snapshot = await sync_to_async(build_fleet_live_feed_payload)(
            user=user if user and user.is_authenticated else None,
            depot_param=self.depot_param
        )
        await self.send_json({
            "type": "fleet_snapshot",
            "connected_at": timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            "depot_filter": self.depot_param or "all",
            "data": snapshot,
        })

    async def disconnect(self, close_code):
        if hasattr(self, 'global_group') and self.global_group:
            await self.channel_layer.group_discard(self.global_group, self.channel_name)
        if hasattr(self, 'depot_group') and self.depot_group:
            await self.channel_layer.group_discard(self.depot_group, self.channel_name)

    async def receive_json(self, content: Dict[str, Any], **kwargs):
        action = content.get('action')
        user = self.scope.get('user')

        if action == 'request_snapshot':
            snapshot = await sync_to_async(build_fleet_live_feed_payload)(
                user=user if user and user.is_authenticated else None,
                depot_param=self.depot_param
            )
            await self.send_json({
                "type": "fleet_snapshot",
                "timestamp": timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                "data": snapshot,
            })
        elif action == 'ping':
            await self.send_json({
                "type": "pong",
                "timestamp": timezone.now().isoformat(),
            })
        elif action == 'simulate_tick':
            from operations.views import api_fleet_telematics_tick
            # Trigger tick generation in background
            from operations.models import Trip, Vehicle, VehicleTelematicsPing
            from decimal import Decimal
            import random, math

            def _run_tick():
                vehicles = list(Vehicle.objects.all()[:5])
                ticks = []
                for v in vehicles:
                    latest = v.telematics_pings.first()
                    base_lat = float(latest.latitude) if latest and latest.latitude else 11.0168
                    base_lng = float(latest.longitude) if latest and latest.longitude else 76.9558
                    d_lat = random.choice([0.0008, 0.0012, -0.0006])
                    d_lng = random.choice([0.0007, 0.0011, -0.0005])
                    n_lat = round(base_lat + d_lat, 6)
                    n_lng = round(base_lng + d_lng, 6)
                    spd = round(random.uniform(45.0, 75.0), 1)
                    hdg = int((math.degrees(math.atan2(d_lng, d_lat)) + 360) % 360)
                    ping = VehicleTelematicsPing.objects.create(
                        vehicle=v,
                        timestamp=timezone.now(),
                        latitude=Decimal(str(n_lat)),
                        longitude=Decimal(str(n_lng)),
                        speed_kmh=Decimal(str(spd)),
                        heading_degrees=hdg,
                        ignition_on=True,
                        fuel_level_pct=Decimal("74.5"),
                        odometer_km=(v.current_km or 40000) + 1
                    )
                    v.current_location = f"{n_lat:.5f}, {n_lng:.5f}"
                    v.save(update_fields=['current_location'])
                    from operations.telematics_broadcast import broadcast_fleet_telemetry
                    broadcast_fleet_telemetry({
                        "id": v.id,
                        "registration_number": v.registration_number,
                        "lat": n_lat,
                        "lng": n_lng,
                        "speed_kmh": spd,
                        "heading_degrees": hdg,
                        "ignition_on": True,
                        "fuel_level_pct": 74.5,
                        "status_code": "on_trip",
                        "status_label": "🟢 On Trip",
                        "status_color": "#10b981",
                        "last_ping_time": ping.timestamp.strftime('%H:%M:%S'),
                    })
                    ticks.append({"id": v.id, "reg": v.registration_number, "lat": n_lat, "lng": n_lng})
                return ticks

            ticks = await sync_to_async(_run_tick)()
            await self.send_json({
                "type": "tick_simulation_result",
                "ticks_count": len(ticks),
                "ticks": ticks,
            })

    # Group send message handlers
    async def fleet_telemetry_broadcast(self, event: Dict[str, Any]):
        await self.send_json({
            "type": "telemetry_ping",
            "data": event.get("data", {}),
        })

    async def emergency_sos_broadcast(self, event: Dict[str, Any]):
        await self.send_json({
            "type": "sos_alert",
            "data": event.get("data", {}),
        })

    async def emergency_ack_broadcast(self, event: Dict[str, Any]):
        await self.send_json({
            "type": "sos_acknowledged",
            "data": event.get("data", {}),
        })

    async def fleet_snapshot_broadcast(self, event: Dict[str, Any]):
        await self.send_json({
            "type": "fleet_snapshot",
            "data": event.get("data", {}),
        })


class EmergencySOSConsumer(AsyncJsonWebsocketConsumer):
    """
    Dedicated Emergency SOS & Panic Alarm WebSocket Consumer.
    Listens on /ws/emergency/sos/ for instantaneous emergency broadcasts.
    """

    async def connect(self):
        self.emergency_group = "emergency_sos_command"
        await self.channel_layer.group_add(self.emergency_group, self.channel_name)
        await self.accept()

        # Send current active emergencies count and list
        def _get_active():
            incidents = EmergencyIncidentAlert.objects.filter(
                status__in=['reported', 'acknowledged', 'standby_dispatched']
            ).select_related('vehicle', 'driver')
            return [
                {
                    "id": inc.id,
                    "incident_id": inc.incident_id,
                    "vehicle_reg": inc.vehicle.registration_number if inc.vehicle else "",
                    "driver_name": inc.driver.name if inc.driver else "Unassigned",
                    "incident_type": inc.get_incident_type_display(),
                    "severity": inc.severity,
                    "status": inc.get_status_display(),
                    "reported_at": inc.reported_at.strftime('%H:%M:%S') if inc.reported_at else "",
                    "description": inc.description,
                }
                for inc in incidents
            ]

        active_incidents = await sync_to_async(_get_active)()
        await self.send_json({
            "type": "emergency_status",
            "active_count": len(active_incidents),
            "incidents": active_incidents,
        })

    async def disconnect(self, close_code):
        if hasattr(self, 'emergency_group') and self.emergency_group:
            await self.channel_layer.group_discard(self.emergency_group, self.channel_name)

    async def receive_json(self, content: Dict[str, Any], **kwargs):
        action = content.get('action')
        if action == 'acknowledge_alert':
            incident_id = content.get('incident_id')
            if incident_id:
                def _ack():
                    inc = EmergencyIncidentAlert.objects.filter(pk=incident_id).first()
                    if inc:
                        inc.status = 'acknowledged'
                        inc.save(update_fields=['status'])
                        return True
                    return False

                success = await sync_to_async(_ack)()
                if success:
                    user_label = "Operations Desk"
                    user = self.scope.get('user')
                    if user and user.is_authenticated:
                        user_label = user.get_full_name() or user.username
                    await sync_to_async(broadcast_incident_acknowledgment)(incident_id, user_label)

    async def emergency_sos_broadcast(self, event: Dict[str, Any]):
        await self.send_json({
            "type": "sos_alert",
            "data": event.get("data", {}),
        })

    async def emergency_ack_broadcast(self, event: Dict[str, Any]):
        await self.send_json({
            "type": "sos_acknowledged",
            "data": event.get("data", {}),
        })
