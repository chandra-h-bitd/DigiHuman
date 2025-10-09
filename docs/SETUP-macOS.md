# Setup Guide (macOS)

This guide assumes a fresh macOS install with no developer tools. It’ll get you from zero to a running Doc Q&A app.

## 1) Install prerequisites

- Xcode Command Line Tools (compilers, git)
  - Open Terminal and run:
    - `xcode-select --install`
  - Accept the prompt and wait for installation.

- Homebrew (package manager)
  - In Terminal:
    - `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
  - Follow on-screen steps; then add brew to PATH if prompted.

- Python 3.10+ (recommended) via pyenv (avoids system Python conflicts)
  - `brew install pyenv`
  - Install Python:
    - `pyenv install 3.10.14`
    - `pyenv global 3.10.14`
  - Confirm:
    - `python --version` → should be 3.10.x

- Node.js LTS (for Angular)
  - `brew install node`
  - Confirm:
    - `node -v` and `npm -v`

## 2) Clone the repository

```
cd ~
mkdir -p Projects && cd Projects
git clone https://github.com/itsaboutps/NTT.git
cd NTT
```

If you’re not using git, download the ZIP from GitHub and unzip; then `cd` into the folder.

## 3) Backend setup (FastAPI)

We use a Python virtual environment and pinned dependencies.

```
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the API server:
```
python app/main.py
```

- The server listens on http://localhost:8000
- Health check: http://localhost:8000/health

Troubleshooting:
- If `sentence-transformers` downloads models on first run, allow a few minutes.
- If `nltk` warns about resources, the app auto-downloads punkt; ensure internet access.
- If you see SSL warnings, they’re safe to ignore for local dev.

## 4) Frontend setup (Angular)

In a new Terminal tab/window:

```
cd NTT/frontend
npm install
npm start
```

- Open http://localhost:4200
- If a browser doesn’t open automatically, copy the URL into Safari/Chrome.

Note:
- The dev server log may show warnings about deprecated options; that’s fine for local dev.

## 5) Using the app

1. Paste your Gemini API key in the left panel and click Validate.
2. Upload a PDF or DOCX (max 10 MB).
3. Ask a question in the bottom input.
4. Sources and fallback indicator appear alongside responses.

Your key is only used in the browser and sent per request; it isn’t stored.

## 6) Common issues on macOS

- Command not found: python
  - Add pyenv shims to PATH (and restart Terminal):
    - `echo 'eval "$(pyenv init -)"' >> ~/.zshrc && source ~/.zshrc`
- Port already in use (8000 or 4200)
  - Stop existing processes or change ports in the respective configs.
- Build tools missing (e.g., during `pip install`)
  - Ensure Xcode CLI tools are installed and retry: `xcode-select --install`

## 7) Stop services

- Backend: Ctrl+C in the terminal running `python app/main.py`
- Frontend: Ctrl+C in the terminal running `npm start`
