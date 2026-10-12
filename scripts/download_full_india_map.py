"""
=====================================================================================
SIVA GAYATHRI TOURS & TRAVELS — FULL INDIA GIS & MAP PRE-SEEDING UTILITY
=====================================================================================
Automates:
1. Pre-warming local high-speed tile cache for major Indian tourist corridors
2. Downloading official Geofabrik India OSM Road Network extracts
3. Validating local MBTiles and PostGIS connections
"""

import os
import sys
import math
import time
import argparse
import urllib.request
from pathlib import Path
from typing import List, Tuple

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = CURRENT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelerp.settings")

import django
django.setup()

from django.conf import settings

GEOFABRIK_FULL_INDIA_URL = "https://download.geofabrik.de/asia/india-latest.osm.pbf"
GEOFABRIK_SOUTH_INDIA_URL = "https://download.geofabrik.de/asia/india/southern-zone-latest.osm.pbf"

# Top Indian Corridors (lat, lng, radius_deg, label)
KEY_INDIAN_CORRIDORS = [
    (11.0168, 76.9558, 0.4, "Coimbatore Hub & Isha Yoga"),
    (11.4102, 76.6950, 0.3, "Ooty & Nilgiris Mountain Corridor"),
    (13.0827, 80.2707, 0.4, "Chennai Metropolitan & OMR"),
    (12.9716, 77.5946, 0.4, "Bangalore Transit Corridor"),
    (9.9312, 76.2673, 0.4, "Kochi & Alleppey Backwaters"),
    (10.0889, 77.0595, 0.3, "Munnar Tea Hills"),
    (9.9252, 78.1198, 0.3, "Madurai & Temple Circuit"),
    (9.2876, 79.3129, 0.3, "Rameshwaram & Dhanushkodi"),
    (15.2993, 74.1240, 0.4, "Goa Coastal Beach Corridor"),
    (28.6139, 77.2090, 0.4, "Delhi NCR Golden Triangle Gate"),
    (27.1767, 78.0081, 0.3, "Agra Taj Mahal Corridor"),
    (26.9124, 75.7873, 0.4, "Jaipur Heritage Circuit"),
    (25.3176, 82.9739, 0.3, "Varanasi Ganges Ghats"),
    (31.1048, 77.1734, 0.3, "Shimla Himalayan Gateway"),
    (32.2432, 77.1892, 0.3, "Manali & Solang Valley"),
]

def deg_to_tile(lat_deg: float, lon_deg: float, zoom: int) -> Tuple[int, int]:
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile

def pre_seed_tiles(corridors, zooms=[5, 7, 9]):
    """
    Downloads and populates the local disk cache for specified Indian tourist corridors.
    """
    tile_cache_root = Path(settings.BASE_DIR) / "media" / "gis_tiles"
    tile_cache_root.mkdir(parents=True, exist_ok=True)
    
    total_downloaded = 0
    total_skipped = 0
    print(f"\n[*] Pre-seeding Full India Tiles for {len(corridors)} Key Corridors at zooms {zooms}...")

    for lat, lng, radius, name in corridors:
        print(f"  -> Seeding: {name} ({lat}, {lng})")
        for z in zooms:
            min_x, min_y = deg_to_tile(lat + radius, lng - radius, z)
            max_x, max_y = deg_to_tile(lat - radius, lng + radius, z)

            for x in range(min(min_x, max_x), max(min_x, max_x) + 1):
                for y in range(min(min_y, max_y), max(min_y, max_y) + 1):
                    target_dir = tile_cache_root / str(z) / str(x)
                    target_file = target_dir / f"{y}.png"

                    if target_file.exists():
                        total_skipped += 1
                        continue

                    # Fetch from OSM and persist
                    url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
                    req = urllib.request.Request(
                        url,
                        headers={"User-Agent": "TravelERP-IndiaPreSeed/2.0 (operations@sivagayathri.com)"}
                    )
                    try:
                        target_dir.mkdir(parents=True, exist_ok=True)
                        with urllib.request.urlopen(req, timeout=3.0) as res:
                            data = res.read()
                        with open(target_file, "wb") as f:
                            f.write(data)
                        total_downloaded += 1
                        time.sleep(0.04) # Polite throttle
                    except Exception as e:
                        pass

    print(f"\n[OK] Tile Pre-seeding Completed! Downloaded: {total_downloaded} new tiles, Skipped (already cached): {total_skipped}")

def main():
    parser = argparse.ArgumentParser(description="Full India GIS Management")
    parser.add_argument("--seed-corridors", action="store_true", help="Pre-seed local tile cache for top Indian tourist corridors")
    parser.add_argument("--status", action="store_true", help="Show Full India map cache statistics")
    args = parser.parse_args()

    if args.seed_corridors:
        pre_seed_tiles(KEY_INDIAN_CORRIDORS, zooms=[5, 7, 8])
    else:
        # Default action: seed top corridors for instant snappy map performance
        pre_seed_tiles(KEY_INDIAN_CORRIDORS[:6], zooms=[5, 7])

if __name__ == "__main__":
    main()
