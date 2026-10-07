import os
import sys
import django

# Set up environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
sys.stdout.reconfigure(encoding='utf-8')
django.setup()

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import Client
from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin, TabularInline, StackedInline

from packages.models import (
    PackageTemplate,
    Package,
    PackageVehicleTariff,
    ItineraryDay,
    PackageInventory,
    BoardingPoint,
    CollegeIVExpedition,
    TourPassengerManifest,
    TempleDarshanSlot,
    InternationalDocumentChecklist,
    PackageSeasonalRate,
    PackageHotelAllotment,
    PackageAddon,
    PackageB2BMargin,
    TourFeedbackLog,
)
from package_tours.models import (
    CollegeIVProxy,
    TourDepartureBatchProxy,
    BoardingPointProxy,
    PassengerManifestProxy,
    HotelAllotmentProxy,
    TourFeedbackProxy,
    SeasonalRateProxy,
    PackageAddonProxy,
    B2BMarginProxy,
)
from core.models import VehicleType, Vehicle, Driver

User = get_user_model()


def run_phase7_verification():
    print("=" * 80)
    print("🚀 SIVA GAYATHRI TOURS & TRAVELS — PHASE 7 VERIFICATION SUITE")
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

    # 2. Verify all 24 ModelAdmins across packages and package_tours
    packages_models = [
        PackageTemplate, Package, PackageVehicleTariff, TempleDarshanSlot,
        InternationalDocumentChecklist, ItineraryDay, PackageSeasonalRate,
        PackageHotelAllotment, PackageAddon, PackageB2BMargin, TourFeedbackLog,
        PackageInventory, BoardingPoint, CollegeIVExpedition, TourPassengerManifest,
    ]

    package_tours_models = [
        CollegeIVProxy, TourDepartureBatchProxy, BoardingPointProxy,
        PassengerManifestProxy, HotelAllotmentProxy, TourFeedbackProxy,
        SeasonalRateProxy, PackageAddonProxy, B2BMarginProxy,
    ]

    all_phase7_models = packages_models + package_tours_models
    print(f"\n--- 1. AUDITING 24 MODELADMINS INHERITANCE (Target: unfold.admin.ModelAdmin) ---")
    admin_count = 0
    for model in all_phase7_models:
        model_admin = admin.site._registry.get(model)
        assert model_admin is not None, f"ModelAdmin for {model.__name__} is not registered in admin.site!"
        assert isinstance(model_admin, UnfoldModelAdmin), f"{model_admin.__class__.__name__} does not inherit from Unfold ModelAdmin!"
        admin_count += 1
        print(f"  [PASS] {model._meta.app_label}.{model.__name__} -> {model_admin.__class__.__name__} (Unfold ModelAdmin)")

    assert admin_count == 24, f"Expected 24 ModelAdmins, found {admin_count}"
    print(f"  ✨ All 24 ModelAdmins successfully verified on Unfold theme!")

    # 3. Verify all 11 Inlines
    print(f"\n--- 2. AUDITING 11 INLINES INHERITANCE ---")
    pkg_admin = admin.site._registry[Package]
    civ_admin = admin.site._registry[CollegeIVProxy]

    expected_pkg_inlines = [
        'ItineraryDayInline', 'PackageVehicleTariffInline', 'PackageSeasonalRateInline',
        'PackageAddonInline', 'PackageHotelAllotmentInline', 'PackageB2BMarginInline',
        'TempleDarshanSlotInline', 'InternationalDocumentChecklistInline'
    ]
    pkg_inline_names = [inline.__name__ for inline in pkg_admin.inlines]
    for exp in expected_pkg_inlines:
        assert exp in pkg_inline_names, f"Inline {exp} missing from PackageAdmin.inlines!"
        inline_cls = next(i for i in pkg_admin.inlines if i.__name__ == exp)
        assert issubclass(inline_cls, (TabularInline, StackedInline)), f"{exp} must inherit from Unfold TabularInline or StackedInline"
        print(f"  [PASS] PackageAdmin inline -> {exp} ({inline_cls.__bases__[0].__name__})")

    batch_admin = admin.site._registry[TourDepartureBatchProxy]
    expected_batch_inlines = ['BoardingPointInline', 'HotelAllotmentInline', 'PassengerManifestInline']
    batch_inline_names = [inline.__name__ for inline in batch_admin.inlines]
    for exp in expected_batch_inlines:
        assert exp in batch_inline_names, f"Inline {exp} missing from TourDepartureBatchAdmin.inlines!"
        inline_cls = next(i for i in batch_admin.inlines if i.__name__ == exp)
        assert issubclass(inline_cls, (TabularInline, StackedInline)), f"{exp} must inherit from Unfold TabularInline or StackedInline"
        print(f"  [PASS] TourDepartureBatchAdmin inline -> {exp} ({inline_cls.__bases__[0].__name__})")

    print(f"  ✨ All 11 Inlines successfully verified on Unfold TabularInline / StackedInline!")

    # 4. Verify Media and Template Configuration
    print(f"\n--- 3. VERIFYING PACKAGE ADMIN TEMPLATE & MEDIA DECOUPLING ---")
    assert pkg_admin.change_form_template == 'admin/packages/package/change_form.html', (
        f"PackageAdmin change_form_template expected 'admin/packages/package/change_form.html', got {pkg_admin.change_form_template}"
    )
    print("  [PASS] PackageAdmin.change_form_template = 'admin/packages/package/change_form.html'")

    media = pkg_admin.media
    media_js_str = str(media._js)
    assert 'package_dynamic_form.js' not in media_js_str, (
        f"Legacy 153KB package_dynamic_form.js MUST NOT be loaded in PackageAdmin.media! Found: {media_js_str}"
    )
    print("  [PASS] Legacy 153KB package_dynamic_form.js successfully decoupled from PackageAdmin.Media.")

    # 5. Seed test instances for end-to-end testing
    print(f"\n--- 4. SEEDING / FETCHING TEST FIXTURES ---")
    vtype, _ = VehicleType.objects.get_or_create(
        name='54-Seater Luxury Pushback Coach',
        defaults={'category': 'bus', 'seating_capacity': 54, 'default_km_rate': Decimal('48.00')}
    )
    template, _ = PackageTemplate.objects.get_or_create(
        name='Mysore - Coorg - Ooty South Circuit',
        defaults={
            'destination': 'Tamil Nadu / Karnataka',
            'category': 'college_iv',
            'duration_days': 4,
            'duration_nights': 3,
            'base_price': Decimal('6500.00'),
            'description': 'Flagship 4-Day Expedition with Ooty Tea Estates, Coorg Campfire DJ, and Mysore Palace.'
        }
    )
    pkg, _ = Package.objects.get_or_create(
        package_code='PKG-TEST-P7',
        defaults={
            'template': template,
            'name': 'Mysore Coorg Ooty Flagship Circuit',
            'destination': 'Ooty, Coorg, Mysore',
            'category': 'college_iv',
            'duration_days': 4,
            'duration_nights': 3,
            'min_pax': 50,
            'base_price': Decimal('6500.00'),
            'price_with_food': Decimal('6500.00'),
            'price_without_food': Decimal('4900.00'),
            'cost_hotel_per_pax': Decimal('1800.00'),
            'cost_coach_per_pax': Decimal('1400.00'),
            'cost_meals_per_pax': Decimal('1500.00'),
            'cost_activities_per_pax': Decimal('400.00'),
            'cost_misc_per_pax': Decimal('200.00'),
            'is_active': True,
        }
    )
    print(f"  [PASS] Test package fixture verified -> id={pkg.id}, code={pkg.package_code}")

    # 6. HTTP GET Changlist for all 24 ModelAdmins
    print(f"\n--- 5. TESTING HTTP 200 CHANGELISTS FOR ALL 24 MODELADMINS ---")
    for model in all_phase7_models:
        meta = model._meta
        url = f"/admin/{meta.app_label}/{meta.model_name}/"
        resp = client.get(url)
        assert resp.status_code == 200, f"GET {url} failed with status {resp.status_code}"
        print(f"  [PASS] 200 OK -> {url}")

    # 7. HTTP GET Package Change Form & Add Form
    print(f"\n--- 6. TESTING PACKAGE CHANGE FORM WITH HTMX DECK ---")
    pkg_change_url = f"/admin/packages/package/{pkg.id}/change/"
    resp = client.get(pkg_change_url)
    assert resp.status_code == 200, f"GET {pkg_change_url} returned {resp.status_code}"
    content = resp.content.decode('utf-8')

    assert 'package_dynamic_form.js' not in content, "Legacy package_dynamic_form.js found in rendered HTML!"
    assert 'hx-get' in content, "HTMX attributes missing from Package change form!"
    assert 'category-intel' in content, "Category intelligence HTMX container missing!"
    assert 'unit-economics' in content, "Unit economics HTMX container missing!"
    assert 'applyPackagePreset' in content, "Preset automation missing from Package change form!"
    print(f"  [PASS] 200 OK -> Package change form rendered with Unfold theme and HTMX reactive decks.")

    pkg_add_url = "/admin/packages/package/add/"
    resp_add = client.get(pkg_add_url)
    assert resp_add.status_code == 200, f"GET {pkg_add_url} returned {resp_add.status_code}"
    print(f"  [PASS] 200 OK -> Package add form rendered cleanly.")

    # 8. Test HTMX Endpoints
    print(f"\n--- 7. TESTING HTMX REACTIVE ENDPOINTS ---")

    # A. Category Intelligence: Devotional
    url_cat_dev = "/packages/htmx/category-intel/?category=devotional"
    r = client.get(url_cat_dev)
    assert r.status_code == 200, f"GET {url_cat_dev} returned {r.status_code}"
    assert "Devotional Protocol" in r.content.decode('utf-8')
    assert "Satvik pure vegetarian meals" in r.content.decode('utf-8')
    print("  [PASS] HTMX /packages/htmx/category-intel/?category=devotional -> 200 OK, devotional rules returned.")

    # B. Category Intelligence: College IV
    url_cat_iv = "/packages/htmx/category-intel/?category=college_iv"
    r = client.get(url_cat_iv)
    assert r.status_code == 200
    assert "Campfire" in r.content.decode('utf-8')
    print("  [PASS] HTMX /packages/htmx/category-intel/?category=college_iv -> 200 OK, student IV rules returned.")

    # C. Category Intelligence: International
    url_cat_intl = "/packages/htmx/category-intel/?category=international"
    r = client.get(url_cat_intl)
    assert r.status_code == 200
    assert "Tourist Visa" in r.content.decode('utf-8')
    print("  [PASS] HTMX /packages/htmx/category-intel/?category=international -> 200 OK, international rules returned.")

    # D. Unit Economics Real-Time Calculation
    url_econ = (
        f"/packages/htmx/unit-economics/?min_pax=50&price_with_food=6500&price_without_food=4900"
        f"&cost_hotel_per_pax=1800&cost_coach_per_pax=1400&cost_meals_per_pax=1500&cost_activities_per_pax=400&cost_misc_per_pax=200"
    )
    r = client.get(url_econ)
    assert r.status_code == 200
    econ_html = r.content.decode('utf-8')
    assert "Operating Unit Economics & Gross Profit P&L" in econ_html
    # Direct cost = 1800 + 1400 + 1500 + 400 + 200 = 5300
    assert "5300" in econ_html
    # Unit margin = 6500 - 5300 = 1200
    assert "1200" in econ_html
    print("  [PASS] HTMX /packages/htmx/unit-economics/ -> 200 OK, unit margin and P&L calculated correctly.")

    # E. Tariff Calculation
    url_tariff = f"/packages/htmx/tariff-calculate/?vehicle_type_id={vtype.id}&duration_days=4&rate_type=daily"
    r = client.get(url_tariff)
    assert r.status_code == 200
    tariff_json = r.json()
    assert tariff_json['included_km'] == 1200  # 300 km/day * 4 days
    assert tariff_json['extra_km_rate'] == 48.0
    print("  [PASS] HTMX /packages/htmx/tariff-calculate/ -> 200 OK, fleet rates computed.")

    # F. WhatsApp Tour Briefing Generator Modal
    url_wa = f"/packages/htmx/whatsapp-briefing/?package_id={pkg.id}"
    r = client.get(url_wa)
    assert r.status_code == 200
    assert "SIVA GAYATHRI TOURS" in r.content.decode('utf-8')
    assert "Client Proposal Pitch" in r.content.decode('utf-8')
    print("  [PASS] HTMX /packages/htmx/whatsapp-briefing/ -> 200 OK, 3 formatted briefings generated.")

    # G. 5-Page Proposal PDF Preview Modal
    url_modal = f"/packages/htmx/proposal-preview/?package_id={pkg.id}"
    r = client.get(url_modal)
    assert r.status_code == 200
    assert f"/packages/quote/{pkg.id}/" in r.content.decode('utf-8')
    print("  [PASS] HTMX /packages/htmx/proposal-preview/ -> 200 OK, modal preview link verified.")

    # 9. Test Proposal Quotation and Manifest Actions
    print(f"\n--- 8. TESTING PROPOSAL QUOTATION & MANIFEST SERVICES ---")
    quote_resp = client.get(f"/packages/quote/{pkg.id}/")
    assert quote_resp.status_code in [200, 302], f"GET /packages/quote/{pkg.id}/ returned {quote_resp.status_code}"
    print(f"  [PASS] /packages/quote/{pkg.id}/ -> {quote_resp.status_code} OK")

    manifest_template_resp = client.get("/packages/manifest/template/download/")
    assert manifest_template_resp.status_code == 200
    assert 'text/csv' in manifest_template_resp.headers.get('Content-Type', '')
    print("  [PASS] /packages/manifest/template/download/ -> 200 OK CSV file generated.")

    print("\n" + "=" * 80)
    print("🎉 ALL PHASE 7 VERIFICATION CHECKS PASSED (100% SUCCESS)!")
    print("=" * 80)


if __name__ == '__main__':
    run_phase7_verification()
