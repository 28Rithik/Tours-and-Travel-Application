@echo off
set "USE_POSTGRES=1"

echo ======================================================================
echo 🚀 SIVAGAYATHRI TRAVEL ERP — LAUNCHING APPLICATION
echo ======================================================================
echo [*] Using Python 3.12 runtime (py -3.12)
echo.
echo 🌐 Server starting on: http://127.0.0.1:8000/
echo 👑 Rathasārathi AI Studio: http://127.0.0.1:8000/admin/operations/rathasarathi-ai/
echo 🗺️ Tour Packages:        http://127.0.0.1:8000/packages/
echo 📊 Staff Operations:      http://127.0.0.1:8000/dashboard/
echo ======================================================================
echo Press Ctrl+C to stop the server.
echo.

py -3.12 "%~dp0manage.py" runserver 127.0.0.1:8000
