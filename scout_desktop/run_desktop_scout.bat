@echo off
cd /d "c:\TalentOpsAI"
set PYTHONPATH=c:\TalentOpsAI;%PYTHONPATH%
start "" "c:\TalentOpsAI\teams_extractor\venv\Scripts\pythonw.exe" -m scout_desktop.app
exit
