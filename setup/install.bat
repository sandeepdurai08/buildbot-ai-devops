@echo off
echo ========================================================
echo      BUILDBOT ULTIMATE - INSTALLATION SCRIPT
echo ========================================================
echo.
echo Features: Dashboard, Templates, Favorites, Shortcuts,
echo           Predictions, Analytics, Scheduler, Collaboration,
echo           Rollback Manager
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ============================================
    echo   PYTHON NOT FOUND!
    echo ============================================
    echo.
    echo Python 3.10+ is required (3.14 recommended)
    echo.
    echo Opening Python download page...
    start https://www.python.org/downloads/
    echo.
    echo IMPORTANT STEPS:
    echo   1. Download Python 3.12 or higher
    echo   2. Run the installer
    echo   3. CHECK the box "Add Python to PATH"
    echo   4. Click "Install Now"
    echo   5. After installation, CLOSE this window and run again
    echo.
    pause
    exit /b 1
)

echo [OK] Python found!
python --version
echo.

REM Navigate to buildbot directory
cd /d "D:\ai module\New-task1-AI devops\buildbot"

echo ============================================
echo   INSTALLING PYTHON PACKAGES
echo ============================================
echo.
echo This may take 2-5 minutes...
echo.

pip install --upgrade pip

echo.
echo Installing BuildBot Ultimate dependencies...
echo.

pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ============================================
    echo   TRYING ALTERNATIVE INSTALLATION
    echo ============================================
    echo.
    python -m pip install streamlit httpx openai python-dotenv pydantic pydantic-settings tenacity python-dateutil aiosmtplib
)

echo.
echo ============================================
echo   CHECKING INSTALLATION
echo ============================================
echo.

python -c "import streamlit; print('[OK] Streamlit - Web UI')"
python -c "import httpx; print('[OK] HTTPX - HTTP Client')"
python -c "import pydantic; print('[OK] Pydantic - Data Validation')"
python -c "import openai; print('[OK] OpenAI - LLM Client')"
python -c "import dotenv; print('[OK] python-dotenv - Config')"
python -c "import tenacity; print('[OK] Tenacity - Retry Logic')"

echo.
echo ============================================
echo   CREATING CONFIG FILE
echo ============================================
echo.

if not exist ".env" (
    copy .env.example .env
    echo [OK] Created .env from template
    echo.
    echo IMPORTANT: You need to edit .env with your settings!
    echo.
    echo Key settings to configure:
    echo   - JENKINS_API_TOKEN (get from Jenkins UI)
    echo   - LLM_VERIFY_SSL=false (for Exterro LLM)
    echo.
    echo Opening .env file now...
    notepad .env
) else (
    echo [OK] .env already exists
)

echo.
echo ========================================================
echo   INSTALLATION COMPLETE!
echo ========================================================
echo.
echo BuildBot Ultimate is ready with 10 innovative features:
echo   - Metrics Dashboard
echo   - Quick Actions
echo   - Build Templates
echo   - Favorites System
echo   - Keyboard Shortcuts (!h, !j, !s, !r)
echo   - AI Predictions
echo   - Analytics Engine
echo   - Build Scheduler
echo   - Collaboration (@mentions)
echo   - Rollback Manager
echo.
echo NEXT STEPS:
echo   1. Edit the .env file with your Jenkins API token
echo   2. Set LLM_VERIFY_SSL=false (for Exterro)
echo   3. Run "run_buildbot.bat" from the setup folder
echo.
pause
