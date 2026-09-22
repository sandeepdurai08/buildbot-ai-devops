@echo off
echo ========================================================
echo         JENKINS CONNECTION TEST
echo ========================================================
echo.
echo Testing connection to http://localhost:8080...
echo.

curl -s -o nul -w "Status: %%{http_code}\n" http://localhost:8080/api/json

if %errorlevel% neq 0 (
    echo.
    echo [FAIL] Cannot connect to Jenkins!
    echo.
    echo Make sure Jenkins is running:
    echo   java -jar jenkins.war --httpPort=8080
) else (
    echo.
    echo [OK] Jenkins is running!
)

echo.
pause
