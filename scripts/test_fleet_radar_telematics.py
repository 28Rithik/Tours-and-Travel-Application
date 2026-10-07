import os
import sys
import time

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelerp.settings')

import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from operations.models import GeofenceZone, VehicleTelematicsPing, DriverBehaviorLog, Trip
from core.models import Vehicle

User = get_user_model()


def run_fleet_radar_telematics_test():
    print("=" * 80)
    print("🛰️ LIVE FLEET TELEMATICS GPS RADAR MAP & GEOFENCE SUITE VERIFICATION")
    print("=" * 80)

    admin_user = User.objects.filter(is_superuser=True).first()
    client = Client()
    client.force_login(admin_user)
    print(f"[*] Authenticated as Superuser: {admin_user.username}")

    checks_passed = 0
    total_checks = 0

    def assert_check(cond, msg):
        nonlocal checks_passed, total_checks
        total_checks += 1
        if cond:
            checks_passed += 1
            print(f"  [PASS] {msg}")
        else:
            print(f"  [FAIL] {msg}")
            raise AssertionError(f"Check failed: {msg}")

    # 1. Test Admin Radar Map Endpoint
    print("\n--- 1. Testing Admin Radar Map View (/admin/operations/fleet-radar/) ---")
    resp_admin = client.get('/admin/operations/fleet-radar/')
    assert_check(resp_admin.status_code == 200, "GET /admin/operations/fleet-radar/ returns 200 OK")
    content_admin = resp_admin.content.decode('utf-8')
    assert_check("Live Fleet Telematics GPS Radar Map" in content_admin, "Admin Radar view contains official title")
    assert_check("liveTelematicsRadarMap" in content_admin, "Admin Radar view renders Leaflet map container")
    assert_check("speedometer-svg" in content_admin, "Admin Radar view renders dynamic SVG speedometer gauge")
    assert_check("radarRangeRings" in content_admin, "Admin Radar view contains concentric tactical range rings logic")
    assert_check("checkPerimeterBreaches" in content_admin, "Admin Radar view contains perimeter breach detector")
    assert_check("basemaps.cartocdn.com" in content_admin or "tile.openstreetmap.org" in content_admin, "Admin Radar view uses high-performance tactical basemap")

    # 2. Test Admin Alias Endpoint
    print("\n--- 2. Testing Admin Radar Alias Route (/admin/fleet-radar/) ---")
    resp_alias = client.get('/admin/fleet-radar/')
    assert_check(resp_alias.status_code == 200, "GET /admin/fleet-radar/ alias returns 200 OK")

    # 3. Test Standalone Operations Desk Endpoint
    print("\n--- 3. Testing Standalone Fleet Live Desk (/fleet/live/) ---")
    resp_live = client.get('/fleet/live/')
    assert_check(resp_live.status_code == 200, "GET /fleet/live/ returns 200 OK")
    content_live = resp_live.content.decode('utf-8')
    assert_check("detailSpeedNeedle" in content_live, "Standalone view contains dynamic speedometer needle")
    assert_check("basemaps.cartocdn.com" in content_live or "tile.openstreetmap.org" in content_live, "Standalone view uses high-performance basemap")

    # 4. Test Live Telematics Feed REST Endpoint (/api/fleet/live-feed/)
    print("\n--- 4. Testing Live Telematics Feed REST API (/api/fleet/live-feed/) ---")
    t0 = time.time()
    resp_feed = client.get('/api/fleet/live-feed/')
    feed_ms = (time.time() - t0) * 1000
    assert_check(resp_feed.status_code == 200, f"GET /api/fleet/live-feed/ returns 200 OK in {feed_ms:.1f}ms")
    data = resp_feed.json()
    assert_check(data.get('status') == 'success', "Feed status is 'success'")
    assert_check('vehicles' in data and len(data['vehicles']) > 0, f"Feed returns {len(data.get('vehicles', []))} fleet vehicles")
    assert_check('summary' in data, "Feed returns operations summary KPI metrics")
    assert_check('geofences' in data and len(data['geofences']) >= 8, f"Feed returns {len(data.get('geofences', []))} active geofence zones")

    # Inspect First Vehicle Payload Fields
    v0 = data['vehicles'][0]
    assert_check('speed_kmh' in v0 and 'heading_degrees' in v0, f"Vehicle contains speed ({v0.get('speed_kmh')} km/h) & heading ({v0.get('heading_degrees')}°)")
    assert_check('fuel_level_pct' in v0 and 'current_km' in v0, f"Vehicle contains fuel ({v0.get('fuel_level_pct')}%) & odometer ({v0.get('current_km')} km)")
    assert_check('breadcrumbs' in v0 and isinstance(v0['breadcrumbs'], list), f"Vehicle contains breadcrumbs trajectory list (crumbs count: {len(v0['breadcrumbs'])})")
    assert_check('geofence_status' in v0, "Vehicle contains geofence proximity evaluation payload")

    # 5. Test Live Telematics Simulation Tick API (/api/fleet/simulate-tick/)
    print("\n--- 5. Testing Live Telematics Simulation Tick API (/api/fleet/simulate-tick/) ---")
    t0 = time.time()
    resp_sim = client.get('/api/fleet/simulate-tick/')
    sim_ms = (time.time() - t0) * 1000
    assert_check(resp_sim.status_code == 200, f"GET /api/fleet/simulate-tick/ returns 200 OK in {sim_ms:.1f}ms")
    sim_data = resp_sim.json()
    assert_check(sim_data.get('status') == 'success', "Simulation tick returns 'success'")
    assert_check(sim_data.get('ticks_count', 0) > 0, f"Simulation tick advanced {sim_data.get('ticks_count')} vehicles in real-time")

    # 6. Verify Geofence Database Integrity
    print("\n--- 6. Verifying Geofence Zones in Database ---")
    gf_count = GeofenceZone.objects.filter(is_active=True).count()
    assert_check(gf_count >= 8, f"Confirmed {gf_count} active geofence zones seeded in database")
    airport_zone = GeofenceZone.objects.filter(name__icontains='Airport').first()
    assert_check(airport_zone is not None, f"Verified Airport Geofence: {airport_zone.name} (Radius: {airport_zone.radius_meters}m)")
    ooty_zone = GeofenceZone.objects.filter(name__icontains='Ooty').first()
    assert_check(ooty_zone is not None, f"Verified Mountain Restricted Geofence: {ooty_zone.name} (Speed limit: {ooty_zone.speed_limit_kmh} km/h)")

    print("\n" + "=" * 80)
    print(f"🏆 ALL {checks_passed}/{total_checks} TELEMATICS RADAR & GEOFENCE CHECKS PASSED (100% SUCCESS)!")
    print("=" * 80)


if __name__ == '__main__':
    run_fleet_radar_telematics_test()
