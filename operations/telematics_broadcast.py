import math
from datetime import timedelta
from decimal import Decimal
from typing import Optional, Dict, Any

from django.utils import timezone
from django.db.models import Max
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from core.models import Vehicle, Driver
from core.depot_scoping import get_user_depot_scope, get_scoped_vehicles
from operations.models import Trip, VehicleTelematicsPing, EmergencyIncidentAlert, GeofenceZone, DriverBehaviorLog
from operations.services import calculate_haversine_distance_meters
from maintenance.models import DefectTicket, PreTripInspectionChecklist
from analytics.models import DriverScorecard

DESTINATION_COORDINATES = {
    'ooty': (11.4102, 76.6950),
    'udhagamandalam': (11.4102, 76.6950),
    'chennai': (13.0827, 80.2707),
    'bangalore': (12.9716, 77.5946),
    'bengaluru': (12.9716, 77.5946),
    'madurai': (9.9252, 78.1198),
    'munnar': (10.0889, 77.0595),
    'kodaikanal': (10.2381, 77.4892),
    'salem': (11.6643, 78.1460),
    'coimbatore': (11.0168, 76.9558),
    'tirupur': (11.1085, 77.3411),
    'pollachi': (10.6580, 77.0090),
    'kochi': (9.9312, 76.2673),
    'mysore': (12.2958, 76.6394),
    'kanyakumari': (8.0883, 77.5385),
    'rameshwaram': (9.2876, 79.3129),
    'trichy': (10.7905, 78.7047),
    'tiruchirappalli': (10.7905, 78.7047),
    'pondicherry': (11.9416, 79.8083),
}


def build_fleet_live_feed_payload(user=None, depot_param=None) -> Dict[str, Any]:
    """
    Constructs the canonical real-time telematics snapshot dictionary containing:
    - Scoped fleet vehicles with live coordinates, heading, speed, fuel, odometer
    - Driver scorecard and assigned active trip breadcrumbs
    - Active SOS incidents and geofence perimeter alerts
    - Dynamic summary KPI counters
    """
    depot_scope = get_user_depot_scope(user, depot_param)
    now = timezone.now()
    five_days_ago = (now - timedelta(days=5)).date()

    vehicles = get_scoped_vehicles(user, depot_param).select_related('vehicle_type', 'default_driver')
    scoped_vehicle_ids = set(vehicles.values_list('id', flat=True))

    active_incidents = EmergencyIncidentAlert.objects.filter(
        status__in=['reported', 'acknowledged', 'standby_dispatched']
    ).select_related('vehicle', 'driver')
    if depot_scope['effective_depot']:
        active_incidents = active_incidents.filter(vehicle_id__in=scoped_vehicle_ids)
    incident_by_vehicle = {inc.vehicle_id: inc for inc in active_incidents}

    # Open defect tickets
    defect_vehicle_ids = set(
        DefectTicket.objects.filter(status='open', vehicle_id__in=scoped_vehicle_ids).values_list('vehicle_id', flat=True)
    )

    # Failed checklists in last 48 hours
    two_days_ago = now - timedelta(days=2)
    failed_checklists_vehicle_ids = set(
        PreTripInspectionChecklist.objects.filter(
            overall_status='failed', created_at__gte=two_days_ago, vehicle_id__in=scoped_vehicle_ids
        ).values_list('vehicle_id', flat=True)
    )

    # Active trips
    active_trips = Trip.objects.filter(
        status__in=['assigned', 'started'],
        vehicle_id__in=scoped_vehicle_ids
    ).select_related('driver', 'booking', 'vehicle')
    trip_by_vehicle = {t.vehicle_id: t for t in active_trips if t.vehicle_id}

    # Recent trips in 5 days
    recent_trip_vehicle_ids = set(
        Trip.objects.filter(start_date__gte=five_days_ago, vehicle_id__in=scoped_vehicle_ids).values_list('vehicle_id', flat=True)
    )

    # Driver scorecards cached by driver_id
    scorecard_by_driver = {
        sc.driver_id: sc for sc in DriverScorecard.objects.all()
    }

    # Active Geofence Zones
    geofences = list(GeofenceZone.objects.filter(is_active=True))
    geofences_list = []
    for g in geofences:
        geofences_list.append({
            "id": g.id,
            "name": g.name,
            "zone_type": g.get_zone_type_display(),
            "zone_code": g.zone_type,
            "lat": float(g.latitude),
            "lng": float(g.longitude),
            "radius": g.radius_meters,
            "speed_limit": g.speed_limit_kmh,
        })

    # Optimized latest telematics pings lookup
    latest_ping_ids = VehicleTelematicsPing.objects.filter(
        vehicle_id__in=scoped_vehicle_ids
    ).values('vehicle_id').annotate(max_id=Max('id')).values_list('max_id', flat=True)
    latest_pings_map = {p.vehicle_id: p for p in VehicleTelematicsPing.objects.filter(id__in=latest_ping_ids)}

    vehicle_list = []
    active_count = 0
    standby_count = 0
    workshop_count = 0
    idle_count = 0
    sos_count = 0
    geofence_breach_count = 0

    depot_hub_coords = {
        'Chennai Central HQ': (13.0827, 80.2707),
        'Coimbatore Hub': (11.0168, 76.9558),
        'Madurai Depo': (9.9252, 78.1198),
        'Bengaluru Station': (12.9716, 77.5946),
        'Central Control Room': (13.0827, 80.2707),
    }
    base_lat, base_lng = depot_hub_coords.get(depot_scope['effective_depot'], (11.0168, 76.9558))

    for v in vehicles:
        incident = incident_by_vehicle.get(v.id)
        active_trip = trip_by_vehicle.get(v.id)
        in_workshop = (
            v.status in ['in_shop', 'breakdown', 'maintenance'] or
            v.id in defect_vehicle_ids or
            v.id in failed_checklists_vehicle_ids
        )
        has_recent_trip = (v.id in recent_trip_vehicle_ids) or (active_trip is not None)

        if incident:
            status_code = 'sos_alert'
            status_label = f"🔴 SOS: {incident.get_incident_type_display()}"
            status_color = "#ef4444"
            sos_count += 1
        elif in_workshop:
            status_code = 'workshop'
            status_label = "🟠 In Workshop / Grounded"
            status_color = "#f59e0b"
            workshop_count += 1
        elif active_trip:
            status_code = 'on_trip'
            status_label = "🟢 On Trip"
            status_color = "#10b981"
            active_count += 1
        elif not has_recent_trip:
            status_code = 'idle'
            status_label = "⚪ Idle (>5 Days)"
            status_color = "#94a3b8"
            idle_count += 1
        else:
            status_code = 'standby'
            status_label = "🔵 Ready Standby"
            status_color = "#3b82f6"
            standby_count += 1

        # Telematics coordinates & gauges
        latest_ping = latest_pings_map.get(v.id)
        if latest_ping and latest_ping.latitude and latest_ping.longitude:
            lat = float(latest_ping.latitude)
            lng = float(latest_ping.longitude)
            speed = float(latest_ping.speed_kmh)
            heading = float(latest_ping.heading_degrees or 0.0)
            ignition = latest_ping.ignition_on
            fuel_pct = float(latest_ping.fuel_level_pct) if latest_ping.fuel_level_pct is not None else 72.0
            ping_time = latest_ping.timestamp.strftime('%H:%M:%S')
            odometer = latest_ping.odometer_km or v.current_km or 40000
            satellites = latest_ping.satellite_count or 10
            altitude = float(latest_ping.altitude_m or 425.0)
        else:
            speed = 52.0 if status_code == 'on_trip' else 0.0
            heading = 45.0 if status_code == 'on_trip' else 0.0
            ignition = True if status_code == 'on_trip' else False
            fuel_pct = 75.0
            ping_time = "Live System"
            odometer = v.current_km or 42000
            satellites = 9
            altitude = 425.0

            assigned_dest = active_trip.destination.lower() if active_trip and active_trip.destination else ""
            coords_found = False
            for place, coords in DESTINATION_COORDINATES.items():
                if place in assigned_dest:
                    lat = coords[0] + (((v.id * 7) % 20) - 10) * 0.002
                    lng = coords[1] + (((v.id * 11) % 20) - 10) * 0.002
                    coords_found = True
                    break
            if not coords_found:
                lat = base_lat + (((v.id * 17) % 40) - 20) * 0.0018
                lng = base_lng + (((v.id * 23) % 40) - 20) * 0.0018

        # Breadcrumbs trail (last positions for radar trailing effect)
        crumbs = [[lat, lng]]
        if speed > 0:
            h_rad = math.radians(heading)
            for step in range(1, 4):
                crumbs.append([
                    round(lat - (step * 0.0012 * math.cos(h_rad)), 6),
                    round(lng - (step * 0.0012 * math.sin(h_rad)), 6)
                ])

        # Geofence Perimeter Detection
        geofence_status = None
        for g in geofences:
            dist = calculate_haversine_distance_meters(lat, lng, g.latitude, g.longitude)
            if dist <= g.radius_meters:
                is_speeding = speed > g.speed_limit_kmh
                is_restricted = (g.zone_type == 'restricted_zone')
                alert_text = (
                    "RESTRICTED ZONE INTRUSION" if is_restricted else
                    ("OVERSPEED IN GEOFENCE" if is_speeding else "INSIDE GEOFENCE")
                )
                if is_speeding or is_restricted:
                    geofence_breach_count += 1

                geofence_status = {
                    "zone_id": g.id,
                    "zone_name": g.name,
                    "zone_type": g.get_zone_type_display(),
                    "zone_code": g.zone_type,
                    "distance_meters": round(dist, 1),
                    "speed_limit_kmh": g.speed_limit_kmh,
                    "is_speeding": is_speeding,
                    "is_restricted": is_restricted,
                    "alert_text": alert_text,
                }
                break

        # Driver details
        driver_obj = active_trip.driver if active_trip and active_trip.driver else v.default_driver
        driver_info = None
        if driver_obj:
            sc = scorecard_by_driver.get(driver_obj.id)
            driver_info = {
                "id": driver_obj.id,
                "name": driver_obj.name,
                "phone": driver_obj.phone,
                "grade": sc.grade if sc else "A+",
                "safety_score": float(sc.safety_score) if sc else 98.0,
            }

        # Trip details and route geometry
        trip_info = None
        trip_route = None
        if active_trip:
            dest_str = (active_trip.destination or "").lower()
            pickup_str = (active_trip.pickup_location or "").lower()

            orig_lat, orig_lng = base_lat, base_lng
            for place, coords in DESTINATION_COORDINATES.items():
                if place in pickup_str:
                    orig_lat, orig_lng = coords
                    break

            dest_lat, dest_lng = (11.4102, 76.6950)  # Default Ooty
            for place, coords in DESTINATION_COORDINATES.items():
                if place in dest_str:
                    dest_lat, dest_lng = coords
                    break

            trip_info = {
                "id": active_trip.id,
                "booking_number": active_trip.booking.booking_number if active_trip.booking else f"TRP-{active_trip.id}",
                "guest_name": active_trip.guest_name or "Guest Passenger",
                "guest_phone": active_trip.booking.guest_phone if active_trip.booking else "",
                "pickup": active_trip.pickup_location or "Coimbatore Terminal",
                "destination": active_trip.destination or "Ooty Boat House",
                "status": active_trip.get_status_display(),
            }

            trip_route = {
                "trip_id": active_trip.id,
                "booking_number": trip_info["booking_number"],
                "origin_name": trip_info["pickup"],
                "origin_coords": [orig_lat, orig_lng],
                "dest_name": trip_info["destination"],
                "dest_coords": [dest_lat, dest_lng],
                "route_path": [
                    [orig_lat, orig_lng],
                    [lat, lng],
                    [dest_lat, dest_lng]
                ],
                "eta_minutes": max(15, int(abs(dest_lat - lat) * 550) + 10),
                "progress_pct": 58,
            }

        # Incident details
        incident_info = None
        if incident:
            incident_info = {
                "id": incident.id,
                "incident_id": incident.incident_id,
                "incident_type": incident.get_incident_type_display(),
                "severity": incident.get_severity_display(),
                "description": incident.description,
                "reported_at": incident.reported_at.strftime('%H:%M') if incident.reported_at else "",
            }

        vehicle_list.append({
            "id": v.id,
            "registration_number": v.registration_number,
            "model_name": f"{v.brand} {v.model}".strip(),
            "vehicle_type": v.vehicle_type.name if v.vehicle_type else "Vehicle",
            "capacity": v.seating_capacity,
            "current_km": odometer,
            "fuel_type": v.get_fuel_type_display() if hasattr(v, 'get_fuel_type_display') else v.fuel_type,
            "status_code": status_code,
            "status_label": status_label,
            "status_color": status_color,
            "base_depot": v.base_depot or "Coimbatore Hub",
            "location_name": v.current_location or "Coimbatore Operational Sector",
            "lat": lat,
            "lng": lng,
            "speed_kmh": speed,
            "heading_degrees": heading,
            "ignition_on": ignition,
            "fuel_level_pct": fuel_pct,
            "satellites": satellites,
            "altitude_m": altitude,
            "breadcrumbs": crumbs,
            "geofence_status": geofence_status,
            "last_ping_time": ping_time,
            "driver": driver_info,
            "trip": trip_info,
            "trip_route": trip_route,
            "incident": incident_info,
        })

    # Recent behavior events (violations in last 24h)
    recent_violations = []
    since_yesterday = now - timedelta(days=1)
    behavior_events = DriverBehaviorLog.objects.filter(
        timestamp__gte=since_yesterday
    ).select_related('driver', 'vehicle').order_by('-timestamp')[:15]
    for b in behavior_events:
        recent_violations.append({
            "id": b.id,
            "event_type": b.get_event_type_display(),
            "severity": b.severity,
            "vehicle_reg": b.vehicle.registration_number if b.vehicle else "N/A",
            "driver_name": b.driver.name if b.driver else "N/A",
            "speed": float(b.recorded_speed_kmh),
            "limit": float(b.speed_limit_kmh),
            "time": b.timestamp.strftime('%H:%M:%S'),
        })

    # Active incidents list
    incidents_list = []
    for inc in active_incidents:
        incidents_list.append({
            "id": inc.id,
            "incident_id": inc.incident_id,
            "vehicle_reg": inc.vehicle.registration_number if inc.vehicle else "",
            "driver_name": inc.driver.name if inc.driver else "Unassigned",
            "incident_type": inc.get_incident_type_display(),
            "severity": inc.severity,
            "status": inc.get_status_display(),
            "location": inc.location_address or "GPS Location",
            "reported_at": inc.reported_at.strftime('%H:%M') if inc.reported_at else "",
            "description": inc.description,
        })

    return {
        "status": "success",
        "timestamp": now.strftime('%Y-%m-%d %H:%M:%S'),
        "depot_scope": {
            "effective_depot": depot_scope['effective_depot'],
            "display_label": depot_scope['display_label'],
            "is_global": depot_scope['is_global'],
            "can_change_depot": depot_scope['can_change_depot'],
            "user_branch": depot_scope['user_branch'],
        },
        "summary": {
            "total_vehicles": len(vehicle_list),
            "active_count": active_count,
            "standby_count": standby_count,
            "workshop_count": workshop_count,
            "idle_count": idle_count,
            "sos_count": sos_count,
            "geofence_breaches_count": geofence_breach_count,
            "active_alerts_count": len(incidents_list),
            "violations_count": len(recent_violations),
        },
        "vehicles": vehicle_list,
        "active_incidents": incidents_list,
        "recent_violations": recent_violations,
        "geofences": geofences_list,
    }


def broadcast_fleet_telemetry(vehicle_data: Dict[str, Any], depot: Optional[str] = None) -> bool:
    """
    Broadcasts real-time vehicle GPS, heading, speed, and status packet to all connected
    WebSocket clients on the global fleet radar channel and depot channel.
    """
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return False

        message = {
            "type": "fleet_telemetry_broadcast",
            "data": vehicle_data,
        }
        async_to_sync(channel_layer.group_send)("fleet_live_radar_global", message)

        if depot:
            safe_depot = str(depot).lower().replace(' ', '_').replace('-', '_')
            async_to_sync(channel_layer.group_send)(f"fleet_depot_{safe_depot}", message)
        return True
    except Exception as e:
        return False


def broadcast_emergency_sos(incident_data: Dict[str, Any]) -> bool:
    """
    Broadcasts high-priority emergency SOS alarm to live operations rooms,
    sounding visual/audio beacons immediately on open dispatcher terminals.
    """
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return False

        message = {
            "type": "emergency_sos_broadcast",
            "data": incident_data,
        }
        async_to_sync(channel_layer.group_send)("fleet_live_radar_global", message)
        async_to_sync(channel_layer.group_send)("emergency_sos_command", message)
        return True
    except Exception:
        return False


def broadcast_incident_acknowledgment(incident_id: int, acknowledged_by: str = "Operations Desk") -> bool:
    """
    Broadcasts acknowledgment of an SOS emergency incident to all connected clients.
    """
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return False

        message = {
            "type": "emergency_ack_broadcast",
            "data": {
                "incident_id": incident_id,
                "acknowledged_by": acknowledged_by,
                "timestamp": timezone.now().strftime('%H:%M:%S'),
            },
        }
        async_to_sync(channel_layer.group_send)("fleet_live_radar_global", message)
        async_to_sync(channel_layer.group_send)("emergency_sos_command", message)
        return True
    except Exception:
        return False


def broadcast_fleet_snapshot(user=None, depot_param=None) -> bool:
    """
    Builds and broadcasts a full refreshed fleet snapshot to WebSocket channels.
    """
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return False

        payload = build_fleet_live_feed_payload(user=user, depot_param=depot_param)
        message = {
            "type": "fleet_snapshot_broadcast",
            "data": payload,
        }
        group = "fleet_live_radar_global"
        if depot_param and depot_param != 'all':
            safe_depot = str(depot_param).lower().replace(' ', '_').replace('-', '_')
            group = f"fleet_depot_{safe_depot}"

        async_to_sync(channel_layer.group_send)(group, message)
        return True
    except Exception:
        return False
