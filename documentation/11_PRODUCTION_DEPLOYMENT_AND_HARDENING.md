# 🚢 SIVA GAYATHRI TOURS & TRAVELS — TRAVELERP
## Chapter 11: Production Docker Stack, Architecture & Deployment Hardening

---

### 1. Production Architecture Overview

The Siva Gayathri TravelERP production deployment is an enterprise-hardened, containerized micro-topology engineered for high-concurrency fleet telematics, sub-second AI operations, spatial routing, and zero-downtime reliability.

```mermaid
graph TD
    Client[("🌐 Public & Staff Clients (HTTPS / WSS)")] -->|Port 443 / TLS 1.3| Nginx["🛡️ Nginx Reverse Proxy & Edge Cache\n(Rate Limiting, HSTS, Brotli/Gzip)"]
    Client -.->|Port 80 / HTTP| NginxRedirect["HTTP to HTTPS 301 Redirect"]
    
    Nginx -->|Static Assets / Cache 1yr| StaticVol["📁 Static Files Volume"]
    Nginx -->|Inspection Media / PDFs| MediaVol["📁 Media Files Volume"]
    Nginx -->|ASGI Proxy / WebSockets| WebApp["⚡ TravelERP Core Web App\n(Daphne / Gunicorn + Uvicorn Workers)"]
    
    WebApp -->|ORM Queries & Vector Search| PostGIS[("🐘 PostgreSQL 15 + PostGIS 3.4 + pgvector 0.8.0\n(78,000+ Records, Port 5434 / 5432)")]
    WebApp -->|Channels & Cache| Redis[("⚡ Redis 7 Cache & Channel Layer\n(Port 6379, Memory-Capped LRU)")]
    WebApp -->|Sub-second LLaMA/Qwen Function Calling| Groq["👑 Groq Cloud API (Rathasārathi AI)"]
    WebApp -->|TSP Route Optimization| OSRM["🗺️ OSRM India Routing Engine (Port 5001)"]
    WebApp -->|Vector / Raster Map Tiles| TileServer["🗾 TileServer GL (Port 8088)"]
    
    BackupDaemon["🛡️ Automated Backup Service (Cron 02:00 AM)"] -->|pg_dump -Fc + SHA-256| PostGIS
    BackupDaemon -->|Daily Compressed Snapshots| BackupVol["💾 Backup Storage Volume (14-day retention)"]
```

---

### 2. Containerized Services Inventory

| Service Name | Container Name | Base Image | Role & Capabilities | Ports (Host:Container) |
| :--- | :--- | :--- | :--- | :--- |
| **`web`** | `travelerp_web` | Custom Multi-Stage `python:3.12-slim` | Core Django ASGI web application with Daphne & Channels | Internal `8000` |
| **`postgis`** | `travelerp_postgis` | `postgis/postgis:15-3.4` + `pgvector` | Relational, spatial PostGIS geometries, and vector embeddings | `5434:5432` |
| **`redis`** | `travelerp_redis` | `redis:7-alpine` | Channel layer for real-time fleet radar & distributed cache | Internal `6379` |
| **`backup`** | `travelerp_backup` | `postgres:15-alpine` | Automated daily 02:00 AM pg_dump with SHA-256 verification | None (Internal) |
| **`nginx`** | `travelerp_nginx` | `nginx:alpine` | SSL termination, HTTP/2, WebSocket upgrade proxy, rate-limiting | `80:80`, `443:443` |
| **`tileserver`**| `travelerp_tileserver`| `maptiler/tileserver-gl:latest` | Self-hosted vector and raster map tiles (MaxZoom 20) | `8088:8080` |
| **`osrm`** | `travelerp_osrm` | `osrm/osrm-backend:latest` | Sub-10ms distance matrices and multi-stop TSP routing | `5001:5000` |

---

### 3. Edge Security & Reverse Proxy Hardening (`deploy/nginx/`)

1. **TLS / SSL Protocols & Cipher Suites**:
   - Enforces **TLSv1.2 and TLSv1.3** only (disables obsolete SSLv3, TLSv1.0, and TLSv1.1).
   - High-strength ECDHE-RSA and ECDHE-ECDSA cipher suites with forward secrecy.
2. **DDoS & Brute-Force Rate Limiting**:
   - General API endpoints: Rate-limited to **30 req/sec** (`travelerp_api_rate`) with burst tolerance of 50.
   - Authentication endpoints (`/accounts/login/`): Rate-limited to **5 req/sec** (`travelerp_login_rate`) with burst tolerance of 10 to thwart brute-force password guessing.
3. **Security Headers**:
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload` (HSTS)
   - `X-Frame-Options: SAMEORIGIN` (prevents clickjacking)
   - `X-Content-Type-Options: nosniff` (prevents MIME sniffing)
   - `Referrer-Policy: strict-origin-when-cross-origin`
4. **WebSocket Upgrade Support**:
   - Direct proxy headers for real-time WebSocket communication:
     ```nginx
     proxy_set_header Upgrade $http_upgrade;
     proxy_set_header Connection $connection_upgrade;
     ```

---

### 4. Automated Backup & Disaster Recovery (`deploy/backup/`)

- **Backup Execution Script:** [`deploy/backup/backup_postgres.sh`](file:///c:/Users/rithi/Documents/Documents%20Project%20Intership%20and%20Course/Projects/Rag%20chatbot/Tours%20and%20Travel%20Application/deploy/backup/backup_postgres.sh)
- **Disaster Recovery Restore Script:** [`deploy/backup/restore_postgres.sh`](file:///c:/Users/rithi/Documents/Documents%20Project%20Intership%20and%20Course/Projects/Rag%20chatbot/Tours%20and%20Travel%20Application/deploy/backup/restore_postgres.sh)
- **Features:**
  1. Dumps database in custom format (`pg_dump -F c`) with native zlib compression.
  2. Verifies archive integrity using `pg_restore --list`.
  3. Computes SHA-256 cryptographic checksum.
  4. Generates audit JSON metadata file with package and itinerary record counts.
  5. Implements a 14-day automated retention policy, pruning expired snapshots automatically.

---

### 5. Production Operations Runbook

#### A. Starting the Full Stack
```bash
# Windows:
deploy_production_stack.bat

# Linux / macOS:
chmod +x deploy_production_stack.sh
./deploy_production_stack.sh
```

#### B. Checking Container Health & Logs
```bash
# Check all containers status:
docker compose -f docker-compose.prod.yml ps

# View live web application logs:
docker compose -f docker-compose.prod.yml logs -f web

# View live Nginx access & error logs:
docker compose -f docker-compose.prod.yml logs -f nginx
```

#### C. Triggering an On-Demand Database Backup
```bash
docker compose -f docker-compose.prod.yml exec backup /scripts/backup_postgres.sh
```

#### D. Restoring Database from a Snapshot
```bash
docker compose -f docker-compose.prod.yml exec backup /scripts/restore_postgres.sh /backups/travelerp_db_travel_erp_gis_YYYYMMDD_HHMMSS.dump
```

#### E. Running Production Validation Audit Suite
```bash
py -3.12 scripts/test_production_docker_stack.py
```

---

### 6. High-Performance Caching & In-Memory Session Architecture

TravelERP incorporates a multi-tiered caching subsystem engineered for sub-50ms live operational latency:

1. **`cached_db` In-Memory Session Acceleration**:
   - `SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'`
   - Bypasses SQL database queries on authenticated page requests by reading session payloads directly from memory cache, while writing updates through to the database for durability across service restarts.
2. **Consolidated Redis & LocMem Cache Tier**:
   - Primary: `django_redis.cache.RedisCache` with connection pooling (`max_connections=50`), 2-second connection timeouts, and automatic retry.
   - Fallback: High-capacity `LocMemCache` (`max_entries=5000`) enabling development and standalone operation with zero external dependencies.
3. **ASGI Redis Channel Layer (`channels-redis 4.3`)**:
   - Real-time fleet tracking radar and operational broadcast WebSocket pipelines utilize `channels_redis.core.RedisChannelLayer` with automatic fallback to `InMemoryChannelLayer`.
4. **WhiteNoise 1-Year Immutable Asset Storage**:
   - `WHITENOISE_MAX_AGE = 31536000` (1 Year).
   - Production storage uses `CompressedManifestStaticFilesStorage` to generate content-hashed filenames (e.g. `base-ui.7b82f18c.css`), allowing permanent browser caching and instant edge delivery.
5. **GZip Compression Middleware**:
   - `django.middleware.gzip.GZipMiddleware` placed at the top of the middleware stack delivers an average **81.5% wire reduction** across HTML and JSON API responses.
6. **SQLite WAL Mode for High HTMX Concurrency**:
   - `PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA cache_size=10000; PRAGMA temp_store=MEMORY;` eliminates database lock contention during concurrent partial HTMX refreshes.

