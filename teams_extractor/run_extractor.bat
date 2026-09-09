@echo off
cd /d "%~dp0"
echo Starting Teams Extractor...

if not exist "venv\Scripts\activate.bat" (
    echo [WARNING] Virtual environment not found! Running setup first...
    call setup.bat
)

call venv\Scripts\activate
python overlay.py
pause
