from decimal import Decimal
import math
from django.db.models import Q
from django.utils import timezone

from core.models import RateCard, Vehicle, Driver
from .models import (
    Trip,
    EmergencyIncidentAlert,
    VehicleTelematicsPing,
    DriverBehaviorLog,
    GeofenceZone,
)


def get_active_rate_card(party, vehicle_type, on_date, vehicle=None):
    if not on_date:
        on_date = timezone.now().date()
    return (
        RateCard.objects.filter(party=party, vehicle_type=vehicle_type, effective_from__lte=on_date)
        .filter(Q(effective_to__isnull=True) | Q(effective_to__gte=on_date))
        .filter(Q(vehicle=vehicle) | Q(vehicle__isnull=True) if vehicle else Q(vehicle__isnull=True))
        .order_by('-vehicle_id', '-effective_from')
        .first()
    )


def calculate_haversine_distance_meters(lat1, lon1, lat2, lon2):
    """
    Computes great-circle distance between two GPS coordinates in meters.
    """
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    delta_phi = math.radians(float(lat2) - float(lat1))
    delta_lambda = math.radians(float(lon2) - float(lon1))

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def ingest_telematics_ping(data):
    """
    Ingests a raw telematics ping payload from GPS trackers (Concox, Teltonika, LocoNav)
    or mobile driver application.
    Updates vehicle live state, records ping history, and evaluates driver behavior.
    """
    imei = data.get('imei')
    vehicle_id = data.get('vehicle_id')
    registration_number = data.get('registration_number')

    vehicle = None
    if imei:
        vehicle = Vehicle.objects.filter(gps_imei=imei).first()
    if not vehicle and vehicle_id:
        vehicle = Vehicle.objects.filter(pk=vehicle_id).first()
    if not vehicle and registration_number:
        vehicle = Vehicle.objects.filter(registration_number__iexact=registration_number.strip()).first()

    if not vehicle:
        return {"status": "error", "message": "Vehicle not found for provided IMEI/ID/RegNumber."}

    lat = Decimal(str(data.get('latitude', 0.0)))
    lng = Decimal(str(data.get('longitude', 0.0)))
    speed = Decimal(str(data.get('speed_kmh', 0.0)))
    heading = data.get('heading')
    altitude = data.get('altitude')
    ignition = bool(data.get('ignition_on', True))
    fuel_pct = Decimal(str(data['fuel_level_pct'])) if data.get('fuel_level_pct') is not None else None
    odometer = int(data['odometer_km']) if data.get('odometer_km') is not None else None
    satellite_count = data.get('satellite_count')

    # Find active trip if running
    active_trip = Trip.objects.filter(vehicle=vehicle, status='started').order_by('-start_date').first()
    assigned_driver = active_trip.driver if active_trip and active_trip.driver else vehicle.default_driver

    # 1. Record Telematics Ping
    ping = VehicleTelematicsPing.objects.create(
        vehicle=vehicle,
        trip=active_trip,
        timestamp=timezone.now(),
        latitude=lat,
        longitude=lng,
        speed_kmh=speed,
        heading_degrees=heading,
        altitude_m=altitude,
        ignition_on=ignition,
        fuel_level_pct=fuel_pct,
        odometer_km=odometer,
        satellite_count=satellite_count,
        raw_telemetry=data.get('raw_data', {})
    )

    # 2. Update Vehicle Current State
    vehicle.current_location = f"{lat:.5f}, {lng:.5f}"
    if odometer and odometer > (vehicle.current_km or 0):
        vehicle.current_km = odometer
    vehicle.save(update_fields=['current_location', 'current_km'])

    # 3. Evaluate Driver Behavior & Driving Infractions
    events_triggered = []
    
    # A. Overspeeding (>80 km/h default highway limit)
    SPEED_LIMIT = Decimal("80.0")
    if speed > SPEED_LIMIT:
        severity = 'critical' if speed >= Decimal("100.0") else ('high' if speed >= Decimal("90.0") else 'medium')
        penalty = 15 if severity == 'critical' else (10 if severity == 'high' else 5)
        event = DriverBehaviorLog.objects.create(
            vehicle=vehicle,
            driver=assigned_driver,
            trip=active_trip,
            timestamp=timezone.now(),
            event_type='overspeeding',
            severity=severity,
            recorded_speed_kmh=speed,
            speed_limit_kmh=SPEED_LIMIT,
            latitude=lat,
            longitude=lng,
            location_address=data.get('location_name', ''),
            penalty_points=penalty,
            notes=f"Exceeded speed limit of {SPEED_LIMIT} km/h by {speed - SPEED_LIMIT:.1f} km/h."
        )
        events_triggered.append(f"Overspeeding ({speed} km/h)")

    # B. Geofencing check
    active_geofences = GeofenceZone.objects.filter(is_active=True)
    for zone in active_geofences:
        dist = calculate_haversine_distance_meters(lat, lng, zone.latitude, zone.longitude)
        if dist <= zone.radius_meters:
            # Inside zone: check zone speed limit
            if speed > Decimal(str(zone.speed_limit_kmh)):
                event = DriverBehaviorLog.objects.create(
                    vehicle=vehicle,
                    driver=assigned_driver,
                    trip=active_trip,
                    timestamp=timezone.now(),
                    event_type='overspeeding',
                    severity='high',
                    recorded_speed_kmh=speed,
                    speed_limit_kmh=Decimal(str(zone.speed_limit_kmh)),
                    latitude=lat,
                    longitude=lng,
                    location_address=zone.name,
                    penalty_points=10,
                    notes=f"Exceeded {zone.name} zone speed limit of {zone.speed_limit_kmh} km/h inside {zone.radius_meters}m radius."
                )
                events_triggered.append(f"Zone speed violation inside {zone.name}")

    return {
        "status": "success",
        "ping_id": ping.pk,
        "vehicle": vehicle.registration_number,
        "speed": float(speed),
        "events_triggered": events_triggered,
    }


def dispatch_standby_vehicle(incident_id, standby_vehicle_id, standby_driver_id=None, eta_minutes=30, notes=""):
    """
    1-Click Emergency Replacement Dispatch:
    Swaps the stranded vehicle on the active trip or contract shift with the assigned standby vehicle,
    transfers duty context, and updates the incident lifecycle to 'standby_dispatched'.
    """
    try:
        incident = EmergencyIncidentAlert.objects.get(pk=incident_id)
    except EmergencyIncidentAlert.DoesNotExist:
        return {"status": "error", "message": "Incident not found."}

    try:
        standby_vehicle = Vehicle.objects.get(pk=standby_vehicle_id)
    except Vehicle.DoesNotExist:
        return {"status": "error", "message": "Standby vehicle not found."}

    standby_driver = None
    if standby_driver_id:
        try:
            standby_driver = Driver.objects.get(pk=standby_driver_id)
        except Driver.DoesNotExist:
            pass

    original_vehicle = incident.vehicle
    now = timezone.now()

    # 1. Update Incident Alert
    incident.standby_vehicle = standby_vehicle
    if standby_driver:
        incident.standby_driver = standby_driver
    incident.standby_dispatched_at = now
    incident.standby_eta_minutes = eta_minutes
    incident.status = 'standby_dispatched'
    if notes:
        incident.resolution_notes = f"{incident.resolution_notes}\n[Dispatch Notes]: {notes}".strip()
    incident.save()

    # 2. Swap Vehicle on Operations Trip if linked
    if incident.trip:
        trip = incident.trip
        handover_text = (
            f"\n[EMERGENCY STANDBY DISPATCH {now.strftime('%d-%b-%Y %H:%M')}]: "
            f"Original vehicle {original_vehicle.registration_number} replaced by standby vehicle {standby_vehicle.registration_number} "
            f"due to incident #{incident.incident_id} ({incident.get_incident_type_display()})."
        )
        trip.vehicle = standby_vehicle
        if standby_driver:
            trip.driver = standby_driver
        trip.partner_handover_notes = (trip.partner_handover_notes or '') + handover_text
        trip.save(update_fields=['vehicle', 'driver', 'partner_handover_notes'])

    # 3. Swap Vehicle on Fleet Contract Trip Log if linked
    if incident.contract_trip:
        ctrip = incident.contract_trip
        ctrip.vehicle = standby_vehicle
        if standby_driver:
            ctrip.driver = standby_driver
        ctrip.is_replacement_vehicle = True
        ctrip.replaced_vehicle = original_vehicle
        ctrip.delay_reason = (ctrip.delay_reason or '') + f" Standby replacement for {original_vehicle.registration_number} (Incident #{incident.incident_id})."
        ctrip.save(update_fields=['vehicle', 'driver', 'is_replacement_vehicle', 'replaced_vehicle', 'delay_reason'])

    return {
        "status": "success",
        "message": f"Standby vehicle {standby_vehicle.registration_number} successfully dispatched for incident #{incident.incident_id}.",
        "incident_id": incident.incident_id,
        "standby_vehicle": standby_vehicle.registration_number,
    }

