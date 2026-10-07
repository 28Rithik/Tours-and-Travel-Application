import os
import sys
import subprocess
import time
import urllib.request
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CURRENT_DIR)
GIS_DIR = os.path.join(PROJECT_DIR, 'gis_stack')
COMPOSE_FILE = os.path.join(GIS_DIR, 'docker-compose.osm.yml')

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def run_cmd(cmd, cwd=GIS_DIR):
    print(f"[*] Running: {cmd}")
    res = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr:
        print(res.stderr.strip())
    return res.returncode

def start_stack():
    print("=" * 70)
    print("🚀 STARTING ENTERPRISE OSM GIS STACK (PostGIS + TileServer + OSRM)")
    print("=" * 70)
    code = run_cmd(f"docker compose -f \"{COMPOSE_FILE}\" up -d")
    if code == 0:
        print("\n✅ Docker services launched successfully.")
        time.sleep(3)
        check_status()
    else:
        print(f"\n❌ Failed to start docker services (exit code {code}).")

def stop_stack():
    print("=" * 70)
    print("🛑 STOPPING ENTERPRISE OSM GIS STACK")
    print("=" * 70)
    run_cmd(f"docker compose -f \"{COMPOSE_FILE}\" down")

def check_status():
    print("\n" + "=" * 70)
    print("🔍 ENTERPRISE OSM GIS STACK STATUS AUDIT")
    print("=" * 70)

    # 1. Docker ps
    print("\n--- 1. Docker Containers ---")
    run_cmd(f"docker compose -f \"{COMPOSE_FILE}\" ps")

    # 2. Check PostGIS (Port 5434)
    print("\n--- 2. PostGIS Spatial Database (Port 5434) ---")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="127.0.0.1",
            port=5434,
            database="travel_erp_gis",
            user="travel_gis_user",
            password="travel_gis_pass",
            connect_timeout=3
        )
        cur = conn.cursor()
        cur.execute("SELECT PostGIS_Full_Version();")
        ver = cur.fetchone()[0]
        print(f"  [PASS] Connected to PostGIS on port 5434!")
        print(f"  Version: {ver[:80]}...")
        
        cur.execute("SELECT count(*) FROM telemetry_geofence_zone;")
        count = cur.fetchone()[0]
        print(f"  [PASS] Geofence zones found: {count} active polygons loaded.")
        conn.close()
    except Exception as e:
        print(f"  [WARN] PostGIS check failed: {e}")

    # 3. Check TileServer GL (Port 8088)
    print("\n--- 3. TileServer GL Engine (Port 8088) ---")
    try:
        req = urllib.request.Request("http://127.0.0.1:8088/styles.json", headers={'User-Agent': 'TravelERP'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"  [PASS] TileServer GL responsive. Available styles: {list(data.keys()) if isinstance(data, dict) else len(data)}")
    except Exception as e:
        print(f"  [INFO] TileServer GL not yet responding or starting up: {e}")

    # 4. Check OSRM (Port 5001 / 5000)
    print("\n--- 4. OSRM Routing Machine (Port 5001 / 5000) ---")
    try:
        req = urllib.request.Request("http://127.0.0.1:5001/", headers={'User-Agent': 'TravelERP'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            print("  [PASS] OSRM service is reachable.")
    except Exception as e:
        print(f"  [INFO] OSRM service on port 5001: {e}")

    # 5. Check GIS Gateway (:8089)
    print("\n--- 5. Nginx GIS Gateway & Edge Cache (Port 8089) ---")
    try:
        req = urllib.request.Request("http://127.0.0.1:8089/health", headers={'User-Agent': 'TravelERP'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"  [PASS] Nginx Gateway active. Status: {data.get('status')}")
    except Exception as e:
        print(f"  [INFO] Nginx Gateway on port 8089: {e}")

    # 6. Check Prometheus (:9090) & Grafana (:3001)
    print("\n--- 6. Observability: Prometheus (:9090) & Grafana (:3001) ---")
    try:
        req = urllib.request.Request("http://127.0.0.1:9090/-/healthy", headers={'User-Agent': 'TravelERP'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            print("  [PASS] Prometheus is healthy.")
    except Exception as e:
        print(f"  [INFO] Prometheus on port 9090: {e}")

    try:
        req = urllib.request.Request("http://127.0.0.1:3001/api/health", headers={'User-Agent': 'TravelERP'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            print("  [PASS] Grafana is healthy.")
    except Exception as e:
        print(f"  [INFO] Grafana on port 3001: {e}")

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if action == 'up':
        start_stack()
    elif action == 'down':
        stop_stack()
    elif action == 'status':
        check_status()
    else:
        print("Usage: python scripts/manage_gis_stack.py [up|down|status]")
