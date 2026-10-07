import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.db import transaction

from fleet_contracts.models import (
    TransportContract,
    ContractTripLog,
    ContractSLAPenalty,
    ContractMonthlyInvoice,
)


class SLAEngine:
    """
    Automated SLA Compliance & Performance Penalty Engine for Corporate & School Contracts.
    
    Responsibilities:
    1. Audits Trip Logs against Shift Timetables & Permissible Grace Periods.
    2. Auto-computes SLA penalty deductions (Late Arrival, Breakdown Delay, Missed Trips).
    3. Seamlessly binds penalties to ContractMonthlyInvoice while enforcing SLA penalty cap ceilings.
    4. Supports dispute resolution and executive waiver tracking.
    """

    DEFAULT_PENALTY_SLABS = {
        'minor_delay': Decimal('300.00'),   # 11 - 20 mins delay
        'major_delay': Decimal('500.00'),   # 21 - 40 mins delay
        'severe_delay': Decimal('1000.00'), # >40 mins delay
        'breakdown': Decimal('1500.00'),    # Vehicle breakdown with delay
        'missed_trip': Decimal('2500.00'),  # Trip completely unserved
    }

    @classmethod
    def calculate_delay_minutes(
        cls,
        scheduled_time: Optional[datetime.time],
        actual_time: Optional[datetime.time]
    ) -> int:
        """
        Calculates difference in minutes between actual arrival/departure and scheduled time.
        """
        if not scheduled_time or not actual_time:
            return 0

        # Convert to minutes from midnight
        sched_mins = (scheduled_time.hour * 60) + scheduled_time.minute
        act_mins = (actual_time.hour * 60) + actual_time.minute

        # Handle night crossover (e.g. scheduled 23:50, arrived 00:15)
        diff = act_mins - sched_mins
        if diff < -720: # crossed midnight
            diff += 1440

        return max(0, diff)

    @classmethod
    def evaluate_trip_sla(
        cls,
        trip_log: ContractTripLog,
        auto_record_penalty: bool = True
    ) -> Dict[str, Any]:
        """
        Evaluates a single ContractTripLog against shift SLA rules.
        """
        shift = trip_log.shift
        contract = shift.route.contract
        grace_period = shift.grace_period_minutes or 10

        # Determine reference time (departure or arrival)
        ref_scheduled = trip_log.scheduled_departure_time or shift.timing
        ref_actual = trip_log.actual_departure_time or trip_log.actual_arrival_time

        delay_minutes = cls.calculate_delay_minutes(ref_scheduled, ref_actual)
        
        # If manually recorded delay_minutes on trip_log is higher, use it
        if trip_log.delay_minutes and trip_log.delay_minutes > delay_minutes:
            delay_minutes = trip_log.delay_minutes

        is_breach = False
        penalty_amount = Decimal('0.00')
        penalty_type = 'late_arrival'
        reason_desc = ""

        # Check breakdown
        if trip_log.status == 'breakdown':
            is_breach = True
            penalty_type = 'breakdown_delay'
            penalty_amount = cls.DEFAULT_PENALTY_SLABS['breakdown']
            reason_desc = f"Vehicle Breakdown on route: {trip_log.vehicle.registration_number if trip_log.vehicle else 'N/A'}"
        elif trip_log.status == 'cancelled':
            is_breach = True
            penalty_type = 'missed_trip'
            penalty_amount = cls.DEFAULT_PENALTY_SLABS['missed_trip']
            reason_desc = f"Scheduled trip unserved / cancelled for shift: {shift.shift_name or shift.direction}"
        elif delay_minutes > grace_period:
            net_delay = delay_minutes - grace_period
            is_breach = True
            penalty_type = 'late_arrival'
            if net_delay <= 10:
                penalty_amount = cls.DEFAULT_PENALTY_SLABS['minor_delay']
            elif net_delay <= 30:
                penalty_amount = cls.DEFAULT_PENALTY_SLABS['major_delay']
            else:
                penalty_amount = cls.DEFAULT_PENALTY_SLABS['severe_delay']
            
            reason_desc = (
                f"Shift {shift.shift_name or shift.direction} scheduled at {ref_scheduled.strftime('%I:%M %p')}, "
                f"actual at {ref_actual.strftime('%I:%M %p') if ref_actual else 'N/A'}. "
                f"Delayed by {delay_minutes} mins (Grace: {grace_period} mins, Net breach: {net_delay} mins)."
            )

        penalty_record = None
        if is_breach and auto_record_penalty and penalty_amount > 0:
            # Check if penalty already logged for this trip log
            existing = ContractSLAPenalty.objects.filter(trip_log=trip_log).first()
            if not existing:
                penalty_record = ContractSLAPenalty.objects.create(
                    contract=contract,
                    trip_log=trip_log,
                    date=trip_log.date,
                    penalty_type=penalty_type,
                    penalty_amount=penalty_amount,
                    description=reason_desc
                )
            else:
                penalty_record = existing

        return {
            "trip_log_id": trip_log.id,
            "contract": contract.name,
            "is_breach": is_breach,
            "delay_minutes": delay_minutes,
            "grace_period": grace_period,
            "penalty_type": penalty_type,
            "penalty_amount": float(penalty_amount),
            "reason": reason_desc,
            "penalty_record_id": penalty_record.id if penalty_record else None
        }

    @classmethod
    def audit_monthly_penalties(
        cls,
        contract: TransportContract,
        from_date: datetime.date,
        to_date: datetime.date
    ) -> Dict[str, Any]:
        """
        Audits all trip logs for a contract across a date range and calculates SLA penalty totals.
        """
        logs = ContractTripLog.objects.filter(
            shift__route__contract=contract,
            date__gte=from_date,
            date__lte=to_date
        ).select_related('shift', 'shift__route', 'vehicle', 'driver')

        evaluated_count = 0
        breach_count = 0
        total_penalty = Decimal('0.00')

        for log in logs:
            evaluated_count += 1
            res = cls.evaluate_trip_sla(log, auto_record_penalty=True)
            if res["is_breach"]:
                breach_count += 1

        # Fetch all active (non-waived) penalties in the range
        active_penalties = ContractSLAPenalty.objects.filter(
            contract=contract,
            date__gte=from_date,
            date__lte=to_date,
            waived=False
        )
        total_penalty = sum((p.penalty_amount for p in active_penalties), Decimal('0.00'))

        waived_penalties = ContractSLAPenalty.objects.filter(
            contract=contract,
            date__gte=from_date,
            date__lte=to_date,
            waived=True
        )
        waived_total = sum((p.penalty_amount for p in waived_penalties), Decimal('0.00'))

        return {
            "contract": contract.name,
            "total_trips_audited": evaluated_count,
            "sla_breaches_detected": breach_count,
            "total_penalty_deduction": float(total_penalty),
            "waived_penalty_amount": float(waived_total),
            "penalties_count": active_penalties.count()
        }

    @classmethod
    def apply_penalties_to_invoice(cls, invoice: ContractMonthlyInvoice) -> Decimal:
        """
        Applies accumulated penalties to the monthly invoice, respecting the contract's SLA penalty cap.
        """
        contract = invoice.contract
        penalties = ContractSLAPenalty.objects.filter(
            contract=contract,
            date__gte=invoice.from_date,
            date__lte=invoice.to_date,
            waived=False
        )

        raw_penalty_total = sum((p.penalty_amount for p in penalties), Decimal('0.00'))

        # Calculate Cap
        cap_pct = contract.sla_penalty_cap_pct or Decimal('10.00')
        max_allowed_penalty = (invoice.base_contract_amount * cap_pct) / Decimal('100.00') if invoice.base_contract_amount else raw_penalty_total

        final_deduction = min(raw_penalty_total, max_allowed_penalty) if max_allowed_penalty > 0 else raw_penalty_total

        # Bind penalties to invoice
        penalties.update(applied_to_invoice=invoice)

        # Update invoice
        invoice.sla_penalty_deduction = final_deduction
        invoice.calculate_totals()
        invoice.save(update_fields=['sla_penalty_deduction', 'net_taxable_amount', 'gst_amount', 'grand_total'])

        return final_deduction
