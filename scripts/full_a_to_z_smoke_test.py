import os
import sys
import time
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
django.setup()

from django.test import Client, RequestFactory
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import reverse
from unfold.admin import ModelAdmin as UnfoldModelAdmin

User = get_user_model()


def run_full_a_to_z_smoke_test():
    start_total_time = time.time()
    print("=" * 90)
    print("🌟 SIVA GAYATHRI TOURS & TRAVELS — COMPLETE A TO Z END-TO-END SMOKE TEST SUITE")
    print("=" * 90)

    # 1. Setup authenticated client
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user, _ = User.objects.get_or_create(
            username='smoke_admin',
            defaults={'email': 'admin@travelerp.com', 'is_staff': True, 'is_superuser': True}
        )
        admin_user.set_password('admin123')
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

    client = Client()
    client.force_login(admin_user)
    print(f"[*] Authenticated Superuser: {admin_user.username}")

    rf = RequestFactory()
    dummy_req = rf.get('/admin/')
    dummy_req.user = admin_user

    # 2. Collect all ModelAdmins grouped by App Label alphabetically
    registry = admin.site._registry
    app_modules = {}
    for model, model_admin in registry.items():
        app_label = model._meta.app_label
        app_modules.setdefault(app_label, []).append((model, model_admin))

    sorted_apps = sorted(app_modules.keys())
    print(f"[*] Total Registered Applications (A to Z): {len(sorted_apps)} apps")
    print(f"[*] Total Registered ModelAdmins: {len(registry)} models")

    total_checks = 0
    passed_checks = 0
    failed_checks = []

    print("\n" + "=" * 90)
    print("📋 SECTION 1: ALL APPLICATION MODULES & MODELADMINS (A TO Z)")
    print("=" * 90)

    for app_idx, app_label in enumerate(sorted_apps, 1):
        models_in_app = app_modules[app_label]
        print(f"\n[{app_idx:02d}/{len(sorted_apps):02d}] 📦 MODULE: {app_label.upper()} ({len(models_in_app)} models)")
        print("-" * 90)

        for model, model_admin in sorted(models_in_app, key=lambda x: x[0].__name__):
            model_name = model.__name__
            info = (app_label, model._meta.model_name)

            # Check 1: Unfold inheritance
            total_checks += 1
            is_unfold = isinstance(model_admin, UnfoldModelAdmin)
            if is_unfold:
                passed_checks += 1
                unfold_str = "Unfold: OK"
            else:
                unfold_str = "Unfold: FAIL"
                failed_checks.append((f"{app_label}.{model_name}", "Not inheriting from unfold.admin.ModelAdmin"))

            # Check 2: Changelist URL
            total_checks += 1
            t0 = time.time()
            try:
                cl_url = reverse(f"admin:{info[0]}_{info[1]}_changelist")
                cl_resp = client.get(cl_url)
                cl_ms = (time.time() - t0) * 1000
                if cl_resp.status_code == 200:
                    passed_checks += 1
                    cl_str = f"CL: 200 OK ({cl_ms:.1f}ms)"
                else:
                    cl_str = f"CL: {cl_resp.status_code} FAIL"
                    failed_checks.append((cl_url, f"Changelist status {cl_resp.status_code}"))
            except Exception as e:
                cl_str = f"CL: ERR ({e})"
                failed_checks.append((str(info), f"Changelist exception: {e}"))

            # Check 3: Changeform / Add URL
            total_checks += 1
            t0 = time.time()
            if hasattr(model_admin, 'has_add_permission') and not model_admin.has_add_permission(dummy_req):
                passed_checks += 1
                add_str = "Add: Read-Only Policy (Permitted)"
            else:
                try:
                    add_url = reverse(f"admin:{info[0]}_{info[1]}_add")
                    add_resp = client.get(add_url)
                    add_ms = (time.time() - t0) * 1000
                    if add_resp.status_code == 200:
                        passed_checks += 1
                        add_str = f"Add: 200 OK ({add_ms:.1f}ms)"
                    elif add_resp.status_code == 403:
                        passed_checks += 1
                        add_str = "Add: 403 Permitted"
                    else:
                        add_str = f"Add: {add_resp.status_code} FAIL"
                        failed_checks.append((add_url, f"Add view status {add_resp.status_code}"))
                except Exception as e:
                    add_str = f"Add: ERR ({e})"
                    failed_checks.append((str(info), f"Add view exception: {e}"))

            # Check 4: Existing Record Change View (from model_admin's queryset)
            try:
                instance = model_admin.get_queryset(dummy_req).first()
            except Exception:
                instance = None

            inst_str = ""
            if instance and hasattr(instance, 'pk') and instance.pk is not None:
                total_checks += 1
                t0 = time.time()
                try:
                    change_url = reverse(f"admin:{info[0]}_{info[1]}_change", args=[instance.pk])
                    change_resp = client.get(change_url)
                    ch_ms = (time.time() - t0) * 1000
                    if change_resp.status_code == 200:
                        passed_checks += 1
                        inst_str = f" | Edit PK#{instance.pk}: 200 OK ({ch_ms:.1f}ms)"
                    elif change_resp.status_code == 403:
                        passed_checks += 1
                        inst_str = f" | Edit PK#{instance.pk}: 403 Policy ({ch_ms:.1f}ms)"
                    else:
                        inst_str = f" | Edit PK#{instance.pk}: {change_resp.status_code} FAIL"
                        failed_checks.append((change_url, f"Change view status {change_resp.status_code}"))
                except Exception as e:
                    inst_str = f" | Edit PK#{instance.pk}: ERR ({e})"
                    failed_checks.append((f"{info}_change", f"Change view exception: {e}"))

            print(f"  • {model_name:<30} [{unfold_str}] [{cl_str}] [{add_str}]{inst_str}")

    # 3. Section 2: Non-Admin Endpoints & Core Views
    print("\n" + "=" * 90)
    print("🌐 SECTION 2: APPLICATION VIEWS, PORTALS & REPORTING SUITE")
    print("=" * 90)

    core_views = [
        # Dashboard & Admin
        ("/admin/", 200, "Mission Control Unfold Dashboard"),
        ("/dashboard/", 200, "Operational Dispatch Dashboard"),
        ("/fleet/live/", 200, "Live Fleet Mission Control Radar Map"),
        ("/api/fleet/live-feed/", 200, "Live Fleet Telematics Radar Feed"),
        # Operations
        ("/bookings/", 200, "Booking Dispatch List"),
        ("/bookings/create/", 200, "Booking Creation Wizard"),
        ("/api/vehicle-types/", 200, "Vehicle Types API"),
        # Driver Portal
        ("/driver/", (200, 302), "Driver Mobile Dashboard (Auth/Redirect Gate)"),
        ("/driver/login/", (200, 302), "Driver Mobile Login Portal"),
        # Customer Portal
        ("/customer-portal/", 200, "B2C / Corporate Customer Portal"),
        # Analytics
        ("/analytics/dashboard/", 200, "Analytics Executive Dashboard"),
        ("/analytics/fleet/", 200, "Fleet Analytics & Telematics Radar"),
        # Finance & Reports
        ("/finance/accounting/", 200, "Finance & Double-Entry Accounting Hub"),
        ("/finance/export/tally/sales/", 200, "Tally Sales Register Export"),
        ("/reports/vehicle-profitability/", 200, "Vehicle Profitability Report"),
        ("/reports/party-profitability/", 200, "Party Profitability Report"),
        ("/statements/generate/", 200, "Statement Generation Form"),
        # Packages
        ("/packages/manifest/upload/", 200, "Tour Packages Manifest Upload"),
    ]

    for url, exp_status, desc in core_views:
        total_checks += 1
        t0 = time.time()
        resp = client.get(url)
        ms = (time.time() - t0) * 1000
        matches = resp.status_code in exp_status if isinstance(exp_status, (list, tuple)) else resp.status_code == exp_status
        if matches:
            passed_checks += 1
            print(f"  [PASS] {resp.status_code} OK ({ms:5.1f}ms) -> {url:<35} ({desc})")
        else:
            print(f"  [FAIL] {resp.status_code} ERR ({ms:5.1f}ms) -> {url:<35} ({desc})")
            failed_checks.append((url, f"Expected {exp_status}, got {resp.status_code}"))

    # 4. Section 3: Reactive HTMX Endpoints
    print("\n" + "=" * 90)
    print("⚡ SECTION 3: REACTIVE HTMX ENDPOINTS (OPERATIONS & PACKAGES)")
    print("=" * 90)

    htmx_endpoints = [
        # Operations HTMX
        (reverse('htmx_operations:party-ledger-summary'), 200, "Party Ledger Summary Deck"),
        (reverse('htmx_operations:booking-package-context'), 200, "Booking Package Context"),
        (reverse('htmx_operations:booking-quote-calc'), 200, "Booking Live Quote Calculator"),
        (reverse('htmx_operations:trip-vehicle-gate'), 200, "Trip Vehicle Fitness Gate"),
        (reverse('htmx_operations:trip-driver-status'), 200, "Trip Driver Telematics Status"),
        (reverse('htmx_operations:trip-calculate-totals'), 200, "Trip Odometer & Bata Totals"),
        (reverse('htmx_operations:fine-vehicle-driver'), 200, "Traffic Fine Vehicle Driver"),
        (reverse('htmx_operations:contract-rate-lookup'), 200, "Contract Slab Rate Lookup"),
        # Packages HTMX
        (reverse('htmx_packages:category-intel') + '?category=devotional', 200, "Category Intel: Devotional"),
        (reverse('htmx_packages:category-intel') + '?category=college_iv', 200, "Category Intel: College IV"),
        (reverse('htmx_packages:category-intel') + '?category=international', 200, "Category Intel: International"),
        (reverse('htmx_packages:unit-economics') + '?min_pax=50&price_with_food=6500', 200, "Unit Economics Live Deck"),
        (reverse('htmx_packages:tariff-calculate') + '?duration_days=3', 200, "Vehicle Tariff Calculator"),
        (reverse('htmx_packages:whatsapp-briefing'), 200, "WhatsApp Briefing Generator"),
        (reverse('htmx_packages:proposal-preview'), 200, "B2B Proposal Preview Modal"),
    ]

    for url, exp_status, desc in htmx_endpoints:
        total_checks += 1
        t0 = time.time()
        resp = client.get(url)
        ms = (time.time() - t0) * 1000
        if resp.status_code == exp_status:
            passed_checks += 1
            print(f"  [PASS] {exp_status} OK ({ms:5.1f}ms) -> {url:<45} ({desc})")
        else:
            print(f"  [FAIL] {resp.status_code} ERR ({ms:5.1f}ms) -> {url:<45} ({desc})")
            failed_checks.append((url, f"HTMX status {resp.status_code}"))

    # 5. Section 4: Error Boundary & Security Pages
    print("\n" + "=" * 90)
    print("🛡️ SECTION 4: ERROR BOUNDARIES & SECURITY PAGES")
    print("=" * 90)

    from django.test import override_settings
    with override_settings(DEBUG=False):
        # 404
        total_checks += 1
        r404 = client.get('/non-existent-smoke-test-path/')
        if r404.status_code == 404 and "Destination Not Found in Radar Grid" in r404.content.decode('utf-8'):
            passed_checks += 1
            print("  [PASS] 404 Not Found -> Custom Unfold Mission Control 404 verified.")
        else:
            failed_checks.append(('/non-existent/', f"404 failed: {r404.status_code}"))

    # Summary
    total_elapsed = time.time() - start_total_time
    print("\n" + "=" * 90)
    print("📊 FULL A TO Z SMOKE TEST EXECUTION SUMMARY")
    print("=" * 90)
    print(f"  Total Distinct Modules Audited: {len(sorted_apps)} apps (A to Z)")
    print(f"  Total Checks Executed:         {total_checks}")
    print(f"  Passed Checks:                 {passed_checks}/{total_checks} ({passed_checks/total_checks*100:.1f}%)")
    print(f"  Failed Checks:                 {len(failed_checks)}")
    print(f"  Total Execution Time:          {total_elapsed:.2f} seconds")
    print("=" * 90)

    if failed_checks:
        print("❌ FAILURES DETECTED:")
        for target, reason in failed_checks:
            print(f"   • {target}: {reason}")
        sys.exit(1)
    else:
        print("🏆 100% OF ALL MODULES A TO Z PASSED ALL SMOKE TESTS WITH ZERO ERRORS!")
        print("=" * 90)


if __name__ == '__main__':
    run_full_a_to_z_smoke_test()
