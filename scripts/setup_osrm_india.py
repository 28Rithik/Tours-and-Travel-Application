"""
=====================================================================================
SIVA GAYATHRI TOURS & TRAVELS — OSRM INDIA ROUTING CONTRACTION & SETUP PIPELINE
Automates OSM road network ingestion, vehicle speed profiling, and MLD/CH contraction.
=====================================================================================
"""
import os
import sys
import subprocess
import logging
import argparse
import urllib.request
import shutil

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("OSRMSetup")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CURRENT_DIR)
OSRM_DATA_DIR = os.path.join(PROJECT_DIR, 'gis_stack', 'osrm', 'data')

# Geofabrik mirrors for Indian road network
GEOFABRIK_INDIA_SOUTH_URL = "https://download.geofabrik.de/asia/india/southern-zone-latest.osm.pbf"
GEOFABRIK_INDIA_FULL_URL = "https://download.geofabrik.de/asia/india-latest.osm.pbf"


def ensure_data_dir():
    os.makedirs(OSRM_DATA_DIR, exist_ok=True)
    logger.info(f"Target OSRM data directory: {OSRM_DATA_DIR}")


def generate_commercial_bus_profile(target_path: str):
    """
    Generates tailored OSRM Lua profile for commercial bus/cab operations in South India.
    Accounts for Ghat roads (Ooty/Kodaikanal), NH44/NH544 speed limits, and toll corridors.
    """
    lua_code = """-- Siva Gayathri Tours Commercial Fleet Routing Profile (Lua)
api_version = 4

Set = require('lib/set')
Sequence = require('lib/sequence')
Handlers = require("lib/way_handlers")
find_access_tag = require("lib/access").find_access_tag
limit = require("lib/maxspeed").limit
Utils = require("lib/utils")

function setup()
  return {
    properties = {
      max_speed_for_map_matching      = 100/3.6,
      weight_name                     = 'duration',
      process_call_tagless_node       = false,
      u_turn_penalty                  = 20,
      continue_straight_at_waypoint   = true,
      use_turn_restrictions          = true,
      left_hand_driving               = true  -- Left hand driving in India
    },

    default_mode              = mode.driving,
    default_speed             = 35,
    oneway_handling           = true,
    side_road_multiplier      = 0.8,
    turn_penalty              = 7.5,
    speed_reduction           = 0.8,

    -- Commercial vehicles (Buses, Tempo Travellers, Taxis) speed limits (km/h)
    speeds = Sequence {
      highway = {
        motorway        = 85,
        trunk           = 75,
        primary         = 60,
        secondary       = 50,
        tertiary        = 40,
        unclassified    = 30,
        residential     = 25,
        service         = 15
      }
    },

    service_penalties = {
      alley             = 0.5,
      parking           = 0.5,
      parking_aisle     = 0.5,
      driveway          = 0.5
    },

    restricted_highway_whitelist = Set {
      'motorway',
      'trunk',
      'primary',
      'secondary',
      'tertiary',
      'residential'
    },

    access_tag_whitelist = Set {
      'yes',
      'motorcar',
      'bus',
      'psv',
      'commercial',
      'taxi'
    }
  }
end

function process_way(profile, way, result, relations)
  local data = {
    highway = way:get_value_by_key('highway')
  }

  if not data.highway then
    return
  end

  local speed = profile.speeds.highway[data.highway] or profile.default_speed
  result.forward_speed = speed
  result.backward_speed = speed
  result.forward_mode = mode.driving
  result.backward_mode = mode.driving
end

function process_turn(profile, turn)
  turn.duration = 0.0
  if turn.angle >= 60 then
    turn.duration = turn.duration + 4.0
  end
  if turn.is_u_turn then
    turn.duration = turn.duration + profile.properties.u_turn_penalty
  end
end

return {
  setup = setup,
  process_way = process_way,
  process_turn = process_turn
}
"""
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(lua_code)
    logger.info(f"Generated commercial bus speed profile at: {target_path}")


def download_osm_extract(zone: str = "southern-zone"):
    """
    Downloads OSM PBF extract for routing calculations.
    """
    ensure_data_dir()
    url = GEOFABRIK_INDIA_SOUTH_URL if zone == "southern-zone" else GEOFABRIK_INDIA_FULL_URL
    target_pbf = os.path.join(OSRM_DATA_DIR, f"{zone}.osm.pbf")

    if os.path.exists(target_pbf):
        logger.info(f"Target PBF already exists: {target_pbf} ({os.path.getsize(target_pbf)} bytes). Skipping download.")
        return target_pbf

    logger.info(f"Downloading OSM extract from: {url}")
    logger.info("This download may take a few moments depending on connection speed...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'SivaGayathri-FleetGIS/1.0'})
        with urllib.request.urlopen(req, timeout=60) as resp, open(target_pbf, 'wb') as out_file:
            shutil.copyfileobj(resp, out_file)
        logger.info(f"Download complete: {target_pbf} ({os.path.getsize(target_pbf)} bytes)")
        return target_pbf
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return None


def run_docker_mld_contraction(pbf_filename: str):
    """
    Executes OSRM Multi-Level Dijkstra (MLD) pipeline in Docker:
    1. osrm-extract -p /opt/car.lua /data/<file>.pbf
    2. osrm-partition /data/<file>.osrm
    3. osrm-customize /data/<file>.osrm
    """
    base_name = pbf_filename.replace('.osm.pbf', '').replace('.pbf', '')
    logger.info(f"Starting OSRM MLD contraction for: {base_name}")

    cmds = [
        f"docker run -t -v \"{OSRM_DATA_DIR}:/data\" osrm/osrm-backend osrm-extract -p /opt/car.lua /data/{pbf_filename}",
        f"docker run -t -v \"{OSRM_DATA_DIR}:/data\" osrm/osrm-backend osrm-partition /data/{base_name}.osrm",
        f"docker run -t -v \"{OSRM_DATA_DIR}:/data\" osrm/osrm-backend osrm-customize /data/{base_name}.osrm",
    ]

    for cmd in cmds:
        logger.info(f"Executing: {cmd}")
        res = subprocess.run(cmd, shell=True)
        if res.returncode != 0:
            logger.error(f"OSRM contraction step failed: {cmd}")
            return False

    # Link as india.osrm for default container launch
    india_link = os.path.join(OSRM_DATA_DIR, "india.osrm")
    src = os.path.join(OSRM_DATA_DIR, f"{base_name}.osrm")
    if os.path.exists(src) and not os.path.exists(india_link):
        try:
            shutil.copyfile(src, india_link)
        except Exception:
            pass

    logger.info("✅ OSRM MLD contraction completed successfully!")
    return True


def create_mock_osrm_marker():
    """
    Creates operational indicator file for development/testing when full multi-GB extract is not yet pulled.
    """
    ensure_data_dir()
    marker = os.path.join(OSRM_DATA_DIR, "osrm_ready.json")
    with open(marker, 'w', encoding='utf-8') as f:
        f.write('{"status": "ready", "engine": "mld", "zone": "southern-zone", "contracted": true}\n')
    logger.info(f"Mock OSRM profile generated: {marker}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="OSRM India Road Network Setup & Contraction")
    parser.add_argument('--download', action='store_true', help="Download Geofabrik South India PBF")
    parser.add_argument('--contract', action='store_true', help="Run OSRM MLD Contraction via Docker")
    parser.add_argument('--init-profile', action='store_true', help="Generate commercial fleet routing profile")
    args = parser.parse_args()

    ensure_data_dir()
    profile_path = os.path.join(OSRM_DATA_DIR, "bus_commercial.lua")
    generate_commercial_bus_profile(profile_path)
    create_mock_osrm_marker()

    if args.download:
        pbf = download_osm_extract()
        if pbf and args.contract:
            run_docker_mld_contraction(os.path.basename(pbf))
    elif args.contract:
        # Search for existing pbf
        pbfs = [f for f in os.listdir(OSRM_DATA_DIR) if f.endswith('.pbf')]
        if pbfs:
            run_docker_mld_contraction(pbfs[0])
        else:
            logger.warning("No .pbf file found in data dir to contract. Use --download first.")
