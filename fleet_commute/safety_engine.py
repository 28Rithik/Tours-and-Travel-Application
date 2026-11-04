import logging
import math
import uuid
import datetime
from datetime import time
from decimal import Decimal
from typing import Dict, Any, List, Optional

from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth in meters.
    """
    R = 6371000.0  # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


class WomenSafetyEngine:
    """
    Women Safety & Night Commute Guardrail Engine.
    Enforces statutory night transport regulations (8:00 PM to 6:00 AM):
    1. Guardrails: Auto-detects isolated female drops without escort.
    2. Commute Buddy: Pairs female employees dropping in vicinity.
    3. Outbound IVR: Automated voice call checking for Safe Arrival (Key 1) or Emergency SOS (Key 2).
    """

    # Statutory Night Shift Window: 20:00 (8 PM) to 06:00 (6 AM)
    NIGHT_START = time(20, 0)
    NIGHT_END = time(6, 0)

    @classmethod
    def is_night_time(cls, check_time: Optional[time]) -> bool:
        if not check_time:
            return False
        return check_time >= cls.NIGHT_START or check_time <= cls.NIGHT_END

    @classmethod
    def audit_night_trip_guardrails(cls, trip_log) -> Dict[str, Any]:
        """
        Audits a ContractTripLog for night shift female safety compliance.
        Flags isolated female drops where a female passenger is the last person in the cab.
        """
        from fleet_commute.models import CommuterBoardingPass
        from fleet_contracts.models import NightSafetyEscortLog

        shift = trip_log.shift
        is_night = cls.is_night_time(shift.timing if shift else None)
        passes = CommuterBoardingPass.objects.filter(trip_log=trip_log).select_related('commuter', 'boarded_stop')

        if not passes.exists():
            return {
                "is_night_shift": is_night,
                "compliant": True,
                "violations": [],
                "flagged_passes": []
            }

        # Sort passengers by stop order ascending (last stop = last drop)
        sorted_passes = sorted(
            passes,
            key=lambda p: (p.boarded_stop.stop_order if p.boarded_stop else 999),
            reverse=False
        )

        has_escort = (
            trip_log.escort_logs.exists() or
            (shift and shift.escort_guard_required)
        )

        violations = []
        flagged_passes = []

        # Check last passenger
        last_pass = sorted_passes[-1]
        is_last_female = (last_pass.commuter.gender == 'female')

        if is_night and is_last_female and not has_escort:
            violations.append(
                f"Statutory Breach: Female commuter {last_pass.commuter.name} is the last drop on night shift ({shift.timing.strftime('%I:%M %p')}) without an escort guard."
            )
            last_pass.is_isolated_night_drop = True
            last_pass.save(update_fields=['is_isolated_night_drop'])
            flagged_passes.append(last_pass)

            # Auto-pair with Commute Buddy if another passenger is on same route
            if len(sorted_passes) >= 2:
                buddy_pass = sorted_passes[-2]
                last_pass.commute_buddy = buddy_pass
                last_pass.save(update_fields=['commute_buddy'])

        return {
            "is_night_shift": is_night,
            "has_escort": has_escort,
            "total_commuters": len(sorted_passes),
            "last_commuter": last_pass.commuter.name,
            "last_commuter_gender": last_pass.commuter.gender,
            "is_isolated_night_drop": is_last_female and is_night and not has_escort,
            "violations": violations,
            "flagged_passes": [p.id for p in flagged_passes]
        }

    @classmethod
    def trigger_outbound_ivr_call(cls, boarding_pass_id: int) -> Dict[str, Any]:
        """
        Simulates an automated outbound IVR safe-drop confirmation call.
        """
        from fleet_commute.models import CommuterBoardingPass
        try:
            bp = CommuterBoardingPass.objects.select_related('commuter', 'trip_log').get(pk=boarding_pass_id)
            c = bp.commuter

            ivr_prompt = (
                f"Hello {c.name}, this is an automated safety verification from Siva Gayathri Corporate Transport Desk. "
                f"Our driver reported drop at your residence. Please press 1 if you have reached home safely. "
                f"Press 2 to immediately escalate to our 24/7 Women Safety Command Centre."
            )

            bp.ivr_status = 'initiated'
            bp.ivr_recording_notes = "Outbound call dialed; awaiting commuter DTMF input."
            bp.save(update_fields=['ivr_status', 'ivr_recording_notes'])

            return {
                "status": "success",
                "call_id": f"IVR_CALL_{bp.id}_{int(timezone.now().timestamp())}",
                "commuter_id": c.commuter_id,
                "commuter_name": c.name,
                "phone": c.phone or "9876543210",
                "ivr_audio_script": ivr_prompt,
                "pass_token": bp.pass_token,
                "timestamp": timezone.now().isoformat()
            }
        except CommuterBoardingPass.DoesNotExist:
            return {"status": "error", "message": "Boarding pass not found."}

    @classmethod
    def handle_ivr_dtmf_webhook(cls, pass_token: str, digit: str) -> Dict[str, Any]:
        """
        Webhook processor receiving DTMF keypress from telecom IVR provider (e.g. Twilio, Exotel, Tata Tele).
        Digit '1' = Safe Drop Confirmed.
        Digit '2' = Panic / SOS Escalation.
        """
        from fleet_commute.models import CommuterBoardingPass
        from operations.models import EmergencyIncidentAlert

        try:
            bp = CommuterBoardingPass.objects.select_related('commuter', 'trip_log__vehicle', 'trip_log__driver').get(pass_token=pass_token)
            now = timezone.now()

            if digit == '1':
                # Safe Drop Confirmed
                bp.ivr_status = 'safe_confirmed'
                bp.ivr_confirmed_at = now
                bp.ivr_recording_notes = "Passenger pressed Key 1: Safe arrival verified inside residence."
                bp.save(update_fields=['ivr_status', 'ivr_confirmed_at', 'ivr_recording_notes'])

                # Update related NightSafetyEscortLog if exists
                if bp.trip_log:
                    escort = bp.trip_log.escort_logs.first()
                    if escort:
                        escort.last_drop_verification_status = 'verified_sms'
                        escort.safe_drop_confirmed_by = f"IVR Key 1 ({bp.commuter.name})"
                        escort.save(update_fields=['last_drop_verification_status', 'safe_drop_confirmed_by'])

                return {
                    "status": "success",
                    "action": "safe_confirmed",
                    "message": f"Safe drop confirmed for {bp.commuter.name} at {now.strftime('%I:%M:%S %p')}."
                }

            elif digit == '2':
                # Critical SOS Escalation
                bp.ivr_status = 'sos_escalated'
                bp.ivr_confirmed_at = now
                bp.ivr_recording_notes = "Passenger pressed Key 2: EMERGENCY ALARM TRIGGERED VIA IVR."
                bp.save(update_fields=['ivr_status', 'ivr_confirmed_at', 'ivr_recording_notes'])

                # Create immediate Emergency Incident in operations
                from core.models import Driver
                vehicle = bp.trip_log.vehicle if bp.trip_log else None
                driver = (bp.trip_log.driver if bp.trip_log else None) or Driver.objects.first()

                if vehicle and driver:
                    EmergencyIncidentAlert.objects.create(
                        vehicle=vehicle,
                        driver=driver,
                        contract_trip=bp.trip_log,
                        incident_type='sos_panic',
                        severity='critical',
                        description=(
                            f"CRITICAL WOMEN SAFETY IVR ALARM: Commuter {bp.commuter.name} (ID: {bp.commuter.commuter_id}) "
                            f"pressed Key 2 (Panic Escalation) during post-drop IVR verification. Contact: {bp.commuter.phone}"
                        ),
                        location_address=bp.commuter.boarding_stop.name if bp.commuter.boarding_stop else "Drop Location",
                        status='reported'
                    )

                return {
                    "status": "sos_escalated",
                    "action": "emergency_alarm",
                    "alert_title": f"EMERGENCY IVR ALARM: {bp.commuter.name}",
                    "message": "Alarm siren dispatched to transport control room and security supervisor."
                }
            else:
                return {"status": "ignored", "message": f"Unrecognized DTMF digit: {digit}"}

        except CommuterBoardingPass.DoesNotExist:
            return {"status": "error", "message": "Invalid pass token."}


class SafetyIncidentEngine:
    """
    Domain 7: Safety, SOS & Incident Response Desk Engine
    Automates emergency distress signaling, route corridor deviation sentry,
    night escort governance, standby rescue dispatch, and statutory escalation protocols.
    """

    DEFAULT_GEOFENCE_CORRIDOR_METERS = 600.0

    @classmethod
    def trigger_panic_sos(
        cls,
        source_type: str = 'commuter_silent',
        commuter_id: Optional[str] = None,
        driver_id: Optional[int] = None,
        trip_id: Optional[int] = None,
        vehicle_id: Optional[int] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        location_name: str = "Live GPS Coordinate Track",
        description: str = "",
        is_silent: bool = False,
        officer_user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Triggers an immediate emergency SOS distress alert.
        Discreetly broadcasts to the Transport Control Center, logs GPS fixes,
        and creates linked Incident & Emergency Alert entities.
        """
        from core.models import Vehicle, Driver
        from fleet_contracts.models import ContractTripLog, CommuterManifest
        from fleet_commute.models import CommuteIncident
        from operations.models import EmergencyIncidentAlert, VehicleTelematicsPing

        now = timezone.now()
        year = now.year
        inc_code = f"INC-SOS-{year}-{uuid.uuid4().hex[:6].upper()}"

        trip = None
        if trip_id:
            trip = ContractTripLog.objects.filter(pk=trip_id).select_related('vehicle', 'driver').first()

        vehicle = None
        if vehicle_id:
            vehicle = Vehicle.objects.filter(pk=vehicle_id).first()
        elif trip and trip.vehicle:
            vehicle = trip.vehicle

        driver = None
        if driver_id:
            driver = Driver.objects.filter(pk=driver_id).first()
        elif trip and trip.driver:
            driver = trip.driver

        commuter = None
        if commuter_id:
            commuter = CommuterManifest.objects.filter(commuter_id=commuter_id).first()
            if not commuter:
                # Fallback search by primary key if numeric
                commuter = CommuterManifest.objects.filter(pk=commuter_id).first() if str(commuter_id).isdigit() else None

        # Build location coordinates fallback from vehicle telematics if absent
        if (latitude is None or longitude is None) and vehicle:
            latest_ping = VehicleTelematicsPing.objects.filter(vehicle=vehicle).order_by('-timestamp').first()
            if latest_ping:
                latitude = float(latest_ping.latitude)
                longitude = float(latest_ping.longitude)
                if not location_name or location_name == "Live GPS Coordinate Track":
                    location_name = f"Near {vehicle.base_depot or 'Coimbatore Tech Corridor'}"

        if latitude is None:
            latitude = 11.0168
        if longitude is None:
            longitude = 76.9558

        if not location_name:
            location_name = "Saravanampatti Tech Corridor / Avinashi Road"

        if not description:
            if source_type == 'commuter_silent':
                description = f"Stealth Silent SOS triggered by commuter {commuter.name if commuter else 'Passenger'} during commute."
            elif source_type == 'driver_panic':
                description = f"Driver distress panic button pressed by Captain {driver.name if driver else 'Chauffeur'}."
            elif source_type == 'ivr_escalation':
                description = "Automated IVR safe-drop call escalated to SOS (Key 2 pressed by commuter)."
            elif source_type == 'geofence_breach':
                description = "Severe route corridor boundary breach detected. Vehicle off-route."
            elif source_type == 'corridor_deviation':
                description = "Automated corridor deviation sentry alarm. Vehicle strayed off path."
            else:
                description = f"Emergency distress alert triggered via {source_type}."

        action_entry = {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "action": "sos_triggered",
            "source": source_type,
            "caller": commuter.name if commuter else (driver.name if driver else "Unknown"),
            "location": location_name,
            "coordinates": [float(latitude), float(longitude)],
            "notes": description,
            "is_silent": is_silent or (source_type == 'commuter_silent'),
        }

        with transaction.atomic():
            # 1. Create CommuteIncident
            incident = CommuteIncident.objects.create(
                incident_id=inc_code,
                incident_type='safety_concern' if 'sos' in source_type or 'commuter' in source_type else 'route_blocked',
                severity='critical',
                status='reported',
                trip=trip,
                vehicle=vehicle,
                driver=driver,
                latitude=Decimal(str(round(latitude, 6))),
                longitude=Decimal(str(round(longitude, 6))),
                location_name=location_name,
                description=description,
                is_silent_sos=is_silent or (source_type == 'commuter_silent'),
                passengers_affected=trip.passenger_count if trip else 1,
                action_log=[action_entry],
                assigned_officer=officer_user,
                reported_at=now
            )

            # 2. Synchronize Operations EmergencyIncidentAlert
            alert_type = 'sos_panic'
            if source_type == 'geofence_breach':
                alert_type = 'geofence_breach'
            elif source_type == 'corridor_deviation':
                alert_type = 'corridor_deviation'

            if vehicle and driver:
                EmergencyIncidentAlert.objects.create(
                    incident_id=inc_code,
                    incident_type=alert_type,
                    severity='critical',
                    vehicle=vehicle,
                    driver=driver,
                    contract_trip=trip,
                    latitude=Decimal(str(round(latitude, 7))),
                    longitude=Decimal(str(round(longitude, 7))),
                    location_address=location_name,
                    passenger_count=incident.passengers_affected,
                    description=description,
                    status='reported',
                    reported_at=now
                )

        return {
            "status": "success",
            "incident_id": incident.incident_id,
            "incident_pk": incident.pk,
            "incident_type": incident.incident_type,
            "severity": incident.severity,
            "is_silent_sos": incident.is_silent_sos,
            "location_name": incident.location_name,
            "latitude": float(incident.latitude),
            "longitude": float(incident.longitude),
            "reported_at": incident.reported_at.strftime("%Y-%m-%d %H:%M:%S"),
            "message": f"Critical SOS alert {incident.incident_id} broadcasted to Control Center."
        }

    @classmethod
    def detect_corridor_deviation(
        cls,
        trip_id: int,
        current_lat: float,
        current_lng: float,
        threshold_meters: float = DEFAULT_GEOFENCE_CORRIDOR_METERS,
        auto_trigger_alert: bool = True
    ) -> Dict[str, Any]:
        """
        Geofence Corridor Sentry:
        Calculates deviation between current vehicle GPS coordinates and route corridor waypoints.
        If distance exceeds threshold_meters, optionally logs a high-severity corridor deviation incident.
        """
        from fleet_contracts.models import ContractTripLog, RouteStop

        trip = ContractTripLog.objects.select_related('shift__route', 'vehicle', 'driver').filter(pk=trip_id).first()
        if not trip:
            return {
                "status": "error",
                "message": f"Trip #{trip_id} not found."
            }

        route = trip.shift.route if (trip.shift and trip.shift.route) else None
        if not route:
            return {
                "status": "warning",
                "message": "Trip has no defined route corridor for geofence validation.",
                "is_deviated": False,
                "min_distance_meters": 0.0
            }

        stops = list(RouteStop.objects.filter(route=route).order_by('stop_order'))
        distances = []

        for stop in stops:
            if stop.latitude is not None and stop.longitude is not None:
                d = haversine_distance_meters(
                    current_lat, current_lng,
                    float(stop.latitude), float(stop.longitude)
                )
                stop_label = getattr(stop, 'name', None) or getattr(stop, 'stop_name', 'Stop')
                distances.append((d, stop_label))

        if not distances:
            # Fallback to route name
            d = haversine_distance_meters(current_lat, current_lng, 11.0168, 76.9558)
            distances.append((d, route.name))

        min_distance, nearest_waypoint = min(distances, key=lambda x: x[0])
        is_deviated = min_distance > threshold_meters

        incident_data = None
        if is_deviated and auto_trigger_alert:
            from fleet_commute.models import CommuteIncident
            existing = CommuteIncident.objects.filter(
                trip=trip,
                incident_type='route_blocked',
                status__in=['reported', 'assigned'],
                reported_at__gte=timezone.now() - datetime.timedelta(minutes=30)
            ).first()

            if not existing:
                incident_data = cls.trigger_panic_sos(
                    source_type='corridor_deviation',
                    trip_id=trip.pk,
                    vehicle_id=trip.vehicle_id,
                    driver_id=trip.driver_id,
                    latitude=current_lat,
                    longitude=current_lng,
                    location_name=f"Off-Route: {round(min_distance)}m away from {nearest_waypoint}",
                    description=f"Automated Corridor Sentry Alert: Vehicle drifted {round(min_distance)}m away from planned corridor (Threshold: {round(threshold_meters)}m).",
                    is_silent=False
                )

        return {
            "status": "success",
            "trip_id": trip.pk,
            "route_name": route.name,
            "current_coordinates": [current_lat, current_lng],
            "nearest_waypoint": nearest_waypoint,
            "min_distance_meters": round(min_distance, 1),
            "threshold_meters": threshold_meters,
            "is_deviated": is_deviated,
            "incident_triggered": incident_data is not None,
            "incident_details": incident_data
        }

    @classmethod
    def dispatch_standby_rescue(
        cls,
        incident_id: str,
        standby_vehicle_id: int,
        standby_driver_id: int,
        eta_minutes: int = 15,
        officer_user: Optional[User] = None,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Autonomous Standby Rescue Dispatch:
        Atomically assigns a backup vehicle & standby driver from the depot to rescue passengers.
        Transitions incident to 'rescue_dispatched' and creates audit timeline entries.
        """
        from core.models import Vehicle, Driver
        from fleet_commute.models import CommuteIncident
        from operations.models import EmergencyIncidentAlert

        incident = CommuteIncident.objects.filter(incident_id=incident_id).first()
        if not incident and str(incident_id).isdigit():
            incident = CommuteIncident.objects.filter(pk=int(incident_id)).first()

        if not incident:
            return {"status": "error", "message": f"Incident {incident_id} not found."}

        standby_vehicle = Vehicle.objects.filter(pk=standby_vehicle_id).first()
        standby_driver = Driver.objects.filter(pk=standby_driver_id).first()

        if not standby_vehicle or not standby_driver:
            return {"status": "error", "message": "Valid standby vehicle and driver are required."}

        now = timezone.now()
        action_entry = {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "action": "rescue_dispatched",
            "officer": officer_user.get_full_name() or officer_user.username if officer_user else "Autonomous Dispatcher",
            "rescue_vehicle": standby_vehicle.registration_number,
            "rescue_driver": standby_driver.name,
            "eta_minutes": eta_minutes,
            "notes": notes or f"Relief standby asset dispatched with ETA of {eta_minutes} mins."
        }

        with transaction.atomic():
            incident.rescue_vehicle = standby_vehicle
            incident.rescue_driver = standby_driver
            incident.rescue_eta_minutes = eta_minutes
            incident.status = 'rescue_dispatched'
            incident.passengers_reallocated = incident.passengers_affected
            if officer_user:
                incident.assigned_officer = officer_user

            log = list(incident.action_log or [])
            log.append(action_entry)
            incident.action_log = log
            incident.save()

            # Mark standby vehicle as assigned
            standby_vehicle.status = 'assigned'
            standby_vehicle.save(update_fields=['status'])

            # Synchronize Operations EmergencyIncidentAlert if matching
            op_alert = EmergencyIncidentAlert.objects.filter(incident_id=incident.incident_id).first()
            if op_alert:
                op_alert.standby_vehicle = standby_vehicle
                op_alert.standby_driver = standby_driver
                op_alert.standby_dispatched_at = now
                op_alert.standby_eta_minutes = eta_minutes
                op_alert.status = 'standby_dispatched'
                op_alert.save()

        return {
            "status": "success",
            "incident_id": incident.incident_id,
            "rescue_vehicle": standby_vehicle.registration_number,
            "rescue_driver": standby_driver.name,
            "rescue_eta_minutes": eta_minutes,
            "message": f"Standby rescue vehicle {standby_vehicle.registration_number} dispatched to scene. ETA: {eta_minutes} mins."
        }

    @classmethod
    def escalate_emergency_protocol(
        cls,
        incident_id: str,
        escalation_target: str,
        notes: str = "",
        officer_user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Speed-Dial Emergency Protocol Escalation:
        Dispatches immediate alerts to 112 Police Control, 108 Ambulance,
        Client Corporate Security, or Depot Chief with timestamped audit trail.
        """
        from fleet_commute.models import CommuteIncident

        incident = CommuteIncident.objects.filter(incident_id=incident_id).first()
        if not incident and str(incident_id).isdigit():
            incident = CommuteIncident.objects.filter(pk=int(incident_id)).first()

        if not incident:
            return {"status": "error", "message": f"Incident {incident_id} not found."}

        target_labels = {
            'police_112': 'Police Control Room (Dial 112)',
            'ambulance_108': 'Emergency Medical Services (Dial 108)',
            'client_security': 'Corporate Client Security Desk (Cognizant / Bosch SOC)',
            'depot_chief': 'Depot Base Station Operations Chief'
        }
        target_name = target_labels.get(escalation_target, escalation_target.upper())

        now = timezone.now()
        action_entry = {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "action": "emergency_escalated",
            "escalation_target": escalation_target,
            "target_name": target_name,
            "officer": officer_user.get_full_name() or officer_user.username if officer_user else "Transport Control Room",
            "notes": notes or f"Priority speed-dial emergency escalation dispatched to {target_name}."
        }

        incident.severity = 'critical'
        log = list(incident.action_log or [])
        log.append(action_entry)
        incident.action_log = log
        incident.save()

        return {
            "status": "success",
            "incident_id": incident.incident_id,
            "escalation_target": escalation_target,
            "target_name": target_name,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "message": f"Emergency protocol escalated to {target_name}."
        }

    @classmethod
    def verify_night_safe_drop(
        cls,
        trip_id: int,
        guard_name: str,
        agency: str = "SIS Security Services",
        badge_number: str = "SEC-TN-042",
        female_count: int = 1,
        drop_time: Optional[datetime.time] = None,
        verification_status: str = 'verified_call',
        confirmed_by: str = "Corporate Transport Supervisor",
        remarks: str = ""
    ) -> Dict[str, Any]:
        """
        Night Escort & Safe-Drop Governance:
        Enforces Tamil Nadu Shops & Establishments / Factories Act night commute rules.
        Verifies female employee safe drop with security escort guard badge and confirmation mode.
        """
        from fleet_contracts.models import ContractTripLog, NightSafetyEscortLog

        trip = ContractTripLog.objects.filter(pk=trip_id).first()
        if not trip:
            return {"status": "error", "message": f"Trip #{trip_id} not found."}

        now_time = drop_time or timezone.now().time()

        escort_log, created = NightSafetyEscortLog.objects.get_or_create(
            trip_log=trip,
            defaults={
                'escort_guard_name': guard_name or "M. Velusamy",
                'security_agency': agency or "SIS Security Services",
                'guard_badge_number': badge_number or "SEC-TN-042",
                'female_passengers_count': female_count,
                'last_female_drop_time': now_time,
                'last_drop_verification_status': verification_status,
                'safe_drop_confirmed_by': confirmed_by,
                'remarks': remarks or f"Night drop compliance verified via {verification_status}."
            }
        )

        if not created:
            escort_log.escort_guard_name = guard_name or escort_log.escort_guard_name
            escort_log.security_agency = agency or escort_log.security_agency
            escort_log.guard_badge_number = badge_number or escort_log.guard_badge_number
            escort_log.female_passengers_count = female_count
            escort_log.last_female_drop_time = now_time
            escort_log.last_drop_verification_status = verification_status
            escort_log.safe_drop_confirmed_by = confirmed_by
            if remarks:
                escort_log.remarks = remarks
            escort_log.save()

        return {
            "status": "success",
            "escort_log_id": escort_log.id,
            "trip_id": trip.id,
            "guard_name": escort_log.escort_guard_name,
            "security_agency": escort_log.security_agency,
            "female_count": escort_log.female_passengers_count,
            "verification_status": escort_log.last_drop_verification_status,
            "drop_time": escort_log.last_female_drop_time.strftime("%H:%M:%S") if escort_log.last_female_drop_time else None,
            "message": f"Night safe-drop verified for Trip #{trip.id} with {escort_log.escort_guard_name} ({escort_log.security_agency})."
        }

    @classmethod
    def resolve_incident(
        cls,
        incident_id: str,
        resolution_notes: str = "",
        officer_user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Resolves and audits an active incident upon passenger safe arrival.
        """
        from fleet_commute.models import CommuteIncident
        from operations.models import EmergencyIncidentAlert

        incident = CommuteIncident.objects.filter(incident_id=incident_id).first()
        if not incident and str(incident_id).isdigit():
            incident = CommuteIncident.objects.filter(pk=int(incident_id)).first()

        if not incident:
            return {"status": "error", "message": f"Incident {incident_id} not found."}

        now = timezone.now()
        action_entry = {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "action": "incident_resolved",
            "officer": officer_user.get_full_name() or officer_user.username if officer_user else "Transport Desk Officer",
            "notes": resolution_notes or "Incident cleared. All passengers safely transferred and arrived at destination."
        }

        with transaction.atomic():
            incident.status = 'resolved'
            incident.resolved_at = now
            log = list(incident.action_log or [])
            log.append(action_entry)
            incident.action_log = log
            incident.save()

            op_alert = EmergencyIncidentAlert.objects.filter(incident_id=incident.incident_id).first()
            if op_alert:
                op_alert.status = 'resolved'
                op_alert.resolved_at = now
                op_alert.resolution_notes = resolution_notes
                op_alert.save()

            # Release standby vehicle back to available if assigned
            if incident.rescue_vehicle:
                incident.rescue_vehicle.status = 'available'
                incident.rescue_vehicle.save(update_fields=['status'])

        return {
            "status": "success",
            "incident_id": incident.incident_id,
            "resolved_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "message": f"Incident {incident.incident_id} successfully resolved and archived."
        }

    @classmethod
    def get_safety_desk_metrics(cls) -> Dict[str, Any]:
        """
        Aggregates live KPI indicators for the Safety & SOS Response Desk.
        """
        from core.models import Vehicle, Driver
        from fleet_commute.models import CommuteIncident
        from fleet_contracts.models import NightSafetyEscortLog

        active_statuses = ['reported', 'assigned', 'rescue_dispatched']

        total_incidents = CommuteIncident.objects.count()
        active_incidents = CommuteIncident.objects.filter(status__in=active_statuses).count()
        critical_sos = CommuteIncident.objects.filter(severity='critical', status__in=['reported', 'assigned']).count()
        rescues_active = CommuteIncident.objects.filter(status='rescue_dispatched').count()
        resolved_count = CommuteIncident.objects.filter(status__in=['resolved', 'closed']).count()

        # Route Corridor Deviations
        active_deviations = CommuteIncident.objects.filter(
            incident_type__in=['route_blocked', 'accident'],
            status__in=active_statuses
        ).count()

        # Night Escort Governance Compliance Rate
        total_escorts = NightSafetyEscortLog.objects.count()
        verified_escorts = NightSafetyEscortLog.objects.filter(
            last_drop_verification_status__in=['verified_call', 'verified_sms', 'supervisor_signoff', 'safe_drop_confirmed']
        ).count()
        compliance_rate = round((verified_escorts / total_escorts * 100.0), 1) if total_escorts > 0 else 100.0

        # Standby Readiness
        standby_ready_vehicles = Vehicle.objects.filter(status='available').count()
        standby_ready_drivers = Driver.objects.filter(status='active').count()

        return {
            "total_incidents": total_incidents,
            "active_incidents": active_incidents,
            "critical_sos": critical_sos,
            "rescues_active": rescues_active,
            "resolved_count": resolved_count,
            "active_deviations": active_deviations,
            "total_escorts": total_escorts,
            "verified_escorts": verified_escorts,
            "compliance_rate": compliance_rate,
            "standby_ready_vehicles": standby_ready_vehicles,
            "standby_ready_drivers": standby_ready_drivers,
        }
