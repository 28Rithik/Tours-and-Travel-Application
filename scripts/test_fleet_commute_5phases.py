import os
import sys
import io
import django
from datetime import time, date
from decimal import Decimal

# Setup Django Environment
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, PROJECT_DIR)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import Vehicle, Driver, Client as CoreClient, VehicleType
from fleet_contracts.models import TransportContract, Route, RouteStop, Shift, CommuterManifest, ContractTripLog
from fleet_commute.models import CommuterBoardingPass, ESGCarbonMetric
from fleet_commute.safety_engine import WomenSafetyEngine
from fleet_commute.commute_services import CommuteService
from operations.models import EmergencyIncidentAlert, DriverBehaviorLog

User = get_user_model()


def run_fleet_commute_5phase_verification():
    print("=" * 85)
    print("🌟 SIVA GAYATHRI TOURS & TRAVELS — CORPORATE COMMUTE & SAFETY 5-PHASE TEST SUITE")
    print("=" * 85)

    total_tests = 0
    passed_tests = 0

    # 0. Setup Foundation Seed Data
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@travelerp.com', 'is_staff': True, 'is_superuser': True}
        )
        admin_user.set_password('admin123')
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

    client = Client()
    client.force_login(admin_user)

    customer, _ = CoreClient.objects.get_or_create(name='Amazon Development Centre India', defaults={'phone': '9840112233'})
    contract, _ = TransportContract.objects.get_or_create(
        customer=customer,
        name='Amazon OMR IT SEZ 24/7 Employee Transit Contract',
        defaults={'start_date': date(2025, 1, 1), 'end_date': date(2027, 12, 31), 'status': 'active'}
    )
    route, _ = Route.objects.get_or_create(
        contract=contract,
        name='Route 9 - Tidel Park Express',
        defaults={'origin': 'Velachery Hub', 'destination': 'OMR Campus', 'distance_km': 28}
    )
    stop, _ = RouteStop.objects.get_or_create(
        route=route,
        stop_order=1,
        defaults={'name': 'Perungudi Toll Plaza', 'pickup_landmark': 'Opp Apollo Hospital'}
    )
    night_shift, _ = Shift.objects.get_or_create(
        route=route,
        direction='drop',
        shift_name='BPO Midnight Drop (11 PM)',
        defaults={'timing': time(23, 0), 'escort_guard_required': False}
    )

    vtype, _ = VehicleType.objects.get_or_create(name='Sedan AC')
    vehicle, _ = Vehicle.objects.get_or_create(
        registration_number='TN-38-BZ-4819',
        defaults={'brand': 'Toyota', 'model': 'Etios', 'vehicle_type': vtype, 'status': 'available', 'ownership_type': 'owned'}
    )
    driver, _ = Driver.objects.get_or_create(
        name='Muthu Kumar (Verified Pilot)',
        phone='9840144556',
        defaults={'driver_type': 'owned', 'status': 'active'}
    )
    trip_log, _ = ContractTripLog.objects.get_or_create(
        shift=night_shift,
        date=timezone.now().date(),
        defaults={'vehicle': vehicle, 'driver': driver, 'status': 'en_route', 'passenger_count': 4}
    )

    # =========================================================================
    # TEST 1: Phase 1 — Women Safety IVR Simulator & Guardrails
    # =========================================================================
    print("\n--- 1. AUDITING PHASE 1: WOMEN SAFETY IVR & NIGHT GUARDRAILS (🅶 & 🅷) ---")
    total_tests += 1
    is_night = WomenSafetyEngine.is_night_time(time(23, 0))
    if is_night:
        passed_tests += 1
        print("  [PASS] Statutory Night Shift Window detection verified (23:00 is Night Shift).")
    else:
        print("  [FAIL] Night shift check failed.")

    total_tests += 1
    female_commuter, _ = CommuterManifest.objects.get_or_create(
        contract=contract,
        commuter_id='AMZ-8891',
        defaults={'name': 'Deepika Narayanan', 'gender': 'female', 'phone': '9840998877', 'boarding_stop': stop}
    )
    bp, _ = CommuterBoardingPass.objects.get_or_create(
        commuter=female_commuter,
        trip_log=trip_log,
        date=timezone.now().date(),
        defaults={'is_isolated_night_drop': True}
    )

    # 1. Trigger Outbound IVR Call
    ivr_call = WomenSafetyEngine.trigger_outbound_ivr_call(bp.id)
    if ivr_call.get('status') == 'success' and 'Deepika' in ivr_call.get('ivr_audio_script', ''):
        passed_tests += 1
        print(f"  [PASS] Outbound IVR call generated with audio script: \"{ivr_call['ivr_audio_script'][:65]}...\"")
    else:
        print(f"  [FAIL] Outbound IVR call failed: {ivr_call}")

    # 2. Test DTMF Key 1: Safe Arrival Confirmed
    total_tests += 1
    safe_res = WomenSafetyEngine.handle_ivr_dtmf_webhook(bp.pass_token, '1')
    bp.refresh_from_db()
    if safe_res.get('status') == 'success' and bp.ivr_status == 'safe_confirmed':
        passed_tests += 1
        print(f"  [PASS] DTMF Key 1 Webhook verified: Commuter marked safe_confirmed.")
    else:
        print(f"  [FAIL] Safe webhook failed: {safe_res}")

    # 3. Test DTMF Key 2: Emergency Panic SOS Trigger
    total_tests += 1
    sos_res = WomenSafetyEngine.handle_ivr_dtmf_webhook(bp.pass_token, '2')
    bp.refresh_from_db()
    emergency_alert = EmergencyIncidentAlert.objects.filter(vehicle=vehicle, incident_type='sos_panic').first()
    if sos_res.get('status') == 'sos_escalated' and bp.ivr_status == 'sos_escalated' and emergency_alert:
        passed_tests += 1
        print(f"  [PASS] DTMF Key 2 Webhook verified: EmergencyIncidentAlert #{emergency_alert.id} generated.")
    else:
        print(f"  [FAIL] SOS webhook failed: {sos_res}")

    # =========================================================================
    # TEST 2: Phase 2 — Passenger OTP Boarding Verification (🅲)
    # =========================================================================
    print("\n--- 2. AUDITING PHASE 2: PASSENGER OTP BOARDING VERIFICATION (🅲) ---")
    total_tests += 1
    male_commuter, _ = CommuterManifest.objects.get_or_create(
        contract=contract,
        commuter_id='AMZ-4412',
        defaults={'name': 'Venkatesh Raghavan', 'gender': 'male', 'phone': '9840556677', 'boarding_stop': stop}
    )
    bp_otp, _ = CommuterBoardingPass.objects.get_or_create(
        commuter=male_commuter,
        trip_log=trip_log,
        date=timezone.now().date(),
        defaults={'boarding_otp': '7821', 'is_boarded': False}
    )
    bp_otp.is_boarded = False
    bp_otp.save()

    verify_res = CommuteService.verify_passenger_boarding_otp(bp_otp.boarding_otp, driver_id=driver.id)
    bp_otp.refresh_from_db()
    if verify_res.get('status') == 'success' and bp_otp.is_boarded:
        passed_tests += 1
        print(f"  [PASS] Passenger OTP Boarding verified for {verify_res['commuter_name']} (OTP: {bp_otp.boarding_otp}).")
    else:
        print(f"  [FAIL] OTP Boarding failed: {verify_res}")

    total_tests += 1
    already_res = CommuteService.verify_passenger_boarding_otp(bp_otp.boarding_otp, driver_id=driver.id)
    if already_res.get('status') == 'already_boarded':
        passed_tests += 1
        print("  [PASS] Duplicate boarding protection active (returned 'already_boarded').")
    else:
        print(f"  [FAIL] Duplicate boarding check failed: {already_res}")

    # =========================================================================
    # TEST 3: Phase 3 — Bulk Corporate Employee CSV Roster Importer (🅱️)
    # =========================================================================
    print("\n--- 3. AUDITING PHASE 3: BULK EMPLOYEE CSV ROSTER IMPORTER (🅱️) ---")
    total_tests += 1
    sample_csv_text = """Employee_ID,Name,Gender,Phone,Department,Route_Name,Stop_Name
TEST_EMP01,Sowmya Raman,Female,9840000001,Architecture,Route 9 - Tidel Park Express,Perungudi Toll Plaza
TEST_EMP02,Ravi Chandran,Male,9840000002,Infrastructure,Route 9 - Tidel Park Express,Perungudi Toll Plaza
"""
    csv_file = io.BytesIO(sample_csv_text.encode('utf-8'))
    import_res = CommuteService.import_employee_roster_csv(csv_file, contract.id)
    if import_res.get('status') == 'success' and (import_res.get('created_count', 0) + import_res.get('updated_count', 0)) >= 2:
        passed_tests += 1
        print(f"  [PASS] Bulk CSV Importer processed {import_res['total_processed']} employees ({import_res['created_count']} created, {import_res['updated_count']} updated).")
    else:
        print(f"  [FAIL] Bulk CSV Import failed: {import_res}")

    total_tests += 1
    resp_sample = client.get('/commute/bulk-import/sample-csv/')
    if resp_sample.status_code == 200 and 'text/csv' in resp_sample['Content-Type']:
        passed_tests += 1
        print("  [PASS] Downloadable sample CSV roster template endpoint verified.")
    else:
        print(f"  [FAIL] Sample CSV download returned HTTP {resp_sample.status_code}.")

    # =========================================================================
    # TEST 4: Phase 4 — Employee Commute Mobile Web Pass (🅼)
    # =========================================================================
    print("\n--- 4. AUDITING PHASE 4: EMPLOYEE COMMUTE MOBILE WEB PASS (🅼) ---")
    total_tests += 1
    resp_pass = client.get(f'/commute/pass/{bp.pass_token}/')
    if resp_pass.status_code == 200 and 'COMMUTE PASS' in resp_pass.content.decode('utf-8'):
        passed_tests += 1
        print(f"  [PASS] Employee Mobile Web Pass loaded successfully for token {bp.pass_token[:10]}... (HTTP 200).")
    else:
        print(f"  [FAIL] Mobile web pass returned HTTP {resp_pass.status_code}.")

    # =========================================================================
    # TEST 5: Phase 5 — ESG Carbon Sustainability & Driver Behavior Scorecard (🅹)
    # =========================================================================
    print("\n--- 5. AUDITING PHASE 5: ESG SUSTAINABILITY & DRIVER BEHAVIOR (🅹) ---")
    total_tests += 1
    esg_metric, _ = ESGCarbonMetric.objects.get_or_create(
        date=timezone.now().date(),
        vehicle=vehicle,
        defaults={'trip_km': Decimal('120.00'), 'passenger_count': 14, 'fuel_type': 'diesel'}
    )
    esg_summary = CommuteService.compute_fleet_esg_summary()
    if esg_summary.get('total_co2_saved_kg', 0) > 0 and esg_summary.get('green_fleet_score', 0) > 0:
        passed_tests += 1
        print(f"  [PASS] ESG Carbon Metric calculated: {esg_summary['total_co2_saved_kg']} kg CO2 avoided ({esg_summary['trees_equivalent_saved']} trees equivalent).")
    else:
        print(f"  [FAIL] ESG Summary failed: {esg_summary}")

    total_tests += 1
    # Add sample driver log
    DriverBehaviorLog.objects.get_or_create(
        vehicle=vehicle,
        driver=driver,
        event_type='harsh_braking',
        defaults={'severity': 'medium', 'notes': 'Test deceleration'}
    )
    scorecards = CommuteService.compute_driver_safety_scorecards(limit=None)
    target_scorecard = next((s for s in scorecards if s['driver_id'] == driver.id), None)
    if target_scorecard and target_scorecard['safety_index'] <= 100:
        passed_tests += 1
        print(f"  [PASS] Driver Safety Index: {target_scorecard['driver_name']} scored {target_scorecard['safety_index']} pts ({target_scorecard['grade']}).")
    else:
        print(f"  [FAIL] Driver scorecard failed: {target_scorecard}")

    total_tests += 1
    resp_esg = client.get('/commute/esg-scorecard/')
    resp_studio = client.get('/commute/women-safety/')
    if resp_esg.status_code == 200 and resp_studio.status_code == 200:
        passed_tests += 1
        print("  [PASS] Both ESG Scorecard Dashboard & Women Safety Studio HTTP views rendered successfully (HTTP 200).")
    else:
        print(f"  [FAIL] Studio views returned HTTP {resp_esg.status_code} / {resp_studio.status_code}.")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 85)
    print(f"🏆 ALL 5 CORPORATE COMMUTE PHASES RESULTS: {passed_tests} / {total_tests} PASSED ({(passed_tests/total_tests)*100:.1f}%)")
    print("=" * 85)


if __name__ == '__main__':
    run_fleet_commute_5phase_verification()
