# Multi-Session RAG Document Assistant - System Architecture

## Overview

This is a comprehensive multi-session RAG (Retrieval-Augmented Generation) document assistant that allows users to create multiple QA sessions, upload documents, and query them using AI. The system supports multiple LLM providers with automatic fallback mechanisms.

## Architecture

### Backend (FastAPI + Python)

**Location:** `backend/app/`

**Core Components:**

1. **main.py** - Main FastAPI application with all endpoints
2. **db.py** - TinyDB wrapper for persistent storage
3. **storage.py** - FAISS vector index manager
4. **config.json** - Configuration for models, thresholds, and settings

**Key Features:**
- Multi-session support with complete isolation
- Per-session FAISS vector indexes
- TinyDB for persistent storage (sessions, documents, conversations, config)
- User-selectable primary LLM (Gemini or ChatGPT)
- Automatic fallback to local LLM (Llama 3 via GPT4All)
- Final fallback to heuristic answer generation
- Support for PDF, DOCX, TXT, and Markdown files
- Smart text chunking with overlap
- Out-of-context detection with configurable threshold

### Frontend (Angular)

**Location:** `frontend/src/app/`

**Core Components:**

1. **app.component.ts** - Main application with view management
2. **app.component.html** - Multi-view template (dashboard, session, settings)
3. **app.component.css** - Comprehensive styling
4. **api.service.ts** - API client for backend communication

**Key Features:**
- Session dashboard with creation and management
- Session-specific chat interface
- Document upload with drag-and-drop support
- Conversation history with source citations
- Settings panel for API key management
- Responsive design for desktop and mobile
- Real-time upload progress tracking

## Data Flow

### Document Upload Flow

1. User uploads document to a session
2. Backend parses file (PDF/DOCX/TXT/MD)
3. Text is normalized and chunked (500-1000 tokens per chunk)
4. Chunks are embedded using:
   - Primary LLM embedding API (Gemini/ChatGPT)
   - Fallback to local SBERT if API fails
5. Vectors added to session-specific FAISS index
6. Document metadata saved to TinyDB
7. FAISS index persisted to disk

### Query Flow

1. User submits question in a session
2. Question is embedded using same provider as documents
3. FAISS index searched for top-k similar chunks
4. If similarity score < threshold → "Out of context" response
5. Otherwise, context + question sent to LLM:
   - Try primary LLM (Gemini or ChatGPT)
   - Fallback to local LLM (GPT4All)
   - Final fallback to heuristic extraction
6. Response saved to conversation history in TinyDB
7. Answer returned with source citations

## Storage Structure

```
~/.rag-assistant/
├── db.json                        # TinyDB database
├── docs/                          # Uploaded documents
│   ├── <session_id>/
│   │   ├── <doc_id>_filename.pdf
│   │   └── ...
├── faiss_<session_id>.index       # FAISS index per session
├── faiss_<session_id>.metadata.pkl # Metadata per session
└── config.json                    # Optional user config
```

## TinyDB Schema

### Sessions Collection
```json
{
  "session_id": "uuid",
  "session_name": "string",
  "primary_llm": "gemini|chatgpt",
  "created_at": "ISO timestamp",
  "last_activity": "ISO timestamp"
}
```

### Documents Collection
```json
{
  "document_id": "uuid",
  "session_id": "uuid",
  "file_name": "string",
  "file_type": ".pdf|.docx|.txt|.md",
  "file_path": "string",
  "chunk_count": "integer",
  "uploaded_at": "ISO timestamp"
}
```

### Conversations Collection
```json
{
  "conversation_id": "uuid",
  "session_id": "uuid",
  "query": "string",
  "response": "string",
  "llm_used": "gemini|chatgpt|local-llm|heuristic|out-of-context",
  "sources": [
    {
      "text": "string",
      "doc": "string",
      "chunk": "integer",
      "score": "float"
    }
  ],
  "created_at": "ISO timestamp"
}
```

### User Config Collection
```json
{
  "key_name": "gemini_api_key|chatgpt_api_key",
  "key_value": "string",
  "updated_at": "ISO timestamp"
}
```

## API Endpoints

### Session Management
- `POST /sessions` - Create new session
- `GET /sessions` - List all sessions
- `GET /sessions/{session_id}` - Get session details
- `PUT /sessions/{session_id}` - Update session
- `DELETE /sessions/{session_id}` - Delete session

### Document Management
- `POST /sessions/{session_id}/upload` - Upload document
- `GET /sessions/{session_id}/documents` - List documents

### Query/Conversation
- `POST /sessions/{session_id}/query` - Query documents
- `GET /sessions/{session_id}/conversations` - Get conversation history

### Configuration
- `POST /config` - Set config value (API keys)
- `GET /config/{key_name}` - Get config value
- `GET /config` - Get all config (keys masked)
- `DELETE /config/{key_name}` - Delete config value

### Diagnostics
- `GET /health` - Health check
- `GET /sessions/{session_id}/diagnostics` - Session diagnostics

## LLM Provider Integration

### Gemini (Google)
- **Embedding Model:** `text-embedding-004`
- **Generation Model:** `gemini-2.0-flash-exp`
- **API:** Google Generative Language API
- **Key Storage:** `gemini_api_key` in user config

### ChatGPT (OpenAI)
- **Embedding Model:** `text-embedding-3-small`
- **Generation Model:** `gpt-4o-mini`
- **API:** OpenAI API
- **Key Storage:** `chatgpt_api_key` in user config

### Local LLM (GPT4All)
- **Model:** Mistral 7B / Orca Mini 3B
- **Location:** `backend/app/models/`
- **Framework:** GPT4All
- **Embedding:** SBERT (all-MiniLM-L6-v2)

## Performance Optimizations

1. **Lazy Loading:** SBERT and local LLM loaded only when needed
2. **FAISS Indexing:** Fast vector similarity search
3. **Batch Embeddings:** Multiple chunks embedded in batches
4. **Index Caching:** FAISS indexes cached in memory
5. **Smart Chunking:** Optimal chunk sizes with overlap
6. **BM25 Re-ranking:** Optional re-ranking of retrieved chunks

## Security Features

1. **API Key Storage:** Keys stored in TinyDB, never logged
2. **Key Masking:** API keys masked in GET responses
3. **Local Storage:** All data stored locally (~/.rag-assistant)
4. **CORS Protection:** Configurable CORS middleware
5. **Input Validation:** File type and size validation

## Scalability Considerations

1. **Per-Session Isolation:** Each session has independent FAISS index
2. **Lazy Index Loading:** Indexes loaded on-demand
3. **Disk Persistence:** All data persists across restarts
4. **Efficient Storage:** TinyDB for lightweight NoSQL storage
5. **Configurable Limits:** Chunk size, k-value, thresholds configurable

## Future Enhancements

1. **Advanced Chunking:** Semantic chunking, sentence window
2. **Hybrid Search:** Combine FAISS with BM25 for better retrieval
3. **Streaming Responses:** Stream LLM responses for better UX
4. **Multi-modal Support:** Images, tables, charts
5. **Session Sharing:** Export/import sessions
6. **Advanced Analytics:** Query patterns, usage statistics
7. **Fine-tuning:** Custom embedding fine-tuning
8. **Multi-user Support:** User authentication and authorization

## Development

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python -m app.main
```

### Frontend Setup
```bash
cd frontend
npm install
npm start
```

### Running Tests
```bash
cd backend
pytest tests/
```

## Deployment

The system can be deployed as:
1. **Desktop Application:** Electron wrapper
2. **Docker Container:** Containerized deployment
3. **Cloud Service:** Deploy on AWS/GCP/Azure
4. **Local Server:** Run on local network

## License

See LICENSE file for details.

## Support

For issues and questions, please open an issue on the GitHub repository.

