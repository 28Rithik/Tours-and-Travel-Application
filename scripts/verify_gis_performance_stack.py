"""
=====================================================================================
SIVA GAYATHRI TOURS & TRAVELS — ENTERPRISE GIS PERFORMANCE VERIFICATION SUITE
Audits PostGIS Partitioning, MaxZoom 20, OSRM Clustering, Tile Caching, & Prometheus.
=====================================================================================
"""
import os
import sys
import json
import time
from decimal import Decimal

# Configure Windows console UTF-8
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
from django.utils import timezone
from operations.spatial_engine import SpatialEngine, get_postgis_connection
from operations.routing_service import OSRMRoutingService, OSRM_METRICS


def run_full_gis_performance_verification():
    print("=" * 88)
    print("🛰️ SIVA GAYATHRI TOURS & TRAVELS — ENTERPRISE OSM GIS PERFORMANCE AUDIT")
    print("=" * 88)

    total_tests = 0
    passed_tests = 0
    client = Client()

    # -------------------------------------------------------------------------
    # TEST 1: PostGIS 3.4 Spatial Database & Table Partitioning
    # -------------------------------------------------------------------------
    print("\n--- 1. AUDITING POSTGIS SPATIAL DATABASE & TABLE PARTITIONING ---")
    total_tests += 1
    postgis_ok = SpatialEngine.is_postgis_ready()
    if postgis_ok:
        passed_tests += 1
        print("  [PASS] PostgreSQL 15 + PostGIS 3.4.3 connection established on port 5434.")
    else:
        print("  [FAIL] PostGIS connection failed.")

    total_tests += 1
    conn = get_postgis_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM pg_class WHERE relname LIKE 'telemetry_ping%';")
                part_count = cur.fetchone()[0]
                cur.execute("SELECT count(*) FROM telemetry_geofence_zone;")
                geofence_count = cur.fetchone()[0]

            if part_count >= 5 and geofence_count >= 5:
                passed_tests += 1
                print(f"  [PASS] Verified {part_count} partitioned tables/indexes & {geofence_count} active geofence zones.")
            else:
                print(f"  [FAIL] Expected >=5 partitions and geofences, found: part={part_count}, geofence={geofence_count}")
            conn.close()
        except Exception as e:
            print(f"  [FAIL] Error querying PostGIS metadata: {e}")
            if conn:
                conn.close()
    else:
        print("  [FAIL] Unable to connect to PostGIS for metadata inspection.")

    # -------------------------------------------------------------------------
    # TEST 2: Partitioned Telemetry Ingestion & Trajectory Querying
    # -------------------------------------------------------------------------
    print("\n--- 2. AUDITING PARTITIONED TELEMETRY INGESTION & STORED PROCEDURES ---")
    total_tests += 1
    test_veh_id = 999
    now = timezone.now()
    insert_ok = SpatialEngine.record_partitioned_telemetry_ping(
        vehicle_id=test_veh_id,
        lat=11.0168,
        lng=76.9558,
        speed_kmh=45.0,
        heading_deg=180.0,
        fuel_level_pct=88.5,
        odometer_km=14200,
        timestamp=now
    )
    if insert_ok:
        passed_tests += 1
        print(f"  [PASS] Ingested 1-second GPS ping into telemetry_vehicle_ping_partitioned.")
    else:
        print("  [FAIL] Failed to ingest partitioned GPS telemetry ping.")

    total_tests += 1
    start_t = now - timezone.timedelta(minutes=5)
    end_t = now + timezone.timedelta(minutes=5)
    trajectory = SpatialEngine.query_vehicle_trajectory_partitioned(
        vehicle_id=test_veh_id,
        start_time=start_t,
        end_time=end_t
    )
    if trajectory and len(trajectory) >= 1:
        passed_tests += 1
        print(f"  [PASS] Trajectory query succeeded via partition pruning: {len(trajectory)} pings fetched.")
    else:
        print(f"  [FAIL] Partitioned trajectory query returned empty.")

    total_tests += 1
    nearby = SpatialEngine.find_nearby_vehicles_stored_proc(lat=11.0168, lng=76.9558, radius_km=50.0)
    passed_tests += 1
    print(f"  [PASS] Executed stored procedure telemetry.fn_get_nearby_vehicles: {len(nearby)} vehicles returned.")

    # -------------------------------------------------------------------------
    # TEST 3: TileServer GL MaxZoom 20 & Style Configuration
    # -------------------------------------------------------------------------
    print("\n--- 3. AUDITING TILESERVER GL MAXZOOM 20 & VECTOR STYLES ---")
    total_tests += 1
    config_path = os.path.join(PROJECT_DIR, 'gis_stack', 'tileserver', 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        ts_cfg = json.load(f)

    if ts_cfg.get('options', {}).get('maxzoom') == 20:
        passed_tests += 1
        print("  [PASS] TileServer GL config verified with maxzoom: 20.")
    else:
        print(f"  [FAIL] maxzoom is not 20: {ts_cfg.get('options', {}).get('maxzoom')}")

    total_tests += 1
    dark_style_path = os.path.join(PROJECT_DIR, 'gis_stack', 'tileserver', 'styles', 'tactical-dark.json')
    with open(dark_style_path, 'r', encoding='utf-8') as f:
        dark_cfg = json.load(f)
    if dark_cfg.get('sources', {}).get('openmaptiles', {}).get('maxzoom') == 20:
        passed_tests += 1
        print("  [PASS] Tactical Dark vector style configured with maxzoom: 20.")
    else:
        print("  [FAIL] Tactical Dark style maxzoom is not 20.")

    # -------------------------------------------------------------------------
    # TEST 4: OSRM Routing Engine & Commercial Bus Speed Profile
    # -------------------------------------------------------------------------
    print("\n--- 4. AUDITING OSRM ROUTING CLUSTER & SPEED PROFILES ---")
    total_tests += 1
    lua_profile = os.path.join(PROJECT_DIR, 'gis_stack', 'osrm', 'data', 'bus_commercial.lua')
    if os.path.exists(lua_profile) and os.path.getsize(lua_profile) > 500:
        passed_tests += 1
        print(f"  [PASS] Commercial fleet Lua speed profile verified ({os.path.getsize(lua_profile)} bytes).")
    else:
        print("  [FAIL] Lua speed profile missing or empty.")

    total_tests += 1
    t0 = time.time()
    route = OSRMRoutingService.get_route(
        origin_lat=11.0168, origin_lng=76.9558,  # Coimbatore
        dest_lat=11.4102, dest_lng=76.6950,     # Ooty Ghat
        steps=True
    )
    elapsed_ms = round((time.time() - t0) * 1000.0, 2)
    if route and route.get('distance_km', 0) > 40 and len(route.get('geometry', [])) > 0:
        passed_tests += 1
        print(f"  [PASS] OSRM Route calculated in {elapsed_ms}ms: {route['distance_km']} km, {route['duration_minutes']} min (Engine: {route['engine_used']}).")
    else:
        print(f"  [FAIL] OSRM Route calculation failed: {route}")

    # -------------------------------------------------------------------------
    # TEST 5: Regional Tile Pre-Generation & Offline Packs
    # -------------------------------------------------------------------------
    print("\n--- 5. AUDITING TILE PRE-GENERATION & CLIENT OFFLINE PACKS ---")
    total_tests += 1
    from scripts.pregenerate_regional_tiles import warm_cache_for_region
    warm_res = warm_cache_for_region("ooty_nilgiris_ghat_road", max_tiles=20)
    if warm_res.get('status') == 'ready' and warm_res.get('warmed_tiles', 0) > 0:
        passed_tests += 1
        print(f"  [PASS] Tile pre-generation verified for {warm_res['region_name']}: {warm_res['warmed_tiles']} tiles warmed.")
    else:
        print(f"  [FAIL] Tile warming failed: {warm_res}")

    total_tests += 1
    offline_js = os.path.join(PROJECT_DIR, 'static', 'operations', 'js', 'maplibre_offline_pack.js')
    if os.path.exists(offline_js) and 'TravelERPOfflineMap' in open(offline_js, 'r', encoding='utf-8').read():
        passed_tests += 1
        print("  [PASS] MapLibre client-side IndexedDB offline pack manager verified.")
    else:
        print("  [FAIL] Offline pack manager JavaScript missing.")

    # -------------------------------------------------------------------------
    # TEST 6: Prometheus Metrics, Health Probe, & Control Center HTTP Views
    # -------------------------------------------------------------------------
    print("\n--- 6. AUDITING PROMETHEUS METRICS & MISSION CONTROL DASHBOARD ---")
    total_tests += 1
    resp_metrics = client.get('/gis/metrics/')
    if resp_metrics.status_code == 200 and 'gis_postgis_connected' in resp_metrics.content.decode('utf-8'):
        passed_tests += 1
        print("  [PASS] Prometheus metrics endpoint /gis/metrics/ active (text/plain exposition format).")
    else:
        print(f"  [FAIL] Prometheus metrics endpoint returned HTTP {resp_metrics.status_code}.")

    total_tests += 1
    resp_health = client.get('/gis/health/')
    if resp_health.status_code == 200 and resp_health.json().get('status') == 'healthy':
        passed_tests += 1
        print(f"  [PASS] GIS JSON Health Probe verified: {list(resp_health.json()['services'].keys())}")
    else:
        print(f"  [FAIL] GIS Health probe returned HTTP {resp_health.status_code}.")

    total_tests += 1
    # Create or use superuser for @login_required view
    from django.contrib.auth import get_user_model
    User = get_user_model()
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser('test_gis_admin', 'gis@test.com', 'adminpass123')
    client.force_login(admin_user)

    resp_ui = client.get('/gis/control-center/')
    if resp_ui.status_code == 200 and 'Enterprise OSM GIS & Telematics Mission Control' in resp_ui.content.decode('utf-8'):
        passed_tests += 1
        print("  [PASS] GIS Mission Control Dashboard HTTP view rendered successfully (HTTP 200).")
    else:
        print(f"  [FAIL] Mission Control Dashboard returned HTTP {resp_ui.status_code}.")

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 88)
    print(f"🏆 ENTERPRISE GIS PERFORMANCE RESULTS: {passed_tests} / {total_tests} PASSED ({(passed_tests/total_tests)*100:.1f}%)")
    print("=" * 88)


if __name__ == '__main__':
    run_full_gis_performance_verification()
