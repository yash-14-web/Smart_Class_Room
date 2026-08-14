@echo off
TITLE Smart Classroom Environment Setup Script
COLOR 0A
echo =======================================================================
echo          SMART CLASSROOM PLATFORM - AUTOMATED SETUP SCRIPT
echo =======================================================================
echo.

:: Step 1: Check Python Installation
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    COLOR 0C
    echo [ERROR] Python is not installed or not added to system PATH.
    echo Please install Python 3.10 or higher and try again.
    pause
    exit /b 1
)
python --version

:: Step 2: Virtual Environment Setup
echo.
echo [2/6] Setting up Virtual Environment (.venv)...
if not exist ".venv" (
    echo Creating new virtual environment in .venv...
    python -m venv .venv
    echo Virtual environment created successfully.
) else (
    echo Existing virtual environment .venv found.
)

:: Step 3: Activate Virtual Environment
echo.
echo [3/6] Activating virtual environment...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    COLOR 0C
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

:: Step 4: Upgrade Pip & Install Dependencies
echo.
echo [4/6] Installing dependencies from requirements.txt...
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    COLOR 0C
    echo [ERROR] Dependency installation failed! Please check error output above.
    pause
    exit /b 1
)

:: Step 5: Check .env Configuration
echo.
echo [5/6] Checking environment variables (.env)...
if not exist ".env" (
    echo Creating default .env configuration file...
    echo SECRET_KEY=django-insecure-smart-classroom-dev-key-2026> .env
    echo DEBUG=True>> .env
    echo ALLOWED_HOSTS=*>> .env
    echo .env file created successfully.
) else (
    echo .env configuration file verified.
)

:: Step 6: Run Database Migrations
echo.
echo [6/6] Running Django Database Migrations...
python manage.py migrate
if %errorlevel% neq 0 (
    COLOR 0C
    echo [ERROR] Django database migration failed!
    pause
    exit /b 1
)

echo.
echo =======================================================================
echo          SUCCESS! ENVIRONMENT SETUP IS COMPLETE!
echo =======================================================================
echo.
echo To launch your local development server, run:
echo    .venv\Scripts\activate
echo    python manage.py runserver
echo.
echo Server will be accessible at: http://127.0.0.1:8000/
echo =======================================================================
pause
