"""
Core GIS & Full India Map Engine for TravelERP.
Provides:
1. Native Full India Slippy Tile Server & High-Speed Disk Cache (/gis/tiles/<z>/<x>/<y>.png)
2. Direct MBTiles Reader (SQLite) for offline pre-packaged India maps
3. India GIS Status & Cache Diagnostics API
"""

import os
import sqlite3
import urllib.request
import logging
from django.http import HttpResponse, JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)

TILE_CACHE_DIR = os.path.join(settings.BASE_DIR, 'media', 'gis_tiles')
MBTILES_PATH = os.path.join(settings.BASE_DIR, 'gis_stack', 'tileserver', 'india-osm.mbtiles')

# 1x1 transparent PNG fallback for missing or errored tiles
TRANSPARENT_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06'
    b'\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01'
    b'H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82'
)


def full_india_tile_proxy_view(request, z: int, x: int, y: int):
    """
    High-Speed Native Tile Server & Persistent Edge Cache for Full India.
    Flow:
    1. Check local persistent disk cache: media/gis_tiles/<z>/<x>/<y>.png
    2. Check local MBTiles SQLite database if available
    3. Stream from OpenStreetMap CDN, persist to disk for future offline requests, and return
    """
    # Restrict zooms to standard web bounds (0 to 19)
    if z < 0 or z > 19:
        return HttpResponse(TRANSPARENT_PNG, content_type='image/png')

    # 1. Check local disk cache
    tile_subdir = os.path.join(TILE_CACHE_DIR, str(z), str(x))
    tile_filepath = os.path.join(tile_subdir, f"{y}.png")

    if os.path.exists(tile_filepath):
        try:
            with open(tile_filepath, 'rb') as f:
                content = f.read()
            resp = HttpResponse(content, content_type='image/png')
            resp['Cache-Control'] = 'public, max-age=2592000'  # 30 days immutable
            resp['X-Tile-Engine'] = 'TravelERP-India-LocalDisk'
            return resp
        except Exception as e:
            logger.warning(f"Error reading cached tile {z}/{x}/{y}: {e}")

    # 2. Check local MBTiles SQLite file if present and valid
    if os.path.exists(MBTILES_PATH) and os.path.getsize(MBTILES_PATH) > 50000:
        try:
            # Slippy map y to TMS y conversion: tms_y = (2^zoom - 1) - y
            tms_y = (1 << z) - 1 - y
            conn = sqlite3.connect(MBTILES_PATH, timeout=1.0)
            cur = conn.cursor()
            cur.execute(
                "SELECT tile_data FROM tiles WHERE zoom_level = ? AND tile_column = ? AND tile_row = ? LIMIT 1",
                (z, x, tms_y)
            )
            row = cur.fetchone()
            conn.close()
            if row and row[0]:
                tile_data = row[0]
                resp = HttpResponse(tile_data, content_type='image/png')
                resp['Cache-Control'] = 'public, max-age=2592000'
                resp['X-Tile-Engine'] = 'TravelERP-India-MBTiles'
                return resp
        except Exception as e:
            logger.debug(f"MBTiles lookup skip for {z}/{x}/{y}: {e}")

    # 3. Stream from Upstream OpenStreetMap CDN and save to local disk cache
    upstream_url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    req = urllib.request.Request(
        upstream_url,
        headers={
            'User-Agent': 'TravelERP-IndiaFleetGIS/2.0 (operations@sivagayathri.com)',
            'Accept': 'image/png,image/*;q=0.8'
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=3.5) as response:
            content = response.read()

        # Save to disk cache asynchronously / directly
        try:
            os.makedirs(tile_subdir, exist_ok=True)
            with open(tile_filepath, 'wb') as f:
                f.write(content)
        except Exception as write_err:
            logger.warning(f"Failed to cache tile to disk: {write_err}")

        resp = HttpResponse(content, content_type='image/png')
        resp['Cache-Control'] = 'public, max-age=2592000'
        resp['X-Tile-Engine'] = 'TravelERP-India-UpstreamCached'
        return resp
    except Exception as fetch_err:
        logger.debug(f"Tile fetch failed for {z}/{x}/{y}: {fetch_err}")
        # Return transparent 1x1 png on network timeout/error so map renders smoothly without broken image icons
        resp = HttpResponse(TRANSPARENT_PNG, content_type='image/png')
        resp['X-Tile-Engine'] = 'TravelERP-Fallback'
        return resp


def api_india_gis_status_view(request):
    """
    Returns diagnostic metrics on Full India map caching and storage.
    """
    cached_tiles_count = 0
    total_bytes = 0

    if os.path.exists(TILE_CACHE_DIR):
        for root, _, files in os.walk(TILE_CACHE_DIR):
            for file in files:
                if file.endswith('.png'):
                    cached_tiles_count += 1
                    try:
                        total_bytes += os.path.getsize(os.path.join(root, file))
                    except Exception:
                        pass

    mbtiles_exists = os.path.exists(MBTILES_PATH)
    mbtiles_size_mb = round(os.path.getsize(MBTILES_PATH) / (1024 * 1024), 2) if mbtiles_exists else 0.0

    return JsonResponse({
        'status': 'success',
        'engine': 'TravelERP Full India Native GIS Engine',
        'mbtiles_installed': mbtiles_exists and mbtiles_size_mb > 1.0,
        'mbtiles_path': MBTILES_PATH,
        'mbtiles_size_mb': mbtiles_size_mb,
        'cached_tiles_count': cached_tiles_count,
        'disk_cache_mb': round(total_bytes / (1024 * 1024), 2),
        'tile_endpoint': '/gis/tiles/{z}/{x}/{y}.png',
        'coverage_bounds': {
            'country': 'India',
            'min_lat': 6.4627,
            'max_lat': 37.0841,
            'min_lng': 68.1097,
            'max_lng': 97.3953
        }
    })
