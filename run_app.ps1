# ==============================================================================
# Siva Gayathri Tours & Travels — TravelERP Application Runner (PowerShell)
# Launches the production-configured application on PostgreSQL + PostGIS + pgvector
# ==============================================================================

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "🚀 SIVAGAYATHRI TRAVEL ERP — LAUNCHING APPLICATION" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Enable PostgreSQL mode
$env:USE_POSTGRES = "1"

# 2. Locate verified Python runtime (.venv or py -3.12)
$PYTHON = "py"
$PYTHON_ARGS = @("-3.12")

if (Test-Path ".\.venv\Scripts\python.exe") {
    $PYTHON = (Resolve-Path ".\.venv\Scripts\python.exe").Path
    $PYTHON_ARGS = @()
    Write-Host "[*] Using virtual environment runtime: $PYTHON" -ForegroundColor Green
} else {
    Write-Host "[*] Using Python 3.12 launcher (py -3.12)" -ForegroundColor Green
}

# 3. Verify PostgreSQL container is running
$pg_running = docker ps --filter "name=travelerp_postgis" --format "{{.Status}}"
if ($pg_running -like "*Up*") {
    Write-Host "[*] PostgreSQL 15 + PostGIS + pgvector container is ACTIVE on port 5434." -ForegroundColor Green
} else {
    Write-Host "[!] Warning: travelerp_postgis container is not running. Starting Docker containers..." -ForegroundColor Yellow
    docker compose -f gis_stack/docker-compose.osm.yml up -d postgis
}

# 4. Display Quick Links
Write-Host ""
Write-Host "🌐 Server starting on: http://127.0.0.1:8000/" -ForegroundColor Yellow
Write-Host "👑 Rathasārathi AI Studio: http://127.0.0.1:8000/admin/operations/rathasarathi-ai/" -ForegroundColor Yellow
Write-Host "🗺️ Tour Packages:        http://127.0.0.1:8000/packages/" -ForegroundColor Yellow
Write-Host "📊 Staff Operations:      http://127.0.0.1:8000/dashboard/" -ForegroundColor Yellow
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server." -ForegroundColor Gray
Write-Host ""

# 5. Launch server
if ($PYTHON_ARGS.Count -gt 0) {
    & $PYTHON $PYTHON_ARGS manage.py runserver 127.0.0.1:8000
} else {
    & $PYTHON manage.py runserver 127.0.0.1:8000
}
