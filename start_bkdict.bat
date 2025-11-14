@echo off
REM BKDict Vocabulary App - Launch Script for Windows
REM This script activates the conda environment and starts the Flask server

echo.
echo ========================================
echo   BKDict Vocabulary App Launcher
echo ========================================
echo.

REM Activate conda environment
echo Activating conda environment: bkdict
call conda activate bkdict

REM Check if activation was successful
if errorlevel 1 (
    echo.
    echo ERROR: Failed to activate conda environment 'bkdict'
    echo Please ensure the conda environment is created:
    echo    conda create -n bkdict python=3.11
    echo    conda activate bkdict
    echo    pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo.
echo Starting BKDict server...
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start Flask application
python app.py

pause
