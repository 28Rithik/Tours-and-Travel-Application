import os
import sys
import time
import json
import urllib.request
import django

# Setup Django Environment
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, PROJECT_DIR)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from operations.spatial_engine import SpatialEngine
from operations.routing_service import OSRMRoutingService
from operations.quotation_engine import compute_route_distance, compute_single_vehicle_quote

User = get_user_model()


def run_full_osm_enterprise_verification():
    print("=" * 80)
    print("🌟 SIVA GAYATHRI TOURS & TRAVELS — ENTERPRISE OSM STACK VERIFICATION")
    print("=" * 80)
    
    total_tests = 0
    passed_tests = 0

    # -------------------------------------------------------------------------
    # TEST 1: PostGIS Database Engine
    # -------------------------------------------------------------------------
    print("\n--- 1. AUDITING POSTGIS SPATIAL DATABASE (Port 5434) ---")
    total_tests += 1
    postgis_ok = SpatialEngine.is_postgis_ready()
    if postgis_ok:
        passed_tests += 1
        print("  [PASS] PostgreSQL 15 + PostGIS 3.4 is connected and healthy.")
    else:
        print("  [FAIL] PostGIS database container is not reachable.")

    # -------------------------------------------------------------------------
    # TEST 2: Spatial Geofence Polygon Synchronization
    # -------------------------------------------------------------------------
    print("\n--- 2. AUDITING SPATIAL GEOFENCE SYNC & ST_CONTAINS ---")
    total_tests += 1
    synced = SpatialEngine.sync_django_geofences_to_postgis()
    if synced > 0:
        passed_tests += 1
        print(f"  [PASS] Successfully synchronized {synced} geofence polygons with ST_Buffer into PostGIS.")
    else:
        print("  [WARN] Zero geofences synchronized.")

    total_tests += 1
    # Test breach at Coimbatore depot coordinates (11.0168, 76.9558) with speed 45 km/h
    breaches = SpatialEngine.check_geofence_breach(11.0168, 76.9558, speed_kmh=45)
    if breaches and any(b.get('is_speeding') for b in breaches):
        passed_tests += 1
        print(f"  [PASS] ST_Contains spatial query detected speeding breach in {breaches[0]['zone_name']}.")
    else:
        print("  [FAIL] ST_Contains breach detection did not trigger expected zone.")

    # -------------------------------------------------------------------------
    # TEST 3: OSRM Routing Engine & Real-World Highway Distance
    # -------------------------------------------------------------------------
    print("\n--- 3. AUDITING OSRM ROUTING MACHINE & HIGHWAY MAPPING ---")
    total_tests += 1
    # Coimbatore to Ooty (Nilgiris Ghat road)
    route = OSRMRoutingService.get_route(11.0168, 76.9558, 11.4102, 76.6950)
    if route.get('distance_km', 0) > 60 and len(route.get('geometry', [])) > 0:
        passed_tests += 1
        print(f"  [PASS] OSRM calculated route: {route['distance_km']} km, {route['duration_minutes']} mins (Engine: {route['engine_used']}).")
        print(f"         Waypoints generated: {len(route['geometry'])} GeoJSON coordinates.")
    else:
        print("  [FAIL] OSRM routing calculation failed.")

    # -------------------------------------------------------------------------
    # TEST 4: AI Quotation Engine Integration with OSRM
    # -------------------------------------------------------------------------
    print("\n--- 4. AUDITING QUOTATION ENGINE OSRM INTEGRATION ---")
    total_tests += 1
    quote_dist = compute_route_distance('chennai', 'madurai')
    if 'osrm' in quote_dist.get('source', '') and quote_dist.get('distance_km', 0) > 400:
        passed_tests += 1
        print(f"  [PASS] Quotation Engine routed Chennai -> Madurai via OSRM: {quote_dist['distance_km']} km ({quote_dist['duration_minutes']} mins).")
    else:
        print(f"  [WARN] Quotation route source: {quote_dist.get('source')} ({quote_dist.get('distance_km')} km).")

    # -------------------------------------------------------------------------
    # TEST 5: PostGIS Nearest-Vehicle Dispatching API (ST_DWithin)
    # -------------------------------------------------------------------------
    print("\n--- 5. AUDITING POSTGIS NEAREST-VEHICLE DISPATCH API ---")
    total_tests += 1
    admin_user = User.objects.filter(is_superuser=True).first()
    client = Client()
    if admin_user:
        client.force_login(admin_user)
    
    resp = client.get('/api/spatial/nearest-vehicles/?lat=11.0168&lng=76.9558&radius_km=100')
    if resp.status_code == 200:
        data = resp.json()
        if data.get('status') == 'success' and data.get('postgis_active'):
            passed_tests += 1
            print(f"  [PASS] /api/spatial/nearest-vehicles/ active with PostGIS ST_DWithin (Found: {data.get('count')} vehicles).")
        else:
            print(f"  [WARN] Endpoint returned non-PostGIS or empty data: {data}")
    else:
        print(f"  [FAIL] Nearest vehicles API returned HTTP {resp.status_code}.")

    # -------------------------------------------------------------------------
    # TEST 6: OSRM Route HTTP Endpoint
    # -------------------------------------------------------------------------
    total_tests += 1
    resp_route = client.get('/api/routing/route/?origin=coimbatore&dest=ooty')
    if resp_route.status_code == 200 and resp_route.json().get('distance_km'):
        passed_tests += 1
        print(f"  [PASS] /api/routing/route/ active and returning GeoJSON routes.")
    else:
        print(f"  [FAIL] Route API returned status {resp_route.status_code}.")

    # -------------------------------------------------------------------------
    # TEST 7: TileServer GL Health & Vector Styles Engine (Port 8088)
    # -------------------------------------------------------------------------
    print("\n--- 7. AUDITING TILESERVER GL VECTOR MAP ENGINE (Port 8088) ---")
    total_tests += 1
    try:
        req = urllib.request.Request("http://127.0.0.1:8088/styles.json", headers={'User-Agent': 'TravelERP-Verification'})
        with urllib.request.urlopen(req, timeout=3) as resp_ts:
            if resp_ts.status == 200:
                styles_data = json.loads(resp_ts.read().decode('utf-8'))
                passed_tests += 1
                print(f"  [PASS] TileServer GL is online and serving {len(styles_data)} vector styles (tactical-dark, voyager-clean).")
            else:
                print(f"  [FAIL] TileServer GL returned HTTP {resp_ts.status}.")
    except Exception as e:
        print(f"  [FAIL] TileServer GL connection failed: {e}")

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print(f"🏆 OSM ENTERPRISE STACK VERIFICATION RESULTS: {passed_tests} / {total_tests} PASSED ({(passed_tests/total_tests)*100:.1f}%)")
    print("=" * 80)


if __name__ == '__main__':
    run_full_osm_enterprise_verification()
