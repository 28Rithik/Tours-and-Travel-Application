@echo off
setlocal

set "CERTS_DIR=%~dp0certs"
if not exist "%CERTS_DIR%" mkdir "%CERTS_DIR%"

if exist "%CERTS_DIR%\fullchain.pem" (
    echo [PASS] SSL certificates already exist in %CERTS_DIR%. Skipping generation.
    exit /b 0
)

echo [*] Generating 4096-bit RSA SSL Private Key & Self-Signed Certificate via OpenSSL...
openssl req -x509 -nodes -days 365 -newkey rsa:4096 ^
    -keyout "%CERTS_DIR%\privkey.pem" ^
    -out "%CERTS_DIR%\fullchain.pem" ^
    -subj "/C=IN/ST=Tamil Nadu/L=Coimbatore/O=Siva Gayathri Tours and Travels/CN=erp.sivagayathiritravels.com" ^
    -addext "subjectAltName=DNS:erp.sivagayathiritravels.com,DNS:sivagayathiritravels.com,DNS:localhost,IP:127.0.0.1"

copy /y "%CERTS_DIR%\fullchain.pem" "%CERTS_DIR%\chain.pem" > nul
echo [PASS] Generated SSL certificates in %CERTS_DIR%
