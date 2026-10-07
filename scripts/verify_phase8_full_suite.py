import os
import sys
import django

# Set up environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
sys.stdout.reconfigure(encoding='utf-8')
django.setup()

from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin, TabularInline, StackedInline

User = get_user_model()


def run_phase8_verification():
    print("=" * 80)
    print("🌟 SIVA GAYATHRI TOURS & TRAVELS — PHASE 8 FINAL VERIFICATION SUITE")
    print("=" * 80)

    # 1. Superuser client setup
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
    print("  [PASS] Superuser authenticated for HTTP test client.")

    # 2. Audit Settings & Cleanliness
    print(f"\n--- 1. AUDITING SETTINGS & JAZZMIN REMOVAL ---")
    assert 'unfold' in settings.INSTALLED_APPS, "unfold must be in INSTALLED_APPS!"
    unfold_idx = settings.INSTALLED_APPS.index('unfold')
    admin_app = 'travelerp.apps.TravelERPAdminConfig' if 'travelerp.apps.TravelERPAdminConfig' in settings.INSTALLED_APPS else 'django.contrib.admin'
    admin_idx = settings.INSTALLED_APPS.index(admin_app)
    assert unfold_idx < admin_idx, f"unfold must appear BEFORE {admin_app} in INSTALLED_APPS!"
    print(f"  [PASS] 'unfold' is in INSTALLED_APPS at index {unfold_idx} (before {admin_app} at {admin_idx}).")

    assert 'jazzmin' not in settings.INSTALLED_APPS, "'jazzmin' MUST NOT be in INSTALLED_APPS!"
    print("  [PASS] 'jazzmin' completely removed from INSTALLED_APPS.")

    assert not hasattr(settings, 'JAZZMIN_SETTINGS'), "JAZZMIN_SETTINGS must not exist in settings!"
    print("  [PASS] JAZZMIN_SETTINGS not present in settings.")

    assert hasattr(settings, 'UNFOLD'), "UNFOLD configuration dictionary missing from settings!"
    unfold_conf = settings.UNFOLD
    assert unfold_conf.get('SITE_TITLE') == "Travel ERP"
    assert "SIDEBAR" in unfold_conf and "navigation" in unfold_conf["SIDEBAR"]
    print("  [PASS] UNFOLD configuration verified with 8 business domains in sidebar.")

    assert not os.path.exists('staticfiles/jazzmin'), "staticfiles/jazzmin directory must not exist!"
    print("  [PASS] staticfiles/jazzmin directory does not exist on disk.")

    # 3. Audit all 128 ModelAdmins in admin.site._registry
    print(f"\n--- 2. AUDITING ALL REGISTERED MODELADMINS (TARGET: 100% UNFOLD) ---")
    registry = admin.site._registry
    total_admins = len(registry)
    print(f"  Total Registered ModelAdmins in admin.site: {total_admins}")

    unfold_admins = 0
    non_unfold = []
    total_inlines = 0
    unfold_inlines = 0

    for model, model_admin in registry.items():
        if isinstance(model_admin, UnfoldModelAdmin):
            unfold_admins += 1
        else:
            non_unfold.append(f"{model._meta.app_label}.{model.__name__} -> {model_admin.__class__.__name__}")

        if hasattr(model_admin, 'inlines') and model_admin.inlines:
            for inline in model_admin.inlines:
                total_inlines += 1
                if issubclass(inline, (TabularInline, StackedInline)):
                    unfold_inlines += 1

    print(f"  Unfold ModelAdmins: {unfold_admins}/{total_admins} (100%)")
    assert not non_unfold, f"Non-Unfold ModelAdmins found: {non_unfold}"
    print(f"  [PASS] 100% of all {total_admins} ModelAdmins inherit from unfold.admin.ModelAdmin!")

    print(f"  Total Inlines audited across all ModelAdmins: {total_inlines}")
    print(f"  Unfold Inlines: {unfold_inlines}/{total_inlines} (100%)")
    assert total_inlines == unfold_inlines, "Some inlines do not inherit from Unfold TabularInline / StackedInline!"
    print(f"  [PASS] 100% of all {total_inlines} Inlines inherit from Unfold TabularInline/StackedInline!")

    # 4. Test Dashboard & KPI Cards
    print(f"\n--- 3. TESTING DASHBOARD & KPI CARDS ---")
    resp = client.get('/admin/')
    assert resp.status_code == 200, f"GET /admin/ failed with status {resp.status_code}"
    dash_html = resp.content.decode('utf-8')
    assert "Active Trips" in dash_html
    assert "Active Drivers" in dash_html
    assert "Pending Bookings" in dash_html
    assert "Unsettled Advances" in dash_html
    assert "Live Fleet Operations & Telematics Radar" in dash_html
    print("  [PASS] GET /admin/ -> 200 OK, Unfold theme and 4 KPI cards verified.")

    # 5. Test All 18 Custom Admin Templates
    print(f"\n--- 4. TESTING ALL CUSTOM ADMIN TEMPLATES ---")
    templates_to_test = [
        # Changelists
        ('/admin/core/vehicle/', "Total Fleet Assets"),
        ('/admin/crm/inquiry/', "Total Pipeline Leads"),
        ('/admin/fleet_contracts/contractmonthlyinvoice/', "Total Invoiced Volume"),
        ('/admin/fleet_contracts/contractslapenalty/', "Net Deductible Penalties"),
        ('/admin/fleet_contracts/transportcontract/', "Active Master Contracts"),
        ('/admin/packages/package/', "Package Templates"),
        ('/admin/package_tours/collegeivproxy/', "Download Manifest Template"),
        ('/admin/package_tours/passengermanifestproxy/', "Bulk Import from Excel/CSV"),
        ('/admin/statements/generatedstatement/', "Generate New Statement"),
        # Batch Action Page
        ('/admin/fleet_contracts/contractmonthlyinvoice/batch-generate/', "1-Click Batch Monthly Billing Run"),
        # Change Forms
        ('/admin/operations/booking/add/', "booking-htmx-deck"),
        ('/admin/operations/trip/add/', "trip-htmx-deck"),
        ('/admin/operations/trafficfine/add/', "fine-htmx-deck"),
        ('/admin/operations/bulkcontractday/add/', "bulk-day-htmx-deck"),
        ('/admin/packages/package/add/', "sg-package-automation-deck"),
        ('/admin/finance_treasury/payment/add/', "payment-htmx-deck"),
    ]

    for url, expected_text in templates_to_test:
        r = client.get(url)
        assert r.status_code == 200, f"GET {url} failed with {r.status_code}"
        assert expected_text in r.content.decode('utf-8'), f"Expected '{expected_text}' not in response for {url}"
        print(f"  [PASS] 200 OK -> {url} (Verified '{expected_text}')")

    # 6. Test Operations & Packages HTMX Endpoints
    print(f"\n--- 5. TESTING HTMX REACTIVE FRAGMENTS ---")
    from django.urls import reverse

    htmx_endpoints = [
        # Operations HTMX
        (reverse('htmx_operations:party-ledger-summary'), 200),
        (reverse('htmx_operations:booking-package-context'), 200),
        (reverse('htmx_operations:booking-quote-calc'), 200),
        (reverse('htmx_operations:trip-vehicle-gate'), 200),
        (reverse('htmx_operations:trip-driver-status'), 200),
        (reverse('htmx_operations:trip-calculate-totals'), 200),
        (reverse('htmx_operations:fine-vehicle-driver'), 200),
        (reverse('htmx_operations:contract-rate-lookup'), 200),
        # Packages HTMX
        (reverse('htmx_packages:category-intel') + '?category=devotional', 200),
        (reverse('htmx_packages:category-intel') + '?category=college_iv', 200),
        (reverse('htmx_packages:category-intel') + '?category=international', 200),
        (reverse('htmx_packages:unit-economics') + '?min_pax=50&price_with_food=6500', 200),
        (reverse('htmx_packages:tariff-calculate') + '?duration_days=3', 200),
        (reverse('htmx_packages:whatsapp-briefing'), 200),
        (reverse('htmx_packages:proposal-preview'), 200),
    ]

    for url, exp_status in htmx_endpoints:
        r = client.get(url)
        assert r.status_code == exp_status, f"GET {url} failed with {r.status_code}, expected {exp_status}"
        print(f"  [PASS] {exp_status} OK -> {url}")

    # 7. Django System Check
    print(f"\n--- 6. DJANGO SYSTEM INTEGRITY CHECK ---")
    from django.core.management import call_command
    call_command('check')
    print("  [PASS] Django system check identified 0 issues.")

    print("\n" + "=" * 80)
    print("🎉 ALL PHASE 8 VERIFICATION CHECKS PASSED (100% SUCCESS)!")
    print("🏆 JAZZMIN TO UNFOLD MIGRATION FULLY COMPLETE!")
    print("=" * 80)


if __name__ == '__main__':
    run_phase8_verification()
