import os
import math
import json
import logging
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)

LOCAL_OSRM_CLUSTER_URL = os.environ.get('OSRM_CLUSTER_URL', 'http://127.0.0.1:5000')
LOCAL_OSRM_NODE1_URL = os.environ.get('OSRM_NODE1_URL', 'http://127.0.0.1:5001')
PUBLIC_OSRM_URL = 'https://router.project-osrm.org'

# Real-time metrics store for Prometheus
OSRM_METRICS = {
    'total_queries': 0,
    'last_latency_ms': 0.0,
    'successful_queries': 0,
    'cluster_hits': 0,
}


class OSRMRoutingService:
    """
    Open Source Routing Machine (OSRM) integration service for TravelERP.
    Provides:
    - Real road network driving distances (KM)
    - Realistic travel duration & ETA (Minutes)
    - High-fidelity turn-by-turn GeoJSON route polylines
    
    Resilient Architecture:
    1. Load-Balanced OSRM Cluster (:5000 / :8089) [multi-instance, high concurrency]
    2. Direct OSRM Node 1 (:5001)
    3. Fallback to Open Public OSRM API
    4. Algorithmic Highway Factor Fallback (Haversine * 1.28 terrain curvature)
    """

    @classmethod
    def get_route(
        cls,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        steps: bool = False
    ) -> Dict[str, Any]:
        """
        Calculates driving route between two GPS coordinates with cluster failover.
        """
        import time
        start_time = time.time()
        OSRM_METRICS['total_queries'] += 1

        # 1. Try Load-Balanced OSRM Cluster (Port 5000)
        local_result = cls._query_osrm_endpoint(
            base_url=LOCAL_OSRM_CLUSTER_URL,
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            steps=steps,
            timeout=1.5
        )
        if local_result:
            duration_ms = round((time.time() - start_time) * 1000.0, 2)
            OSRM_METRICS['last_latency_ms'] = duration_ms
            OSRM_METRICS['successful_queries'] += 1
            OSRM_METRICS['cluster_hits'] += 1
            local_result["engine_used"] = "osrm_load_balanced_cluster"
            local_result["latency_ms"] = duration_ms
            return local_result

        # 2. Try Direct Node 1 (Port 5001)
        node1_result = cls._query_osrm_endpoint(
            base_url=LOCAL_OSRM_NODE1_URL,
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            steps=steps,
            timeout=2.0
        )
        if node1_result:
            duration_ms = round((time.time() - start_time) * 1000.0, 2)
            OSRM_METRICS['last_latency_ms'] = duration_ms
            OSRM_METRICS['successful_queries'] += 1
            node1_result["engine_used"] = "local_docker_osrm_node1"
            node1_result["latency_ms"] = duration_ms
            return node1_result

        # 3. Try Public OSRM Gateway
        public_result = cls._query_osrm_endpoint(
            base_url=PUBLIC_OSRM_URL,
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            steps=steps,
            timeout=3.0
        )
        if public_result:
            public_result["engine_used"] = "public_osrm"
            return public_result

        # 3. Algorithmic Fallback
        return cls._algorithmic_route_estimate(origin_lat, origin_lng, dest_lat, dest_lng)

    @classmethod
    def _query_osrm_endpoint(
        cls,
        base_url: str,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        steps: bool,
        timeout: float
    ) -> Optional[Dict[str, Any]]:
        # OSRM expects coordinates in lng,lat format
        coords = f"{origin_lng:.6f},{origin_lat:.6f};{dest_lng:.6f},{dest_lat:.6f}"
        url = f"{base_url}/route/v1/driving/{coords}?overview=full&geometries=geojson"
        if steps:
            url += "&steps=true"

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "TravelERP-OSRM-Client/1.0"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    if data.get('code') == 'Ok' and data.get('routes'):
                        route = data['routes'][0]
                        dist_km = round(route['distance'] / 1000.0, 2)
                        dur_mins = round(route['duration'] / 60.0)
                        geometry = route.get('geometry', {}).get('coordinates', [])
                        
                        return {
                            "status": "success",
                            "distance_km": dist_km,
                            "duration_minutes": dur_mins,
                            "geometry": geometry,
                            "summary": route.get('legs', [{}])[0].get('summary', 'Road route'),
                            "waypoints": data.get('waypoints', [])
                        }
        except Exception as e:
            logger.debug(f"OSRM endpoint {base_url} query failed: {e}")
        return None

    @classmethod
    def _algorithmic_route_estimate(
        cls,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> Dict[str, Any]:
        """
        High-precision mathematical estimate using Indian road curvature factor (1.25x - 1.30x).
        Generates simulated intermediate waypoints for smooth map rendering.
        """
        straight_km = cls.haversine_km(lat1, lon1, lat2, lon2)
        # Indian road network curvature coefficient
        road_km = round(straight_km * 1.28, 2)
        # Average commercial bus/car travel speed in India: ~48 km/h
        duration_mins = max(15, round((road_km / 48.0) * 60))

        # Generate 10-point interpolation for map polyline
        steps_count = 10
        coords = []
        for i in range(steps_count + 1):
            ratio = i / float(steps_count)
            # Slight S-curve perturbation for realistic road bend
            pert = math.sin(ratio * math.pi) * 0.005
            p_lat = round(lat1 + (lat2 - lat1) * ratio + pert, 6)
            p_lng = round(lon1 + (lon2 - lon1) * ratio - pert, 6)
            coords.append([p_lng, p_lat])

        return {
            "status": "estimated",
            "distance_km": road_km,
            "duration_minutes": duration_mins,
            "geometry": coords,
            "summary": "Calculated Highway Route",
            "engine_used": "algorithmic_curvature_engine"
        }

    @staticmethod
    def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (math.sin(d_lat / 2.0) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2.0) ** 2)
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c
