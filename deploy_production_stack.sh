#!/bin/sh
set -e

# ==============================================================================
# Siva Gayathri Tours & Travels — Production Docker Stack Deployment Script
# ==============================================================================

echo "======================================================================"
echo "🚀 SIVAGAYATHRI TRAVEL ERP — PRODUCTION DOCKER DEPLOYMENT"
echo "======================================================================"

# Check Docker
if ! docker info > /dev/null 2>&1; then
    echo "❌ ERROR: Docker daemon is not running."
    exit 1
fi

# 1. Validate configuration
echo "[*] Validating docker-compose.prod.yml..."
docker compose -f docker-compose.prod.yml config -q
echo "✅ Docker Compose topology verified."

# 2. Check SSL Certificates
if [ ! -f "deploy/nginx/certs/fullchain.pem" ]; then
    echo "[*] Generating SSL Certificates..."
    python3 deploy/nginx/generate_certs.py
fi

# 3. Launch stack
echo "[*] Starting Production Stack containers..."
docker compose -f docker-compose.prod.yml up -d --remove-orphans

# 4. Show status
echo ""
echo "======================================================================"
echo "📊 PRODUCTION CONTAINER CLUSTER STATUS"
echo "======================================================================"
docker compose -f docker-compose.prod.yml ps

echo ""
echo "======================================================================"
echo "🎉 PRODUCTION DEPLOYMENT ACTIVE!"
echo "   - HTTPS Web App:     https://localhost"
echo "   - HTTP Redirect:     http://localhost"
echo "   - TileServer Maps:   http://localhost:8088"
echo "   - OSRM Routing:      http://localhost:5001"
echo "   - PostgreSQL Port:   localhost:5434"
echo "======================================================================"
