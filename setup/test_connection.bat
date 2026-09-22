@echo off
echo ========================================================
echo      BUILDBOT ULTIMATE - CONNECTION TEST
echo ========================================================
echo.

cd /d "D:\ai module\New-task1-AI devops\buildbot"

echo ============================================
echo   1. Checking Python Version
echo ============================================
python --version
if %errorlevel% neq 0 (
    echo [FAIL] Python not found!
    goto :end
)
echo [OK] Python installed
echo.

echo ============================================
echo   2. Checking Required Packages
echo ============================================
python -c "import streamlit; print('[OK] Streamlit - Web UI')"
python -c "import httpx; print('[OK] HTTPX - HTTP Client')"
python -c "import pydantic; print('[OK] Pydantic - Data Validation')"
python -c "import openai; print('[OK] OpenAI - LLM Client')"
python -c "import dotenv; print('[OK] python-dotenv - Config')"
python -c "import tenacity; print('[OK] Tenacity - Retry Logic')"
echo.

echo ============================================
echo   3. Checking Configuration File
echo ============================================
if exist ".env" (
    echo [OK] .env file exists
) else (
    echo [WARN] .env file not found - run install.bat first
)
echo.

echo ============================================
echo   4. Checking Jenkins Connection
echo ============================================
python -c "import os; from dotenv import load_dotenv; load_dotenv(); import httpx; url=os.getenv('JENKINS_URL','http://localhost:8080'); r=httpx.get(f'{url}/api/json', auth=(os.getenv('JENKINS_USER','admin'), os.getenv('JENKINS_API_TOKEN','')), timeout=10); print(f'[OK] Jenkins connected at {url}') if r.status_code==200 else print(f'[WARN] Jenkins returned {r.status_code}')" 2>nul
if %errorlevel% neq 0 (
    echo [WARN] Could not connect to Jenkins
    echo        Make sure Jenkins is running at http://localhost:8080
)
echo.

echo ============================================
echo   5. Checking LLM Endpoint
echo ============================================
python -c "import os; from dotenv import load_dotenv; load_dotenv(); import httpx; url=os.getenv('LLM_URL',''); verify=os.getenv('LLM_VERIFY_SSL','true').lower()!='false'; print(f'[INFO] LLM URL: {url}'); print(f'[INFO] SSL Verify: {verify}')" 2>nul
echo [INFO] LLM connection will be tested on first message
echo.

echo ============================================
echo   SUMMARY
echo ============================================
echo.
echo If all checks show [OK], you're ready to run BuildBot!
echo.
echo To start: run_buildbot.bat
echo Then open: http://localhost:8501
echo.
echo Features available:
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

:end
pause
