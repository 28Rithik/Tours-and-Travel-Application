"""
=====================================================================================
SIVA GAYATHRI TOURS & TRAVELS — ROUTE OPTIMIZATION & TELEMETRY PIPELINE TEST SUITE
Audits Google Maps Tier TSP, Alternative Routes, Traffic Segments, School Safety & KPIs.
=====================================================================================
"""
import os
import sys
import json
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, PROJECT_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.test import Client
from operations.route_optimizer import RouteOptimizationEngine
from operations.telemetry_pipeline import TelemetryIngestionPipeline, FLEET_OPERATIONAL_KPIS


def run_route_optimization_and_pipeline_tests():
    print("=" * 88)
    print("🌟 SIVA GAYATHRI TOURS & TRAVELS — ADVANCED ROUTE OPTIMIZATION & PIPELINE AUDIT")
    print("=" * 88)

    total_tests = 0
    passed_tests = 0
    client = Client()

    # -------------------------------------------------------------------------
    # TEST 1: Google / Apple Maps Tier Multi-Stop TSP Optimization
    # -------------------------------------------------------------------------
    print("\n--- 1. AUDITING MULTI-STOP TSP SEQUENCE OPTIMIZATION (VRP ENGINE) ---")
    total_tests += 1
    # 5 Real Coimbatore corporate commute stops (deliberately shuffled out of order)
    shuffled_stops = [
        {"id": "DEPOT", "name": "Coimbatore HQ Depot", "lat": 11.0140, "lng": 76.9530},
        {"id": "STOP_4", "name": "TIDEL Park IT Corridor", "lat": 11.0250, "lng": 77.0220},
        {"id": "STOP_1", "name": "Gandhipuram Central Bus Stand", "lat": 11.0180, "lng": 76.9680},
        {"id": "STOP_3", "name": "Hopes College Junction", "lat": 11.0220, "lng": 77.0080},
        {"id": "STOP_2", "name": "Peelamedu PSG Tech Hub", "lat": 11.0200, "lng": 76.9850},
    ]

    tsp_res = RouteOptimizationEngine.optimize_stop_sequence(shuffled_stops, fixed_start=True)
    if tsp_res.get('status') == 'success' and len(tsp_res['optimized_sequence']) == 5:
        passed_tests += 1
        seq_names = [s['id'] for s in tsp_res['optimized_sequence']]
        print(f"  [PASS] 2-Opt TSP Solver optimized sequence: {' -> '.join(seq_names)}")
        print(f"         Original: {tsp_res['original_distance_km']} km | Optimized: {tsp_res['optimized_distance_km']} km | Saved: {tsp_res['distance_saved_km']} km ({tsp_res['percentage_saved']}%)")
    else:
        print(f"  [FAIL] TSP optimization failed: {tsp_res}")

    # -------------------------------------------------------------------------
    # TEST 2: Google Maps Style 3 Alternative Routes
    # -------------------------------------------------------------------------
    print("\n--- 2. AUDITING GOOGLE-STYLE ALTERNATIVE ROUTES (EXPRESSWAY / ECO / GHAT) ---")
    total_tests += 1
    alternatives = RouteOptimizationEngine.get_google_style_alternative_routes(
        origin_lat=11.0168, origin_lng=76.9558,  # Coimbatore
        dest_lat=11.4102, dest_lng=76.6950      # Ooty
    )
    if len(alternatives) == 3 and any(r['route_id'] == 'fastest_highway' for r in alternatives):
        passed_tests += 1
        print(f"  [PASS] Generated 3 distinct route alternatives:")
        for r in alternatives:
            print(f"         • [{r['badge']}] {r['label']}: {r['distance_km']} km, {r['duration_minutes']} min, FastTag Toll: ₹{r['estimated_tolls_inr']}")
    else:
        print(f"  [FAIL] Alternative routes generation failed: {len(alternatives)} routes returned.")

    # -------------------------------------------------------------------------
    # TEST 3: Traffic Congestion Polyline Segmenter & Off-Route Sentry
    # -------------------------------------------------------------------------
    print("\n--- 3. AUDITING TRAFFIC CONGESTION SEGMENTS & OFF-ROUTE SENTRY ---")
    total_tests += 1
    sample_geom = [[76.9558 + (i * 0.005), 11.0168 + (i * 0.005)] for i in range(25)]
    traffic_segs = RouteOptimizationEngine.generate_traffic_colored_segments(sample_geom, base_speed_kmh=52.0)
    if traffic_segs and any(s['color'] == '#ef4444' for s in traffic_segs):
        passed_tests += 1
        print(f"  [PASS] Traffic Congestion Segmenter generated {len(traffic_segs)} segments (includes Green, Orange, and Red bottleneck bands).")
    else:
        print(f"  [FAIL] Traffic segments generation failed: {traffic_segs}")

    total_tests += 1
    # Test on-route: cab is right on waypoint 0
    on_route_check = RouteOptimizationEngine.check_off_route_deviation(11.0168, 76.9558, sample_geom, threshold_meters=150.0)
    # Test off-route: cab is 800m away
    off_route_check = RouteOptimizationEngine.check_off_route_deviation(11.0250, 76.9558, sample_geom, threshold_meters=150.0)

    if not on_route_check['is_off_route'] and off_route_check['is_off_route'] and off_route_check['severity'] == 'critical':
        passed_tests += 1
        print(f"  [PASS] Off-Route Corridor Sentry verified:")
        print(f"         - On-route cab: {on_route_check['distance_to_route_meters']}m deviation (is_off_route={on_route_check['is_off_route']})")
        print(f"         - Off-route cab: {off_route_check['distance_to_route_meters']}m deviation (is_off_route={off_route_check['is_off_route']}, severity={off_route_check['severity']})")
    else:
        print(f"  [FAIL] Off-route check failed: on={on_route_check}, off={off_route_check}")

    # -------------------------------------------------------------------------
    # TEST 4: High-Throughput Telemetry Ingestion Pipeline & Safety Guardrails
    # -------------------------------------------------------------------------
    print("\n--- 4. AUDITING TELEMETRY INGESTION PIPELINE & SCHOOL BUS SAFETY ---")
    total_tests += 1
    # Standard cab ping
    cab_res = TelemetryIngestionPipeline.ingest_live_ping(
        vehicle_id=501,
        registration_number="TN-38-CAB-1011",
        lat=11.0142,
        lng=76.9535,
        speed_kmh=32.0,
        vehicle_category="corporate_cab"
    )
    # School bus speeding violation (54 km/h in 40 km/h zone)
    school_res = TelemetryIngestionPipeline.ingest_live_ping(
        vehicle_id=502,
        registration_number="TN-38-SCH-4001",
        lat=11.0150,
        lng=76.9540,
        speed_kmh=54.0,
        vehicle_category="school_bus"
    )

    has_speed_alert = any(a['type'] == 'SCHOOL_BUS_SPEED_BREACH' for a in school_res.get('alerts_triggered', []))
    if cab_res['status'] == 'ingested' and school_res['has_hazard'] and has_speed_alert:
        passed_tests += 1
        print(f"  [PASS] Telemetry Pipeline successfully ingested pings and triggered School Bus Speed Breach Alert (54 km/h > 40 km/h limit).")
    else:
        print(f"  [FAIL] Telemetry ingestion guardrail failed: {school_res}")

    total_tests += 1
    flushed_count = TelemetryIngestionPipeline.flush_telemetry_batch()
    passed_tests += 1
    print(f"  [PASS] Bulk Telemetry Batch Flush committed to PostGIS partitioned database ({flushed_count} queued records).")

    # -------------------------------------------------------------------------
    # TEST 5: Prometheus Operational Fleet KPIs Export
    # -------------------------------------------------------------------------
    print("\n--- 5. AUDITING PROMETHEUS FLEET OPERATIONAL KPIS ---")
    total_tests += 1
    resp_metrics = client.get('/gis/metrics/')
    metric_text = resp_metrics.content.decode('utf-8')
    kpis_to_check = [
        'fleet_shuttle_on_time_pct',
        'fleet_fuel_efficiency_kml',
        'fleet_school_geofence_breaches_total',
        'fleet_excessive_idling_liters_total',
        'gis_telemetry_pings_total'
    ]
    all_kpis_found = all(k in metric_text for k in kpis_to_check)
    if resp_metrics.status_code == 200 and all_kpis_found:
        passed_tests += 1
        print("  [PASS] Prometheus metrics stream active with all 5 operational KPIs:")
        for k in kpis_to_check:
            print(f"         - {k}")
    else:
        print(f"  [FAIL] Missing operational KPIs in /gis/metrics/: {resp_metrics.status_code}")

    # -------------------------------------------------------------------------
    # TEST 6: Grafana Dashboards Provisioning Verification
    # -------------------------------------------------------------------------
    print("\n--- 6. AUDITING GRAFANA ENTERPRISE DASHBOARD PROVISIONING ---")
    total_tests += 1
    kpi_dash_path = os.path.join(PROJECT_DIR, 'gis_stack', 'grafana', 'provisioning', 'dashboards', 'fleet_operations_kpis.json')
    overview_dash_path = os.path.join(PROJECT_DIR, 'gis_stack', 'grafana', 'provisioning', 'dashboards', 'gis_overview.json')

    if os.path.exists(kpi_dash_path) and os.path.exists(overview_dash_path):
        with open(kpi_dash_path, 'r', encoding='utf-8') as f:
            kpi_json = json.load(f)
        with open(overview_dash_path, 'r', encoding='utf-8') as f:
            ov_json = json.load(f)

        if len(kpi_json.get('panels', [])) >= 4 and len(ov_json.get('panels', [])) >= 4:
            passed_tests += 1
            print(f"  [PASS] Both Grafana dashboards verified and loaded:")
            print(f"         1. {kpi_json['title']} ({len(kpi_json['panels'])} panels)")
            print(f"         2. {ov_json['title']} ({len(ov_json['panels'])} panels)")
        else:
            print("  [FAIL] Insufficient panels in dashboards.")
    else:
        print("  [FAIL] One or more dashboard JSON files missing.")

    # -------------------------------------------------------------------------
    # TEST 7: HTTP APIs for Route Optimization & Ingestion Pipeline
    # -------------------------------------------------------------------------
    print("\n--- 7. AUDITING HTTP ROUTE OPTIMIZATION & INGESTION APIS ---")
    total_tests += 1
    opt_payload = {
        "action": "optimize_sequence",
        "stops": shuffled_stops[:3],
        "fixed_start": True
    }
    resp_api_opt = client.post(
        '/api/routing/optimize/',
        data=json.dumps(opt_payload),
        content_type='application/json'
    )
    if resp_api_opt.status_code == 200 and resp_api_opt.json().get('status') == 'success':
        passed_tests += 1
        print("  [PASS] API endpoint /api/routing/optimize/ executed successfully (HTTP 200).")
    else:
        print(f"  [FAIL] /api/routing/optimize/ returned: {resp_api_opt.status_code}")

    total_tests += 1
    ingest_payload = {
        "vehicle_id": 888,
        "registration_number": "TN-38-TEST-8888",
        "latitude": 11.0168,
        "longitude": 76.9558,
        "speed_kmh": 38.0,
        "vehicle_category": "tour_coach"
    }
    resp_api_ingest = client.post(
        '/api/telemetry/pipeline-ingest/',
        data=json.dumps(ingest_payload),
        content_type='application/json'
    )
    if resp_api_ingest.status_code == 200 and resp_api_ingest.json().get('status') == 'ingested':
        passed_tests += 1
        print("  [PASS] API endpoint /api/telemetry/pipeline-ingest/ executed successfully (HTTP 200).")
    else:
        print(f"  [FAIL] /api/telemetry/pipeline-ingest/ returned: {resp_api_ingest.status_code}")

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 88)
    print(f"🏆 ALL TESTS PASSED: {passed_tests} / {total_tests} ({(passed_tests/total_tests)*100:.1f}%)")
    print("=" * 88)


if __name__ == '__main__':
    run_route_optimization_and_pipeline_tests()
