import os
import sys

# Ensure UTF-8 stdout on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import json
from decimal import Decimal
import django

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from core.models import Vehicle, VehicleType
from finance_fleet.cpk_engine import (
    DEFAULT_DIESEL_PRICE,
    calculate_vehicle_cpk,
    get_fleet_cpk_radar_metrics,
    get_route_profitability_benchmarks,
    simulate_what_if_tariff,
    get_fuel_anomaly_radar,
    resolve_expected_mileage,
)

User = get_user_model()


def run_tests():
    print("=" * 80)
    print("[*] REAL-TIME FLEET CPK & PROFITABILITY OPTIMIZATION RADAR -- TEST SUITE")
    print("=" * 80)

    checks_passed = 0
    total_checks = 0

    def assert_check(condition, label):
        nonlocal checks_passed, total_checks
        total_checks += 1
        if condition:
            checks_passed += 1
            print(f"  [PASS] {label}")
        else:
            print(f"  [FAIL] {label}")
            sys.exit(1)

    # --------------------------------------------------------------------------
    # STAGE 1: Vehicle CPK Engine & Zero-Division Safety
    # --------------------------------------------------------------------------
    print("\n--- [STAGE 1] Testing Vehicle CPK Engine & Zero-Division Safety ---")

    vehicle = Vehicle.objects.filter(fuel_records__isnull=False).first()
    if not vehicle:
        vehicle = Vehicle.objects.first()

    assert_check(vehicle is not None, f"Found target vehicle: {vehicle.registration_number}")

    cpk_data = calculate_vehicle_cpk(vehicle)
    assert_check(cpk_data['total_cpk'] >= Decimal('0.00'), f"Total CPK computed: ₹{cpk_data['total_cpk']}/KM")
    assert_check(cpk_data['fuel_cpk'] >= Decimal('0.00'), f"Fuel CPK computed: ₹{cpk_data['fuel_cpk']}/KM")
    assert_check(cpk_data['toll_cpk'] >= Decimal('0.00'), f"Toll CPK computed: ₹{cpk_data['toll_cpk']}/KM")
    assert_check(cpk_data['driver_cpk'] >= Decimal('0.00'), f"Driver CPK computed: ₹{cpk_data['driver_cpk']}/KM")
    assert_check(cpk_data['maintenance_cpk'] >= Decimal('0.00'), f"Maintenance CPK computed: ₹{cpk_data['maintenance_cpk']}/KM")
    assert_check(cpk_data['tier'] in ['tier_1_high', 'tier_2_standard', 'tier_3_low', 'tier_4_loss'], f"Health tier assigned: {cpk_data['tier']}")

    # --------------------------------------------------------------------------
    # STAGE 2: Dynamic Diesel Price Shift Simulation
    # --------------------------------------------------------------------------
    print("\n--- [STAGE 2] Testing Live Diesel Price Sensitivity ---")

    base_price = Decimal('92.50')
    surge_price = Decimal('105.00')

    res_base = calculate_vehicle_cpk(vehicle, diesel_price_override=base_price)
    res_surge = calculate_vehicle_cpk(vehicle, diesel_price_override=surge_price)

    assert_check(res_surge['fuel_cost'] >= res_base['fuel_cost'], f"Fuel cost increased under diesel surge: ₹{res_base['fuel_cost']} ➔ ₹{res_surge['fuel_cost']}")
    assert_check(res_surge['total_cpk'] >= res_base['total_cpk'], f"Total CPK reflected fuel surge: ₹{res_base['total_cpk']} ➔ ₹{res_surge['total_cpk']}")

    # --------------------------------------------------------------------------
    # STAGE 3: Interactive What-If Tariff Optimizer
    # --------------------------------------------------------------------------
    print("\n--- [STAGE 3] Testing What-If Tariff Optimizer ---")

    # Innova 350 KM @ 25% target margin
    sim_innova = simulate_what_if_tariff(
        diesel_price=Decimal('95.00'),
        distance_km=350,
        vehicle_category='innova',
        target_margin_pct=Decimal('25.0'),
        days_count=1
    )

    assert_check(sim_innova['recommended_quote'] > sim_innova['total_trip_cost'], f"Recommended quote exceeds operating cost: ₹{sim_innova['recommended_quote']} > ₹{sim_innova['total_trip_cost']}")
    assert_check(sim_innova['cpk'] > Decimal('0.00'), f"Computed trip CPK: ₹{sim_innova['cpk']}/KM")
    assert_check(sim_innova['recommended_rpk'] > sim_innova['cpk'], f"Recommended RPK exceeds CPK: ₹{sim_innova['recommended_rpk']} > ₹{sim_innova['cpk']}")
    
    # Verify margin formula precision: (Quote - Cost) / Quote ~ Target Margin
    actual_margin_pct = (sim_innova['projected_profit'] / sim_innova['recommended_quote']) * Decimal('100.0')
    assert_check(abs(actual_margin_pct - Decimal('25.0')) < Decimal('1.0'), f"Target margin achieved within 1% tolerance: {actual_margin_pct:.1f}%")

    # Tempo Traveller 600 KM @ 30% margin
    sim_tt = simulate_what_if_tariff(
        diesel_price=Decimal('92.50'),
        distance_km=600,
        vehicle_category='traveller',
        target_margin_pct=Decimal('30.0'),
        days_count=2
    )
    assert_check(sim_tt['recommended_quote'] > Decimal('10000.00'), f"TT 600 KM 2-day quote computed: ₹{sim_tt['recommended_quote']}")
    assert_check(sim_tt['fuel_cost'] > Decimal('5000.00'), f"TT fuel cost computed: ₹{sim_tt['fuel_cost']}")

    # --------------------------------------------------------------------------
    # STAGE 4: Route Profitability Benchmarks
    # --------------------------------------------------------------------------
    print("\n--- [STAGE 4] Testing Route Benchmarking ---")

    routes = get_route_profitability_benchmarks(diesel_price=Decimal('92.50'))
    assert_check(len(routes) >= 5, f"Benchmarked {len(routes)} major highway corridors")
    for r in routes:
        assert_check(r['recommended_quote'] > r['total_route_cost'], f"Corridor {r['route_name']}: Quote ₹{r['recommended_quote']} > Cost ₹{r['total_route_cost']}")
        assert_check(r['route_cpk'] > Decimal('5.00'), f"Route CPK realistic: ₹{r['route_cpk']}/KM")

    # --------------------------------------------------------------------------
    # STAGE 5: Fuel Theft & Efficiency Anomaly Radar
    # --------------------------------------------------------------------------
    print("\n--- [STAGE 5] Testing Fuel Theft & Anomaly Radar ---")

    anomalies = get_fuel_anomaly_radar(threshold_variance_pct=Decimal('15.0'))
    assert_check(isinstance(anomalies, list), f"Anomaly radar scanned fleet: {len(anomalies)} anomaly alert(s)")
    if anomalies:
        top_anomaly = anomalies[0]
        assert_check(top_anomaly['financial_loss'] >= Decimal('0.00'), f"Quantified financial loss: ₹{top_anomaly['financial_loss']} on {top_anomaly['registration_number']}")
        assert_check(top_anomaly['variance_pct'] < Decimal('-15.0'), f"Flagged anomaly variance: {top_anomaly['variance_pct']}%")

    # --------------------------------------------------------------------------
    # STAGE 6: Fleet-Wide Metrics Aggregation
    # --------------------------------------------------------------------------
    print("\n--- [STAGE 6] Testing Fleet-Wide Aggregation ---")

    fleet_metrics = get_fleet_cpk_radar_metrics()
    assert_check(fleet_metrics['vehicles_analyzed'] > 0, f"Analyzed {fleet_metrics['vehicles_analyzed']} fleet vehicles")
    assert_check(fleet_metrics['fleet_avg_cpk'] > Decimal('0.00'), f"Fleet average CPK: ₹{fleet_metrics['fleet_avg_cpk']}/KM")
    assert_check(fleet_metrics['fleet_avg_rpk'] > Decimal('0.00'), f"Fleet average RPK: ₹{fleet_metrics['fleet_avg_rpk']}/KM")
    assert_check(len(fleet_metrics['leaderboard']) > 0, "Leaderboard populated with ranked vehicles")

    # --------------------------------------------------------------------------
    # STAGE 7: HTTP Views & Web APIs
    # --------------------------------------------------------------------------
    print("\n--- [STAGE 7] Testing Web Views & API Endpoints ---")

    admin_user, _ = User.objects.get_or_create(username='admin', defaults={'is_staff': True, 'is_superuser': True})
    client = Client()
    client.force_login(admin_user)

    # 1. Unfold Admin Studio View
    resp_studio = client.get('/admin/finance/cpk-radar/')
    assert_check(resp_studio.status_code == 200, "Unfold CPK Radar Studio returns HTTP 200 OK")
    assert_check(b"Fleet Profitability" in resp_studio.content, "Studio title rendered")
    assert_check(b"Vehicle CPK" in resp_studio.content, "Leaderboard tab rendered")

    # 2. Alias Route
    resp_alias = client.get('/admin/fleet/cpk-radar/')
    assert_check(resp_alias.status_code == 200, "Alias /admin/fleet/cpk-radar/ returns HTTP 200 OK")

    # 3. Dynamic Metrics API
    resp_api = client.get('/api/finance/cpk-radar/metrics/?diesel_price=98.50')
    assert_check(resp_api.status_code == 200, "Metrics API returns HTTP 200 OK")
    api_data = resp_api.json()
    assert_check(api_data['success'] is True, "Metrics API returned success=True")
    assert_check(api_data['diesel_price'] == 98.5, f"Applied dynamic diesel price: {api_data['diesel_price']}")
    assert_check(len(api_data['leaderboard']) > 0, "Serialized leaderboard returned")

    # 4. Tariff Optimizer API
    resp_opt = client.post(
        '/api/finance/cpk-radar/optimize-tariff/',
        data=json.dumps({
            'diesel_price': '94.00',
            'distance_km': 420,
            'vehicle_category': 'innova',
            'target_margin_pct': '28.0',
            'days_count': 1,
        }),
        content_type='application/json'
    )
    assert_check(resp_opt.status_code == 200, "Optimizer API returns HTTP 200 OK")
    opt_data = resp_opt.json()
    assert_check(opt_data['success'] is True, "Optimizer API returned success=True")
    assert_check(opt_data['recommended_quote'] > 0, f"Optimized quote returned: ₹{opt_data['recommended_quote']}")
    assert_check(opt_data['target_margin_pct'] == 28.0, "Applied 28% margin target")

    print("\n" + "=" * 80)
    print(f"[*] ALL CHECKS PASSED: {checks_passed} / {total_checks} (100% SUCCESS!)")
    print("=" * 80)


if __name__ == '__main__':
    run_tests()
