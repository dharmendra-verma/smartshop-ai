@echo off
title SmartShop AI - Server + Client
echo ==========================================
echo   SmartShop AI - Starting Services
echo ==========================================
echo.

:: Set project root to wherever this script lives
set "PROJECT_DIR=%~dp0"

:: Start FastAPI server in background
echo [1/2] Starting FastAPI server on http://localhost:8000 ...
start "SmartShop-FastAPI" cmd /k "cd /d "%PROJECT_DIR%" && call venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait a few seconds for the server to boot
echo       Waiting 3 seconds for server to start...
timeout /t 3 /nobreak >nul

:: Start Streamlit UI
echo [2/2] Starting Streamlit UI on http://localhost:8501 ...
start "SmartShop-Streamlit" cmd /k "cd /d "%PROJECT_DIR%" && call venv\Scripts\activate.bat && streamlit run app/ui/streamlit_app.py --server.port 8501"

echo.
echo ==========================================
echo   Both services are starting!
echo   - API:  http://localhost:8000/docs
echo   - UI:   http://localhost:8501
echo ==========================================
echo.
echo Close the two spawned terminal windows to stop the services.
pause
