@echo off
rem ============================================================
rem  E-commerce CS - stop all services
rem ============================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo.
echo Stopping all containers...
docker compose down

echo.
echo [OK] All services stopped. Data volumes are kept.
echo      (To remove data as well, run: docker compose down -v)
echo.
pause
endlocal
