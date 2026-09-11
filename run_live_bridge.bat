@echo off
title TalentOps Live AI Screenshot Ingestion Bridge
echo ======================================================================
echo >> Starting TalentOps Live AI Screenshot Ingestion Bridge
echo >> Auto-uploading to: https://talentopsai-1.onrender.com
echo ======================================================================
cd /d %~dp0
python scout_desktop/live_ai_bridge.py
pause
