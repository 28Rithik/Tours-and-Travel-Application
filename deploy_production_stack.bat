@echo off
setlocal

echo ======================================================================
echo 🚀 SIVAGAYATHRI TRAVEL ERP — PRODUCTION DOCKER DEPLOYMENT
echo ======================================================================

REM Check Docker daemon
docker info > nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Docker daemon is not running. Please start Docker Desktop first.
    exit /b 1
)

REM 1. Validate Docker Compose Config
echo [*] Validating docker-compose.prod.yml configuration...
docker compose -f docker-compose.prod.yml config -q
if errorlevel 1 (
    echo ❌ ERROR: docker-compose.prod.yml validation failed.
    exit /b 1
)
echo [PASS] Docker Compose topology verified.

REM 2. Ensure SSL Certificates exist
if not exist "deploy\nginx\certs\fullchain.pem" (
    echo [*] Generating SSL Certificates...
    py -3.12 deploy\nginx\generate_certs.py
)

REM 3. Launch Stack in Detached Mode
echo [*] Starting Production Stack containers...
docker compose -f docker-compose.prod.yml up -d --remove-orphans

REM 4. Check Container Status
echo.
echo ======================================================================
echo 📊 PRODUCTION CONTAINER CLUSTER STATUS
echo ======================================================================
docker compose -f docker-compose.prod.yml ps

echo.
echo ======================================================================
echo 🎉 PRODUCTION DEPLOYMENT ACTIVE!
echo   - HTTPS Web App:     https://localhost
echo   - HTTP Redirect:     http://localhost
echo   - TileServer Maps:   http://localhost:8088
echo   - OSRM Routing:      http://localhost:5001
echo   - PostgreSQL Port:   localhost:5434
echo ======================================================================
