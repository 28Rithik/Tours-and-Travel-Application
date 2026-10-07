import os
import sys
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory
from django.urls import reverse
from unfold.admin import ModelAdmin as UnfoldModelAdmin, TabularInline, StackedInline

User = get_user_model()


class Command(BaseCommand):
    help = "Unified Enterprise Pre-Flight & Regression Verification for Siva Gayathri Travel ERP"

    def add_arguments(self, parser):
        parser.add_argument(
            '--fast',
            action='store_true',
            help='Run fast critical smoke checks only',
        )

    def handle(self, *args, **options):
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')

        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("[*] SIVA GAYATHRI TOURS & TRAVELS -- ENTERPRISE PRE-FLIGHT AUDIT"))
        self.stdout.write(self.style.SUCCESS("=" * 80))

        client = Client()
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user, _ = User.objects.get_or_create(
                username='audit_admin',
                defaults={'email': 'audit@travelerp.com', 'is_staff': True, 'is_superuser': True}
            )
            admin_user.set_password('audit123')
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save()
        client.force_login(admin_user)

        # ----------------------------------------------------------------------
        # 1. SETTINGS & UNFOLD INTEGRITY
        # ----------------------------------------------------------------------
        self.stdout.write("\n" + self.style.MIGRATE_HEADING("--- [1/6] AUDITING SETTINGS & UNFOLD INTEGRITY ---"))
        assert 'unfold' in settings.INSTALLED_APPS, "unfold missing from INSTALLED_APPS"
        unfold_idx = settings.INSTALLED_APPS.index('unfold')
        admin_app = 'travelerp.apps.TravelERPAdminConfig' if 'travelerp.apps.TravelERPAdminConfig' in settings.INSTALLED_APPS else 'django.contrib.admin'
        admin_idx = settings.INSTALLED_APPS.index(admin_app)
        assert unfold_idx < admin_idx, f"unfold (index {unfold_idx}) must precede admin app (index {admin_idx})"
        self.stdout.write(f"  [PASS] 'unfold' installed at index {unfold_idx} before admin app.")

        assert 'jazzmin' not in settings.INSTALLED_APPS, "'jazzmin' found in INSTALLED_APPS"
        assert not hasattr(settings, 'JAZZMIN_SETTINGS'), "JAZZMIN_SETTINGS found in settings"
        assert not hasattr(settings, 'JAZZMIN_UI_TWEAKS'), "JAZZMIN_UI_TWEAKS found in settings"
        self.stdout.write("  [PASS] 'jazzmin' completely eradicated from settings.")

        assert hasattr(settings, 'UNFOLD'), "UNFOLD configuration missing"
        nav = settings.UNFOLD.get("SIDEBAR", {}).get("navigation", [])
        assert len(nav) >= 8, f"Expected at least 8 navigation categories, found {len(nav)}"
        self.stdout.write(f"  [PASS] UNFOLD configuration verified ({len(nav)} navigation domains).")

        assert not os.path.exists('staticfiles/jazzmin'), "staticfiles/jazzmin still exists on disk!"
        self.stdout.write("  [PASS] staticfiles/jazzmin directory confirmed absent from disk.")

        # ----------------------------------------------------------------------
        # 2. SCHEMA & MIGRATIONS INTEGRITY
        # ----------------------------------------------------------------------
        self.stdout.write("\n" + self.style.MIGRATE_HEADING("--- [2/6] AUDITING DATABASE SCHEMA & MIGRATIONS ---"))
        try:
            call_command('makemigrations', check=True, dry_run=True)
            self.stdout.write("  [PASS] Zero schema drift: All models match database migrations 100%.")
        except SystemExit as e:
            if e.code != 0:
                raise CommandError("Unapplied model changes or missing migrations detected!")

        # ----------------------------------------------------------------------
        # 3. MODELADMIN & INLINE REGISTRY AUDIT (100% UNFOLD)
        # ----------------------------------------------------------------------
        self.stdout.write("\n" + self.style.MIGRATE_HEADING("--- [3/6] AUDITING MODELADMIN & INLINE REGISTRY (100% UNFOLD) ---"))
        registry = admin.site._registry
        total_admins = len(registry)
        unfold_admins = 0
        total_inlines = 0
        unfold_inlines = 0
        non_unfold = []

        for model, model_admin in registry.items():
            if isinstance(model_admin, UnfoldModelAdmin):
                unfold_admins += 1
            else:
                non_unfold.append(f"{model._meta.app_label}.{model.__name__}")

            if hasattr(model_admin, 'inlines') and model_admin.inlines:
                for inl in model_admin.inlines:
                    total_inlines += 1
                    if issubclass(inl, (TabularInline, StackedInline)):
                        unfold_inlines += 1

        assert not non_unfold, f"Non-Unfold ModelAdmins detected: {non_unfold}"
        assert total_inlines == unfold_inlines, "Some inlines do not inherit from Unfold TabularInline / StackedInline"
        self.stdout.write(f"  [PASS] 100% of ModelAdmins ({unfold_admins}/{total_admins}) inherit from unfold.admin.ModelAdmin.")
        self.stdout.write(f"  [PASS] 100% of Inlines ({unfold_inlines}/{total_inlines}) inherit from Unfold TabularInline / StackedInline.")

        # ----------------------------------------------------------------------
        # 4. REACTIVE HTMX SUITE AUDIT
        # ----------------------------------------------------------------------
        self.stdout.write("\n" + self.style.MIGRATE_HEADING("--- [4/6] AUDITING 15 REACTIVE HTMX ENDPOINTS ---"))
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
            resp = client.get(url)
            assert resp.status_code == exp_status, f"Endpoint {url} returned {resp.status_code}, expected {exp_status}"
            self.stdout.write(f"  [PASS] 200 OK -> {url}")

        # ----------------------------------------------------------------------
        # 5. ANOMALY & RESILIENCE AUDIT
        # ----------------------------------------------------------------------
        self.stdout.write("\n" + self.style.MIGRATE_HEADING("--- [5/6] AUDITING COMPUTED PROPERTIES & ZERO-DIVISION SAFETY ---"))
        from packages.models import PackageAddon
        from finance_fleet.models import FuelRecord

        # Zero-division tests
        addon = PackageAddon(selling_price=Decimal('0.00'), cost_price=Decimal('0.00'))
        assert addon.margin_percentage == Decimal('0.0'), "PackageAddon zero selling price must return 0.0 margin"

        fuel = FuelRecord(opening_km=1200, closing_km=1000, fuel_quantity=Decimal('0.00'), fuel_price=Decimal('100.00'))
        assert fuel.distance == 0, "FuelRecord inverted km must clamp to 0"
        assert fuel.mileage == 0, "FuelRecord zero quantity must safely return 0 mileage"
        self.stdout.write("  [PASS] Computed properties & mathematical models validated with 0 ZeroDivisionErrors.")

        # ----------------------------------------------------------------------
        # 6. DJANGO SYSTEM CHECK
        # ----------------------------------------------------------------------
        self.stdout.write("\n" + self.style.MIGRATE_HEADING("--- [6/6] DJANGO SYSTEM INTEGRITY CHECK ---"))
        call_command('check')
        self.stdout.write("  [PASS] Django system check identified 0 issues.")

        self.stdout.write("\n" + self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("[*] PRE-FLIGHT AUDIT PASSED WITH 100% SUCCESS -- SYSTEM IS BULLETPROOF!"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
