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

echo [1/4] Sync dependencies (including web extras)...
uv sync --extra web
if %errorlevel% neq 0 (
    echo [ERROR] Dependency sync failed.
    pause
    exit /b 1
)
echo       Done.
echo.

echo [2/4] Running diagnostics...
uv run bco doctor
echo.

echo [3/4] Starting Web backend (http://127.0.0.1:8080) ...
start "BCO Web" cmd /c "uv run bco web"
echo       Web backend started in new window.
echo.

echo [4/4] Starting TUI Dashboard...
echo       Closing this window will stop all services.
echo.
echo ------------------------------------------
echo   Web Dashboard: http://127.0.0.1:8080
echo   Press Ctrl+C to exit Dashboard
echo ------------------------------------------
echo.
uv run bco dashboard

echo.
echo Dashboard closed. Stopping Web backend...
taskkill /fi "WINDOWTITLE eq BCO Web" >nul 2>&1
echo All services stopped.
pause
