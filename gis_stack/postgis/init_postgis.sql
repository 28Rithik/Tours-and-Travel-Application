-- ============================================================================
-- SIVA GAYATHRI TOURS & TRAVELS — ENTERPRISE POSTGIS INITIALIZATION & TUNING
-- High-Performance Spatial Database for Fleet Telemetry & Geofencing
-- ============================================================================

-- 1. Initialize PostGIS & Spatial Extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;

-- 2. Create Schema for TravelERP Spatial Telemetry
CREATE SCHEMA IF NOT EXISTS telemetry;

-- 3. High-Performance Vehicle Live Location Table (Point in Time)
CREATE TABLE IF NOT EXISTS telemetry_vehicle_live (
    vehicle_id INT PRIMARY KEY,
    registration_number VARCHAR(50) NOT NULL,
    vehicle_type VARCHAR(50),
    current_status VARCHAR(50) DEFAULT 'standby',
    speed_kmh NUMERIC(6, 2) DEFAULT 0.0,
    heading_deg NUMERIC(6, 2) DEFAULT 0.0,
    odometer_km NUMERIC(10, 2) DEFAULT 0.0,
    fuel_level_pct NUMERIC(5, 2) DEFAULT 100.0,
    location GEOMETRY(Point, 4326),
    last_ping_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Spatial GIST Index for instantaneous proximity lookups (ST_DWithin)
CREATE INDEX IF NOT EXISTS idx_telemetry_vehicle_live_location 
ON telemetry_vehicle_live USING GIST(location);

-- Spatial Clustering on vehicle live location for maximum I/O cache locality
CLUSTER telemetry_vehicle_live USING idx_telemetry_vehicle_live_location;

-- 4. Partitioned Historical Telemetry Table (Time-Series GPS Track)
-- Range-partitioned by timestamp for high-concurrency 1-second pings
CREATE TABLE IF NOT EXISTS telemetry_vehicle_ping_partitioned (
    id BIGSERIAL,
    vehicle_id INT NOT NULL,
    trip_id INT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    location GEOMETRY(Point, 4326) NOT NULL,
    speed_kmh NUMERIC(5, 2) DEFAULT 0.0,
    heading_deg NUMERIC(5, 2) DEFAULT 0.0,
    ignition_on BOOLEAN DEFAULT TRUE,
    fuel_level_pct NUMERIC(5, 2),
    odometer_km INT,
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Monthly & Quarterly Partitions for high-throughput operational pings
CREATE TABLE IF NOT EXISTS telemetry_ping_2026_09 PARTITION OF telemetry_vehicle_ping_partitioned
    FOR VALUES FROM ('2026-09-01 00:00:00+00') TO ('2026-10-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS telemetry_ping_2026_10 PARTITION OF telemetry_vehicle_ping_partitioned
    FOR VALUES FROM ('2026-10-01 00:00:00+00') TO ('2026-11-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS telemetry_ping_2026_11 PARTITION OF telemetry_vehicle_ping_partitioned
    FOR VALUES FROM ('2026-11-01 00:00:00+00') TO ('2026-12-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS telemetry_ping_2026_12 PARTITION OF telemetry_vehicle_ping_partitioned
    FOR VALUES FROM ('2026-12-01 00:00:00+00') TO ('2027-01-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS telemetry_ping_2027_q1 PARTITION OF telemetry_vehicle_ping_partitioned
    FOR VALUES FROM ('2027-01-01 00:00:00+00') TO ('2027-04-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS telemetry_ping_default PARTITION OF telemetry_vehicle_ping_partitioned
    DEFAULT;

-- High-Performance Indexes on Partitioned Table
CREATE INDEX IF NOT EXISTS idx_ping_part_location 
ON telemetry_vehicle_ping_partitioned USING GIST(location);

CREATE INDEX IF NOT EXISTS idx_ping_part_veh_time 
ON telemetry_vehicle_ping_partitioned (vehicle_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_ping_part_brin_time 
ON telemetry_vehicle_ping_partitioned USING BRIN (timestamp);

-- 5. Geofence Polygon Boundary Table
CREATE TABLE IF NOT EXISTS telemetry_geofence_zone (
    id SERIAL PRIMARY KEY,
    zone_code VARCHAR(50) UNIQUE NOT NULL,
    zone_name VARCHAR(100) NOT NULL,
    zone_type VARCHAR(50) NOT NULL, -- 'depot', 'airport', 'techpark', 'hill_station', 'restricted'
    speed_limit_kmh INT DEFAULT 40,
    boundary GEOMETRY(Polygon, 4326),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Spatial GIST Index for polygon intersection (ST_Contains)
CREATE INDEX IF NOT EXISTS idx_telemetry_geofence_boundary 
ON telemetry_geofence_zone USING GIST(boundary);

-- 6. High-Performance Spatial Query Functions
CREATE OR REPLACE FUNCTION telemetry.fn_get_nearby_vehicles(
    p_lat DOUBLE PRECISION,
    p_lng DOUBLE PRECISION,
    p_radius_km DOUBLE PRECISION DEFAULT 10.0
)
RETURNS TABLE (
    vehicle_id INT,
    registration_number VARCHAR(50),
    distance_km DOUBLE PRECISION,
    speed_kmh NUMERIC(6, 2),
    current_status VARCHAR(50),
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        v.vehicle_id,
        v.registration_number,
        ROUND((ST_Distance(v.location::geography, ST_SetSRID(ST_MakePoint(p_lng, p_lat), 4326)::geography) / 1000.0)::numeric, 2)::double precision AS distance_km,
        v.speed_kmh,
        v.current_status,
        ST_Y(v.location)::double precision AS lat,
        ST_X(v.location)::double precision AS lng
    FROM telemetry_vehicle_live v
    WHERE ST_DWithin(
        v.location::geography,
        ST_SetSRID(ST_MakePoint(p_lng, p_lat), 4326)::geography,
        p_radius_km * 1000.0
    )
    ORDER BY distance_km ASC;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION telemetry.fn_check_geofence_status(
    p_lat DOUBLE PRECISION,
    p_lng DOUBLE PRECISION
)
RETURNS TABLE (
    zone_code VARCHAR(50),
    zone_name VARCHAR(100),
    zone_type VARCHAR(50),
    speed_limit_kmh INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        g.zone_code,
        g.zone_name,
        g.zone_type,
        g.speed_limit_kmh
    FROM telemetry_geofence_zone g
    WHERE g.is_active = TRUE
      AND ST_Contains(g.boundary, ST_SetSRID(ST_MakePoint(p_lng, p_lat), 4326));
END;
$$ LANGUAGE plpgsql STABLE;

-- 7. Seed Siva Gayathri Tours Depots & Regional Geofences
INSERT INTO telemetry_geofence_zone (zone_code, zone_name, zone_type, speed_limit_kmh, boundary)
VALUES 
(
    'CBE_HQ_DEPOT',
    'Siva Gayathri Coimbatore HQ Central Depot',
    'depot',
    25,
    ST_GeomFromText('POLYGON((76.9530 11.0140, 76.9585 11.0140, 76.9585 11.0195, 76.9530 11.0195, 76.9530 11.0140))', 4326)
),
(
    'CJB_AIRPORT_ZONE',
    'Coimbatore International Airport Zone (CJB)',
    'airport',
    40,
    ST_GeomFromText('POLYGON((77.0350 11.0250, 77.0500 11.0250, 77.0500 11.0400, 77.0350 11.0400, 77.0350 11.0250))', 4326)
),
(
    'TIDEL_TECH_PARK',
    'TIDEL Park IT Corridor Pickup Hub',
    'techpark',
    30,
    ST_GeomFromText('POLYGON((77.0180 11.0200, 77.0260 11.0200, 77.0260 11.0280, 77.0180 11.0280, 77.0180 11.0200))', 4326)
),
(
    'CHENNAI_OMR_SEZ',
    'Chennai OMR IT Highway Express Zone (Siruseri)',
    'techpark',
    50,
    ST_GeomFromText('POLYGON((80.2000 12.8200, 80.2350 12.8200, 80.2350 12.8600, 80.2000 12.8600, 80.2000 12.8200))', 4326)
),
(
    'OOTY_HILL_STATION_HUB',
    'Ooty Charring Cross & Lake Ghat Road Zone',
    'hill_station',
    35,
    ST_GeomFromText('POLYGON((76.6800 11.4000, 76.7250 11.4000, 76.7250 11.4350, 76.6800 11.4350, 76.6800 11.4000))', 4326)
),
(
    'KODAIKANAL_LAKE_HUB',
    'Kodaikanal Lake Hill Station Perimeter',
    'hill_station',
    30,
    ST_GeomFromText('POLYGON((77.4800 10.2250, 77.5100 10.2250, 77.5100 10.2500, 77.4800 10.2500, 77.4800 10.2250))', 4326)
)
ON CONFLICT (zone_code) DO NOTHING;
