@echo off
echo ========================================================
echo         BUILDBOT ULTIMATE LAUNCHER
echo ========================================================
echo.
echo Starting BuildBot with 10 innovative features...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed!
    echo Please run install.bat first.
    pause
    exit /b 1
)

REM Navigate to buildbot directory
cd /d "D:\ai module\New-task1-AI devops\buildbot"

REM Check if .env exists
if not exist ".env" (
    echo ERROR: .env file not found!
    echo Please run install.bat first.
    pause
    exit /b 1
)

echo ========================================================
echo   FEATURES INCLUDED:
echo ========================================================
echo.
echo   1. Metrics Dashboard     - Real-time stats
echo   2. Quick Actions         - One-click operations
echo   3. Build Templates       - Save configurations
echo   4. Favorites System      - Star frequent jobs
echo   5. Keyboard Shortcuts    - !h, !j, !s, !r
echo   6. AI Predictions        - Success forecasting
echo   7. Analytics Engine      - Build trends
echo   8. Build Scheduler       - Recurring builds
echo   9. Collaboration         - @mentions, comments
echo  10. Rollback Manager      - Failure recovery
echo.
echo ========================================================
echo   Open your browser at: http://localhost:8501
echo ========================================================
echo.
echo Quick commands to try:
echo   help          - Show all commands
echo   list jobs     - Show Jenkins jobs
echo   !h            - Shortcut for help
echo   !r            - Rebuild last build
echo.
echo Press Ctrl+C to stop the server.
echo.

streamlit run app.py

pause
