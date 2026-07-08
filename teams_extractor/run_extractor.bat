@echo off
echo Starting Teams Extractor...
cd /d C:\TalentOpsAI\teams_extractor
call venv\Scripts\activate
python overlay.py
pause
