@echo off
setlocal
cd /d %~dp0
echo === Library Management System - SOA ===
echo Gateway: http://localhost:5000
echo Books:   http://localhost:5001/health
echo Members: http://localhost:5002/health
echo Loans:   http://localhost:5003/health
echo Reports: http://localhost:5004/health
echo.
if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe run.py all
) else (
    python run.py all
)
endlocal
