# Setup Guide (Windows 10/11)

This guide assumes a fresh Windows system with only the OS installed. It covers installing all prerequisites and running the app.

## 1) Install prerequisites

- Git for Windows
  - Download: https://git-scm.com/download/win
  - During setup, accept defaults. Use Git Bash or PowerShell.

- Microsoft Visual Studio Build Tools (C++ toolchain)
  - Required by some Python packages.
  - Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
  - Install "Desktop development with C++" workload (includes MSVC, Windows 10/11 SDK, and CMake).

- Python 3.10 (recommended)
  - Download: https://www.python.org/downloads/release/python-31014/
  - IMPORTANT: During installation, check "Add Python to PATH".
  - Confirm in a new PowerShell:
    - `python --version` → 3.10.x
    - `pip --version`

- Node.js LTS (for Angular)
  - Download: https://nodejs.org/en (LTS)
  - Confirm:
    - `node -v` and `npm -v`

## 2) Clone the repository

Open PowerShell (Windows Terminal recommended):

```
cd $HOME
mkdir Projects
cd Projects
git clone https://github.com/itsaboutps/NTT.git
cd NTT
```

Alternatively, download the ZIP from GitHub, unzip, and `cd` into the folder.

## 3) Backend setup (FastAPI)

Create and activate a virtual environment:

```
cd backend
python -m venv .venv
. .venv/Scripts/Activate.ps1   # PowerShell
# Or: .venv\Scripts\activate.bat   # CMD
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the API server:
```
python app/main.py
```

- The server listens on http://localhost:8000
- Health: http://localhost:8000/health

Troubleshooting:
- If Windows blocks scripts (ExecutionPolicy):
  - Run PowerShell as Administrator:
    - `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned`
- If `pip install` fails due to build tools:
  - Ensure "Desktop development with C++" is installed from Build Tools.
- If `sentence-transformers` downloads models on first run, allow time.

## 4) Frontend setup (Angular)

Open a new PowerShell window/tab:

```
cd $HOME/Projects/NTT/frontend
npm install
npm start
```

- Open http://localhost:4200 in your browser.

## 5) Using the app

1. Paste your Gemini API key in the left panel and click Validate.
2. Upload a PDF or DOCX (max 10 MB).
3. Ask a question using the bottom input.

Your key is only used in the browser and sent per request; it’s not stored.

## 6) Common issues on Windows

- "python" not recognized
  - Close and reopen PowerShell after install, or use `py -3.10`.
- Permission error on activate
  - Use `Set-ExecutionPolicy RemoteSigned` in Administrator PowerShell.
- Port 8000/4200 in use
  - Stop other apps or adjust ports.
- Long path issues when cloning
  - Enable long paths: in Administrator PowerShell:
    - `git config --system core.longpaths true`

## 7) Stop services

- Backend: Ctrl+C in the PowerShell running `python app/main.py`
- Frontend: Ctrl+C in the PowerShell running `npm start`
