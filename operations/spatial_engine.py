import os
import math
import logging
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)

# Default connection settings for TravelERP PostGIS container
POSTGIS_HOST = os.environ.get('POSTGIS_HOST', '127.0.0.1')
POSTGIS_PORT = int(os.environ.get('POSTGIS_PORT', '5434'))
POSTGIS_DB = os.environ.get('POSTGIS_DB', 'travel_erp_gis')
POSTGIS_USER = os.environ.get('POSTGIS_USER', 'travel_gis_user')
POSTGIS_PASS = os.environ.get('POSTGIS_PASS', 'travel_gis_pass')


def get_postgis_connection():
    """
    Returns a raw psycopg2 connection to the PostGIS spatial database.
    Returns None if connection fails.
    """
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=POSTGIS_HOST,
            port=POSTGIS_PORT,
            database=POSTGIS_DB,
            user=POSTGIS_USER,
            password=POSTGIS_PASS,
            connect_timeout=2
        )
        return conn
    except Exception as e:
        logger.debug(f"PostGIS database not reachable on {POSTGIS_HOST}:{POSTGIS_PORT}: {e}")
        return None


class SpatialEngine:
    """
    High-performance Spatial Engine for TravelERP.
    Leverages PostgreSQL 15 + PostGIS 3.4 for O(1) GIST indexed spatial lookups:
    - ST_Contains for geofence boundary breaches
    - ST_DWithin for vehicle nearest-neighbor dispatching
    - ST_Distance for proximity metrics
    Includes robust zero-failure in-memory fallback for offline/development environments.
    """

    @classmethod
    def is_postgis_ready(cls) -> bool:
        conn = get_postgis_connection()
        if not conn:
            return False
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT PostGIS_Version();")
                _ = cur.fetchone()
            conn.close()
            return True
        except Exception:
            return False

    @classmethod
    def sync_django_geofences_to_postgis(cls) -> int:
        """
        Synchronizes Django's GeofenceZone models into the PostGIS telemetry_geofence_zone table,
        converting circular lat/lng + radius into true spatial polygon geometries via ST_Buffer.
        """
        from operations.models import GeofenceZone
        zones = GeofenceZone.objects.filter(is_active=True)

        conn = get_postgis_connection()
        if not conn:
            logger.info("PostGIS not connected; skipping spatial geofence sync.")
            return 0

        synced_count = 0
        try:
            with conn.cursor() as cur:
                for z in zones:
                    zone_code = f"ZONE_{z.id}"
                    zone_name = z.name
                    zone_type = z.zone_type
                    speed_limit = z.speed_limit_kmh
                    lat = float(z.latitude)
                    lng = float(z.longitude)
                    radius = float(z.radius_meters)

                    # Build polygon boundary via ST_Buffer on geography point, cast back to geometry
                    query = """
                    INSERT INTO telemetry_geofence_zone 
                    (zone_code, zone_name, zone_type, speed_limit_kmh, boundary, is_active)
                    VALUES (
                        %s, %s, %s, %s,
                        ST_Buffer(ST_SetSRID(ST_Point(%s, %s), 4326)::geography, %s)::geometry,
                        TRUE
                    )
                    ON CONFLICT (zone_code) DO UPDATE 
                    SET zone_name = EXCLUDED.zone_name,
                        zone_type = EXCLUDED.zone_type,
                        speed_limit_kmh = EXCLUDED.speed_limit_kmh,
                        boundary = EXCLUDED.boundary,
                        is_active = TRUE;
                    """
                    cur.execute(query, (zone_code, zone_name, zone_type, speed_limit, lng, lat, radius))
                    synced_count += 1
                conn.commit()
            conn.close()
            return synced_count
        except Exception as e:
            logger.error(f"Failed to sync geofences to PostGIS: {e}")
            if conn:
                conn.close()
            return 0

    @classmethod
    def record_live_telemetry(
        cls,
        vehicle_id: int,
        registration_number: str,
        vehicle_type: str,
        current_status: str,
        lat: float,
        lng: float,
        speed_kmh: float = 0.0,
        heading_deg: float = 0.0,
        odometer_km: float = 0.0,
        fuel_level_pct: float = 100.0
    ) -> bool:
        """
        Records or updates real-time vehicle GPS ping in PostGIS with spatial GIST indexing.
        """
        conn = get_postgis_connection()
        if not conn:
            return False

        try:
            with conn.cursor() as cur:
                query = """
                INSERT INTO telemetry_vehicle_live 
                (vehicle_id, registration_number, vehicle_type, current_status, speed_kmh, heading_deg, odometer_km, fuel_level_pct, location, last_ping_at)
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    ST_SetSRID(ST_Point(%s, %s), 4326),
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (vehicle_id) DO UPDATE 
                SET registration_number = EXCLUDED.registration_number,
                    vehicle_type = EXCLUDED.vehicle_type,
                    current_status = EXCLUDED.current_status,
                    speed_kmh = EXCLUDED.speed_kmh,
                    heading_deg = EXCLUDED.heading_deg,
                    odometer_km = EXCLUDED.odometer_km,
                    fuel_level_pct = EXCLUDED.fuel_level_pct,
                    location = EXCLUDED.location,
                    last_ping_at = CURRENT_TIMESTAMP;
                """
                cur.execute(query, (
                    vehicle_id, registration_number, vehicle_type, current_status,
                    speed_kmh, heading_deg, odometer_km, fuel_level_pct,
                    lng, lat
                ))
                conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"PostGIS live telemetry record failed: {e}")
            if conn:
                conn.close()
            return False

    @classmethod
    def check_geofence_breach(cls, lat: float, lng: float, speed_kmh: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Checks if the coordinate (lat, lng) lies inside any active PostGIS Geofence Zone.
        Returns a list of breached zones with details and hazard status.
        """
        conn = get_postgis_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    query = """
                    SELECT zone_code, zone_name, zone_type, speed_limit_kmh,
                           ST_Contains(boundary, ST_SetSRID(ST_Point(%s, %s), 4326)) AS inside
                    FROM telemetry_geofence_zone
                    WHERE is_active = TRUE
                      AND ST_Contains(boundary, ST_SetSRID(ST_Point(%s, %s), 4326)) = TRUE;
                    """
                    cur.execute(query, (lng, lat, lng, lat))
                    rows = cur.fetchall()
                    breaches = []
                    for row in rows:
                        zone_code, zone_name, zone_type, speed_limit, _ = row
                        is_speeding = (speed_kmh is not None and speed_kmh > speed_limit)
                        is_restricted = (zone_type == 'restricted')
                        breaches.append({
                            "zone_code": zone_code,
                            "zone_name": zone_name,
                            "zone_type": zone_type,
                            "speed_limit_kmh": speed_limit,
                            "is_speeding": is_speeding,
                            "is_restricted": is_restricted,
                            "alert_text": "Speeding violation" if is_speeding else ("Restricted zone" if is_restricted else "Inside zone")
                        })
                    conn.close()
                    return breaches
            except Exception as e:
                logger.error(f"PostGIS geofence query failed, falling back to Python: {e}")
                if conn:
                    conn.close()

        # Fallback to Django SQLite models with Haversine distance
        return cls._fallback_check_geofence(lat, lng, speed_kmh)

    @classmethod
    def find_nearest_vehicles(
        cls,
        lat: float,
        lng: float,
        max_distance_meters: float = 30000.0,
        vehicle_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Finds nearest vehicles within max_distance_meters using PostGIS ST_DWithin and ST_Distance.
        """
        conn = get_postgis_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    where_clauses = ["ST_DWithin(location::geography, ST_SetSRID(ST_Point(%s, %s), 4326)::geography, %s)"]
                    params: List[Any] = [lng, lat, max_distance_meters]

                    if vehicle_type:
                        where_clauses.append("vehicle_type = %s")
                        params.append(vehicle_type)

                    query = f"""
                    SELECT vehicle_id, registration_number, vehicle_type, current_status, speed_kmh,
                           ST_Distance(location::geography, ST_SetSRID(ST_Point(%s, %s), 4326)::geography) AS distance_meters
                    FROM telemetry_vehicle_live
                    WHERE {' AND '.join(where_clauses)}
                    ORDER BY distance_meters ASC
                    LIMIT %s;
                    """
                    # Add point for distance calculation
                    full_params = [lng, lat] + params + [limit]
                    cur.execute(query, full_params)
                    rows = cur.fetchall()
                    results = []
                    for row in rows:
                        results.append({
                            "vehicle_id": row[0],
                            "registration_number": row[1],
                            "vehicle_type": row[2],
                            "status": row[3],
                            "speed_kmh": float(row[4] or 0),
                            "distance_meters": round(float(row[5]), 1),
                            "distance_km": round(float(row[5]) / 1000.0, 2)
                        })
                    conn.close()
                    return results
            except Exception as e:
                logger.error(f"PostGIS nearest vehicle search failed: {e}")
                if conn:
                    conn.close()

        # Fallback to Django models
        return cls._fallback_find_nearest_vehicles(lat, lng, max_distance_meters, limit)

    # =========================================================================
    # Resilient In-Memory / SQLite Fallback Logic
    # =========================================================================
    @classmethod
    def _fallback_check_geofence(cls, lat: float, lng: float, speed_kmh: Optional[float] = None) -> List[Dict[str, Any]]:
        try:
            from operations.models import GeofenceZone
            zones = GeofenceZone.objects.filter(is_active=True)
            breaches = []
            for z in zones:
                dist_m = cls.haversine_distance_meters(lat, lng, float(z.latitude), float(z.longitude))
                if dist_m <= z.radius_meters:
                    is_speeding = (speed_kmh is not None and speed_kmh > z.speed_limit_kmh)
                    is_restricted = (z.zone_type == 'restricted_zone')
                    breaches.append({
                        "zone_code": f"ZONE_{z.id}",
                        "zone_name": z.name,
                        "zone_type": z.zone_type,
                        "speed_limit_kmh": z.speed_limit_kmh,
                        "is_speeding": is_speeding,
                        "is_restricted": is_restricted,
                        "alert_text": "Speeding violation" if is_speeding else ("Restricted zone" if is_restricted else "Inside zone")
                    })
            return breaches
        except Exception:
            return []

    @classmethod
    def _fallback_find_nearest_vehicles(cls, lat: float, lng: float, max_dist_m: float, limit: int) -> List[Dict[str, Any]]:
        try:
            from core.models import Vehicle
            from operations.models import VehicleTelematicsPing
            vehicles = Vehicle.objects.filter(status__in=['available', 'on_trip', 'standby'])
            found = []
            for v in vehicles:
                last_ping = VehicleTelematicsPing.objects.filter(vehicle=v).order_by('-timestamp').first()
                if last_ping:
                    dist_m = cls.haversine_distance_meters(lat, lng, float(last_ping.latitude), float(last_ping.longitude))
                    if dist_m <= max_dist_m:
                        found.append({
                            "vehicle_id": v.id,
                            "registration_number": v.registration_number,
                            "vehicle_type": str(v.vehicle_type) if v.vehicle_type else "Vehicle",
                            "status": v.status,
                            "speed_kmh": float(last_ping.speed_kmh),
                            "distance_meters": round(dist_m, 1),
                            "distance_km": round(dist_m / 1000.0, 2)
                        })
            found.sort(key=lambda x: x["distance_meters"])
            return found[:limit]
        except Exception:
            return []

    @staticmethod
    def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371000.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)
        a = math.sin(d_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    @classmethod
    def record_partitioned_telemetry_ping(
        cls,
        vehicle_id: int,
        lat: float,
        lng: float,
        speed_kmh: float = 0.0,
        heading_deg: float = 0.0,
        trip_id: Optional[int] = None,
        fuel_level_pct: Optional[float] = None,
        odometer_km: Optional[int] = None,
        timestamp: Optional[Any] = None
    ) -> bool:
        """
        Inserts a GPS telemetry point into the high-performance partitioned table
        telemetry_vehicle_ping_partitioned. Routes to current partition with GiST indexing.
        """
        conn = get_postgis_connection()
        if not conn:
            return False
        try:
            with conn.cursor() as cur:
                ts_clause = "CURRENT_TIMESTAMP" if not timestamp else "%s"
                query = f"""
                INSERT INTO telemetry_vehicle_ping_partitioned
                (vehicle_id, trip_id, timestamp, location, speed_kmh, heading_deg, fuel_level_pct, odometer_km)
                VALUES (%s, %s, {ts_clause}, ST_SetSRID(ST_Point(%s, %s), 4326), %s, %s, %s, %s);
                """
                params = [vehicle_id, trip_id]
                if timestamp:
                    params.append(timestamp)
                params.extend([lng, lat, speed_kmh, heading_deg, fuel_level_pct, odometer_km])
                cur.execute(query, params)
                conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"PostGIS partitioned telemetry insert failed: {e}")
            if conn:
                conn.close()
            return False

    @classmethod
    def query_vehicle_trajectory_partitioned(
        cls,
        vehicle_id: int,
        start_time: Any,
        end_time: Any,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """
        Queries GPS trajectory from partitioned telemetry table utilizing partition pruning and BRIN indexes.
        """
        conn = get_postgis_connection()
        if not conn:
            return []
        try:
            with conn.cursor() as cur:
                query = """
                SELECT id, timestamp, ST_Y(location) AS lat, ST_X(location) AS lng,
                       speed_kmh, heading_deg, fuel_level_pct, odometer_km
                FROM telemetry_vehicle_ping_partitioned
                WHERE vehicle_id = %s
                  AND timestamp >= %s
                  AND timestamp <= %s
                ORDER BY timestamp ASC
                LIMIT %s;
                """
                cur.execute(query, (vehicle_id, start_time, end_time, limit))
                rows = cur.fetchall()
                results = []
                for row in rows:
                    p_id, ts, lat, lng, speed, heading, fuel, odo = row
                    results.append({
                        "id": p_id,
                        "timestamp": ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
                        "latitude": float(lat),
                        "longitude": float(lng),
                        "speed_kmh": float(speed) if speed is not None else 0.0,
                        "heading_deg": float(heading) if heading is not None else 0.0,
                        "fuel_level_pct": float(fuel) if fuel is not None else None,
                        "odometer_km": odo
                    })
                conn.close()
                return results
        except Exception as e:
            logger.error(f"PostGIS partitioned trajectory query failed: {e}")
            if conn:
                conn.close()
            return []

    @classmethod
    def find_nearby_vehicles_stored_proc(
        cls,
        lat: float,
        lng: float,
        radius_km: float = 10.0
    ) -> List[Dict[str, Any]]:
        """
        Calls high-speed stored procedure telemetry.fn_get_nearby_vehicles in PostGIS.
        """
        conn = get_postgis_connection()
        if not conn:
            return []
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM telemetry.fn_get_nearby_vehicles(%s, %s, %s);", (lat, lng, radius_km))
                rows = cur.fetchall()
                results = []
                for r in rows:
                    v_id, reg_no, dist_km, speed, status, v_lat, v_lng = r
                    results.append({
                        "vehicle_id": v_id,
                        "registration_number": reg_no,
                        "distance_km": float(dist_km),
                        "speed_kmh": float(speed) if speed is not None else 0.0,
                        "current_status": status,
                        "latitude": float(v_lat),
                        "longitude": float(v_lng)
                    })
                conn.close()
                return results
        except Exception as e:
            logger.error(f"PostGIS stored procedure fn_get_nearby_vehicles failed: {e}")
            if conn:
                conn.close()
            return []

