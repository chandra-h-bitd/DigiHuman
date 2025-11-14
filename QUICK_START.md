# Quick Start Guide

Get FINQUEST AI running in 5 minutes!

## 🎯 Prerequisites

- Python 3.9 or higher
- Node.js 18 or higher
- 8GB RAM minimum

## 🚀 Installation

### ⚡ Option 1: One-Click Installation (Recommended)

**Just run this and you're done!**

**Windows:**
```bash
install.bat
```

**Linux/Mac:**
```bash
chmod +x install.sh
./install.sh
```

**What it does:**
- Detects if you're on a corporate network
- Automatically configures SSL if needed
- Installs all dependencies (backend + frontend)
- Optionally starts both services

**That's it!** Skip to [Step 3: Access Application](#step-3-access-application)

---

### 📖 Option 2: Manual Installation

**Only use this if you want to install step-by-step**

### Step 1: Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
python -m app.main
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### Step 2: Frontend Setup

**Open a new terminal:**

```bash
# Navigate to frontend
cd frontend

# If on company network (SSL issues):
npm config set strict-ssl false

# Install dependencies
npm install

# Start development server
npm start
```

**Expected output:**
```
Angular Live Development Server is listening on localhost:4200
** Compiled successfully.
```

### Step 3: Access Application

Open your browser and navigate to:
```
http://localhost:4200
```

## ⚙️ Configure API Keys

### Option 1: Via UI (Easiest)

1. Click the **Settings** (gear icon) in the top-right
2. Enter your API keys:
   - **Gemini API Key**: Get from https://aistudio.google.com/app/apikey
   - **ChatGPT API Key**: Get from https://platform.openai.com/api-keys
   - **Groq API Key**: Get from https://console.groq.com (FREE!)
3. Click **Save All Settings**

### Option 2: Via Configuration

The database stores API keys in:
```
~/.rag-assistant/db.json
```

## 📖 Using FINQUEST AI

### 1. Create a Session

- Click **"New Session"**
- Enter a name (e.g., "Financial Reports")
- Select primary LLM (Gemini or ChatGPT)
- Click **Create**

### 2. Upload Documents

- Select your session from the sidebar
- Click **"Upload Document"**
- Choose PDF, DOCX, TXT, or Markdown files
- Wait for processing (progress bar shows status)

### 3. Ask Questions

- Type your question in the input box
- Click **"Ask"** or press Enter
- View AI-generated answer with source citations

### 4. View History

- All conversations are automatically saved
- Scroll up to view previous Q&A pairs
- Source documents are highlighted for each answer

## 🏢 Corporate Network Setup

If you're on a company laptop and `npm install` fails, the one-click installer handles this automatically. For manual fixes, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## ✅ Verification

### Check Backend Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy"}
```

### Check Frontend

Open browser: `http://localhost:4200`

You should see the FINQUEST AI interface.

## 🔧 Common Issues

For detailed troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## 📋 Quick Reference

### Start Commands

**Backend:**
```bash
cd backend
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
python -m app.main
```

**Frontend:**
```bash
cd frontend
npm start
```

### Ports

- Backend API: `http://localhost:8000`
- Frontend UI: `http://localhost:4200`
- API Docs (Swagger): `http://localhost:8000/docs`

### Data Locations

- Database: `~/.rag-assistant/db.json`
- FAISS Indexes: `~/.rag-assistant/*.index`
- Uploaded Files: `~/.rag-assistant/documents/`

## 🎓 Next Steps

1. **Upload your first document** - Try with a PDF or DOCX file
2. **Ask questions** - Test the Q&A functionality
3. **Configure Groq** - Get free, fast fallback LLM
4. **Create multiple sessions** - Organize different document sets

## 📚 Additional Resources

- **Full Documentation**: [README.md](README.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **API Documentation**: http://localhost:8000/docs
