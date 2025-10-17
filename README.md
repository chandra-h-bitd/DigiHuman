# Document Q&A (Multi-LLM Support)

Single-page Angular app with FastAPI backend. Upload PDFs/DOCX, embed with multiple LLM providers (Gemini, OpenAI), store vectors in in-memory Qdrant, and ask questions.

## Features
- Angular SPA (no routing) with Material UI
- **Multi-LLM Support**: Choose between Google Gemini and OpenAI
- **Model Selection**: Select specific embedding and generation models
- **Real-time API Validation**: Test API keys before use
- Upload PDF/DOCX with progress
- Ask questions; see sources and fallback indicator
- FastAPI backend: parsing, token-aware chunking, embeddings (provider-specific with SBERT fallback), in-memory Qdrant, comprehensive model discovery

## Local setup

If this is your first time on a fresh machine, follow an OS-specific guide first:

- macOS: docs/SETUP-macOS.md
- Windows: docs/SETUP-Windows.md

Quickstart (after prerequisites):

Backend:

```
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app/main.py


/Users/prashant/Downloads/CodeBase/NTT/backend/venv/bin/python3 -m app.main
```

Frontend:

```
cd frontend
npm install
npm start
```

Open http://localhost:4200

## Endpoints
- POST /upload (multipart: file, session_id, provider, api_key, embedding_model, generation_model)
- POST /ask (JSON: session_id, question, k, provider, api_key, embedding_model, generation_model)
- GET /models?provider=gemini&api_key=...
- POST /validate (JSON: provider, api_key, embedding_model, generation_model)

## Testing

```
cd backend
pytest -q
```

## Notes
- Keys are not persisted server-side and not logged.
- If provider embedding/generation fails, SBERT/heuristic fallbacks are used.
- Qdrant is purely in-memory; restarting clears data.
- **Supported Providers**: Google Gemini, OpenAI
- **Model Selection**: Choose from available embedding and generation models for each provider
- **API Validation**: Real-time validation ensures your API keys work before processing documents

## Folder structure
- backend: FastAPI app and unit tests
- frontend: Angular single-page app
- examples: sample files placeholder

## Architecture
Upload → Parsing → Chunking → Embeddings → Qdrant → Retrieval → LLM Generation → Answer

```mermaid
flowchart LR
	A[Angular SPA]\nProvider + Key + Models + File + Question -->|/upload| B(FastAPI)
	B --> C{Parse}
	C -->|PDF| D[PyMuPDF]
	C -->|DOCX| E[python-docx]
	D --> F[Token-aware Chunker]
	E --> F
	F --> G{Embeddings}
	G -->|Primary| H[Provider Embedding\nGemini/OpenAI]
	G -->|Fallback| I[SBERT all-MiniLM-L6-v2]
	H --> J[(Qdrant In-Memory)]
	I --> J
	A -->|/ask| K{Retrieve Top-k}
	K --> J
	J --> L[Context]
	L --> M{Generate}
	M -->|Primary| N[Provider LLM\nGemini/OpenAI]
	M -->|Fallback| O[Local LLM/Heuristic]
	N --> P[Answer + Sources + Fallback flag]
	O --> P
	P --> A
```

# NTT
