@echo off
title TalentOps AI - Teams Background Autonomous Ingestion Engine
cd /d "%~dp0"

echo ======================================================================
echo  TalentOps AI - Headless Microsoft Teams Background Ingestion Engine
echo  Runs 100%% in Background via UIA - No Screen Coordinate/Overlay Dependency
echo ======================================================================

set PYTHON_EXE=venv\Scripts\python.exe
if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python
)

echo Starting background extraction loop for group chat: CTV- Phone numbers...
%PYTHON_EXE% background_teams_extractor.py --chat "CTV- Phone numbers" --interval 30
pause
