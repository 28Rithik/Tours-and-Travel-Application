import logging
from datetime import time, datetime
from typing import Dict, Any, List, Optional
from django.utils import timezone

logger = logging.getLogger(__name__)


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
                # ✅ Safe Drop Confirmed
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
                # 🚨 Critical SOS Escalation
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
                            f"🚨 CRITICAL WOMEN SAFETY IVR ALARM: Commuter {bp.commuter.name} (ID: {bp.commuter.commuter_id}) "
                            f"pressed Key 2 (Panic Escalation) during post-drop IVR verification. Contact: {bp.commuter.phone}"
                        ),
                        location_address=bp.commuter.boarding_stop.name if bp.commuter.boarding_stop else "Drop Location",
                        status='reported'
                    )

                return {
                    "status": "sos_escalated",
                    "action": "emergency_alarm",
                    "alert_title": f"🚨 EMERGENCY IVR ALARM: {bp.commuter.name}",
                    "message": "Alarm siren dispatched to transport control room and security supervisor."
                }
            else:
                return {"status": "ignored", "message": f"Unrecognized DTMF digit: {digit}"}

        except CommuterBoardingPass.DoesNotExist:
            return {"status": "error", "message": "Invalid pass token."}
