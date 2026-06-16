@echo off
REM SwasthAI API - Production Server Startup (Windows)
REM Run with: .\start_server.bat

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║         SwasthAI - Anemia Detection API                        ║
echo ║         Production Server (Windows)                            ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Activate virtual environment
call .\.venv\Scripts\activate.bat

if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    exit /b 1
)

echo ✅ Virtual environment activated
echo.

REM Set environment variables
set FLASK_ENV=production
set FLASK_APP=wsgi.py
set PYTHONUNBUFFERED=1
set PYTHONIOENCODING=utf-8

REM Start with Waitress (Windows-friendly WSGI server)
echo 🚀 Starting SwasthAI API Server...
echo    Server: Waitress WSGI
echo    Host: 0.0.0.0
echo    Port: 5000
echo    Workers: 4
echo    URL: http://localhost:5000
echo.
echo    Press Ctrl+C to stop the server
echo.

REM Run Waitress with 4 worker threads
.\.venv\Scripts\waitress-serve.exe --host=0.0.0.0 --port=5000 --threads=4 wsgi:app

if errorlevel 1 (
    echo.
    echo ❌ Server failed to start
    pause
    exit /b 1
)
