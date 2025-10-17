@echo off
echo 🚀 Starting Document Q&A Frontend...
echo.

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js not found! Please install Node.js from https://nodejs.org
    pause
    exit /b 1
)

REM Check if npm is installed
npm --version >nul 2>&1
if errorlevel 1 (
    echo ❌ npm not found! Please install Node.js (includes npm) from https://nodejs.org
    pause
    exit /b 1
)

REM Install dependencies
echo 📥 Installing dependencies...
npm install

REM Start the application
echo 🚀 Starting frontend development server...
echo.
echo ✅ Frontend will be available at: http://localhost:4200
echo.
echo Press Ctrl+C to stop the server
echo.

npm start

pause
