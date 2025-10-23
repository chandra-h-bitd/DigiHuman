@echo off
REM Fix for Angular font inlining SSL error on company laptops
REM Run this if you get "Inlining of fonts failed" error

echo.
echo ========================================
echo FINQUEST AI - Frontend SSL Fix
echo ========================================
echo.

echo [1/3] Clearing Angular cache...
cd /d "%~dp0..\frontend"

if exist .angular (
    rmdir /s /q .angular
    echo   [OK] Cleared .angular cache
) else (
    echo   [INFO] No .angular cache found
)

if exist dist (
    rmdir /s /q dist
    echo   [OK] Cleared dist folder
) else (
    echo   [INFO] No dist folder found
)

echo.
echo [2/3] Clearing npm cache...
call npm cache clean --force

echo.
echo [3/3] Starting development server...
echo This should work now without SSL errors!
echo.

call npm start

echo.
echo ========================================
pause

