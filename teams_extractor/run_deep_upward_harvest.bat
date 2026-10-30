@echo off
title TalentOps AI - Teams Deep Upward Autonomous Ingestion Engine
cd /d "%~dp0"

echo ======================================================================
echo  TalentOps AI - Deep Upward Microsoft Teams Ingestion Engine
echo  Starts at Bottom of Chat and Harvests Upwards Into History
echo  Extracts 100%% of Candidate Details (Multi-Phone, Multi-Email, Entities)
echo ======================================================================

set PYTHON_EXE=venv\Scripts\python.exe
if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python
)

echo Starting deep upward harvesting for group chat: CTV- Phone numbers (Duration: 2 Hours = 7200s)...
%PYTHON_EXE% deep_upward_extractor.py --chat "CTV- Phone numbers" --duration 7200 --delay 1.8

pause
