@echo off
setlocal

:loop
echo [%date% %time%] Starting TalentOps AI Outlook Bridge...
python app\scripts\local_outlook_bridge.py %*

echo [%date% %time%] Bridge process terminated with exit code %errorlevel%.
echo Restarting in 10 seconds...
timeout /t 10 /nobreak > nul
goto loop
