import json
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import Vehicle, VehicleType, StaffProfile
from core.depot_scoping import DEPOT_CHENNAI, DEPOT_COIMBATORE
from maintenance.models import (
    ServiceRecord, ServiceReminder, DefectTicket,
    PartInventory, SparePart, SparePartUsageLog,
    VehicleAsset, TireInspectionLog,
    VehicleDamageInspection, VehicleDamageMarker,
    MechanicLaborLog
)
from maintenance.pm_engine import (
    calculate_daily_vehicle_accumulation,
    predict_preventive_service_due,
    get_fleet_predictive_pm_radar,
    auto_schedule_preventive_job_card,
    clock_in_mechanic,
    clock_out_mechanic,
    get_fleet_tire_audit_ledger,
)

User = get_user_model()


class MaintenanceWorkshopEngineTestCase(TestCase):
    """
    Automated Test Suite for Domain 9: Fleet Maintenance, Workshop Job Cards & Predictive PM Sentry.
    Covers:
    1. Real-time daily GPS accumulation rates & commercial fleet baselines.
    2. Predictive PM horizon forecasting, risk tiering, and breakdown risk index.
    3. Executive Predictive PM Radar metrics & 30-day budget projection.
    4. 1-Click Auto-Schedule Job Card creation with bay assignment & parts pre-fill.
    5. Vehicle status grounding to 'maintenance' and restoration to 'available'.
    6. Mechanic bay labor clock-in and clock-out with automatic labor cost calculation.
    7. 2D vehicle damage inspection linkage to job cards.
    8. Fleet tyre audit ledger & wear severity tracking.
    9. REST APIs and Studio Web Views.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='chief_engineer',
            email='engineer@travelerp.com',
            password='Password123!',
            is_staff=True,
            is_superuser=True
        )
        StaffProfile.objects.create(
            user=self.user,
            role='workshop_manager',
            employee_id='ENG-WRK-01',
            branch=DEPOT_CHENNAI
        )
        self.client.force_login(self.user)

        # Vehicle Types
        self.vtype_sedan = VehicleType.objects.create(name='Prime Sedan', seating_capacity=4)
        self.vtype_tempo = VehicleType.objects.create(name='Force Urbania', seating_capacity=17)
        self.vtype_coach = VehicleType.objects.create(name='Volvo B11R Luxury Coach', seating_capacity=49)

        # Vehicles
        self.veh_sedan = Vehicle.objects.create(
            registration_number='TN01-SD-1001',
            brand='Maruti',
            model='Dzire Tour',
            vehicle_type=self.vtype_sedan,
            seating_capacity=4,
            current_km=19800,
            base_depot=DEPOT_CHENNAI,
            status='available'
        )
        self.veh_coach = Vehicle.objects.create(
            registration_number='TN09-VL-9900',
            brand='Volvo',
            model='9600 Multi-Axle',
            vehicle_type=self.vtype_coach,
            seating_capacity=49,
            current_km=119500,
            base_depot=DEPOT_CHENNAI,
            status='available'
        )

        # Store Spares Inventory
        self.oil_item = PartInventory.objects.create(
            part_name='Shell Rimula 15W-40 Diesel Engine Oil (5L)',
            sku='OIL-SH-15W40',
            barcode='EAN-8901112223334',
            category='lubricant_fluid',
            unit_of_measure='liters',
            current_stock=50,
            minimum_stock_level=10,
            default_unit_price=Decimal('1850.00'),
            base_depot=DEPOT_CHENNAI
        )
        self.brake_item = PartInventory.objects.create(
            part_name='Bosch Heavy Commercial Brake Pad Set',
            sku='BRK-BOSCH-HV',
            barcode='EAN-8904445556667',
            category='brakes',
            unit_of_measure='sets',
            current_stock=20,
            minimum_stock_level=5,
            default_unit_price=Decimal('3400.00'),
            base_depot=DEPOT_CHENNAI
        )

        # Tyres
        self.tire_steer = VehicleAsset.objects.create(
            asset_type='tyre',
            serial_number='MICH-STR-001',
            vehicle=self.veh_coach,
            position='front_left',
            brand='Michelin',
            model_or_size='295/80 R22.5',
            original_tread_depth_mm=Decimal('15.00'),
            current_tread_depth_mm=Decimal('2.10'), # CRITICAL
            psi_pressure=115,
            installed_date=date(2025, 1, 1),
            installed_odometer=60000,
            expected_life_km=80000,
            retread_count=0,
            max_retread_cycles=2,
            purchase_price=Decimal('24000.00'),
            status='in_use'
        )

        # Service Reminder
        self.reminder_sedan = ServiceReminder.objects.create(
            vehicle=self.veh_sedan,
            service_task='20,000 KM General Periodic Service',
            interval_km=10000,
            last_service_km=10000, # due at 20000 KM, current 19800 -> 200 KM remaining!
            is_active=True
        )

    def test_01_calculate_daily_vehicle_accumulation_baselines(self):
        """Verifies intelligent daily accumulation rates based on vehicle seating."""
        sedan_rate = calculate_daily_vehicle_accumulation(self.veh_sedan)
        self.assertEqual(sedan_rate, 120.0)

        coach_rate = calculate_daily_vehicle_accumulation(self.veh_coach)
        self.assertEqual(coach_rate, 260.0)

    def test_02_predict_preventive_service_due(self):
        """Verifies predictive horizon, days until due, and risk tier categorization."""
        predictions = predict_preventive_service_due(vehicle_id=self.veh_sedan.id)
        self.assertTrue(len(predictions) >= 1)
        pred = predictions[0]

        # due_km=20000, current=19800 => km_until_due=200, daily_rate=120 => days_until_due = 200/120 = 1 day
        self.assertEqual(pred['vehicle_reg'], 'TN01-SD-1001')
        self.assertEqual(pred['km_until_due'], 200)
        self.assertIn(pred['risk_tier'], ['CRITICAL', 'HIGH'])
        self.assertTrue(pred['days_until_due'] <= 2)
        self.assertIn(pred['status'], ['available', 'maintenance'])

    def test_03_get_fleet_predictive_pm_radar(self):
        """Verifies high-level radar KPIs, budget estimation, and fleet health score."""
        radar = get_fleet_predictive_pm_radar(depot=DEPOT_CHENNAI)
        self.assertTrue(radar['total_scanned'] >= 2)
        self.assertIn('fleet_health_score', radar)
        self.assertTrue(0 <= radar['fleet_health_score'] <= 100)
        self.assertTrue(radar['estimated_budget_30d'] >= 0)
        self.assertTrue(radar['forecast_due_7_days'] >= 1)

    def test_04_auto_schedule_preventive_job_card(self):
        """Tests 1-click scheduling of PM into Job Card, parts auto-recommendation & vehicle grounding."""
        res = auto_schedule_preventive_job_card(
            vehicle_id=self.veh_sedan.id,
            task_name='20,000 KM Engine Oil & Filter Service',
            bay_number='Bay 2',
            mechanic_user=self.user,
            notes='Auto-scheduled via PM Radar'
        )
        self.assertTrue(res['success'])
        self.assertFalse(res['already_exists'])
        job_card_id = res['job_card_id']

        # Verify Job Card created
        jc = ServiceRecord.objects.get(pk=job_card_id)
        self.assertEqual(jc.vehicle, self.veh_sedan)
        self.assertEqual(jc.bay_number, 'Bay 2')
        self.assertEqual(jc.status, 'in_progress')

        # Verify vehicle grounded to 'maintenance'
        self.veh_sedan.refresh_from_db()
        self.assertEqual(self.veh_sedan.status, 'maintenance')

        # Verify idempotent duplicate call
        dup = auto_schedule_preventive_job_card(
            vehicle_id=self.veh_sedan.id,
            task_name='20,000 KM Engine Oil & Filter Service'
        )
        self.assertTrue(dup['success'])
        self.assertTrue(dup['already_exists'])
        self.assertEqual(dup['job_card_id'], job_card_id)

    def test_05_mechanic_labor_clock_in_and_clock_out(self):
        """Tests mechanic bay labor clock-in, clock-out, and auto-cost calculation."""
        jc = ServiceRecord.objects.create(
            vehicle=self.veh_sedan,
            service_type='routine',
            status='in_progress',
            date=timezone.now().date(),
            odometer_reading=19800,
            labor_charges=Decimal('0.00'),
            total_cost=Decimal('0.00')
        )

        # Clock In
        cin = clock_in_mechanic(
            job_card_id=jc.id,
            mechanic_user=self.user,
            mechanic_name='Senior Tech K. Raman',
            task_description='Front caliper overhaul and brake fluid bleed'
        )
        self.assertTrue(cin['success'])
        log_id = cin['labor_log_id']

        log = MechanicLaborLog.objects.get(pk=log_id)
        self.assertTrue(log.is_active)
        self.assertEqual(log.service_record, jc)

        # Simulate time passage: 2.5 hours
        log.clock_in = timezone.now() - timedelta(hours=2, minutes=30)
        log.save(update_fields=['clock_in'])

        # Clock Out
        cout = clock_out_mechanic(labor_log_id=log_id)
        self.assertTrue(cout['success'])
        self.assertEqual(cout['total_hours'], 2.5)
        # 2.5 hours * ₹250/hr = ₹625.00
        self.assertEqual(cout['labor_cost'], 625.0)

        # Check ServiceRecord labor charges and total_cost recalculated
        jc.refresh_from_db()
        self.assertEqual(jc.labor_charges, Decimal('625.00'))
        self.assertEqual(jc.total_cost, Decimal('625.00'))

    def test_06_vehicle_damage_inspection_linkage(self):
        """Verifies damage inspection link to ServiceRecord and display on job card."""
        insp = VehicleDamageInspection.objects.create(
            vehicle=self.veh_sedan,
            customer_name='Trip Handover',
            odometer_reading=19800,
            inspection_type='routine'
        )
        marker = VehicleDamageMarker.objects.create(
            inspection=insp,
            marker_number=1,
            damage_type='scratch',
            severity='minor',
            panel_zone='rear_bumper',
            notes='Scratch near boot release'
        )

        jc = ServiceRecord.objects.create(
            vehicle=self.veh_sedan,
            service_type='bodywork',
            damage_inspection=insp,
            status='in_progress',
            date=timezone.now().date(),
            odometer_reading=19800
        )
        self.assertEqual(jc.damage_inspection, insp)
        self.assertEqual(jc.damage_inspection.markers.count(), 1)

    def test_07_tire_audit_ledger(self):
        """Verifies tyre audit ledger, tread depth threshold flagging, and retread counters."""
        ledger = get_fleet_tire_audit_ledger(depot=DEPOT_CHENNAI)
        self.assertTrue(len(ledger) >= 1)
        tire_entry = next((t for t in ledger if t['serial_number'] == 'MICH-STR-001'), None)
        self.assertIsNotNone(tire_entry)
        self.assertEqual(tire_entry['health_status'], 'critical')
        self.assertEqual(tire_entry['current_tread_depth_mm'], 2.10)
        self.assertEqual(tire_entry['retread_count'], 0)

    def test_08_predictive_pm_web_views_and_rest_apis(self):
        """Verifies HTTP 200 responses and JSON payloads for PM Studio and REST endpoints."""
        # 1. PM Sentry Studio HTML View
        res_studio = self.client.get('/maintenance/pm-sentry/')
        self.assertEqual(res_studio.status_code, 200)
        self.assertContains(res_studio, 'Predictive PM Sentry')
        self.assertContains(res_studio, 'TN01-SD-1001')

        # 2. PM Sentry Forecast JSON API
        res_forecast = self.client.get('/maintenance/api/pm-sentry/forecast/')
        self.assertEqual(res_forecast.status_code, 200)
        data = res_forecast.json()
        self.assertTrue(data['success'])
        self.assertIn('radar', data)
        self.assertIn('forecast', data)

        # 3. Auto-Schedule API
        post_data = {
            'vehicle_id': self.veh_coach.id,
            'task_name': '120,000 KM Annual Major Overhaul',
            'bay_number': 'Bay 1',
            'notes': 'High priority coach servicing'
        }
        res_sched = self.client.post(
            '/maintenance/api/pm-sentry/auto-schedule/',
            data=json.dumps(post_data),
            content_type='application/json'
        )
        self.assertEqual(res_sched.status_code, 200)
        sched_json = res_sched.json()
        self.assertTrue(sched_json['success'])
        self.assertIn('job_card_id', sched_json)

        # 4. Mechanic Clock-In API
        jc_id = sched_json['job_card_id']
        res_clockin = self.client.post(
            f'/maintenance/api/job-card/{jc_id}/clock-in/',
            data=json.dumps({'mechanic_name': 'Chief Mechanic Selvan', 'task_description': 'Major engine diagnostics'}),
            content_type='application/json'
        )
        self.assertEqual(res_clockin.status_code, 200)
        cin_json = res_clockin.json()
        self.assertTrue(cin_json['success'])
        log_id = cin_json['labor_log_id']

        # 5. Mechanic Clock-Out API
        res_clockout = self.client.post(f'/maintenance/api/labor-log/{log_id}/clock-out/')
        self.assertEqual(res_clockout.status_code, 200)
        cout_json = res_clockout.json()
        self.assertTrue(cout_json['success'])

        # 6. Tyre Ledger HTML View
        res_tire_ledger = self.client.get('/maintenance/tire-ledger/')
        self.assertEqual(res_tire_ledger.status_code, 200)
        self.assertContains(res_tire_ledger, 'MICH-STR-001')

        # 7. Tyre Ledger JSON API
        res_tire_api = self.client.get('/maintenance/api/tire-ledger/')
        self.assertEqual(res_tire_api.status_code, 200)
        t_json = res_tire_api.json()
        self.assertTrue(t_json['success'])
        self.assertTrue(t_json['count'] >= 1)

    def test_09_vehicle_status_lifecycle_in_workshop(self):
        """Verifies that grounding in workshop sets status to 'maintenance' and completing job card restores to 'available'."""
        jc = ServiceRecord.objects.create(
            vehicle=self.veh_sedan,
            service_type='routine',
            status='in_progress',
            date=timezone.now().date(),
            odometer_reading=19800
        )
        self.veh_sedan.refresh_from_db()
        self.assertEqual(self.veh_sedan.status, 'maintenance')

        # Complete Job Card
        jc.status = 'completed'
        jc.save()
        self.veh_sedan.refresh_from_db()
        self.assertEqual(self.veh_sedan.status, 'available')
