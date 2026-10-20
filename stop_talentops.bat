@echo off
title TalentOps AI - Stop Local Services
color 0c
echo ==============================================================================
echo                      STOPPING TALENTOPS AI LOCAL SERVICES
echo ==============================================================================
echo.

echo Stopping TalentOps Supervisor, Backend, and Frontend...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*talentops_supervisor*' -or $_.CommandLine -like '*uvicorn*backend.app.main:app*' -or $_.CommandLine -like '*vite.js*' -or $_.CommandLine -like '*autostart_talentops*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

echo.
echo [OK] All local TalentOps AI background services stopped.
echo ==============================================================================
timeout /t 3 >nul
