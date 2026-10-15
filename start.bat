@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install Python 3 and add it to PATH.
    pause
    exit /b 1
)

python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Flask is not installed. Installing project requirements...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Dependency installation failed.
        pause
        exit /b 1
    )
)

set POS_SHOP_SLUG=keecoo_pos
set POS_PORT=51119
start "Keecoo POS - 51119" /D "%~dp0" cmd /k python app.py

set POS_SHOP_SLUG=workstation_specialty_coffee_pos
set POS_PORT=51120
start "Workstation Specialty Coffee POS - 51120" /D "%~dp0" cmd /k python app.py

echo Keecoo POS: http://127.0.0.1:51119/
echo Workstation Specialty Coffee POS: http://127.0.0.1:51120/
echo The shop chooser remains available with: python app.py
