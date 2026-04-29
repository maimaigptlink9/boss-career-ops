@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==========================================
echo    Boss Career Ops - Quick Start
echo ==========================================
echo.

where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] uv not found. Install: https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

echo [1/3] Sync dependencies (including web extras)...
uv sync --extra web
if %errorlevel% neq 0 (
    echo [ERROR] Dependency sync failed.
    pause
    exit /b 1
)
echo       Done.
echo.

echo [2/3] Running diagnostics...
uv run bco doctor
echo.

echo [3/3] Starting Web backend (http://127.0.0.1:8080) ...
echo.
echo ------------------------------------------
echo   Web Dashboard: http://127.0.0.1:8080
echo   Press Ctrl+C to stop
echo ------------------------------------------
echo.
uv run bco web
