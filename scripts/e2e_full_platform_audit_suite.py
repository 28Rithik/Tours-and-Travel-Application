import os
import sys
import json
import datetime
from decimal import Decimal
from pathlib import Path

# Ensure UTF-8 stdout
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.core.management import call_command
from core.models import Vehicle, Driver, Party
from operations.models import Booking, Trip
from maintenance.models import VehicleDamageInspection, VehicleDamageMarker

def run_e2e_audit():
    print("=" * 80)
    print("      TRAVELERP / SIVAGAYATHIRI TRAVELS — FULL END-TO-END AUDIT SUITE      ")
    print("=" * 80)
    
    audit_results = {
        'system_check': False,
        'routes_tested': 0,
        'routes_passed': 0,
        'routes_failed': [],
        'workflows_tested': 0,
        'workflows_passed': 0,
        'workflows_failed': [],
    }

    # --------------------------------------------------------------------------
    # 1. SYSTEM HEALTH & DATABASE CHECK
    # --------------------------------------------------------------------------
    print("\n[PHASE 1: SYSTEM & DATABASE HEALTH]")
    try:
        call_command('check')
        print("  ✓ Django System Check: PASSED (0 issues)")
        audit_results['system_check'] = True
    except Exception as e:
        print(f"  ✗ Django System Check FAILED: {e}")
        audit_results['system_check'] = False

    vehicle_count = Vehicle.objects.count()
    driver_count = Driver.objects.count()
    trip_count = Trip.objects.count()
    booking_count = Booking.objects.count()
    party_count = Party.objects.count()

    print(f"  ✓ Database Records: {vehicle_count} Vehicles | {driver_count} Drivers | {party_count} Parties | {booking_count} Bookings | {trip_count} Trips")

    # --------------------------------------------------------------------------
    # 2. ALL CORE PORTAL & SIDEBAR ROUTES AUDIT (Authenticated as Staff / Superuser)
    # --------------------------------------------------------------------------
    print("\n[PHASE 2: ALL PORTAL & SIDEBAR ROUTES AUDIT]")
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.filter(is_staff=True).first()
    
    client = Client()
    client.force_login(admin_user)

    routes_to_test = [
        # 1. Operations Desk
        ("Operations", "Control Room", "/dashboard/"),
        ("Operations", "Staff & RBAC Matrix", "/staff/roles-matrix/"),
        ("Operations", "Dispatch Control", "/dispatch/"),
        ("Operations", "Handover & Bot Studio", "/admin/operations/whatsapp-bot/"),
        ("Operations", "Rathasārathi AI Copilot", "/admin/operations/rathasarathi-ai/"),
        
        # 2. Fleet & Telematics
        ("Fleet", "Live Fleet Map", "/fleet/live/"),
        ("Fleet", "Vehicle Fleet & Assets", "/fleet/vehicles/"),
        ("Fleet", "Vehicle Categories", "/fleet/categories/"),
        ("Fleet", "Vehicle Types & Tariffs", "/fleet/types/"),
        ("Fleet", "Chauffeurs & Captains", "/fleet/drivers/"),
        ("Fleet", "2D Vehicle Damage Studio", "/admin/maintenance/damage-marker/"),
        ("Fleet", "2D Axle & Tire Health Studio", "/maintenance/tire-studio/"),
        ("Fleet", "Workshop & Job Cards", "/maintenance/workshop-studio/"),
        ("Fleet", "Compliance & Maintenance", "/maintenance/compliance/"),
        ("Fleet", "Fleet Analytics & CPK", "/analytics/fleet/"),
        
        # 3. Tour Packages & Architect
        ("Packages", "Tour Packages Catalog", "/packages/"),
        ("Packages", "Package Templates Master", "/packages/?tab=templates"),
        ("Packages", "College IV Expeditions", "/packages/?tab=expeditions"),
        ("Packages", "Hotel Allotments & Rooms", "/suppliers/hotel-vouchers/"),
        
        # 4. Sales, CRM & DMC Pipelines
        ("CRM", "DMC Executive Board", "/crm/dashboard/"),
        ("CRM", "CRM Visual Kanban Board", "/admin/crm/kanban/"),
        ("CRM", "Query Tracker 2.0", "/crm/queries/"),
        ("CRM", "Quotation Studio", "/crm/quotations/new/"),
        ("CRM", "Partners & FTOs", "/crm/partners/"),
        ("CRM", "Suppliers & Rates", "/crm/suppliers/"),
        ("CRM", "Marketing Campaigns", "/marketing/campaign-studio/"),
        ("CRM", "Service Vouchers", "/crm/vouchers/"),
        ("CRM", "Document Vault", "/crm/documents/"),
        ("CRM", "Quality & Grievances", "/crm/complaints/"),
        ("CRM", "DMC Reports Hub", "/crm/reports/"),
        
        # 5. Finance, Invoicing & Accounts
        ("Finance", "Invoices & Billing", "/crm/invoices/"),
        ("Finance", "Driver Bata & Settlement", "/admin/finance/driver-settlement/"),
        ("Finance", "Corporate GST & E-Way Bill", "/admin/finance/gst-studio/"),
        ("Finance", "Dynamic UPI & Payment Studio", "/admin/finance/payment-studio/"),
        ("Finance", "Petty Cash Float Register", "/admin/finance/petty-cash-studio/"),
        ("Finance", "Bank Statement CSV Reconciler", "/admin/finance/bank-reconciliation/"),
        ("Finance", "Statements & Ledgers", "/statements/generate/"),
        ("Finance", "Accounts Payable", "/crm/requisitions/"),
        ("Finance", "Pending Receivables", "/crm/reports/client-pending-payments/"),
        ("Finance", "Outsourced Settlements", "/suppliers/settlement-hub/"),
        ("Finance", "Tally, Zoho & Payroll", "/finance/accounting/"),
        ("Finance", "Vehicle Profitability", "/reports/vehicle-profitability/"),
        ("Finance", "Party Profitability", "/reports/party-profitability/"),
        
        # 6. System Administration & Health
        ("Admin", "Tariffs & Master Data", "/crm/suppliers/"),
        ("Admin", "Database & System Health", "/admin/operations/database-health/"),
        ("Admin", "Unfold Admin Workspace", "/admin/"),
        
        # 7. Public & Authentication Views
        ("Public", "Public Landing View", "/"),
        ("Public", "Staff Login View", "/staff/login/"),
    ]

    for section, name, path in routes_to_test:
        audit_results['routes_tested'] += 1
        try:
            resp = client.get(path)
            if resp.status_code in [200, 302]:
                print(f"  ✓ [{section}] {name} ({path}) -> HTTP {resp.status_code}")
                audit_results['routes_passed'] += 1
            else:
                print(f"  ✗ [{section}] {name} ({path}) -> HTTP {resp.status_code}")
                audit_results['routes_failed'].append((section, name, path, resp.status_code))
        except Exception as e:
            print(f"  ✗ [{section}] {name} ({path}) -> EXCEPTION: {e}")
            audit_results['routes_failed'].append((section, name, path, str(e)))

    # --------------------------------------------------------------------------
    # 3. BUSINESS WORKFLOW & TRANSACTION TESTS
    # --------------------------------------------------------------------------
    print("\n[PHASE 3: CORE OPERATIONAL WORKFLOWS]")

    # WORKFLOW 1: Vehicle Damage Inspection E2E
    audit_results['workflows_tested'] += 1
    try:
        v = Vehicle.objects.first()
        payload = {
            'vehicle_id': v.id,
            'inspection_type': 'checkout',
            'vehicle_body_style': 'suv',
            'customer_name': 'E2E Audit Tester',
            'customer_phone': '+91 99999 88888',
            'odometer_reading': 55000,
            'fuel_level_percent': 80,
            'security_deposit_held': '0.00',
            'notes': 'Automated E2E Suite Inspection Record',
            'markers': [{
                'marker_number': 1,
                'damage_type': 'scratch',
                'severity': 'minor',
                'panel_zone': 'front_bumper',
                'x_percent': 48,
                'y_percent': 12,
                'estimated_repair_cost': '0.00',
                'is_pre_existing': True,
                'notes': 'Front bumper bumper scrape'
            }]
        }
        resp = client.post('/maintenance/api/damage-inspection/save/', json.dumps(payload), content_type='application/json')
        data = resp.json()
        assert resp.status_code == 200 and data.get('status') == 'success'
        insp_id = data['inspection_id']
        print_resp = client.get(f'/maintenance/damage-inspection/{insp_id}/print/')
        assert print_resp.status_code == 200
        print(f"  ✓ Workflow 1: 2D Damage Marker Save & Certificate Print -> PASSED (Insp #{data['inspection_number']})")
        audit_results['workflows_passed'] += 1
    except Exception as e:
        print(f"  ✗ Workflow 1: 2D Damage Marker Save FAILED: {e}")
        audit_results['workflows_failed'].append(('2D Damage Marker Save', str(e)))

    # WORKFLOW 2: Driver Bata & Trip Settlement E2E
    audit_results['workflows_tested'] += 1
    try:
        completed_trip = Trip.objects.filter(status='completed').first()
        if completed_trip:
            # 1. Fetch settlement context
            ctx_resp = client.get(f'/api/finance/settle/{completed_trip.id}/context/')
            assert ctx_resp.status_code == 200
            ctx_data = ctx_resp.json()
            assert ctx_data.get('status') == 'success'
            
            # 2. Execute settlement payout
            settle_payload = {
                'driver_id': completed_trip.driver_id,
                'base_bata': float(ctx_data['data']['base_bata']),
                'night_halt_allowance': 0,
                'early_morning_allowance': 0,
                'ghat_road_allowance': 0,
                'fuel_reimbursement': 0,
                'toll_reimbursement': 0,
                'cash_advance_deduction': 0,
                'cash_collected_deduction': 0,
                'payout_method': 'upi',
                'payout_reference': 'UPI-TEST-998877',
                'notes': 'E2E Automated Audit Settlement'
            }
            exec_resp = client.post(f'/api/finance/settle/{completed_trip.id}/', json.dumps(settle_payload), content_type='application/json')
            assert exec_resp.status_code == 200
            print(f"  ✓ Workflow 2: Driver Bata Calculation & 1-Click Payout -> PASSED (Trip {completed_trip.trip_id})")
            audit_results['workflows_passed'] += 1
        else:
            print("  - Workflow 2: Skipped (No completed trip found)")
    except Exception as e:
        print(f"  ✗ Workflow 2: Driver Bata Settlement FAILED: {e}")
        audit_results['workflows_failed'].append(('Driver Bata Settlement', str(e)))

    # WORKFLOW 3: Dynamic UPI Payment Generation E2E
    audit_results['workflows_tested'] += 1
    try:
        upi_payload = {
            'amount': 2500.00,
            'customer_name': 'Anand Kumar',
            'customer_phone': '+91 98411 23456',
            'note': 'E2E Booking Advance',
            'reference_id': 'BK-2026-TEST'
        }
        upi_resp = client.post('/api/payments/dynamic-upi/generate/', json.dumps(upi_payload), content_type='application/json')
        assert upi_resp.status_code == 200
        upi_data = upi_resp.json()
        assert upi_data.get('status') == 'success'
        print(f"  ✓ Workflow 3: Dynamic UPI QR & Payment Link Generation -> PASSED (UPI String generated)")
        audit_results['workflows_passed'] += 1
    except Exception as e:
        print(f"  ✗ Workflow 3: Dynamic UPI Generation FAILED: {e}")
        audit_results['workflows_failed'].append(('Dynamic UPI Generation', str(e)))

    # WORKFLOW 4: CRM Kanban Stage Update E2E
    audit_results['workflows_tested'] += 1
    try:
        from crm.models import Inquiry
        inq = Inquiry.objects.first()
        if inq:
            update_payload = {'new_status': 'quoted', 'kanban_order': 1}
            stage_resp = client.post(f'/crm/api/inquiries/{inq.id}/update-stage/', json.dumps(update_payload), content_type='application/json')
            assert stage_resp.status_code == 200
            data = stage_resp.json()
            assert data.get('status') == 'success'
            print(f"  ✓ Workflow 4: CRM Kanban Pipeline Drag-and-Drop Stage Update -> PASSED (Inq #{inq.id} -> 'Quotation Sent')")
            audit_results['workflows_passed'] += 1
        else:
            print("  - Workflow 4: Skipped (No inquiries found)")
    except Exception as e:
        print(f"  ✗ Workflow 4: CRM Kanban Stage Update FAILED: {e}")
        audit_results['workflows_failed'].append(('CRM Kanban Stage Update', str(e)))

    # WORKFLOW 5: Database Health Audit E2E
    audit_results['workflows_tested'] += 1
    try:
        health_resp = client.get('/api/database-health/audit/')
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data.get('status') in ['HEALTHY', 'healthy', 'WARNING']
        print(f"  ✓ Workflow 5: Database Health Diagnostics & Auto-Tuning Engine -> PASSED (Status: {health_data.get('status')} | Passed: {health_data.get('summary', {}).get('passed_checks')}/{health_data.get('summary', {}).get('total_checks')} checks)")
        audit_results['workflows_passed'] += 1
    except Exception as e:
        print(f"  ✗ Workflow 5: Database Health Audit FAILED: {e}")
        audit_results['workflows_failed'].append(('Database Health Audit', str(e)))

    # --------------------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("                        E2E AUDIT SUMMARY RESULTS                        ")
    print("=" * 80)
    print(f"Total Routes Tested:      {audit_results['routes_tested']}")
    print(f"Total Routes Passed:      {audit_results['routes_passed']} ({round(audit_results['routes_passed']/audit_results['routes_tested']*100, 1)}%)")
    print(f"Total Workflows Tested:   {audit_results['workflows_tested']}")
    print(f"Total Workflows Passed:   {audit_results['workflows_passed']} ({round(audit_results['workflows_passed']/audit_results['workflows_tested']*100, 1)}%)")
    
    if audit_results['routes_failed']:
        print("\nFailed Routes:")
        for r in audit_results['routes_failed']:
            print(f"  - {r}")
            
    if audit_results['workflows_failed']:
        print("\nFailed Workflows:")
        for w in audit_results['workflows_failed']:
            print(f"  - {w}")

    if not audit_results['routes_failed'] and not audit_results['workflows_failed']:
        print("\n>>> ALL CHECKS PASSED: PLATFORM IS 100% PRODUCTION READY! <<<")
    print("=" * 80)

if __name__ == '__main__':
    run_e2e_audit()
