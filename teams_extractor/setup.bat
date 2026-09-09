@echo off
cd /d "%~dp0"
echo ====================================================
echo        Teams Extractor - Automatic Setup
echo ====================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo IMPORTANT: Make sure to CHECK "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b
)

echo [1/3] Python found. Creating virtual environment (venv)...
if not exist "venv" (
    python -m venv venv
)

echo [2/3] Activating virtual environment and upgrading pip...
call venv\Scripts\activate
python -m pip install --upgrade pip

echo [3/3] Installing required packages...
pip install -r requirements.txt

echo.
echo ====================================================
echo Setup complete! You can now run 'run_extractor.bat'.
echo ====================================================
echo.
pause
