@echo off
REM Push BuildBot to GitHub with sandeepdurai08 account
REM This script uses repository-specific configuration

echo ========================================
echo  Push to GitHub: sandeepdurai08
echo ========================================
echo.

cd /d "%~dp0\.."

echo Repository: https://github.com/sandeepdurai08/buildbot-ai-devops.git
echo User: sandeepdurai08
echo.

echo Checking git status...
git status
echo.

echo ========================================
echo  Ready to push!
echo ========================================
echo.
echo When prompted for credentials:
echo   Username: sandeepdurai08
echo   Password: Use your Personal Access Token (PAT)
echo.
echo To create a PAT:
echo   1. Go to: https://github.com/settings/tokens
echo   2. Generate new token (classic)
echo   3. Select 'repo' scope
echo   4. Copy the token (starts with ghp_)
echo.
pause

git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo  Success! Code pushed to GitHub
    echo ========================================
    echo.
    echo View at: https://github.com/sandeepdurai08/buildbot-ai-devops
) else (
    echo.
    echo ========================================
    echo  Push failed. Check your credentials.
    echo ========================================
)

echo.
pause
