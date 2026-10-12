@echo off
rem ============================================================
rem  E-commerce CS - one click start (double click me)
rem  Builds and starts ALL services with Docker, then opens
rem  the browser automatically at http://localhost:8080
rem ============================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
    echo.
    echo [ERROR] Docker command not found.
    echo         Please install and start Docker Desktop first.
    echo.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
set "RC=%ERRORLEVEL%"

echo.
pause
endlocal
exit /b %RC%
