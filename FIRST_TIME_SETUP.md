# 🚀 First Time Setup - FINQUEST AI

## For Company Laptop Users (Corporate Network)

If you're installing on a company laptop, **use the one-click installer** - it handles all SSL issues automatically!

### Windows (Company Laptop):
```bash
# Just double-click this file or run:
install.bat
```

### Linux/Mac (Company Laptop):
```bash
chmod +x install.sh
./install.sh
```

**That's it!** The installer will:
- ✅ Detect corporate network automatically
- ✅ Configure SSL bypass for npm
- ✅ Install all dependencies
- ✅ Handle font loading issues
- ✅ Start both services (optional)

---

## For Personal Computer Users (Home Network)

You can use the one-click installer OR manual installation:

### Option 1: One-Click (Easiest)
```bash
# Windows
install.bat

# Linux/Mac
chmod +x install.sh && ./install.sh
```

### Option 2: Manual
See [QUICK_START.md](QUICK_START.md) for step-by-step instructions.

---

## What Gets Installed

**Backend:**
- Python virtual environment
- FastAPI and dependencies
- SBERT for embeddings
- FAISS for vector search

**Frontend:**
- Angular application
- Material Design components
- All npm dependencies

**Total time:** 3-5 minutes (depends on internet speed)

---

## After Installation

1. **Configure API Keys** (Optional but recommended)
   - Go to Settings in the UI
   - Add your Gemini/ChatGPT/Groq API keys
   - At minimum, add Groq key (it's FREE!)

2. **Start Using**
   - Create a session
   - Upload documents
   - Ask questions!

---

## Common Issues & Solutions

### "npm install stuck" or "SSL certificate error"
**Already handled!** The `install.bat` script configures this automatically.

If you ran manual installation, just run:
```bash
npm config set strict-ssl false
cd frontend
npm install
```

### "Font inlining failed"
**Already fixed!** The app doesn't need Google Fonts anymore.

If you still see this:
```bash
cd frontend
rm -rf .angular dist
npm start
```

### Port already in use
```bash
# Backend (8000)
netstat -ano | findstr ":8000"
taskkill /PID <PID> /F

# Frontend (4200)
netstat -ano | findstr ":4200"
taskkill /PID <PID> /F
```

---

## Need Help?

- **Quick Start**: [QUICK_START.md](QUICK_START.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Full Docs**: [README.md](README.md)
- **Corporate Setup**: [setup/](setup/) folder

---

## Summary

**For 99% of users:**
```bash
# Just run this!
install.bat  # Windows
./install.sh # Linux/Mac
```

**It handles everything - corporate networks, SSL, dependencies, everything!** 🎉

