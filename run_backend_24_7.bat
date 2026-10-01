@echo off
title TalentOps AI - 24/7 Autonomous Backend Daemon
echo ==============================================================================
echo TALENTOPS AI: 24/7 PERMANENT AUTONOMOUS BACKEND DAEMON
echo Auto-restart loop enabled. Press Ctrl+C twice to stop.
echo ==============================================================================

cd /d "c:\TalentOpsAI"
set PYTHONPATH=c:\TalentOpsAI

:loop
echo [%date% %time%] Starting FastAPI Backend and WebHarvest Engine...
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
echo.
echo [%date% %time%] Backend stopped or crashed. Restarting in 3 seconds...
timeout /t 3 /nobreak >nul
goto loop
