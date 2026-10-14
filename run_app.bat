@echo off
setlocal

echo ======================================================================
echo 🚀 SIVAGAYATHRI TRAVEL ERP — LAUNCHING APPLICATION
echo ======================================================================

set "USE_POSTGRES=1"

REM Locate verified Python runtime (.venv or py -3.12)
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
    echo [*] Using virtual environment runtime: %PYTHON_EXE%
) else (
    set "PYTHON_EXE=py -3.12"
    echo [*] Using Python 3.12 launcher (py -3.12)
)

echo.
echo 🌐 Server starting on: http://127.0.0.1:8000/
echo 👑 Rathasārathi AI Studio: http://127.0.0.1:8000/admin/operations/rathasarathi-ai/
echo 🗺️ Tour Packages:        http://127.0.0.1:8000/packages/
echo 📊 Staff Operations:      http://127.0.0.1:8000/dashboard/
echo ======================================================================
echo Press Ctrl+C to stop the server.
echo.

%PYTHON_EXE% "%~dp0manage.py" runserver 127.0.0.1:8000
