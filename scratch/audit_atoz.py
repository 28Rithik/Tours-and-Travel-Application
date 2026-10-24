import os
import sys
import traceback
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.contrib import admin
from django.urls import get_resolver
from django.template import loader, TemplateSyntaxError
from django.conf import settings
from django.core.exceptions import PermissionDenied

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def run_atoz_audit():
    print("=" * 80)
    print("SIVAGAYATHIRI TRAVEL ERP - COMPREHENSIVE A-TO-Z AUDIT")
    print("=" * 80)

    # 1. Django System Checks
    print("\n[1/5] Running Django Core System Checks...")
    from django.core.management import call_command
    try:
        call_command('check')
        print("  [PASS] Django Core System Checks PASSED (0 errors).")
    except Exception as e:
        print(f"  [FAIL] Core System Check failed: {e}")
        return False

    # 2. Template Syntax Audit
    print("\n[2/5] Validating All Workspace HTML Templates for Syntax Errors...")
    template_errors = []
    template_dirs = [os.path.join(settings.BASE_DIR, 'templates')]
    
    from django.apps import apps
    base_dir_lower = str(settings.BASE_DIR).lower()
    for app_config in apps.get_app_configs():
        app_path = os.path.abspath(app_config.path)
        if app_path.lower().startswith(base_dir_lower) and '.venv' not in app_path.lower():
            tmpl_dir = os.path.join(app_path, 'templates')
            if os.path.isdir(tmpl_dir):
                template_dirs.append(tmpl_dir)

    checked_templates = 0
    for tdir in template_dirs:
        for root, _, files in os.walk(tdir):
            for file in files:
                if file.endswith('.html'):
                    rel_path = os.path.relpath(os.path.join(root, file), tdir).replace('\\', '/')
                    checked_templates += 1
                    try:
                        loader.get_template(rel_path)
                    except TemplateSyntaxError as tse:
                        template_errors.append((rel_path, str(tse)))
                    except Exception as ex:
                        if "is not a valid tag library" in str(ex) or "Invalid block tag" in str(ex):
                            template_errors.append((rel_path, str(ex)))

    print(f"  Checked {checked_templates} templates.")
    if template_errors:
        print(f"  [FAIL] Found {len(template_errors)} Template Syntax Errors:")
        for tpath, err in template_errors:
            print(f"    - {tpath}: {err}")
    else:
        print("  [PASS] All templates parsed successfully with 0 syntax errors.")

    # 3. Superuser Client Setup
    print("\n[3/5] Initializing Test Client with Superuser Session...")
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser('admin_audit', 'admin@example.com', 'adminpass123')
        print("  Created temporary superuser 'admin_audit'.")
    else:
        print(f"  Using existing superuser: {admin_user.username}")

    client = Client()
    client.force_login(admin_user)

    # 4. Check All Registered Django Admin Changelists & Forms
    print("\n[4/5] Auditing All Django Admin Models & Custom Studios...")
    admin_results = defaultdict(list)
    total_admin_endpoints = 0
    admin_failures = []

    for model, model_admin in admin.site._registry.items():
        opts = model._meta
        app_label = opts.app_label
        model_name = opts.model_name
        
        # Test Changelist
        cl_url = f"/admin/{app_label}/{model_name}/"
        total_admin_endpoints += 1
        try:
            resp = client.get(cl_url, follow=True)
            if resp.status_code >= 400 and resp.status_code != 403: # 403 can be permission-restricted proxy
                admin_failures.append((cl_url, resp.status_code, "HTTP Error"))
            elif resp.status_code == 200:
                admin_results['success'].append(cl_url)
            else:
                admin_results['redirect_or_restricted'].append((cl_url, resp.status_code))
        except PermissionDenied:
            admin_results['redirect_or_restricted'].append((cl_url, 403))
        except Exception as e:
            admin_failures.append((cl_url, 500, f"Exception: {traceback.format_exc()}"))

        # Test Add Form
        add_url = f"/admin/{app_label}/{model_name}/add/"
        total_admin_endpoints += 1
        try:
            resp = client.get(add_url, follow=True)
            if resp.status_code >= 400 and resp.status_code != 403:
                admin_failures.append((add_url, resp.status_code, "HTTP Error"))
            elif resp.status_code == 200:
                admin_results['success'].append(add_url)
            else:
                admin_results['redirect_or_restricted'].append((add_url, resp.status_code))
        except PermissionDenied:
            admin_results['redirect_or_restricted'].append((add_url, 403))
        except Exception as e:
            admin_failures.append((add_url, 500, f"Exception: {traceback.format_exc()}"))

    print(f"  Audited {total_admin_endpoints} Django Admin URLs across {len(admin.site._registry)} models.")
    if admin_failures:
        print(f"  [FAIL] {len(admin_failures)} Django Admin URLs failed:")
        for url, code, msg in admin_failures:
            print(f"    - {url} [{code}]: {msg[:200]}")
    else:
        print(f"  [PASS] All Django Admin changelists and add forms passed with 0 errors!")

    # 5. Dedicated Audit of Every Custom Studio & Operational Route
    custom_studios = [
        # P1 - P8 Studios
        ('/operations/border-permits/', 'P5 Border Permits Sentry'),
        ('/operations/driver-fatigue-sentry/', 'P5 Chauffeur Fatigue Sentry'),
        ('/suppliers/vendor-bill-audit/', 'P6 Vendor Bill Auditor'),
        ('/crm/feedback-reviews/', 'P6 Customer Reviews Hub'),
        ('/operations/breakdown-sos/', 'P7 Highway Breakdown SOS'),
        ('/maintenance/parts-inventory/', 'P7 Workshop Spare Parts'),
        ('/operations/pnr-arrivals/', 'P8 Flight/Train PNR Arrivals'),
        ('/crm/followup-cadence/', 'P8 CRM Follow-up Cadence'),
        ('/finance/tds-194c/', 'P8 Section 194C TDS Ledger'),
        ('/finance/fastag-reconciliation/', 'P4 FASTag Reconciliation Studio'),
        ('/packages/manifest-grid/', 'P4 Passenger Manifest Spreadsheet'),
        ('/finance/fuel-receipt-ocr/', 'P3 Highway Fuel OCR Studio'),
        ('/finance/driver-settlement/', 'P3 Driver Settlement Studio'),
        ('/operations/cash-envelopes/', 'P9 Cash Advance Envelopes'),
        ('/operations/statutory-compliance/', 'P9 Statutory Compliance Sentry'),
        ('/operations/echallan-sentry/', 'P9 E-Challan Sentry'),
        ('/operations/empty-legs/', 'P9 Empty-Leg Marketplace'),
        # Core & Staff Portals
        ('/', 'Public Landing Page'),
        ('/dashboard/', 'Main Operations Dashboard'),
        ('/dispatch/', 'Booking & Dispatch Console'),
        ('/bookings/', 'Bookings Directory'),
        ('/fleet/vehicles/', 'Staff Vehicles Roster'),
        ('/fleet/categories/', 'Vehicle Categories Matrix'),
        ('/fleet/types/', 'Vehicle Types Matrix'),
        ('/fleet/drivers/', 'Staff Drivers Roster'),
        ('/staff/roles-matrix/', 'Staff Roles Matrix'),
        ('/finance/accounting/', 'Accounting & Tally/Zoho Export'),
        ('/finance/gst-studio/', 'GST & NIC E-Way Bill Studio'),
        ('/finance/petty-cash/', 'Petty Cash Float Register'),
        ('/finance/bank-reconciliation/', 'Bank Reconciliation Studio'),
        ('/finance/payments/', 'Payment Gateway Studio'),
        ('/crm/kanban/', 'CRM Leads Kanban Board'),
        ('/maintenance/damage-marker/', 'Damage Marker Studio'),
        ('/maintenance/tire-studio/', 'Tire Health Studio'),
        ('/maintenance/workshop/', 'Workshop Mechanic Studio'),
        ('/operations/fleet-radar/', 'Fleet Live Radar Map'),
        ('/operations/whatsapp-bot/', 'WhatsApp Bot Studio'),
        ('/operations/database-health/', 'Database Health Sentry'),
        ('/packages/', 'Packages Catalog'),
    ]

    print("\n[5/5] Auditing Core Studios & Key Operational Dashboards...")
    studio_failures = []
    for endpoint, name in custom_studios:
        try:
            resp = client.get(endpoint, follow=True)
            if resp.status_code == 200:
                print(f"  [PASS 200 OK] {name} ({endpoint})")
            elif resp.status_code in (301, 302) and resp.redirect_chain:
                print(f"  [PASS {resp.status_code} -> 200] {name} ({endpoint})")
            else:
                studio_failures.append((name, endpoint, resp.status_code, "Unexpected status"))
                print(f"  [FAIL {resp.status_code}] {name} ({endpoint})")
        except Exception as e:
            studio_failures.append((name, endpoint, 500, traceback.format_exc()))
            print(f"  [FAIL 500 CRASH] {name} ({endpoint}):\n{traceback.format_exc()}")

    print("\n" + "=" * 80)
    print("AUDIT SUMMARY:")
    print(f"  - Template Errors: {len(template_errors)}")
    print(f"  - Admin URL Errors: {len(admin_failures)}")
    print(f"  - Studio Errors: {len(studio_failures)}")
    print("=" * 80)

    if not template_errors and not admin_failures and not studio_failures:
        print("\nALL SYSTEMS FUNCTIONING PROPERLY WITH ZERO ERRORS.")
        return True
    else:
        print(f"\nAUDIT COMPLETED WITH ISSUES TO RESOLVE.")
        return False

if __name__ == '__main__':
    run_atoz_audit()
