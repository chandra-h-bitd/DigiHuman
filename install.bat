@echo off
REM FINQUEST AI - One-Click Installation Script
REM Handles corporate networks automatically

echo.
echo ========================================
echo FINQUEST AI - Smart Installation
echo ========================================
echo.

REM Detect if we're on corporate network
echo [INFO] Detecting network environment...

REM Test npm registry access
npm ping >nul 2>&1
if %errorlevel% neq 0 (
    echo [DETECTED] Corporate network - Configuring for SSL bypass...
    echo.
    
    REM Configure npm for corporate network
    call npm config set strict-ssl false
    call npm config set registry https://registry.npmjs.org/
    
    echo [OK] npm configured for corporate network
    echo.
) else (
    echo [OK] Direct internet access detected
    echo.
)

REM ========== BACKEND SETUP ==========
echo ========================================
echo BACKEND SETUP
echo ========================================
echo.

echo [1/4] Creating Python virtual environment...
cd /d "%~dp0backend"

if not exist venv (
    python -m venv venv
    echo   [OK] Virtual environment created
) else (
    echo   [INFO] Virtual environment already exists
)

echo.
echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [3/4] Upgrading pip and setuptools...
python -m pip install --upgrade pip setuptools --quiet

echo.
echo [4/4] Installing Python dependencies...
pip install -r requirements.txt --quiet

if %errorlevel% equ 0 (
    echo   [OK] Backend dependencies installed
) else (
    echo   [ERROR] Backend installation failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo FRONTEND SETUP
echo ========================================
echo.

cd /d "%~dp0frontend"

echo [1/3] Clearing any existing caches...
if exist node_modules rmdir /s /q node_modules >nul 2>&1
if exist .angular rmdir /s /q .angular >nul 2>&1
if exist dist rmdir /s /q dist >nul 2>&1
call npm cache clean --force >nul 2>&1

echo.
echo [2/3] Installing Node dependencies...
echo   This may take 2-5 minutes...
call npm install

if %errorlevel% equ 0 (
    echo   [OK] Frontend dependencies installed
) else (
    echo.
    echo   [ERROR] npm install failed!
    echo.
    echo   Common fixes:
    echo   1. Run: npm config set strict-ssl false
    echo   2. Run: npm cache clean --force
    echo   3. Try again
    echo.
    pause
    exit /b 1
)

echo.
echo [3/3] Verifying installation...
if exist node_modules\@angular (
    echo   [OK] Angular installed successfully
) else (
    echo   [ERROR] Angular installation incomplete
    pause
    exit /b 1
)

REM ========== SUCCESS ==========
echo.
echo ========================================
echo INSTALLATION COMPLETE!
echo ========================================
echo.
echo Next steps:
echo.
echo 1. Start Backend:
echo    cd backend
echo    venv\Scripts\activate
echo    python -m app.main
echo.
echo 2. Start Frontend (new terminal):
echo    cd frontend
echo    npm start
echo.
echo 3. Open browser:
echo    http://localhost:4200
echo.
echo ========================================
echo.

REM Ask if user wants to start now
set /p start="Start FINQUEST AI now? (y/n): "
if /i "%start%"=="y" (
    echo.
    echo Starting backend...
    start "FINQUEST AI - Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && python -m app.main"
    
    timeout /t 5 /nobreak >nul
    
    echo Starting frontend...
    start "FINQUEST AI - Frontend" cmd /k "cd /d %~dp0frontend && npm start"
    
    echo.
    echo [OK] Both services starting...
    echo [INFO] Frontend will open at http://localhost:4200
    echo.
)

pause

