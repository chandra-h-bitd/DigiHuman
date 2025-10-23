# Troubleshooting Guide

Common issues and solutions for FINQUEST AI.

## 🚀 Quick Fixes

### Backend Issues

**Port 8000 already in use:**
```bash
# Windows
netstat -ano | findstr ":8000"
taskkill /PID <PID> /F

# Then restart backend
cd backend
python -m app.main
```

**Python dependencies fail:**
```bash
cd backend
pip install --upgrade pip setuptools
pip install -r requirements.txt
```

### Frontend Issues

**Port 4200 already in use:**
```bash
# Kill the process
netstat -ano | findstr ":4200"
taskkill /PID <PID> /F

# Then restart frontend
cd frontend
npm start
```

**npm install stuck/fails on company laptop:**
See [Corporate Network Setup](#corporate-network-npm-issues)

## 📡 Corporate Network / NPM Issues

### SSL Certificate Error (npm install)

**Error:** `unable to get issuer certificate locally`

**Solution:**
```bash
# Disable SSL verification
npm config set strict-ssl false

# Test
npm ping

# Install
cd frontend
npm install
```

### SSL Certificate Error (npm start / Font Inlining)

**Error:** `Inlining of fonts failed. An error has occurred while retrieving https://fonts.googleapis.com/icon`

**This is already fixed!** The app is configured to work without Google Fonts CDN.

If you still see this error:
```bash
# Clear Angular cache
cd frontend
rm -rf .angular
rm -rf dist

# Or on Windows
Remove-Item -Recurse -Force .angular
Remove-Item -Recurse -Force dist

# Try again
npm start
```

### Proxy Configuration

**If npm ping fails:**

1. **Get proxy settings:**
```powershell
Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
```

2. **Configure npm:**
```bash
npm config set proxy http://PROXY:PORT
npm config set https-proxy http://PROXY:PORT
```

3. **Test:**
```bash
npm ping
```

### Offline Installation (No Network Access)

**On personal laptop (with internet):**
```bash
cd frontend
npm install
tar -czf node_modules.tar.gz node_modules
# Or zip with 7-Zip
```

**On company laptop:**
```bash
cd frontend
# Extract node_modules.tar.gz or .zip here
# Skip npm install - done!
```

### Automated Fix

Use the setup scripts in `setup/` folder:
- `company_laptop_setup.bat` - Auto-configures npm for corporate networks
- `diagnose_npm.ps1` - Diagnoses network issues
- `FIX_SSL_CERTIFICATE.md` - Detailed SSL fix guide

## 🔄 Fallback & API Key Issues

### Dimension Mismatch Error

**Error:** `Embedding model mismatch detected`

**Cause:** Documents uploaded with one embedding model (e.g., Gemini 768D), querying with another (e.g., SBERT 384D)

**Solution:**
```bash
# Option 1: Restore original API key
# Go to Settings → Enter original Gemini key

# Option 2: Re-upload documents
# Delete all documents → Upload again with current settings
```

### Groq Fallback Not Working

**Error:** Model decommissioned

**Check config:**
```json
// backend/app/config.json
{
  "groq": {
    "generation_model": "llama-3.1-8b-instant"  // Use this model
  }
}
```

**Test Groq:**
```bash
# Set Groq API key in Settings UI
# Or in database via API:
curl -X POST http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{"key_name": "groq_api_key", "key_value": "YOUR_KEY"}'
```

## 🗄️ Database & Storage Issues

### Clear Session Data

```bash
# Delete all sessions and documents
rm -rf ~/.rag-assistant/*

# Or on Windows
Remove-Item -Recurse -Force $env:USERPROFILE\.rag-assistant\*
```

### Reset Configuration

```bash
# Delete database (resets API keys and sessions)
rm ~/.rag-assistant/db.json

# Or on Windows
Remove-Item $env:USERPROFILE\.rag-assistant\db.json
```

## 🐛 Runtime Errors

### FAISS Index Errors

**Clear indexes:**
```bash
rm ~/.rag-assistant/*.index
rm ~/.rag-assistant/*.pkl
```

### Import Errors

**Missing dependencies:**
```bash
cd backend
pip install -r requirements.txt --force-reinstall
```

## 📊 Performance Issues

### Slow Query Responses

- Check which LLM is being used (Gemini/Groq/heuristic)
- Groq should respond in 3-4 seconds
- If using heuristic, API keys may be missing

### High Memory Usage

- Large FAISS indexes from many documents
- Solution: Delete old sessions, re-upload only needed documents

## 🔍 Diagnostic Commands

```bash
# Check backend health
curl http://localhost:8000/health

# Check frontend
curl http://localhost:4200

# Check API keys
curl http://localhost:8000/config

# Check sessions
curl http://localhost:8000/sessions

# Test npm
npm ping
npm config list

# Check Python
python --version
pip list
```

## 📞 Getting Help

1. **Check logs:**
   - Backend: Terminal running `python -m app.main`
   - Frontend: Browser console (F12)

2. **Common error patterns:**
   - `404`: Endpoint not found - check URL
   - `500`: Server error - check backend logs
   - `CORS`: Backend not running or wrong port
   - Certificate errors: Corporate network issue

3. **For corporate network:**
   - Ask IT for proxy settings
   - Request npm registry whitelist
   - Use offline installation method

## ✅ Health Check Checklist

```bash
# 1. Backend running?
curl http://localhost:8000/health
# Expected: {"status": "healthy"}

# 2. Frontend running?
curl http://localhost:4200
# Expected: HTML response

# 3. Can upload documents?
# Test via UI: http://localhost:4200

# 4. Can query?
# Upload doc → Ask question → Check response

# 5. API keys configured?
curl http://localhost:8000/config
# Should show your API keys (masked)
```

---

**For detailed setup instructions, see [QUICK_START.md](QUICK_START.md)**  
**For corporate network setup, see [setup/](setup/) folder**

