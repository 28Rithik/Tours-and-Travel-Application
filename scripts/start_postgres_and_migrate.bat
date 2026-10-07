@echo off
title TravelERP PostgreSQL Launcher & Data Migrator
echo ======================================================================
echo 🐘 SIVAGAYATHRI TRAVEL ERP — POSTGRESQL STACK LAUNCHER & MIGRATOR
echo ======================================================================
echo.
echo [*] Step 1: Starting PostGIS container on port 5434...
docker compose -f gis_stack\docker-compose.osm.yml up -d postgis
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Docker daemon is not active. Please launch Docker Desktop from the Start Menu first.
    echo.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [*] Step 2: Running automated database migration and data parity sync...
.\.venv\Scripts\python.exe scripts\migrate_to_postgres.py

echo.
echo [*] Step 3: Launching TravelERP on PostgreSQL (port 8000)...
set USE_POSTGRES=1
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
pause
