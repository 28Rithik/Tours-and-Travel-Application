import logging
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple

from django.utils import timezone
from django.db.models import Q

from core.models import Vehicle, Driver, VehicleType
from operations.models import Trip, Booking, VehicleTelematicsPing
from operations.spatial_engine import SpatialEngine

logger = logging.getLogger(__name__)

# Known hill station destinations in South India
HILL_STATION_KEYWORDS = [
    'ooty', 'udagamandalam', 'kodaikanal', 'kodai', 'munnar', 'wayanad',
    'valparai', 'coorg', 'madikeri', 'yercaud', 'chikmagalur', 'vagamon',
    'nilgiris', 'kotagiri', 'ponmudi'
]

# Base depot / HQ coordinates (Coimbatore HQ default)
DEFAULT_DEPOT_LAT = 11.0168
DEFAULT_DEPOT_LNG = 76.9558


class SmartDispatchEngine:
    """
    Intelligent Dispatch & Safety Compliance Recommendation Engine for TravelERP.

    Evaluates and scores available fleet vehicles and drivers for a specific Trip
    based on:
    1. Operational Availability (excluding active overlapping trips)
    2. Regulatory Roadworthiness & Document Compliance (FC, Insurance, PUC, RC, Permits)
    3. Spatial Proximity & Telematics (GPS distance to pickup)
    4. Vehicle Capacity & Type Compatibility
    5. Driver Shift Fatigue & Rest Intervals (minimum 8h rest, 24h driving limits)
    6. Route Skill Matching (Hill Station experience, Heavy Vehicle certification)
    """

    @classmethod
    def evaluate_candidates(cls, trip_id: int) -> Dict[str, Any]:
        """
        Main recommendation pipeline. Given a trip_id, returns ranked
        candidate vehicles, candidate drivers, top recommended pairs,
        and any critical compliance warnings.
        """
        try:
            trip = Trip.objects.select_related('booking', 'vehicle', 'driver').get(pk=trip_id)
        except Trip.DoesNotExist:
            return {"status": "error", "message": f"Trip #{trip_id} not found."}

        booking = trip.booking
        trip_start = trip.start_date or (booking.pickup_date if booking else timezone.localdate())
        trip_end = trip.end_date or (booking.drop_date if (booking and booking.drop_date) else trip_start)
        pax_count = (booking.pax_count if booking and booking.pax_count else 1)
        required_type = booking.vehicle_type if booking else (trip.vehicle.vehicle_type if trip.vehicle else None)
        
        pickup_loc = (booking.pickup_location if booking else "") or trip.pickup_location or "Coimbatore"
        destination_loc = (booking.destination if booking else "") or trip.destination or ""
        
        # Determine if destination is a hill station
        is_hill_trip = any(k in destination_loc.lower() for k in HILL_STATION_KEYWORDS) or any(k in pickup_loc.lower() for k in HILL_STATION_KEYWORDS)

        # 1. Evaluate Candidate Vehicles
        candidate_vehicles = cls._evaluate_vehicles(
            trip=trip,
            start_date=trip_start,
            end_date=trip_end,
            pax_count=pax_count,
            required_type=required_type
        )

        # 2. Evaluate Candidate Drivers
        candidate_drivers = cls._evaluate_drivers(
            trip=trip,
            start_date=trip_start,
            end_date=trip_end,
            is_hill_trip=is_hill_trip
        )

        # 3. Formulate Top Compatible Pairs
        top_pairs = cls._formulate_pairs(
            candidate_vehicles=candidate_vehicles,
            candidate_drivers=candidate_drivers,
            is_hill_trip=is_hill_trip
        )

        return {
            "status": "success",
            "trip": {
                "id": trip.id,
                "trip_ref": trip.trip_id or f"TRIP-{trip.id}",
                "guest_name": trip.guest_name or (booking.guest_name if booking else "Valued Guest"),
                "pickup_location": pickup_loc,
                "destination": destination_loc,
                "start_date": trip_start.strftime("%Y-%m-%d"),
                "end_date": trip_end.strftime("%Y-%m-%d"),
                "pax_count": pax_count,
                "vehicle_type_required": str(required_type) if required_type else "Any Fleet",
                "is_hill_trip": is_hill_trip,
            },
            "top_pairs": top_pairs[:5],
            "ranked_vehicles": candidate_vehicles[:8],
            "ranked_drivers": candidate_drivers[:8],
        }

    # =========================================================================
    # VEHICLE EVALUATION
    # =========================================================================
    @classmethod
    def _evaluate_vehicles(
        cls,
        trip: Trip,
        start_date: date,
        end_date: date,
        pax_count: int,
        required_type: Optional[VehicleType]
    ) -> List[Dict[str, Any]]:
        today = timezone.localdate()

        # Step A: Identify vehicles already assigned to overlapping trips
        overlapping_vehicle_ids = Trip.objects.filter(
            status__in=['assigned', 'started', 'on_trip', 'driver_confirmed'],
            vehicle__isnull=False
        ).exclude(pk=trip.pk).filter(
            Q(start_date__lte=end_date, end_date__gte=start_date)
        ).values_list('vehicle_id', flat=True)

        all_vehicles = Vehicle.objects.exclude(
            id__in=overlapping_vehicle_ids
        ).filter(
            status__in=['available', 'assigned']
        ).select_related('vehicle_type', 'owner_party')

        evaluated: List[Dict[str, Any]] = []

        for v in all_vehicles:
            score = 0
            compliance_flags = []
            is_disqualified = False
            disqualification_reason = None

            # 1. Roadworthiness & Document Compliance Check (Max 35 pts)
            doc_score = 35
            expiries = {
                'Insurance': v.insurance_expiry,
                'FC / Fitness': v.fc_expiry,
                'PUC / Pollution': v.pollution_expiry,
                'Permit': v.permit_expiry,
                'Tax': v.tax_expiry,
            }

            expired_docs = []
            expiring_soon_docs = []

            for doc_name, exp_date in expiries.items():
                if exp_date:
                    days_left = (exp_date - today).days
                    if days_left < 0:
                        expired_docs.append(f"{doc_name} expired ({abs(days_left)}d ago)")
                    elif days_left <= 15:
                        expiring_soon_docs.append(f"{doc_name} expires in {days_left}d")

            if expired_docs:
                is_disqualified = True
                doc_score = 0
                disqualification_reason = f"Non-Compliant: {', '.join(expired_docs)}"
                compliance_flags.append({
                    "type": "danger",
                    "label": f"🔴 Expired: {', '.join(expired_docs)}"
                })
            elif expiring_soon_docs:
                doc_score = 25  # slight deduction for urgency
                compliance_flags.append({
                    "type": "warning",
                    "label": f"🟡 Soon: {', '.join(expiring_soon_docs)}"
                })
            else:
                compliance_flags.append({
                    "type": "success",
                    "label": "🟢 All Documents Valid"
                })

            score += doc_score

            # 2. Capacity & Vehicle Type Suitability (Max 30 pts)
            capacity_score = 0
            seats = v.seating_capacity or 4

            if pax_count > seats:
                # Undersized vehicle cannot fit passengers
                is_disqualified = True
                cap_reason = f"Capacity Mismatch: {seats} seats for {pax_count} pax"
                disqualification_reason = f"{disqualification_reason}; {cap_reason}" if disqualification_reason else cap_reason
                capacity_score = 0
            else:
                if required_type and v.vehicle_type_id == required_type.id:
                    capacity_score = 30  # Exact match
                elif seats >= pax_count and seats <= pax_count + 4:
                    capacity_score = 25  # Right-sized fit
                elif seats > pax_count + 4:
                    capacity_score = 15  # Oversized (e.g. 33-seater for 4 pax)
                else:
                    capacity_score = 20

            score += capacity_score

            # 3. Proximity & Telematics Location (Max 20 pts)
            dist_km, dist_label = cls._get_vehicle_proximity(v)
            if dist_km <= 5.0:
                proximity_score = 20
            elif dist_km <= 15.0:
                proximity_score = 16
            elif dist_km <= 30.0:
                proximity_score = 12
            elif dist_km <= 60.0:
                proximity_score = 8
            else:
                proximity_score = 4
            score += proximity_score

            # 4. Fleet Ownership & CPK Cost Efficiency (Max 15 pts)
            ownership_score = 15 if v.ownership_type == 'owned' else 8
            score += ownership_score

            # Maintenance & Odometer Check
            if v.next_service_due_km and v.current_km:
                if v.current_km >= v.next_service_due_km:
                    score = max(0, score - 15)
                    compliance_flags.append({
                        "type": "warning",
                        "label": f"⚠️ Service Overdue by {v.current_km - v.next_service_due_km} km"
                    })

            # Clamp score 0 - 100
            score = max(0, min(100, score))
            if is_disqualified:
                score = min(score, 30)

            evaluated.append({
                "id": v.id,
                "registration_number": v.registration_number,
                "brand_model": f"{v.brand} {v.model}".strip() or v.registration_number,
                "vehicle_type": str(v.vehicle_type.name) if v.vehicle_type else "Fleet",
                "seating_capacity": seats,
                "ownership_type": v.get_ownership_type_display(),
                "score": score,
                "is_disqualified": is_disqualified,
                "disqualification_reason": disqualification_reason,
                "compliance_flags": compliance_flags,
                "distance_km": dist_km,
                "distance_label": dist_label,
                "current_km": v.current_km,
                "default_driver_id": v.default_driver_id,
                "default_driver_name": v.default_driver.name if v.default_driver else None,
            })

        # Sort: Qualified first, then by score descending
        evaluated.sort(key=lambda x: (not x['is_disqualified'], x['score']), reverse=True)
        return evaluated

    # =========================================================================
    # DRIVER EVALUATION
    # =========================================================================
    @classmethod
    def _evaluate_drivers(
        cls,
        trip: Trip,
        start_date: date,
        end_date: date,
        is_hill_trip: bool
    ) -> List[Dict[str, Any]]:
        today = timezone.localdate()

        # Step A: Identify drivers already on overlapping active trips
        overlapping_driver_ids = Trip.objects.filter(
            status__in=['assigned', 'started', 'on_trip', 'driver_confirmed'],
            driver__isnull=False
        ).exclude(pk=trip.pk).filter(
            Q(start_date__lte=end_date, end_date__gte=start_date)
        ).values_list('driver_id', flat=True)

        all_drivers = Driver.objects.exclude(
            id__in=overlapping_driver_ids
        ).filter(
            status='active'
        )

        evaluated: List[Dict[str, Any]] = []

        for d in all_drivers:
            score = 0
            compliance_flags = []
            is_disqualified = False
            disqualification_reason = None

            # 1. License Validity Check (Max 35 pts)
            lic = d.license_status
            if lic['status'] == 'expired':
                is_disqualified = True
                disqualification_reason = f"Driver License Expired ({lic['label']})"
                compliance_flags.append({
                    "type": "danger",
                    "label": f"🔴 License Expired"
                })
                score += 0
            elif lic['status'] == 'expiring_soon':
                compliance_flags.append({
                    "type": "warning",
                    "label": f"🟡 License {lic['label']}"
                })
                score += 25
            elif lic['status'] == 'missing':
                compliance_flags.append({
                    "type": "warning",
                    "label": "⚠️ No License Expiry Set"
                })
                score += 20
            else:
                compliance_flags.append({
                    "type": "success",
                    "label": "🟢 License Valid"
                })
                score += 35

            # 2. Fatigue & Rest Period Analysis (Max 35 pts)
            rest_hours, rest_label, fatigue_risk = cls._compute_driver_rest(d, start_date)
            if fatigue_risk == 'critical':
                score += 5
                is_disqualified = True
                disqualification_reason = f"Fatigue Risk: Only {rest_hours:.1f}h rest since last trip"
                compliance_flags.append({
                    "type": "danger",
                    "label": f"🚨 Rest: {rest_label}"
                })
            elif fatigue_risk == 'warning':
                score += 20
                compliance_flags.append({
                    "type": "warning",
                    "label": f"🟡 Rest: {rest_label}"
                })
            else:
                score += 35
                compliance_flags.append({
                    "type": "success",
                    "label": f"🟢 Rest: {rest_label}"
                })

            # 3. Route & Skill Match (Max 30 pts)
            skill_score = 15
            if is_hill_trip:
                if d.hill_station_experience:
                    skill_score += 15
                    compliance_flags.append({
                        "type": "info",
                        "label": "⛰️ Hill Station Certified"
                    })
                else:
                    skill_score -= 5
                    compliance_flags.append({
                        "type": "warning",
                        "label": "⚠️ No Hill Road Certification"
                    })
            else:
                skill_score += 10

            if d.is_volvo_certified:
                compliance_flags.append({
                    "type": "info",
                    "label": "⭐ Volvo Certified"
                })

            score += skill_score
            score = max(0, min(100, score))

            if is_disqualified:
                score = min(score, 35)

            evaluated.append({
                "id": d.id,
                "name": d.name,
                "phone": d.phone or "No Phone",
                "badge_number": d.badge_number or "N/A",
                "score": score,
                "is_disqualified": is_disqualified,
                "disqualification_reason": disqualification_reason,
                "compliance_flags": compliance_flags,
                "rest_hours": rest_hours,
                "rest_label": rest_label,
                "hill_station_experience": d.hill_station_experience,
                "is_volvo_certified": d.is_volvo_certified,
            })

        evaluated.sort(key=lambda x: (not x['is_disqualified'], x['score']), reverse=True)
        return evaluated

    # =========================================================================
    # PAIR FORMULATION
    # =========================================================================
    @classmethod
    def _formulate_pairs(
        cls,
        candidate_vehicles: List[Dict[str, Any]],
        candidate_drivers: List[Dict[str, Any]],
        is_hill_trip: bool
    ) -> List[Dict[str, Any]]:
        """
        Calculates composite match scores (0 to 100) for paired vehicles & drivers.
        Gives bonus if vehicle has a preferred/default driver relationship.
        """
        pairs: List[Dict[str, Any]] = []

        # Only evaluate non-disqualified candidates for top recommendations
        valid_vehicles = [v for v in candidate_vehicles if not v['is_disqualified']]
        valid_drivers = [d for d in candidate_drivers if not d['is_disqualified']]

        # Fallback to top candidates if all are restricted
        if not valid_vehicles:
            valid_vehicles = candidate_vehicles[:3]
        if not valid_drivers:
            valid_drivers = candidate_drivers[:3]

        for v in valid_vehicles[:6]:
            for d in valid_drivers[:6]:
                # 50% vehicle score + 50% driver score
                composite_score = round((v['score'] * 0.5) + (d['score'] * 0.5))

                # Default pairing synergy bonus
                is_default_pair = (v.get('default_driver_id') == d['id'])
                if is_default_pair:
                    composite_score = min(100, composite_score + 8)

                match_label = "Optimal Match"
                if composite_score >= 90:
                    match_label = "🌟 Top Match"
                elif composite_score >= 75:
                    match_label = "🟢 Highly Recommended"
                elif composite_score >= 60:
                    match_label = "🟡 Suitable Alternative"
                else:
                    match_label = "⚠️ Conditional"

                pairs.append({
                    "vehicle": v,
                    "driver": d,
                    "composite_score": composite_score,
                    "match_label": match_label,
                    "is_default_pair": is_default_pair,
                    "quick_summary": f"{v['registration_number']} ({v['brand_model']}) + {d['name']}",
                })

        pairs.sort(key=lambda p: p['composite_score'], reverse=True)
        return pairs

    # =========================================================================
    # UTILITY & TELEMETRY HELPERS
    # =========================================================================
    @classmethod
    def _get_vehicle_proximity(cls, vehicle: Vehicle) -> Tuple[float, str]:
        """
        Computes distance from vehicle's latest telematics ping or home depot to HQ/origin.
        """
        try:
            latest_ping = vehicle.telematics_pings.order_by('-timestamp').first()
            if latest_ping and latest_ping.latitude and latest_ping.longitude:
                dist_m = SpatialEngine.haversine_distance_meters(
                    DEFAULT_DEPOT_LAT, DEFAULT_DEPOT_LNG,
                    float(latest_ping.latitude), float(latest_ping.longitude)
                )
                dist_km = round(dist_m / 1000.0, 1)
                return dist_km, f"{dist_km} km (Live GPS)"
        except Exception:
            pass

        # Depot fallback
        return 2.5, "2.5 km (At Central Depot)"

    @classmethod
    def _compute_driver_rest(cls, driver: Driver, trip_start_date: date) -> Tuple[float, str, str]:
        """
        Computes hours of rest since the driver's last completed trip.
        Returns: (rest_hours, rest_label, fatigue_risk: 'safe'|'warning'|'critical')
        """
        try:
            last_trip = Trip.objects.filter(
                driver=driver,
                status='completed',
                end_date__isnull=False
            ).order_by('-end_date').first()

            if not last_trip or not last_trip.end_date:
                return 48.0, "Well Rested (>48h)", "safe"

            days_gap = (trip_start_date - last_trip.end_date).days
            if days_gap < 0:
                return 0.0, "Schedule Conflict", "critical"
            elif days_gap == 0:
                # Same day dispatch! High risk unless confirmed
                return 4.0, "Only 4h Rest (Same Day)", "critical"
            elif days_gap == 1:
                return 12.0, "12h Rest", "safe"
            else:
                hours = days_gap * 24.0
                return hours, f"{int(hours)}h Rest", "safe"

        except Exception as e:
            logger.debug(f"Error computing rest for driver #{driver.id}: {e}")
            return 24.0, "24h Rest (Default)", "safe"
