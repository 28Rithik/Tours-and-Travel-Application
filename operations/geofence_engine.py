"""
operations/geofence_engine.py

Autonomous Geofence & Fleet Safety Engine for Sivagayathiri Tours & Travels (TravelERP).

Responsibilities:
1. Evaluates live and simulated telematics coordinate pings against GeofenceZone perimeters.
2. Detects unauthorized restricted zone intrusions, zone overspeeding, and route corridor deviations.
3. Enforces night transit stoppage watchdogs (10 PM - 5 AM stationary idle checks).
4. Auto-creates EmergencyIncidentAlert records, DriverBehaviorLog infractions, and outbound WhatsApp alarms.
5. Provides throttling / deduplication to prevent alert storms.
6. Offers dispatcher acknowledgment and incident resolution workflows.
"""

import math
import logging
from decimal import Decimal
from datetime import timedelta
from typing import Dict, Any, List, Optional, Tuple

from django.utils import timezone
from django.db import transaction

from core.models import Vehicle, Driver
from operations.models import (
    VehicleTelematicsPing,
    GeofenceZone,
    DriverBehaviorLog,
    EmergencyIncidentAlert,
    WhatsAppBotMessage,
    Trip,
)

logger = logging.getLogger('operations.geofence')

# Standard coordinate benchmarks across Tamil Nadu / South India circuits
HQ_DEPOT_COORDS = (11.0168, 76.9558)  # Coimbatore HQ
KNOWN_DESTINATIONS = {
    'ooty': (11.4102, 76.6950),
    'coonoor': (11.3530, 76.7959),
    'kodaikanal': (10.2381, 77.4892),
    'munnar': (10.0889, 77.0595),
    'madurai': (9.9252, 78.1198),
    'coimbatore': (11.0168, 76.9558),
    'pollachi': (10.6609, 77.0048),
    'valparai': (10.3262, 76.9554),
    'palani': (10.4500, 77.5200),
    'salem': (11.6643, 78.1460),
    'chennai': (13.0827, 80.2707),
    'bangalore': (12.9716, 77.5946),
    'bengaluru': (12.9716, 77.5946),
    'mysore': (12.2958, 76.6394),
}


def haversine_distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Computes great-circle distance between two GPS coordinates in meters.
    """
    r = 6371000.0  # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def distance_point_to_segment_meters(p_lat: float, p_lng: float,
                                    a_lat: float, a_lng: float,
                                    b_lat: float, b_lng: float) -> float:
    """
    Computes orthogonal or clamped distance from point P to line segment AB in meters.
    Uses equirectangular projection approximation for local route segments.
    """
    mid_lat_rad = math.radians((a_lat + b_lat) / 2.0)
    cos_lat = math.cos(mid_lat_rad)

    def to_xy(lat, lng):
        return (lng * 111000.0 * cos_lat, lat * 111000.0)

    px, py = to_xy(p_lat, p_lng)
    ax, ay = to_xy(a_lat, a_lng)
    bx, by = to_xy(b_lat, b_lng)

    dx = bx - ax
    dy = by - ay
    line_len_sq = dx * dx + dy * dy

    if line_len_sq == 0:
        return math.hypot(px - ax, py - ay)

    # Project point onto segment: t in [0, 1]
    t = ((px - ax) * dx + (py - ay) * dy) / line_len_sq
    t = max(0.0, min(1.0, t))

    proj_x = ax + t * dx
    proj_y = ay + t * dy

    return math.hypot(px - proj_x, py - proj_y)


class GeofenceSafetyEngine:
    """
    Autonomous Geofence, Route Corridor & Fleet Safety Evaluation Engine.
    """

    ALERT_COOLDOWN_MINUTES = 15  # Avoid alert flooding per vehicle/event

    @classmethod
    def evaluate_ping(cls, ping: VehicleTelematicsPing) -> Dict[str, Any]:
        """
        Evaluates a single VehicleTelematicsPing against active GeofenceZones,
        trip route corridors, and night transit safety watchdogs.

        Returns an evaluation report dict with detected violations and triggered actions.
        """
        if not ping or not ping.latitude or not ping.longitude:
            return {"status": "skipped", "reason": "invalid_coordinates"}

        vehicle = ping.vehicle
        driver = vehicle.default_driver
        active_trip = ping.trip or Trip.objects.filter(
            vehicle=vehicle,
            status__in=['assigned', 'started']
        ).first()

        if active_trip and active_trip.driver:
            driver = active_trip.driver

        lat = float(ping.latitude)
        lng = float(ping.longitude)
        speed = float(ping.speed_kmh or 0.0)
        timestamp = ping.timestamp or timezone.now()

        active_geofences = list(GeofenceZone.objects.filter(is_active=True))
        violations_detected = []
        incident_created = None
        whatsapp_message = None

        # ----------------------------------------------------------------------
        # 1. EVALUATE GEOFENCE ZONES (Restricted Intrusions & Overspeed)
        # ----------------------------------------------------------------------
        for zone in active_geofences:
            z_lat = float(zone.latitude)
            z_lng = float(zone.longitude)
            dist_meters = haversine_distance_meters(lat, lng, z_lat, z_lng)

            if dist_meters <= zone.radius_meters:
                # Inside Zone
                # Check 1A: Restricted Zone Intrusion
                if zone.zone_type == 'restricted_zone':
                    violation = cls._handle_restricted_intrusion(
                        vehicle=vehicle,
                        driver=driver,
                        trip=active_trip,
                        zone=zone,
                        ping=ping,
                        dist_meters=dist_meters
                    )
                    violations_detected.append(violation)
                    if violation.get('incident'):
                        incident_created = violation['incident']
                    if violation.get('whatsapp'):
                        whatsapp_message = violation['whatsapp']

                # Check 1B: Zone Speed Limit Violation
                elif speed > zone.speed_limit_kmh:
                    violation = cls._handle_zone_overspeed(
                        vehicle=vehicle,
                        driver=driver,
                        trip=active_trip,
                        zone=zone,
                        ping=ping,
                        speed=speed
                    )
                    violations_detected.append(violation)
                    if violation.get('incident'):
                        incident_created = violation['incident']
                    if violation.get('whatsapp'):
                        whatsapp_message = violation['whatsapp']

        # ----------------------------------------------------------------------
        # 2. EVALUATE ROUTE CORRIDOR ADHERENCE
        # ----------------------------------------------------------------------
        if active_trip:
            corridor_violation = cls._evaluate_route_corridor(
                vehicle=vehicle,
                driver=driver,
                trip=active_trip,
                ping=ping,
                lat=lat,
                lng=lng,
                speed=speed
            )
            if corridor_violation:
                violations_detected.append(corridor_violation)
                if corridor_violation.get('incident'):
                    incident_created = corridor_violation['incident']
                if corridor_violation.get('whatsapp'):
                    whatsapp_message = corridor_violation['whatsapp']

        # ----------------------------------------------------------------------
        # 3. EVALUATE NIGHT TRANSIT SAFETY (10 PM - 5 AM Idle Watchdog)
        # ----------------------------------------------------------------------
        if active_trip:
            night_violation = cls._evaluate_night_stoppage(
                vehicle=vehicle,
                driver=driver,
                trip=active_trip,
                ping=ping,
                speed=speed,
                timestamp=timestamp
            )
            if night_violation:
                violations_detected.append(night_violation)

        return {
            "status": "evaluated",
            "vehicle": vehicle.registration_number,
            "violations_count": len(violations_detected),
            "violations": violations_detected,
            "incident_created_id": incident_created.incident_id if incident_created else None,
            "whatsapp_sent": bool(whatsapp_message),
        }

    @classmethod
    def _handle_restricted_intrusion(
        cls,
        vehicle: Vehicle,
        driver: Optional[Driver],
        trip: Optional[Trip],
        zone: GeofenceZone,
        ping: VehicleTelematicsPing,
        dist_meters: float
    ) -> Dict[str, Any]:
        """
        Handles unauthorized entry into a restricted / prohibited perimeter.
        """
        cutoff = timezone.now() - timedelta(minutes=cls.ALERT_COOLDOWN_MINUTES)
        recent_log = DriverBehaviorLog.objects.filter(
            vehicle=vehicle,
            event_type='geofence_breach',
            timestamp__gte=cutoff,
            location_address=zone.name
        ).first()

        if recent_log:
            return {
                "type": "restricted_intrusion",
                "zone": zone.name,
                "status": "throttled",
                "message": f"Intrusion already logged within {cls.ALERT_COOLDOWN_MINUTES}m"
            }

        # 1. Create DriverBehaviorLog
        behavior_log = DriverBehaviorLog.objects.create(
            vehicle=vehicle,
            driver=driver,
            trip=trip,
            timestamp=ping.timestamp or timezone.now(),
            event_type='geofence_breach',
            severity='critical',
            recorded_speed_kmh=ping.speed_kmh or Decimal('0.0'),
            speed_limit_kmh=Decimal(str(zone.speed_limit_kmh)),
            latitude=ping.latitude,
            longitude=ping.longitude,
            location_address=zone.name,
            penalty_points=20,
            notes=f"CRITICAL: Unauthorized vehicle intrusion into restricted perimeter '{zone.name}' ({int(dist_meters)}m from center)."
        )

        # 2. Create EmergencyIncidentAlert
        desc = (
            f"Autonomous Geofence Alarm: Vehicle {vehicle.registration_number} entered restricted zone "
            f"'{zone.name}' at speed {ping.speed_kmh or 0} km/h. Distance from center: {int(dist_meters)}m."
        )
        incident = EmergencyIncidentAlert.objects.create(
            incident_type='geofence_breach',
            severity='critical',
            vehicle=vehicle,
            driver=driver or vehicle.default_driver or Driver.objects.first(),
            trip=trip,
            reported_at=timezone.now(),
            latitude=ping.latitude,
            longitude=ping.longitude,
            location_address=f"{zone.name} (Restricted Zone)",
            passenger_count=trip.passenger_count if trip and hasattr(trip, 'passenger_count') else 0,
            passengers_safety_status='all_safe',
            description=desc,
            status='reported'
        )

        # 3. Dispatch WhatsApp Alarm
        whatsapp_msg = cls._broadcast_whatsapp_alert(
            incident=incident,
            zone_name=zone.name,
            alert_headline="RESTRICTED ZONE INTRUSION"
        )

        return {
            "type": "restricted_intrusion",
            "zone": zone.name,
            "status": "alert_dispatched",
            "behavior_log_id": behavior_log.id,
            "incident": incident,
            "whatsapp": whatsapp_msg
        }

    @classmethod
    def _handle_zone_overspeed(
        cls,
        vehicle: Vehicle,
        driver: Optional[Driver],
        trip: Optional[Trip],
        zone: GeofenceZone,
        ping: VehicleTelematicsPing,
        speed: float
    ) -> Dict[str, Any]:
        """
        Handles overspeeding violation inside a speed-limited geofence zone (e.g. school/depot).
        """
        diff = speed - zone.speed_limit_kmh
        severity = 'critical' if diff >= 25.0 else 'high'
        cutoff = timezone.now() - timedelta(minutes=cls.ALERT_COOLDOWN_MINUTES)

        recent_log = DriverBehaviorLog.objects.filter(
            vehicle=vehicle,
            event_type='overspeeding',
            timestamp__gte=cutoff,
            location_address=zone.name
        ).first()

        if recent_log:
            return {
                "type": "zone_overspeed",
                "zone": zone.name,
                "status": "throttled",
                "speed": speed,
                "limit": zone.speed_limit_kmh
            }

        penalty = 15 if severity == 'critical' else 8
        behavior_log = DriverBehaviorLog.objects.create(
            vehicle=vehicle,
            driver=driver,
            trip=trip,
            timestamp=ping.timestamp or timezone.now(),
            event_type='overspeeding',
            severity=severity,
            recorded_speed_kmh=Decimal(str(round(speed, 1))),
            speed_limit_kmh=Decimal(str(zone.speed_limit_kmh)),
            latitude=ping.latitude,
            longitude=ping.longitude,
            location_address=zone.name,
            penalty_points=penalty,
            notes=f"Zone Overspeed: Speed {speed:.1f} km/h exceeded zone limit {zone.speed_limit_kmh} km/h inside '{zone.name}' (+{diff:.1f} km/h)."
        )

        incident = None
        whatsapp_msg = None

        if severity == 'critical':
            desc = (
                f"Severe Speed Violation: Vehicle {vehicle.registration_number} recorded at {speed:.1f} km/h "
                f"in zone '{zone.name}' (Limit: {zone.speed_limit_kmh} km/h). Excessive delta: +{diff:.1f} km/h."
            )
            incident = EmergencyIncidentAlert.objects.create(
                incident_type='overspeed_violation',
                severity='high',
                vehicle=vehicle,
                driver=driver or vehicle.default_driver or Driver.objects.first(),
                trip=trip,
                reported_at=timezone.now(),
                latitude=ping.latitude,
                longitude=ping.longitude,
                location_address=f"{zone.name} (Speed Restricted)",
                description=desc,
                status='reported'
            )
            whatsapp_msg = cls._broadcast_whatsapp_alert(
                incident=incident,
                zone_name=zone.name,
                alert_headline=f"ZONE OVERSPEED (+{int(diff)} KM/H)"
            )

        return {
            "type": "zone_overspeed",
            "zone": zone.name,
            "status": "logged",
            "speed": speed,
            "limit": zone.speed_limit_kmh,
            "severity": severity,
            "behavior_log_id": behavior_log.id,
            "incident": incident,
            "whatsapp": whatsapp_msg
        }

    @classmethod
    def _evaluate_route_corridor(
        cls,
        vehicle: Vehicle,
        driver: Optional[Driver],
        trip: Trip,
        ping: VehicleTelematicsPing,
        lat: float,
        lng: float,
        speed: float
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates whether vehicle has deviated off the designated route corridor.
        Corridor buffer tolerance: 2500 meters (2.5 km).
        """
        pickup_str = (trip.pickup_location or '').lower()
        dest_str = (trip.destination or '').lower()

        orig_coords = HQ_DEPOT_COORDS
        for k, coords in KNOWN_DESTINATIONS.items():
            if k in pickup_str:
                orig_coords = coords
                break

        dest_coords = KNOWN_DESTINATIONS.get('ooty', (11.4102, 76.6950))
        for k, coords in KNOWN_DESTINATIONS.items():
            if k in dest_str:
                dest_coords = coords
                break

        deviation_meters = distance_point_to_segment_meters(
            lat, lng,
            orig_coords[0], orig_coords[1],
            dest_coords[0], dest_coords[1]
        )

        CORRIDOR_BUFFER_METERS = 2500.0

        if deviation_meters > CORRIDOR_BUFFER_METERS:
            dev_km = deviation_meters / 1000.0
            cutoff = timezone.now() - timedelta(minutes=cls.ALERT_COOLDOWN_MINUTES)
            recent_dev = DriverBehaviorLog.objects.filter(
                vehicle=vehicle,
                event_type='geofence_breach',
                notes__icontains='Route Corridor Deviation',
                timestamp__gte=cutoff
            ).first()

            if recent_dev:
                return None

            log = DriverBehaviorLog.objects.create(
                vehicle=vehicle,
                driver=driver,
                trip=trip,
                timestamp=ping.timestamp or timezone.now(),
                event_type='geofence_breach',
                severity='high',
                recorded_speed_kmh=Decimal(str(round(speed, 1))),
                speed_limit_kmh=Decimal('80.0'),
                latitude=ping.latitude,
                longitude=ping.longitude,
                location_address=f"Highway Deviation ({dev_km:.1f} km off corridor)",
                penalty_points=10,
                notes=f"Route Corridor Deviation: Vehicle is {dev_km:.1f} km off assigned route path ({trip.pickup_location} -> {trip.destination})."
            )

            incident = None
            whatsapp_msg = None
            if dev_km > 4.0:
                desc = (
                    f"Route Corridor Breach: Vehicle {vehicle.registration_number} on Trip #{trip.trip_id} "
                    f"has deviated {dev_km:.1f} km off the designated corridor between {trip.pickup_location} and {trip.destination}."
                )
                incident = EmergencyIncidentAlert.objects.create(
                    incident_type='corridor_deviation',
                    severity='high',
                    vehicle=vehicle,
                    driver=driver or vehicle.default_driver or Driver.objects.first(),
                    trip=trip,
                    reported_at=timezone.now(),
                    latitude=ping.latitude,
                    longitude=ping.longitude,
                    location_address=f"{dev_km:.1f} km off-route corridor",
                    description=desc,
                    status='reported'
                )
                whatsapp_msg = cls._broadcast_whatsapp_alert(
                    incident=incident,
                    zone_name=f"{trip.destination} Route Corridor",
                    alert_headline=f"ROUTE DEVIATION ({dev_km:.1f} KM OFF-ROUTE)"
                )

            return {
                "type": "corridor_deviation",
                "deviation_km": round(dev_km, 1),
                "behavior_log_id": log.id,
                "incident": incident,
                "whatsapp": whatsapp_msg
            }

        return None

    @classmethod
    def _evaluate_night_stoppage(
        cls,
        vehicle: Vehicle,
        driver: Optional[Driver],
        trip: Trip,
        ping: VehicleTelematicsPing,
        speed: float,
        timestamp
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates unauthorized stationary idle during night hours (22:00 to 05:00).
        """
        hour = timestamp.hour
        is_night = (hour >= 22 or hour < 5)

        if is_night and speed < 2.0:
            dist_to_hq = haversine_distance_meters(
                float(ping.latitude), float(ping.longitude),
                HQ_DEPOT_COORDS[0], HQ_DEPOT_COORDS[1]
            )
            if dist_to_hq > 3000.0:  # > 3 km away from safe HQ depot
                cutoff = timezone.now() - timedelta(minutes=cls.ALERT_COOLDOWN_MINUTES)
                recent_idle = DriverBehaviorLog.objects.filter(
                    vehicle=vehicle,
                    event_type='excessive_idling',
                    notes__icontains='Night Transit Stoppage',
                    timestamp__gte=cutoff
                ).first()

                if recent_idle:
                    return None

                log = DriverBehaviorLog.objects.create(
                    vehicle=vehicle,
                    driver=driver,
                    trip=trip,
                    timestamp=timestamp,
                    event_type='excessive_idling',
                    severity='medium',
                    recorded_speed_kmh=Decimal('0.0'),
                    speed_limit_kmh=Decimal('0.0'),
                    latitude=ping.latitude,
                    longitude=ping.longitude,
                    location_address="Highway Night Stoppage",
                    penalty_points=5,
                    notes=f"Night Transit Stoppage: Vehicle parked or idling during active night tour transit ({timestamp.strftime('%H:%M')}). Safety check suggested."
                )
                return {
                    "type": "night_stoppage",
                    "behavior_log_id": log.id,
                    "timestamp": timestamp.strftime('%H:%M:%S')
                }

        return None

    @classmethod
    def _broadcast_whatsapp_alert(
        cls,
        incident: EmergencyIncidentAlert,
        zone_name: str,
        alert_headline: str
    ) -> Optional[WhatsAppBotMessage]:
        """
        Creates an outbound WhatsAppBotMessage alert dispatched to the Operations Duty Officer.
        """
        duty_phone = "+919842100001"  # Sivagayathiri 24/7 Operations Control Room
        driver_name = incident.driver.name if incident.driver else "Unassigned"
        driver_phone = incident.driver.phone if incident.driver else "N/A"
        lat = float(incident.latitude) if incident.latitude else 11.0168
        lng = float(incident.longitude) if incident.longitude else 76.9558
        maps_link = f"https://www.google.com/maps?q={lat},{lng}"

        body = (
            f"🚨 *SIVAGAYATHIRI TRAVELS - SAFETY WATCHDOG*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *{alert_headline}*\n"
            f"📍 *Zone/Location:* {zone_name}\n"
            f"🚗 *Vehicle:* {incident.vehicle.registration_number} ({incident.vehicle.model or 'Fleet'})\n"
            f"👤 *Driver:* {driver_name} (📞 {driver_phone})\n"
            f"🆔 *Incident ID:* {incident.incident_id}\n"
            f"🗺️ *Live GPS:* {maps_link}\n"
            f"📝 *Details:* {incident.description}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Control Room Duty Officer: Open Mission Control to dispatch standby unit or acknowledge."
        )

        try:
            msg = WhatsAppBotMessage.objects.create(
                sender_phone="+919842199999",
                recipient_phone=duty_phone,
                message_direction='outbound',
                intent='geofence_breach_alert',
                message_body=body,
                status='delivered',
                trip=incident.trip,
                driver=incident.driver,
                message_id=f"wamid_gf_{incident.incident_id.lower()}",
                raw_payload={
                    "incident_id": incident.incident_id,
                    "alert_headline": alert_headline,
                    "zone_name": zone_name,
                    "vehicle": incident.vehicle.registration_number,
                    "lat": lat,
                    "lng": lng,
                }
            )
            logger.info("Dispatched geofence WhatsApp alarm for incident %s", incident.incident_id)
            return msg
        except Exception as e:
            logger.exception("Failed to dispatch WhatsApp geofence alert: %s", e)
            return None

    @classmethod
    def acknowledge_breach_alert(
        cls,
        incident_id: str,
        user=None,
        resolution_notes: str = ""
    ) -> Dict[str, Any]:
        """
        Acknowledges an active EmergencyIncidentAlert by a dispatcher.
        """
        incident = EmergencyIncidentAlert.objects.filter(incident_id=incident_id).first()
        if not incident:
            return {"status": "error", "message": f"Incident {incident_id} not found"}

        with transaction.atomic():
            incident.status = 'acknowledged'
            user_name = user.get_full_name() or user.username if user and hasattr(user, 'username') else 'Dispatcher'
            note_entry = f"Acknowledged by {user_name} at {timezone.now().strftime('%Y-%m-%d %H:%M')}. {resolution_notes}".strip()
            incident.resolution_notes = f"{incident.resolution_notes}\n{note_entry}".strip()
            incident.save(update_fields=['status', 'resolution_notes'])

        return {
            "status": "success",
            "incident_id": incident.incident_id,
            "new_status": incident.status,
            "notes": incident.resolution_notes
        }
