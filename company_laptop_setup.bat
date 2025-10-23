@echo off
REM Quick Fix for NPM SSL Certificate Issue on Company Laptop
REM Run this script on your company laptop

echo.
echo ========================================
echo NPM SSL Certificate Fix
echo ========================================
echo.

echo [1/6] Disabling SSL verification...
call npm config set strict-ssl false

echo.
echo [2/6] Clearing npm cache...
call npm cache clean --force

echo.
echo [3/6] Testing connection to npm registry...
call npm ping

echo.
echo [4/6] Current npm config:
call npm config get strict-ssl
call npm config get registry

echo.
echo [5/6] Going to frontend directory...
cd /d "%~dp0frontend"

echo.
echo [6/6] Installing dependencies...
echo This may take a few minutes...
call npm install

echo.
echo ========================================
echo Done!
echo ========================================
echo.
echo If successful, you can now run:
echo   cd frontend
echo   npm start
echo.
pause

