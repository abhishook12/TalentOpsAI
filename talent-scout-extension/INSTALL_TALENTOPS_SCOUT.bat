@echo off
title TalentOps Talent Scout - 1-Click Chrome Installer
color 0b
echo ====================================================================
echo             TALENTOPS TALENT SCOUT - INSTANT SETUP
echo ====================================================================
echo.
echo [1/2] Opening Chrome Extensions page in your browser...
start chrome://extensions/
echo.
echo [2/2] QUICK 3-STEP SETUP:
echo   ---------------------------------------------------------------
echo   1. Enable "Developer mode" (Toggle switch at top-right corner)
echo   2. Click "Load unpacked" (Button at top-left corner)
echo   3. Select THIS directory:
echo      %~dp0
echo   ---------------------------------------------------------------
echo.
echo ====================================================================
echo  Ready! Once loaded, Talent Scout captures verified leads 24/7.
echo ====================================================================
pause
