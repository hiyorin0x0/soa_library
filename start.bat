@echo off
chcp 65001 >nul
setlocal
cd /d %~dp0
echo =========================================================
echo   LibCore University — SOA Library System
echo =========================================================
echo   Staff Portal: http://localhost:5000/login
echo   Public OPAC:  http://localhost:5000/catalog
echo   Services:     5001 (Books) ^| 5002 (Members) ^| 5003 (Loans) ^| 5004 (Reports)
echo =========================================================
echo.

venv\Scripts\python.exe --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    venv\Scripts\python.exe run.py all
) else (
    python run.py all
)
endlocal
