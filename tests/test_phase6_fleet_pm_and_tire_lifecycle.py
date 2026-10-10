from decimal import Decimal
from datetime import date
import json

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Vehicle, VehicleType
from maintenance.models import (
    VehicleAsset,
    AssetRotationLog,
    TireInspectionLog,
    ServiceReminder,
    DefectTicket,
)
from maintenance.pm_engine import (
    evaluate_fleet_pm_triggers,
    rotate_tire_asset,
    send_tire_for_retread,
    return_tire_from_retread,
    log_tire_inspection,
)


class Phase6FleetPMAndTireLifecycleTestCase(TestCase):
    """
    Comprehensive Automated Test Suite for Phase 6: Fleet Engineering:
    1. VehicleAsset Engineering Properties (Tread Wear %, Critical/Warning Thresholds, Cost-Per-KM)
    2. Tire Physical Inspection Logging & Live Asset Updates
    3. Atomic Tire Rotation & Cross-Axle Swap Logging
    4. Multi-Cycle Retreading Lifecycle & Scrap Constraints
    5. Odometer-Triggered PM Engine Service Auditing & Automated Defect Ticket Creation
    6. Critical Tire Tread Safety Alerting (< 2.5mm legal limit)
    7. 2D Tire Health Studio Web View & Interactive Chassis Schematic JSON API
    8. REST APIs for Inspection, Rotation, Retread, and PM Audit
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='fleet_engineer',
            email='engineer@sivagayathiri.com',
            password='password123'
        )
        self.client.force_login(self.user)

        self.vtype = VehicleType.objects.create(name='Heavy BharatBenz Coach', seating_capacity=45)
        self.vehicle = Vehicle.objects.create(
            registration_number='TN-01-BB-8899',
            brand='BharatBenz',
            model='1624 Glider',
            vehicle_type=self.vtype,
            seating_capacity=45,
            status='available',
            current_km=60000
        )

        # Provision Tyre Assets on Vehicle
        self.tire_fl = VehicleAsset.objects.create(
            asset_type='tyre',
            serial_number='MRF-STEEL-FL-001',
            vehicle=self.vehicle,
            position='front_left',
            installed_date=date(2025, 1, 10),
            installed_odometer=40000,
            expected_life_km=50000,
            status='in_use',
            purchase_price=Decimal('18000.00'),
            brand='MRF',
            model_or_size='295/80 R22.5',
            original_tread_depth_mm=Decimal('15.00'),
            current_tread_depth_mm=Decimal('12.00'),
            psi_pressure=110,
            retread_count=0,
            max_retread_cycles=2
        )

        self.tire_fr = VehicleAsset.objects.create(
            asset_type='tyre',
            serial_number='MRF-STEEL-FR-002',
            vehicle=self.vehicle,
            position='front_right',
            installed_date=date(2025, 1, 10),
            installed_odometer=40000,
            expected_life_km=50000,
            status='in_use',
            purchase_price=Decimal('18000.00'),
            brand='MRF',
            model_or_size='295/80 R22.5',
            original_tread_depth_mm=Decimal('15.00'),
            current_tread_depth_mm=Decimal('11.50'),
            psi_pressure=110,
            retread_count=0,
            max_retread_cycles=2
        )

        self.tire_rlo = VehicleAsset.objects.create(
            asset_type='tyre',
            serial_number='APOLLO-ENDUR-RLO-003',
            vehicle=self.vehicle,
            position='rear_left_outer',
            installed_date=date(2025, 1, 10),
            installed_odometer=40000,
            expected_life_km=50000,
            status='in_use',
            purchase_price=Decimal('17500.00'),
            brand='Apollo',
            model_or_size='295/80 R22.5',
            original_tread_depth_mm=Decimal('15.00'),
            current_tread_depth_mm=Decimal('3.50'),  # Warning level (<= 4.0mm)
            psi_pressure=105,
            retread_count=0,
            max_retread_cycles=2
        )

        self.tire_rro = VehicleAsset.objects.create(
            asset_type='tyre',
            serial_number='APOLLO-ENDUR-RRO-004',
            vehicle=self.vehicle,
            position='rear_right_outer',
            installed_date=date(2025, 1, 10),
            installed_odometer=40000,
            expected_life_km=50000,
            status='in_use',
            purchase_price=Decimal('17500.00'),
            brand='Apollo',
            model_or_size='295/80 R22.5',
            original_tread_depth_mm=Decimal('15.00'),
            current_tread_depth_mm=Decimal('2.10'),  # Critical level (<= 2.5mm)
            psi_pressure=100,
            retread_count=0,
            max_retread_cycles=2
        )

        self.tire_spare = VehicleAsset.objects.create(
            asset_type='tyre',
            serial_number='BRIDGESTONE-SPARE-005',
            vehicle=self.vehicle,
            position='spare',
            installed_date=date(2025, 1, 10),
            installed_odometer=40000,
            expected_life_km=50000,
            status='spare',
            purchase_price=Decimal('19000.00'),
            brand='Bridgestone',
            model_or_size='295/80 R22.5',
            original_tread_depth_mm=Decimal('15.00'),
            current_tread_depth_mm=Decimal('15.00'),
            psi_pressure=115,
            retread_count=0,
            max_retread_cycles=2
        )

    def test_01_vehicle_asset_engineering_properties_and_wear(self):
        """Validates wear %, CPK, warning/critical thresholds, and overall health status."""
        # Tire FL: original 15mm, current 12mm -> 3mm worn / 15mm = 20.0%
        self.assertEqual(self.tire_fl.tread_wear_percent, 20.0)
        self.assertFalse(self.tire_fl.is_critical_tread)
        self.assertFalse(self.tire_fl.is_warning_tread)
        self.assertEqual(self.tire_fl.health_status, 'good')

        # Current run KM: 60000 - 40000 = 20000 KM
        self.assertEqual(self.tire_fl.current_run_km, 20000)
        # Cost per KM: 18000 / 20000 = 0.90 INR/KM
        self.assertEqual(self.tire_fl.cost_per_km, Decimal('0.90'))

        # Rear Left Outer: current 3.5mm -> warning tread (2.5 < td <= 4.0)
        self.assertFalse(self.tire_rlo.is_critical_tread)
        self.assertTrue(self.tire_rlo.is_warning_tread)
        self.assertEqual(self.tire_rlo.health_status, 'warning')

        # Rear Right Outer: current 2.1mm -> critical tread (<= 2.5mm)
        self.assertTrue(self.tire_rro.is_critical_tread)
        self.assertFalse(self.tire_rro.is_warning_tread)
        self.assertEqual(self.tire_rro.health_status, 'critical')

    def test_02_tire_inspection_logging_updates_live_asset(self):
        """Verifies log_tire_inspection() logs record and updates current measurements on asset."""
        res = log_tire_inspection(
            asset_id=self.tire_fl.pk,
            tread_depth_mm=Decimal('10.80'),
            psi_pressure=112,
            odometer=60500,
            inspector_name='Chief Inspector Raman',
            has_irregular_wear=False,
            action_taken='pressure_adjusted',
            notes='Tread healthy, slight pressure boost applied.'
        )

        self.assertEqual(res['status'], 'success')
        self.assertEqual(res['tread_depth_mm'], 10.80)
        self.assertEqual(res['health_status'], 'good')

        # Refresh asset from DB
        self.tire_fl.refresh_from_db()
        self.assertEqual(self.tire_fl.current_tread_depth_mm, Decimal('10.80'))
        self.assertEqual(self.tire_fl.psi_pressure, 112)
        self.assertEqual(self.tire_fl.last_inspected_odometer, 60500)
        self.assertEqual(self.tire_fl.last_inspected_date, timezone.now().date())

        # Check inspection log record created
        log = TireInspectionLog.objects.get(pk=res['log_id'])
        self.assertEqual(log.asset, self.tire_fl)
        self.assertEqual(log.odometer, 60500)
        self.assertEqual(log.inspector_name, 'Chief Inspector Raman')
        self.assertEqual(log.action_taken, 'pressure_adjusted')

    def test_03_tire_rotation_atomic_swap_and_rotation_log(self):
        """Verifies rotating a tyre to an occupied position atomically swaps both tyres and logs entries."""
        # Swap FL ('front_left') with RLO ('rear_left_outer')
        res = rotate_tire_asset(
            asset_id=self.tire_fl.pk,
            to_position='rear_left_outer',
            odometer=61000,
            mechanic_notes='Standard 20k KM axle rotation'
        )

        self.assertEqual(res['status'], 'success')
        self.assertEqual(res['from_position'], 'front_left')
        self.assertEqual(res['to_position'], 'rear_left_outer')
        self.assertEqual(res['swapped_with'], self.tire_rlo.serial_number)

        self.tire_fl.refresh_from_db()
        self.tire_rlo.refresh_from_db()

        self.assertEqual(self.tire_fl.position, 'rear_left_outer')
        self.assertEqual(self.tire_rlo.position, 'front_left')

        # Verify rotation logs
        logs = AssetRotationLog.objects.filter(asset__in=[self.tire_fl, self.tire_rlo])
        self.assertEqual(logs.count(), 2)

    def test_04_tire_retreading_lifecycle_and_constraints(self):
        """Tests sending tyre for retreading, restoring tread on return, and max retread constraints."""
        # 1. Send for retread
        send_res = send_tire_for_retread(
            asset_id=self.tire_rro.pk,
            vendor_name='Madras Rubber Retreaders Ltd',
            notes='Low tread 2.1mm, send for cold process retreading'
        )
        self.assertEqual(send_res['status'], 'success')
        self.assertEqual(send_res['new_status'], 'retreading')
        self.assertEqual(send_res['retread_count'], 1)

        self.tire_rro.refresh_from_db()
        self.assertEqual(self.tire_rro.status, 'retreading')
        self.assertEqual(self.tire_rro.position, '')
        self.assertEqual(self.tire_rro.vendor_name, 'Madras Rubber Retreaders Ltd')

        # 2. Return from retread
        ret_res = return_tire_from_retread(
            asset_id=self.tire_rro.pk,
            new_tread_depth_mm=Decimal('12.50'),
            cost=Decimal('3500.00'),
            notes='Retread completed with new high-mileage pattern'
        )
        self.assertEqual(ret_res['status'], 'success')
        self.assertEqual(ret_res['status_now'], 'spare')
        self.assertEqual(ret_res['restored_tread_depth'], 12.50)

        self.tire_rro.refresh_from_db()
        self.assertEqual(self.tire_rro.status, 'spare')
        self.assertEqual(self.tire_rro.current_tread_depth_mm, Decimal('12.50'))
        self.assertEqual(self.tire_rro.purchase_price, Decimal('21000.00'))  # 17500 + 3500

        # 3. Simulate reaching max retread cycles
        self.tire_rro.retread_count = 2  # max_retread_cycles is 2
        self.tire_rro.save()
        with self.assertRaises(ValueError):
            send_tire_for_retread(asset_id=self.tire_rro.pk)

    def test_05_pm_engine_scheduled_odometer_reminders_and_defect_ticket(self):
        """Tests evaluate_fleet_pm_triggers() flags overdue service reminders and creates DefectTicket."""
        # Create an overdue ServiceReminder: due at 55000 KM, vehicle is at 60000 KM (overdue by 5000 KM)
        reminder = ServiceReminder.objects.create(
            vehicle=self.vehicle,
            service_task="Engine Oil & Filter Replacement (60,000 KM Major PM)",
            last_service_km=45000,
            interval_km=10000,
            is_active=True,
            notes="Use synthetic 15W40 heavy duty lube"
        )

        eval_result = evaluate_fleet_pm_triggers(vehicle_id=self.vehicle.pk, create_tickets=True)
        self.assertGreaterEqual(eval_result['overdue_services_count'], 1)
        self.assertGreaterEqual(eval_result['tickets_created_count'], 1)

        # Defect ticket should have been generated
        ticket = DefectTicket.objects.filter(
            vehicle=self.vehicle,
            reported_by='Fleet PM Engine',
            description__icontains="Engine Oil & Filter Replacement"
        ).first()
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.status, 'open')

        # Re-running evaluation should deduplicate and not recreate duplicate tickets
        eval_result2 = evaluate_fleet_pm_triggers(vehicle_id=self.vehicle.pk, create_tickets=True)
        # Tickets created in second pass for PM should be 0
        pm_tickets_second_run = [t for t in eval_result2['tickets_created'] if t.get('type') == 'pm_service']
        self.assertEqual(len(pm_tickets_second_run), 0)

    def test_06_pm_engine_critical_tire_tread_detection_and_safety_alert(self):
        """Tests that tyre tread <= 2.5mm triggers automated Tire Safety DefectTicket."""
        # Tyre RRO has current_tread_depth_mm = 2.10
        eval_result = evaluate_fleet_pm_triggers(vehicle_id=self.vehicle.pk, create_tickets=True)

        self.assertGreaterEqual(eval_result['critical_tires_count'], 1)
        crit_serials = [t['serial_number'] for t in eval_result['critical_tires']]
        self.assertIn(self.tire_rro.serial_number, crit_serials)

        # Safety ticket created for bald tire
        safety_ticket = DefectTicket.objects.filter(
            vehicle=self.vehicle,
            reported_by='Tire Safety Engine',
            description__icontains=self.tire_rro.serial_number
        ).first()
        self.assertIsNotNone(safety_ticket)
        self.assertIn("critical tread 2.10mm", safety_ticket.description)

    def test_07_tire_studio_template_view_renders(self):
        """Tests HTTP 200 on Tire Studio portal view with context badges."""
        res = self.client.get(reverse('maintenance:tire_studio'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "2D Axle &amp; Tire Health Studio")
        self.assertContains(res, "TN-01-BB-8899")
        self.assertContains(res, "MRF-STEEL-FL-001")

        # Test with vehicle_id filter parameter
        res_filtered = self.client.get(reverse('maintenance:tire_studio') + f"?vehicle_id={self.vehicle.pk}")
        self.assertEqual(res_filtered.status_code, 200)

    def test_08_api_vehicle_tire_schematic_endpoint(self):
        """Tests /maintenance/api/tire-schematic/<id>/ returns JSON chassis mapping."""
        url = reverse('maintenance:api_tire_schematic', kwargs={'vehicle_id': self.vehicle.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['vehicle']['registration'], 'TN-01-BB-8899')
        self.assertEqual(data['total_tires'], 5)

        positions = [t['position'] for t in data['tires']]
        self.assertIn('front_left', positions)
        self.assertIn('front_right', positions)
        self.assertIn('rear_left_outer', positions)
        self.assertIn('rear_right_outer', positions)
        self.assertIn('spare', positions)

    def test_09_rest_apis_inspect_rotate_retread_evaluate(self):
        """Tests JSON REST endpoints for tire inspection, rotation, retreading, and PM audit."""
        # 1. API Inspect
        inspect_payload = {
            'asset_id': self.tire_fl.pk,
            'tread_depth_mm': '11.20',
            'psi_pressure': 108,
            'odometer': 60100,
            'inspector_name': 'Station Technician',
            'action_taken': 'none',
            'notes': 'Normal wear pattern'
        }
        res_insp = self.client.post(
            reverse('maintenance:api_tire_inspect'),
            data=json.dumps(inspect_payload),
            content_type='application/json'
        )
        self.assertEqual(res_insp.status_code, 200)
        self.assertEqual(res_insp.json()['status'], 'success')

        # 2. API Rotate
        rotate_payload = {
            'asset_id': self.tire_fl.pk,
            'to_position': 'spare',
            'odometer': 60200,
            'notes': 'Rotated into spare slot'
        }
        res_rot = self.client.post(
            reverse('maintenance:api_tire_rotate'),
            data=json.dumps(rotate_payload),
            content_type='application/json'
        )
        self.assertEqual(res_rot.status_code, 200)
        self.assertEqual(res_rot.json()['status'], 'success')
        self.assertEqual(res_rot.json()['to_position'], 'spare')

        # 3. API Retread Send
        retread_send_payload = {
            'action': 'send',
            'asset_id': self.tire_rlo.pk,
            'vendor_name': 'Tyre Care Hub',
            'notes': 'Sending for precision cold recap'
        }
        res_ret_send = self.client.post(
            reverse('maintenance:api_tire_retread'),
            data=json.dumps(retread_send_payload),
            content_type='application/json'
        )
        self.assertEqual(res_ret_send.status_code, 200)
        self.assertEqual(res_ret_send.json()['status'], 'success')
        self.assertEqual(res_ret_send.json()['new_status'], 'retreading')

        # 4. API Retread Return
        retread_ret_payload = {
            'action': 'return',
            'asset_id': self.tire_rlo.pk,
            'new_tread_depth_mm': '11.00',
            'cost': '3200.00',
            'notes': 'Successfully recapped'
        }
        res_ret_return = self.client.post(
            reverse('maintenance:api_tire_retread'),
            data=json.dumps(retread_ret_payload),
            content_type='application/json'
        )
        self.assertEqual(res_ret_return.status_code, 200)
        self.assertEqual(res_ret_return.json()['status'], 'success')
        self.assertEqual(res_ret_return.json()['status_now'], 'spare')

        # 5. API PM Engine Evaluate
        res_pm = self.client.post(
            reverse('maintenance:api_pm_engine_evaluate'),
            data={'vehicle_id': self.vehicle.pk}
        )
        self.assertEqual(res_pm.status_code, 200)
        self.assertIn('fleet_health_score', res_pm.json())
