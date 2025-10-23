# FINQUEST AI

A powerful, single-user RAG (Retrieval-Augmented Generation) document assistant that supports multiple sessions, various document types, and multiple LLM providers with intelligent fallback mechanisms.

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🌟 Features

### Core Capabilities

- **Multi-Session Support**: Create and manage multiple independent Q&A sessions
- **Multi-Document Upload**: Upload multiple documents per session (PDF, DOCX, TXT, Markdown)
- **User-Selectable LLM**: Choose between Gemini API or ChatGPT API per session
- **Intelligent Fallback**: Automatic fallback to local LLM (Llama 3) if API fails
- **Persistent Storage**: All data persists across app refresh or backend restart
- **Source Citations**: Every answer includes references to source documents
- **Out-of-Context Detection**: Intelligent detection of questions outside document scope

### Technical Features

- **FAISS Vector Search**: Efficient similarity search with per-session indexes
- **TinyDB Persistence**: Lightweight NoSQL database for sessions, documents, and conversations
- **Smart Chunking**: Large PDFs automatically chunked (500-1000 tokens) with overlap
- **API Key Management**: Securely store and manage your API keys locally
- **Responsive UI**: Beautiful Angular SPA with Material Design
- **Real-time Progress**: Live upload progress and query status

## 📋 Prerequisites

- Python 3.8+ (tested on 3.9-3.11)
- Node.js 18+ (for Angular frontend)
- npm or yarn
- 8GB RAM minimum (16GB recommended for large documents)
- 10GB free disk space (for models and indexes)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd NTT
```

### 2. Backend Setup

```bash
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

The backend will start on `http://localhost:8000`

### 3. Frontend Setup

Open a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

The frontend will open automatically at `http://localhost:4200`

## 📚 Usage Guide

### Creating a Session

1. Click "Create New Session" on the dashboard
2. Enter a descriptive session name (e.g., "Q2 Financial Reports")
3. Select your primary LLM (Gemini or ChatGPT)
4. Click "Create Session"

### Configuring API Keys

1. Click the Settings icon (⚙️) in the top-right corner
2. Enter your API keys:
   - **Gemini API Key**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - **ChatGPT API Key**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)
3. Click "Save Settings"

> **Note**: API keys are stored locally in TinyDB and never shared or logged.

### Uploading Documents

1. Open a session
2. Drag and drop files into the upload zone, or click "Upload Document"
3. Supported formats:
   - PDF (`.pdf`)
   - Word Documents (`.docx`)
   - Text Files (`.txt`)
   - Markdown (`.md`, `.markdown`)
4. Wait for processing to complete

### Asking Questions

1. Type your question in the input field
2. Press Enter or click "Ask"
3. View the answer with source citations
4. Click on source references to see the original text

### Managing Sessions

- **View All Sessions**: Click the Dashboard icon (📊)
- **Delete Session**: Click the delete icon (🗑️) on a session card
- **Switch Sessions**: Click on any session card to open it

## 🏗️ Architecture

```
~/.rag-assistant/
├── db.json                        # TinyDB database
├── docs/                          # Uploaded documents
│   └── <session_id>/
│       └── <doc_id>_filename.pdf
├── faiss_<session_id>.index       # FAISS vector index
└── faiss_<session_id>.metadata.pkl # Chunk metadata
```

### Technology Stack

**Backend:**
- FastAPI (API framework)
- TinyDB (NoSQL database)
- FAISS (Vector similarity search)
- PyMuPDF (PDF parsing)
- python-docx (Word document parsing)
- SentenceTransformers (Local embeddings)
- GPT4All (Local LLM)

**Frontend:**
- Angular 18 (Framework)
- Angular Material (UI components)
- RxJS (Reactive programming)
- TypeScript (Type safety)

## 🔧 Configuration

### Backend Configuration

Edit `backend/app/config.json`:

```json
{
  "retrieval": {
    "similarity_threshold": 0.3,
    "default_k": 5
  },
  "chunking": {
    "default_chunk_size": 700,
    "min_chunk_size": 100
  },
  "gemini": {
    "embedding_model": "text-embedding-004",
    "generation_model": "gemini-2.0-flash-exp"
  },
  "openai": {
    "embedding_model": "text-embedding-3-small",
    "generation_model": "gpt-4o-mini"
  }
}
```

### Environment Variables

Optional environment variables:

```bash
# Storage location (default: ~/.rag-assistant)
export STORAGE_PATH=/path/to/storage

# Local LLM model path
export LOCAL_LLM_PATH=/path/to/model.gguf
```

## 📖 API Documentation

The backend exposes a RESTful API. View the interactive API documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Key Endpoints

- `POST /sessions` - Create new session
- `GET /sessions` - List all sessions
- `POST /sessions/{session_id}/upload` - Upload document
- `POST /sessions/{session_id}/query` - Query documents
- `POST /config` - Save API keys

See [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) for detailed API documentation.

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest tests/
```

### Frontend Tests

```bash
cd frontend
npm test
```

## 🐛 Troubleshooting

### Backend won't start

**Error: "ModuleNotFoundError"**
```bash
# Ensure virtual environment is activated
pip install -r requirements.txt
```

**Error: "Port 8000 already in use"**
```bash
# Change port in backend/app/main.py
uvicorn.run("main:app", host="0.0.0.0", port=8001)
```

### SBERT model download fails

```bash
cd backend
python fix_sbert.py
```

### Local LLM not loading

```bash
cd backend
python install_local_llm.py
```

### Frontend build errors

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

## 📊 Performance Tips

1. **Large PDFs**: Upload takes longer for 50+ page documents (1-3 minutes)
2. **Embeddings**: First query per session may be slower as models load
3. **Local LLM**: Responses are slower than API-based LLMs (15-30 seconds)
4. **Memory**: Close unused sessions to free up memory
5. **Disk Space**: Regularly clean up old sessions you no longer need

## 🔒 Security & Privacy

- All data stored locally on your machine
- API keys stored in TinyDB, never logged or transmitted
- No telemetry or analytics
- No data sent to third parties (except chosen LLM APIs)
- Documents never leave your machine (except embeddings sent to APIs)

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- FastAPI for the excellent API framework
- Angular team for the powerful frontend framework
- FAISS team at Facebook AI Research
- SentenceTransformers for the embedding models
- GPT4All for local LLM support

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/ntt/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/ntt/discussions)
- **Documentation**: [System Architecture](SYSTEM_ARCHITECTURE.md)

## 🗺️ Roadmap

- [ ] Advanced semantic chunking
- [ ] Streaming responses
- [ ] Multi-user support with authentication
- [ ] Session export/import
- [ ] Advanced analytics dashboard
- [ ] Multi-modal support (images, tables)
- [ ] Custom embedding fine-tuning
- [ ] Cloud deployment options

---

**Built with ❤️ using Python and Angular**
