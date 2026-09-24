import os
import sys
import django

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from packages.models import Package, PackageTemplate
from core.models import VehicleType

def test_package_dropdown_consistency():
    print("==================================================")
    print("Testing All Dropdown Options & Reactive Form Sync")
    print("==================================================")

    # 1. Check all choices exist on Package model
    categories = [c[0] for c in Package.CATEGORIES]
    transit_modes = [t[0] for t in Package.TRANSIT_MODES]
    pricing_types = [p[0] for p in Package.PRICING_TYPES]
    meal_plans = [m[0] for m in Package.MEAL_PLANS]
    room_sharing_types = [r[0] for r in Package.ROOM_SHARING_TYPES]

    print(f"Categories ({len(categories)}): {categories}")
    print(f"Transit Modes ({len(transit_modes)}): {transit_modes}")
    print(f"Pricing Types ({len(pricing_types)}): {pricing_types}")
    print(f"Meal Plans ({len(meal_plans)}): {meal_plans}")
    print(f"Room Sharing Types ({len(room_sharing_types)}): {room_sharing_types}")

    assert 'flight_coach' in transit_modes, "Missing flight_coach"
    assert 'train_coach' in transit_modes, "Missing train_coach"
    assert 'road_coach' in transit_modes, "Missing road_coach"
    assert 'land_only' in transit_modes, "Missing land_only"

    # 2. Check JavaScript file has matching values
    with open('packages/static/packages/js/package_dynamic_form.js', 'r', encoding='utf-8') as f:
        js_content = f.read()

    assert "transitMode === 'flight_coach'" in js_content, "JS missing flight_coach handler"
    assert "transitMode === 'train_coach'" in js_content, "JS missing train_coach handler"
    assert "transitMode === 'land_only'" in js_content, "JS missing land_only handler"
    assert "onTransitModeChange()" in js_content, "JS missing onTransitModeChange"
    assert "onPricingTypeChange()" in js_content, "JS missing onPricingTypeChange"
    assert "onDefaultVehicleTypeChange()" in js_content, "JS missing onDefaultVehicleTypeChange"
    assert "onMealPlanChange()" in js_content, "JS missing onMealPlanChange"
    assert "onRoomSharingTypeChange()" in js_content, "JS missing onRoomSharingTypeChange"
    assert "onCurrencyCodeChange()" in js_content, "JS missing onCurrencyCodeChange"
    assert "autoEstimateTripCosts(" in js_content, "JS missing autoEstimateTripCosts"

    print("\n✓ JavaScript Reactive Engine contains complete event handlers for all dropdowns!")

    # 3. Test HTTP Admin rendering and select presence
    c = Client()
    User = get_user_model()
    u = User.objects.filter(is_superuser=True).first()
    c.force_login(u)
    res = c.get('/admin/packages/package/1/change/')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    html = res.content.decode('utf-8')

    expected_selects = [
        'id_category',
        'id_transit_mode',
        'id_pricing_type',
        'id_default_vehicle_type',
        'id_meal_plan',
        'id_room_sharing_type',
        'id_currency_code',
        'id_template'
    ]

    for sel in expected_selects:
        assert f'id="{sel}"' in html, f"Select #{sel} missing from change form HTML"
        print(f"✓ Found dropdown <select id='{sel}'> in admin change form")

    # 4. Verify fieldset layout for flight & train estimates
    assert 'field-flight_estimate_per_pax' in html, "flight_estimate_per_pax missing"
    assert 'field-train_estimate_per_pax' in html, "train_estimate_per_pax missing"
    assert 'field-vehicle_seating_desc' in html, "vehicle_seating_desc missing"
    assert 'field-bus_amenities_desc' in html, "bus_amenities_desc missing"

    print("\n==================================================")
    print("ALL DROPDOWN TESTS PASSED SUCCESSFULLY (100% OK)!")
    print("==================================================")

if __name__ == '__main__':
    test_package_dropdown_consistency()
