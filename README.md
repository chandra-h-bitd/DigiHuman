# Document Q&A (Gemini + SBERT Fallback)

Single-page Angular app with FastAPI backend. Upload PDFs/DOCX, embed with Gemini (fallback to SBERT), store vectors in in-memory Qdrant, and ask questions.

## Features
- Angular SPA (no routing) with Material UI
- Enter Gemini API key (in-memory only)
- Upload PDF/DOCX with progress
- Ask questions; see sources and fallback indicator
- FastAPI backend: parsing, token-aware chunking, embeddings (Gemini primary, SBERT fallback), in-memory Qdrant, model discovery

## Local setup

Backend:

```
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app/main.py
```

Frontend:

```
cd frontend
npm install
npm start
```

Open http://localhost:4200

## Endpoints
- POST /upload (multipart: file, optional session_id, gemini_api_key)
- POST /ask (JSON: session_id, question, k, gemini_api_key)
- GET /models?gemini_api_key=...

## Testing

```
cd backend
pytest -q
```

## Notes
- Keys are not persisted server-side and not logged.
- If Gemini embedding/generation fails, SBERT/heuristic fallbacks are used.
- Qdrant is purely in-memory; restarting clears data.

## Folder structure
- backend: FastAPI app and unit tests
- frontend: Angular single-page app
- examples: sample files placeholder

## Architecture
Upload → Parsing → Chunking → Embeddings → Qdrant → Retrieval → Gemini → Answer

```mermaid
flowchart LR
	A[Angular SPA]\nKey + File + Question -->|/upload| B(FastAPI)
	B --> C{Parse}
	C -->|PDF| D[PyMuPDF]
	C -->|DOCX| E[python-docx]
	D --> F[Token-aware Chunker]
	E --> F
	F --> G{Embeddings}
	G -->|Primary| H[Gemini Embedding]
	G -->|Fallback| I[SBERT all-MiniLM-L6-v2]
	H --> J[(Qdrant In-Memory)]
	I --> J
	A -->|/ask| K{Retrieve Top-k}
	K --> J
	J --> L[Context]
	L --> M{Generate}
	M -->|Primary| N[Gemini Text Model]
	M -->|Fallback| O[Heuristic Concatenation]
	N --> P[Answer + Sources + Fallback flag]
	O --> P
	P --> A
```

# NTT
