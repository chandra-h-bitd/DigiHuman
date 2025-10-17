@echo off
echo 🚀 Starting Document Q&A Backend...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate

REM Install dependencies
echo 📥 Installing dependencies...
pip install -r requirements.txt
echo 🔧 Updating huggingface-hub for compatibility...
pip install --upgrade huggingface-hub

REM Install local LLM models (optional but recommended)
echo 🤖 Installing local LLM models for fallback...
echo 💡 This will download ~4-8GB of models for offline use
set /p install_llm="❓ Install local LLM models? (y/N): "
if /i "%install_llm%"=="y" (
    python install_local_llm.py
) else (
    echo ⏭️ Skipping local LLM installation
    echo 💡 You can run 'python install_local_llm.py' later to install them
)

REM Start the application
echo 🚀 Starting backend server...
echo.
echo ✅ Backend will be available at: http://localhost:8000
echo ✅ Health check: http://localhost:8000/health
echo ✅ API docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

python -m app.main

pause
