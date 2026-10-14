#!/bin/sh
set -e

# ==============================================================================
# Siva Gayathri Tours & Travels — SSL/TLS Certificate Provisioning Script
# Generates high-strength 4096-bit self-signed SSL certificates for staging/local
# ==============================================================================

CERTS_DIR="${1:-./deploy/nginx/certs}"
mkdir -p "$CERTS_DIR"

if [ -f "$CERTS_DIR/fullchain.pem" ] && [ -f "$CERTS_DIR/privkey.pem" ]; then
    echo "✅ SSL certificates already exist in $CERTS_DIR. Skipping generation."
    exit 0
fi

echo "[*] Generating 4096-bit RSA SSL Private Key & Self-Signed Certificate..."
openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
    -keyout "$CERTS_DIR/privkey.pem" \
    -out "$CERTS_DIR/fullchain.pem" \
    -subj "/C=IN/ST=Tamil Nadu/L=Coimbatore/O=Siva Gayathri Tours and Travels/CN=erp.sivagayathiritravels.com" \
    -addext "subjectAltName=DNS:erp.sivagayathiritravels.com,DNS:sivagayathiritravels.com,DNS:localhost,IP:127.0.0.1"

cp "$CERTS_DIR/fullchain.pem" "$CERTS_DIR/chain.pem"
chmod 600 "$CERTS_DIR/privkey.pem"
chmod 644 "$CERTS_DIR/fullchain.pem" "$CERTS_DIR/chain.pem"

echo "✅ Generated production-grade self-signed certificates in $CERTS_DIR"
