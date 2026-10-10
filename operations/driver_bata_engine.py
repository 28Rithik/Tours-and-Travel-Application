from decimal import Decimal
from datetime import time, date, datetime, timedelta
from typing import Dict, Any


def calculate_trip_driver_bata(trip) -> Dict[str, Any]:
    """
    Intelligent Multi-Component Driver Allowance (Batta) Engine.
    
    Calculates transparent, compliant driver allowances adhering to Indian transport
    and travel agency enterprise standards:
    1. Base Daily Bata (Derived from vehicle master, client rate card, or seating tier)
    2. Night Halt Allowance (Overnight outstation halts or duties extending past 22:00)
    3. Early Morning Reporting Allowance (Reporting before 06:00 AM)
    4. Late Night Drop Allowance (Final drop after 23:00 / 11:00 PM)
    5. Extended Tour Incentive (Multi-day expedition bonus for >= 5 days)
    6. Overtime Bata (Hours beyond standard 12-hour daily shift @ ₹100/hr)
    """
    days = max(getattr(trip, 'days_count', 1) or 1, 1)

    # 1. Base Daily Bata Determination
    daily_rate = Decimal('500.00')
    rate_source = "Standard Fleet Benchmark"

    # Check vehicle type default bata
    if getattr(trip, 'vehicle', None) and getattr(trip.vehicle, 'vehicle_type', None) and getattr(trip.vehicle.vehicle_type, 'driver_bata', None) and trip.vehicle.vehicle_type.driver_bata > 0:
        daily_rate = Decimal(str(trip.vehicle.vehicle_type.driver_bata))
        rate_source = f"Vehicle Type ({trip.vehicle.vehicle_type.name})"
    # Check vehicle default bata
    elif getattr(trip, 'vehicle', None) and getattr(trip.vehicle, 'driver_bata', None) and trip.vehicle.driver_bata > 0:
        daily_rate = Decimal(str(trip.vehicle.driver_bata))
        rate_source = f"Vehicle Master ({trip.vehicle.registration_number})"
    # Check rate card if available
    elif getattr(trip, 'party', None) and getattr(trip, 'booking', None) and getattr(trip.booking, 'vehicle_type', None):
        try:
            from core.models import RateCard
            rc = RateCard.objects.filter(
                party=trip.party,
                vehicle_type=trip.booking.vehicle_type.name
            ).first()
            if rc and getattr(rc, 'driver_bata', None) and rc.driver_bata > 0:
                daily_rate = Decimal(str(rc.driver_bata))
                rate_source = f"Client Rate Card ({trip.party.name})"
        except Exception:
            pass
    # Fallback tier by seating capacity
    elif getattr(trip, 'vehicle', None):
        cap = getattr(trip.vehicle, 'seating_capacity', None) or 4
        if cap <= 4:
            daily_rate = Decimal('400.00')
            rate_source = "Sedan / Prime Tier"
        elif cap <= 8:
            daily_rate = Decimal('500.00')
            rate_source = "SUV / Crysta Tier"
        elif cap <= 18:
            daily_rate = Decimal('700.00')
            rate_source = "Tempo Traveller Tier"
        else:
            daily_rate = Decimal('1000.00')
            rate_source = "Heavy Luxury Coach Tier"

    base_bata = (daily_rate * Decimal(str(days))).quantize(Decimal('0.01'))

    # 2. Night Halt Allowance
    night_halts_count = 0
    night_halt_rate = Decimal('400.00')
    if days > 1:
        night_halts_count = days - 1
    elif getattr(trip, 'end_time', None):
        # Single day trip ending at or after 22:00
        if trip.end_time >= time(22, 0):
            night_halts_count = 1

    night_halt_bata = (Decimal(str(night_halts_count)) * night_halt_rate).quantize(Decimal('0.01'))

    # 3. Early Morning Reporting Allowance (< 06:00 AM)
    early_morning_bata = Decimal('0.00')
    is_early_reporting = False
    if getattr(trip, 'start_time', None) and trip.start_time < time(6, 0):
        early_morning_bata = Decimal('200.00')
        is_early_reporting = True

    # 4. Late Night Drop Allowance (>= 23:00 / 11:00 PM on return)
    late_night_bata = Decimal('0.00')
    is_late_drop = False
    if getattr(trip, 'end_time', None) and trip.end_time >= time(23, 0):
        late_night_bata = Decimal('200.00')
        is_late_drop = True

    # 5. Multi-Day Expedition Tour Bonus (>= 5 days)
    outstation_bonus = Decimal('0.00')
    if days >= 5:
        outstation_bonus = Decimal('500.00')

    # 6. Overtime Calculation for Single-Day Extended Shifts (> 12 hours)
    overtime_hours = 0
    overtime_bata = Decimal('0.00')
    if days == 1 and getattr(trip, 'start_time', None) and getattr(trip, 'end_time', None):
        try:
            today = date.today()
            t_start = datetime.combine(today, trip.start_time)
            t_end = datetime.combine(today, trip.end_time)
            if t_end < t_start:
                t_end += timedelta(days=1)
            duration_hours = (t_end - t_start).total_seconds() / 3600.0
            if duration_hours > 12.0:
                overtime_hours = int(duration_hours - 12.0)
                overtime_bata = (Decimal(str(overtime_hours)) * Decimal('100.00')).quantize(Decimal('0.01'))
        except Exception:
            pass

    # Total Sum
    total_bata = (
        base_bata +
        night_halt_bata +
        early_morning_bata +
        late_night_bata +
        outstation_bonus +
        overtime_bata
    ).quantize(Decimal('0.01'))

    # Build calculation narrative
    notes_parts = [f"Base: {days} day(s) @ ₹{daily_rate:,.0f} ({rate_source})"]
    if night_halts_count > 0:
        notes_parts.append(f"{night_halts_count} Night Halt(s) @ ₹{night_halt_rate:,.0f}")
    if is_early_reporting:
        notes_parts.append("Early Morning Reporting (< 06:00 AM) @ ₹200")
    if is_late_drop:
        notes_parts.append("Late Night Drop (>= 23:00 PM) @ ₹200")
    if outstation_bonus > 0:
        notes_parts.append("Long Tour Expedition Bonus @ ₹500")
    if overtime_hours > 0:
        notes_parts.append(f"{overtime_hours}h Overtime (>12h) @ ₹100/hr")

    calculation_notes = " + ".join(notes_parts)

    return {
        'total_bata': total_bata,
        'base_bata': base_bata,
        'days_count': days,
        'daily_rate': daily_rate,
        'rate_source': rate_source,
        'night_halts_count': night_halts_count,
        'night_halt_bata': night_halt_bata,
        'early_morning_bata': early_morning_bata,
        'late_night_bata': late_night_bata,
        'outstation_bonus': outstation_bonus,
        'overtime_hours': overtime_hours,
        'overtime_bata': overtime_bata,
        'calculation_notes': calculation_notes,
    }
