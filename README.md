# FINQUEST AI

A powerful RAG (Retrieval-Augmented Generation) document Q&A system with multi-session support, intelligent LLM fallback, and enterprise-ready features.

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Features

- **Multi-Session Management** - Create independent Q&A sessions for different document sets
- **Multiple Document Types** - Support for PDF, DOCX, TXT, and Markdown files
- **Intelligent LLM Fallback** - Gemini → Groq (free, fast) → Heuristic
- **Vector Search** - FAISS-powered semantic search with per-session indexes
- **API Key Management** - Configure keys via UI or config file
- **Source Citations** - Every answer includes document references
- **Persistent Storage** - All data persists across restarts

## 🚀 Quick Start

### Prerequisites

- Python 3.9+ 
- Node.js 18+
- 8GB RAM (16GB recommended)

### Installation

**1. Backend Setup:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m app.main
```

**2. Frontend Setup:**
```bash
cd frontend
npm install
npm start
```

**3. Access Application:**
- Frontend: `http://localhost:4200`
- Backend API: `http://localhost:8000`

### Quick Setup Scripts

**Windows:**
```bash
# Backend
cd backend
start_windows.bat

# Frontend  
cd frontend
start_windows.bat
```

**Linux/Mac:**
```bash
chmod +x backend/start_linux.sh frontend/start_linux.sh
./backend/start_linux.sh
./frontend/start_linux.sh
```

## ⚙️ Configuration

### API Keys

**Method 1: UI Settings** (Recommended for users)
1. Go to `http://localhost:4200`
2. Click Settings (gear icon)
3. Enter your API keys
4. Click Save

**Method 2: Database** (Stored in `~/.rag-assistant/db.json`)
```bash
# Via API
curl -X POST http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{"key_name": "groq_api_key", "key_value": "YOUR_KEY"}'
```

### Get API Keys

- **Gemini (Google)**: https://aistudio.google.com/app/apikey
- **ChatGPT (OpenAI)**: https://platform.openai.com/api-keys
- **Groq (Free fallback)**: https://console.groq.com

## 📖 Usage

1. **Create Session**
   - Click "New Session"
   - Choose primary LLM (Gemini/ChatGPT)

2. **Upload Documents**
   - Select session
   - Upload PDF, DOCX, TXT, or MD files
   - Wait for processing

3. **Ask Questions**
   - Type your question
   - Get AI-generated answers with source citations

## 🏢 Corporate Network Setup

For company laptops with network restrictions:

**NPM SSL Certificate Issue:**
```bash
npm config set strict-ssl false
cd frontend
npm install
```

**Automated Fix:**
```bash
# Run the setup script
setup\company_laptop_setup.bat
```

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) and [setup/](setup/) folder for detailed guides.

## 🔧 Troubleshooting

**Backend won't start:**
- Check Python version: `python --version` (need 3.9+)
- Check port 8000: `netstat -ano | findstr ":8000"`
- Install dependencies: `pip install -r requirements.txt`

**Frontend won't start:**
- Check Node version: `node --version` (need 18+)
- Check port 4200: `netstat -ano | findstr ":4200"`
- Clear cache: `npm cache clean --force`

**Dimension mismatch error:**
- Documents uploaded with one embedding model, queried with another
- Solution: Re-upload documents with current API key settings

**For more issues, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)**

## 📁 Project Structure

```
FINQUEST-AI/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI application
│   │   ├── db.py            # TinyDB persistence
│   │   ├── storage.py       # FAISS vector storage
│   │   └── config.json      # Configuration
│   ├── requirements.txt     # Python dependencies
│   └── start_windows.bat    # Start script
├── frontend/
│   ├── src/app/
│   │   ├── app.component.*  # Main Angular component
│   │   └── api.service.ts   # API service
│   ├── package.json         # Node dependencies
│   └── start_windows.bat    # Start script
├── setup/                   # Corporate network setup
│   ├── company_laptop_setup.bat
│   ├── diagnose_npm.ps1
│   └── FIX_SSL_CERTIFICATE.md
├── docs/                    # Platform-specific setup guides
├── TROUBLESHOOTING.md       # Common issues and solutions
└── README.md                # This file
```

## 🔄 LLM Fallback Mechanism

```
1. Primary LLM (Gemini or ChatGPT)
   ↓ (if API key missing/invalid)
2. Groq (Llama 3.1 8B - free, fast, 3-sec responses)
   ↓ (if Groq unavailable)
3. Heuristic (rule-based text extraction)
```

**Configure Groq (recommended free fallback):**
- Get key: https://console.groq.com
- Add in Settings UI
- Enjoy fast, intelligent fallback!

## 🗄️ Data Storage

| Data | Location |
|------|----------|
| Sessions/Documents | `~/.rag-assistant/db.json` |
| FAISS Indexes | `~/.rag-assistant/*.index` |
| Vector Metadata | `~/.rag-assistant/*.pkl` |
| Uploaded Files | `~/.rag-assistant/documents/` |

## 🛠️ Development

**Backend (FastAPI):**
```bash
cd backend
python -m app.main --reload  # Auto-reload on changes
```

**Frontend (Angular):**
```bash
cd frontend
ng serve --open
```

**Run Tests:**
```bash
cd backend
python -m pytest tests/
```

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/config` | GET/POST | API key management |
| `/sessions` | GET/POST | Session management |
| `/sessions/{id}/upload` | POST | Upload documents |
| `/sessions/{id}/query` | POST | Ask questions |
| `/sessions/{id}/documents` | GET | List documents |
| `/sessions/{id}/conversations` | GET | Get chat history |

**Full API docs:** `http://localhost:8000/docs` (Swagger UI)

## 🔐 Security Notes

- API keys stored locally (database or config file)
- For production: Use environment variables or secret management
- Never commit `backend/app/config.json` with API keys
- Database location: User's home directory (gitignored)

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📞 Support

- **Issues**: Open a GitHub issue
- **Corporate Network**: See `setup/` folder
- **Troubleshooting**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

**Built with:** FastAPI • Angular • FAISS • TinyDB • Gemini • ChatGPT • Groq
