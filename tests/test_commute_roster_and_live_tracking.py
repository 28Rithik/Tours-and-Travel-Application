import datetime
from decimal import Decimal
import json

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse

from core.models import Client as CoreClient, VehicleType, Driver, Vehicle
from fleet_contracts.models import (
    TransportContract,
    Route,
    RouteStop,
    Shift,
    ContractFleetRoster,
    ContractTripLog,
    ContractSLAPenalty,
    ContractMonthlyInvoice,
    CommuterManifest,
)
from fleet_commute.models import CommuterBoardingPass
from fleet_commute.roster_dispatch_engine import RosterDispatchEngine
from fleet_contracts.sla_engine import SLAEngine
from maintenance.models import PreTripInspectionChecklist


class CommuteRosterAndLiveTrackingTests(TestCase):
    """
    Comprehensive End-to-End Test Suite for Part 1:
    The 300+ Vehicle School & Employee Commute Automation:
    1. Automated Batch Daily Roster Dispatch Engine
    2. Pre-flight Statutory Compliance Gate & Standby Vehicle Swap
    3. Parent & Employee Live Bus Tracking Portal & Telematics API
    4. Corporate SLA Performance & Penalty Deductions Engine
    5. Driver Morning Pre-Shift "Fit-to-Drive" & Sobriety Breathalyzer Gate
    """

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='commute_dispatcher',
            email='dispatcher@sivagayathiri.in',
            password='Password@123'
        )
        self.client.force_login(self.admin_user)

        self.today = timezone.now().date()
        self.future_date = self.today + datetime.timedelta(days=365)
        self.past_date = self.today - datetime.timedelta(days=30)

        # 1. Master Customer & Contract
        self.corporate_client = CoreClient.objects.create(
            name='Robert Bosch Engineering & Business Solutions',
            phone='04222223344',
            email='transport@bosch.com'
        )

        self.contract = TransportContract.objects.create(
            name='Bosch CHIL SEZ Campus Employee Transport 2026-27',
            customer=self.corporate_client,
            contract_category='corporate',
            start_date=self.past_date,
            end_date=self.future_date,
            status='active',
            billing_model='per_trip',
            default_rate=Decimal('2200.00'),
            committed_vehicle_count=50,
            standby_vehicle_count=5,
            sla_penalty_cap_pct=Decimal('10.00')
        )

        # 2. Route & Stops
        self.route = Route.objects.create(
            contract=self.contract,
            name='Route 14: Gandhipuram to Keeranatham IT Park',
            origin='Gandhipuram Bus Stand',
            destination='Bosch Keeranatham Campus',
            distance_km=18,
            estimated_travel_minutes=45,
            is_active=True
        )

        self.stop1 = RouteStop.objects.create(
            route=self.route,
            stop_order=1,
            name='Gandhipuram Central Depot',
            scheduled_offset_minutes=0
        )
        self.stop2 = RouteStop.objects.create(
            route=self.route,
            stop_order=2,
            name='Saravanampatti Checkpost',
            scheduled_offset_minutes=25
        )
        self.stop3 = RouteStop.objects.create(
            route=self.route,
            stop_order=3,
            name='Bosch Campus Gate 2',
            scheduled_offset_minutes=45
        )

        # 3. Shifts (Morning Pickup & Evening Drop)
        self.morning_shift = Shift.objects.create(
            route=self.route,
            shift_name='Morning General Shift Login',
            direction='pickup',
            timing=datetime.time(7, 0),
            days_of_week='All 7 Days',
            grace_period_minutes=10
        )

        self.evening_shift = Shift.objects.create(
            route=self.route,
            shift_name='Evening General Shift Logout',
            direction='drop',
            timing=datetime.time(17, 30),
            days_of_week='All 7 Days',
            grace_period_minutes=10
        )

        # 4. Fleet Vehicles & Crew
        self.v_type = VehicleType.objects.create(
            name='Force Traveller 3350 AC (17 Seater)',
            seating_capacity=17,
            default_day_rate=Decimal('4500.00'),
            default_km_rate=Decimal('22.00')
        )

        self.primary_vehicle = Vehicle.objects.create(
            registration_number='TN-38-BZ-4819',
            vehicle_type=self.v_type,
            status='available',
            current_km=84500,
            fc_expiry=self.today + datetime.timedelta(days=180),
            insurance_expiry=self.today + datetime.timedelta(days=180)
        )

        self.standby_vehicle = Vehicle.objects.create(
            registration_number='TN-38-SB-9900',
            vehicle_type=self.v_type,
            status='available',
            current_km=42000,
            fc_expiry=self.today + datetime.timedelta(days=240),
            insurance_expiry=self.today + datetime.timedelta(days=240)
        )

        self.driver = Driver.objects.create(
            name='Captain Selvakumar M',
            phone='9840155667',
            status='active',
            license_validity_tr=self.today + datetime.timedelta(days=365)
        )

        # 5. Master Roster Allocation
        self.roster = ContractFleetRoster.objects.create(
            contract=self.contract,
            route=self.route,
            primary_vehicle=self.primary_vehicle,
            primary_driver=self.driver,
            standby_vehicle=self.standby_vehicle,
            start_date=self.past_date,
            is_active=True
        )

        # 6. Commuter Manifest Passengers
        self.commuter1 = CommuterManifest.objects.create(
            contract=self.contract,
            commuter_id='BOSCH-EMP-401',
            name='Deepika Ramaswamy',
            gender='female',
            phone='9840122334',
            boarding_stop=self.stop2,
            is_active=True
        )

        self.commuter2 = CommuterManifest.objects.create(
            contract=self.contract,
            commuter_id='BOSCH-EMP-402',
            name='Kavitha Natarajan',
            gender='female',
            phone='9840133445',
            boarding_stop=self.stop1,
            is_active=True
        )

    # --------------------------------------------------------------------------
    # Test 1: Batch Daily Roster Dispatch Engine
    # --------------------------------------------------------------------------
    def test_01_execute_batch_roster_dispatch(self):
        """Verify 1-click batch engine creates trips and commuter boarding passes for the date."""
        result = RosterDispatchEngine.execute_batch_roster_dispatch(
            target_date=self.today,
            contract_id=self.contract.id,
            force_refresh=True
        )

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['trips_created'], 2) # morning + evening
        self.assertGreaterEqual(result['passes_created'], 4) # 2 commuters * 2 shifts
        self.assertEqual(result['roster_gaps_count'], 0)

        # Verify ContractTripLog records
        logs = ContractTripLog.objects.filter(date=self.today, shift__route=self.route)
        self.assertEqual(logs.count(), 2)

        morning_log = logs.filter(shift=self.morning_shift).first()
        self.assertIsNotNone(morning_log)
        self.assertEqual(morning_log.vehicle, self.primary_vehicle)
        self.assertEqual(morning_log.driver, self.driver)
        self.assertEqual(morning_log.passenger_count, 2)
        self.assertEqual(morning_log.status, 'scheduled')

        # Verify Boarding Pass created
        bp = CommuterBoardingPass.objects.filter(commuter=self.commuter1, date=self.today).first()
        self.assertIsNotNone(bp)
        self.assertTrue(len(bp.pass_token) >= 24)
        self.assertTrue(len(bp.boarding_otp) == 4)

    # --------------------------------------------------------------------------
    # Test 2: Statutory Compliance Gate & Standby Vehicle Swap
    # --------------------------------------------------------------------------
    def test_02_compliance_gate_auto_swaps_standby_vehicle(self):
        """Verify expired FC on primary vehicle triggers automatic standby substitution."""
        # Expire primary vehicle fitness certificate
        self.primary_vehicle.fc_expiry = self.today - datetime.timedelta(days=5)
        self.primary_vehicle.save(update_fields=['fc_expiry'])

        result = RosterDispatchEngine.execute_batch_roster_dispatch(
            target_date=self.today,
            contract_id=self.contract.id,
            force_refresh=True
        )

        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['compliance_substitutions']), 2) # 2 shifts swapped

        # Verify trip logs assigned standby vehicle
        logs = ContractTripLog.objects.filter(date=self.today, shift__route=self.route)
        for log in logs:
            self.assertEqual(log.vehicle, self.standby_vehicle)
            self.assertTrue(log.is_replacement_vehicle)
            self.assertEqual(log.replaced_vehicle, self.primary_vehicle)

    # --------------------------------------------------------------------------
    # Test 3: Parent & Employee Real-Time Live Bus Tracking Portal & Telematics API
    # --------------------------------------------------------------------------
    def test_03_parent_live_bus_tracking_and_api(self):
        """Verify public zero-login tracking portal renders live bus position and JSON telemetry."""
        # Create a boarding pass and trip log
        log = ContractTripLog.objects.create(
            shift=self.morning_shift,
            date=self.today,
            vehicle=self.primary_vehicle,
            driver=self.driver,
            status='en_route'
        )
        bp = CommuterBoardingPass.objects.create(
            commuter=self.commuter1,
            trip_log=log,
            shift=self.morning_shift,
            date=self.today
        )

        # 1. Test HTML Tracking Portal
        tracking_url = reverse('fleet_commute:parent_live_bus_tracking', kwargs={'pass_token': bp.pass_token})
        resp = self.client.get(tracking_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Deepika Ramaswamy')
        self.assertContains(resp, 'TN-38-BZ-4819')
        self.assertContains(resp, 'Captain Selvakumar M')
        self.assertContains(resp, 'LIVE RADAR')

        # 2. Test JSON Telematics Polling Endpoint
        api_url = reverse('fleet_commute:api_commute_live_bus_telematics', kwargs={'pass_token': bp.pass_token})
        api_resp = self.client.get(api_url)
        self.assertEqual(api_resp.status_code, 200)

        data = json.loads(api_resp.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['trip_status'], 'en_route')
        self.assertEqual(data['vehicle_number'], 'TN-38-BZ-4819')
        self.assertIn('latitude', data)
        self.assertIn('longitude', data)
        self.assertIn('speed_kmh', data)
        self.assertIn('eta_minutes', data)

    # --------------------------------------------------------------------------
    # Test 4: Corporate SLA Delay Calculation & Invoice Deduction
    # --------------------------------------------------------------------------
    def test_04_sla_delay_detection_and_monthly_invoice_deduction(self):
        """Verify late arrival > grace period triggers ContractSLAPenalty and deducts from monthly invoice."""
        # Trip scheduled at 07:00 AM, arrived at 07:35 AM (delay = 35m, grace = 10m -> breach = 25m)
        log = ContractTripLog.objects.create(
            shift=self.morning_shift,
            date=self.today,
            vehicle=self.primary_vehicle,
            driver=self.driver,
            status='delayed',
            scheduled_departure_time=datetime.time(7, 0),
            actual_arrival_time=datetime.time(7, 35)
        )

        # Run SLA evaluation
        eval_res = SLAEngine.evaluate_trip_sla(log, auto_record_penalty=True)
        self.assertTrue(eval_res['is_breach'])
        self.assertEqual(eval_res['delay_minutes'], 35)
        self.assertEqual(Decimal(str(eval_res['penalty_amount'])), Decimal('500.00')) # major delay slab

        # Verify ContractSLAPenalty persisted
        penalty = ContractSLAPenalty.objects.filter(trip_log=log).first()
        self.assertIsNotNone(penalty)
        self.assertEqual(penalty.penalty_amount, Decimal('500.00'))
        self.assertFalse(penalty.waived)

        # Test Monthly Invoice Binding & SLA Deduction
        invoice = ContractMonthlyInvoice.objects.create(
            contract=self.contract,
            invoice_number='INV-BOSCH-2026-09-001',
            billing_month=self.today.replace(day=1),
            from_date=self.today - datetime.timedelta(days=15),
            to_date=self.today + datetime.timedelta(days=15),
            base_contract_amount=Decimal('44000.00'), # 20 trips * 2200
            status='draft'
        )

        deducted = SLAEngine.apply_penalties_to_invoice(invoice)
        self.assertEqual(deducted, Decimal('500.00'))
        invoice.refresh_from_db()
        self.assertEqual(invoice.sla_penalty_deduction, Decimal('500.00'))
        self.assertEqual(invoice.net_taxable_amount, Decimal('43500.00')) # 44000 - 500

    # --------------------------------------------------------------------------
    # Test 5: Driver Morning Pre-Shift "Fit-to-Drive" Sobriety Gate
    # --------------------------------------------------------------------------
    def test_05_driver_pre_shift_safety_gate(self):
        """Verify breathalyzer alcohol level or fatigue blocks trip dispatch, while clean pass clears trip to en_route."""
        log = ContractTripLog.objects.create(
            shift=self.morning_shift,
            date=self.today,
            vehicle=self.primary_vehicle,
            driver=self.driver,
            status='scheduled'
        )

        url = reverse('fleet_commute:api_driver_pre_shift_safety_gate')

        # 1. Test Failed Sobriety Check (Alcohol Level > 0.00)
        failed_payload = {
            'trip_log_id': log.id,
            'driver_id': self.driver.id,
            'odometer': 84520,
            'breathalyzer_passed': False,
            'blood_alcohol_content': '0.04',
            'rest_hours_declared': 8,
            'brakes_functional': True
        }

        resp_fail = self.client.post(url, data=json.dumps(failed_payload), content_type='application/json')
        self.assertEqual(resp_fail.status_code, 400)
        fail_data = json.loads(resp_fail.content)
        self.assertFalse(fail_data['fit_to_drive'])
        self.assertIn('VEHICLE GROUNDED', fail_data['message'])

        log.refresh_from_db()
        self.assertEqual(log.status, 'delayed')

        # 2. Test Successful Fit-to-Drive Check (BAC = 0.00, Rest = 8 hrs)
        pass_payload = {
            'trip_log_id': log.id,
            'driver_id': self.driver.id,
            'odometer': 84520,
            'breathalyzer_passed': True,
            'blood_alcohol_content': '0.00',
            'rest_hours_declared': 8,
            'brakes_functional': True,
            'first_aid_kit_present': True,
            'fire_extinguisher_present': True
        }

        resp_pass = self.client.post(url, data=json.dumps(pass_payload), content_type='application/json')
        self.assertEqual(resp_pass.status_code, 200)
        pass_data = json.loads(resp_pass.content)
        self.assertTrue(pass_data['fit_to_drive'])
        self.assertEqual(pass_data['trip_status'], 'en_route')

        log.refresh_from_db()
        self.assertEqual(log.status, 'en_route')
        self.assertIsNotNone(log.actual_departure_time)

        # Verify PreTripInspectionChecklist recorded
        insp = PreTripInspectionChecklist.objects.filter(contract_trip=log, overall_status='passed').first()
        self.assertIsNotNone(insp)
        self.assertTrue(insp.brakes_functional)
