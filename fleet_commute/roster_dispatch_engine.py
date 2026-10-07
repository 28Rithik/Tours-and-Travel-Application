import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.db import transaction

from core.models import Vehicle, Driver
from fleet_contracts.models import (
    TransportContract,
    Route,
    RouteStop,
    Shift,
    ContractFleetRoster,
    ContractTripLog,
    CommuterManifest,
)
from fleet_commute.models import CommuterBoardingPass


class RosterDispatchEngine:
    """
    Automated Batch Roster Dispatcher for 300+ School & Corporate Commute Vehicles.
    
    Responsibilities:
    1. Batch spins up daily/shift ContractTripLog records from ContractFleetRoster allocations.
    2. Enforces pre-flight statutory compliance (FC, Commercial Insurance, Driver License).
    3. Auto-switches to dedicated standby backup vehicles if primary fails compliance.
    4. Auto-provisions CommuterBoardingPass records with 4-digit OTPs and mobile tracking tokens.
    5. Detects and flags unassigned shifts / roster coverage gaps for dispatchers.
    """

    DAY_MAP = {
        0: 'Mon',
        1: 'Tue',
        2: 'Wed',
        3: 'Thu',
        4: 'Fri',
        5: 'Sat',
        6: 'Sun'
    }

    @classmethod
    def is_shift_operating_on_date(cls, shift: Shift, target_date: datetime.date) -> bool:
        """
        Evaluates whether a shift operates on a given date based on days_of_week pattern.
        Common patterns: 'Mon-Fri', 'Mon-Sat', 'All 7 Days', 'Daily', 'Mon,Wed,Fri'
        """
        dow = target_date.weekday() # 0 = Monday, 6 = Sunday
        pattern = (shift.days_of_week or 'Mon-Fri').strip().lower()

        if pattern in ['all 7 days', 'daily', 'all', '7 days']:
            return True
        if pattern in ['mon-fri', 'mon - fri', 'monday-friday']:
            return dow < 5
        if pattern in ['mon-sat', 'mon - sat', 'monday-saturday']:
            return dow < 6
        
        # Check specific day abbreviation match (e.g. 'Mon', 'Wed')
        day_abbr = cls.DAY_MAP.get(dow, '').lower()
        return day_abbr in pattern

    @classmethod
    def evaluate_compliance(
        cls,
        vehicle: Vehicle,
        driver: Driver,
        target_date: datetime.date
    ) -> Dict[str, Any]:
        """
        Validates statutory documents for vehicle & driver on target date.
        """
        issues = []
        is_compliant = True

        # Vehicle FC Check
        if vehicle.fc_expiry and vehicle.fc_expiry < target_date:
            is_compliant = False
            issues.append(f"Vehicle {vehicle.registration_number}: FC expired on {vehicle.fc_expiry.strftime('%d/%m/%Y')}")

        # Vehicle Insurance Check
        if vehicle.insurance_expiry and vehicle.insurance_expiry < target_date:
            is_compliant = False
            issues.append(f"Vehicle {vehicle.registration_number}: Insurance expired on {vehicle.insurance_expiry.strftime('%d/%m/%Y')}")

        # Driver License Check
        validity = driver.license_validity_tr or driver.license_validity_nt
        if validity and validity < target_date:
            is_compliant = False
            issues.append(f"Driver {driver.name}: Driving license expired on {validity.strftime('%d/%m/%Y')}")

        return {
            "is_compliant": is_compliant,
            "issues": issues
        }

    @classmethod
    def execute_batch_roster_dispatch(
        cls,
        target_date: Optional[datetime.date] = None,
        contract_id: Optional[int] = None,
        direction: Optional[str] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Executes bulk daily shift provisioning for active contracts.
        """
        if target_date is None:
            target_date = timezone.now().date()

        contracts_query = TransportContract.objects.filter(
            status='active',
            start_date__lte=target_date,
            end_date__gte=target_date
        )
        if contract_id:
            contracts_query = contracts_query.filter(pk=contract_id)

        active_contracts = list(contracts_query)

        trips_created = 0
        trips_existing = 0
        passes_created = 0
        compliance_substitutions = []
        compliance_blocks = []
        roster_gaps = []

        with transaction.atomic():
            for contract in active_contracts:
                # 1. Fetch active roster allocations for this contract
                from django.db.models import Q
                rosters = ContractFleetRoster.objects.filter(
                    contract=contract,
                    is_active=True,
                    start_date__lte=target_date
                ).filter(
                    Q(end_date__isnull=True) | Q(end_date__gte=target_date)
                ).select_related('route', 'shift', 'primary_vehicle', 'primary_driver', 'standby_vehicle')

                # Helper to map roster by (route_id, shift_id)
                roster_map = {}
                for r in rosters:
                    key = (r.route_id, r.shift_id)
                    roster_map[key] = r

                # 2. Iterate through all active routes and shifts for the contract
                routes = Route.objects.filter(contract=contract, is_active=True).prefetch_related('shifts')

                for route in routes:
                    shifts_query = route.shifts.all()
                    if direction:
                        shifts_query = shifts_query.filter(direction=direction)

                    for shift in shifts_query:
                        # Check if shift operates on target date
                        if not cls.is_shift_operating_on_date(shift, target_date):
                            continue

                        # Find matching roster allocation
                        roster = roster_map.get((route.id, shift.id)) or roster_map.get((route.id, None)) or roster_map.get((None, None))

                        if not roster:
                            roster_gaps.append({
                                "contract": contract.name,
                                "route": route.name,
                                "shift": str(shift),
                                "timing": shift.timing.strftime('%I:%M %p'),
                                "direction": shift.get_direction_display(),
                                "reason": "No active vehicle/driver assigned in Roster"
                            })
                            continue

                        assigned_vehicle = roster.primary_vehicle
                        assigned_driver = roster.primary_driver
                        is_replacement = False
                        replacement_reason = ""

                        # 3. Pre-flight compliance evaluation
                        comp_check = cls.evaluate_compliance(assigned_vehicle, assigned_driver, target_date)
                        if not comp_check["is_compliant"]:
                            # Attempt standby vehicle swap if vehicle was the issue
                            if roster.standby_vehicle:
                                standby_check = cls.evaluate_compliance(roster.standby_vehicle, assigned_driver, target_date)
                                if standby_check["is_compliant"]:
                                    replacement_reason = f"Primary vehicle {assigned_vehicle.registration_number} compliance failed. Swapped with standby vehicle {roster.standby_vehicle.registration_number}."
                                    assigned_vehicle = roster.standby_vehicle
                                    is_replacement = True
                                    compliance_substitutions.append({
                                        "contract": contract.name,
                                        "route": route.name,
                                        "primary": roster.primary_vehicle.registration_number,
                                        "standby": assigned_vehicle.registration_number,
                                        "driver": assigned_driver.name,
                                        "reasons": comp_check["issues"]
                                    })
                                else:
                                    compliance_blocks.append({
                                        "contract": contract.name,
                                        "route": route.name,
                                        "vehicle": assigned_vehicle.registration_number,
                                        "standby": roster.standby_vehicle.registration_number,
                                        "driver": assigned_driver.name,
                                        "issues": comp_check["issues"] + standby_check["issues"]
                                    })
                                    continue
                            else:
                                compliance_blocks.append({
                                    "contract": contract.name,
                                    "route": route.name,
                                    "vehicle": assigned_vehicle.registration_number,
                                    "driver": assigned_driver.name,
                                    "issues": comp_check["issues"]
                                })
                                continue

                        # 4. Count expected commuters for this route
                        assigned_commuters = CommuterManifest.objects.filter(
                            contract=contract,
                            is_active=True
                        ).filter(
                            boarding_stop__route=route
                        ).select_related('boarding_stop')

                        commuter_count = assigned_commuters.count()

                        # 5. Create or retrieve ContractTripLog
                        trip_log, created = ContractTripLog.objects.get_or_create(
                            shift=shift,
                            date=target_date,
                            defaults={
                                'vehicle': assigned_vehicle,
                                'driver': assigned_driver,
                                'status': 'scheduled',
                                'scheduled_departure_time': shift.timing,
                                'passenger_count': commuter_count,
                                'is_replacement_vehicle': is_replacement,
                                'replaced_vehicle': roster.primary_vehicle if is_replacement else None,
                                'delay_reason': replacement_reason
                            }
                        )

                        if created:
                            trips_created += 1
                        else:
                            trips_existing += 1
                            if force_refresh and trip_log.status == 'scheduled':
                                trip_log.vehicle = assigned_vehicle
                                trip_log.driver = assigned_driver
                                trip_log.passenger_count = commuter_count
                                trip_log.scheduled_departure_time = shift.timing
                                if is_replacement:
                                    trip_log.is_replacement_vehicle = True
                                    trip_log.replaced_vehicle = roster.primary_vehicle
                                trip_log.save(update_fields=['vehicle', 'driver', 'passenger_count', 'scheduled_departure_time', 'is_replacement_vehicle', 'replaced_vehicle'])

                        # 6. Generate CommuterBoardingPass records for each passenger
                        for commuter in assigned_commuters:
                            is_night = (
                                shift.direction == 'drop' and
                                commuter.gender == 'female' and
                                (shift.timing.hour >= 20 or shift.timing.hour < 6)
                            )
                            _, pass_created = CommuterBoardingPass.objects.get_or_create(
                                commuter=commuter,
                                date=target_date,
                                shift=shift,
                                defaults={
                                    'trip_log': trip_log,
                                    'boarded_stop': commuter.boarding_stop,
                                    'is_isolated_night_drop': is_night,
                                    'escort_assigned': shift.escort_guard_required or is_night
                                }
                            )
                            if pass_created:
                                passes_created += 1

        return {
            "status": "success",
            "target_date": target_date.strftime('%Y-%m-%d'),
            "target_day_name": target_date.strftime('%A'),
            "active_contracts_evaluated": len(active_contracts),
            "trips_created": trips_created,
            "trips_existing": trips_existing,
            "total_trips_in_schedule": trips_created + trips_existing,
            "passes_created": passes_created,
            "compliance_substitutions": compliance_substitutions,
            "compliance_blocks": compliance_blocks,
            "roster_gaps": roster_gaps,
            "roster_gaps_count": len(roster_gaps),
        }


def models_q_open_ended(target_date):
    from django.db.models import Q
    return Q(end_date__isnull=True) | Q(end_date__gte=target_date)
