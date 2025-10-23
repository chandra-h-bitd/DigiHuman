"""
FINQUEST AI - Main Backend
Supports multiple sessions with TinyDB persistence and FAISS vector storage
"""
import os
import io
import re
import uuid
import json
import logging
import threading
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import fitz  # PyMuPDF
from docx import Document
import markdown

import nltk
from nltk.tokenize import sent_tokenize

import numpy as np
import requests

# Import our custom modules
from .db import get_db, Database
from .storage import get_faiss_manager, FAISSManager

# Ensure NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    try:
        nltk.download('punkt_tab')
    except Exception:
        pass

# Logging setup
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="FINQUEST AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize storage
db: Database = get_db()
faiss_manager: FAISSManager = get_faiss_manager()

# Storage paths
STORAGE_PATH = os.path.expanduser("~/.rag-assistant")
DOCS_PATH = os.path.join(STORAGE_PATH, "docs")
os.makedirs(DOCS_PATH, exist_ok=True)

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, 'r') as f:
    CONFIG = json.load(f)

# Model names from config
GEMINI_EMBED_MODEL = CONFIG["gemini"]["embedding_model"]
GEMINI_GEN_MODEL = CONFIG["gemini"]["generation_model"]
OPENAI_EMBED_MODEL = CONFIG["openai"]["embedding_model"]
OPENAI_GEN_MODEL = CONFIG["openai"]["generation_model"]
GROQ_GEN_MODEL = CONFIG["groq"]["generation_model"]
GROQ_API_URL = CONFIG["groq"]["api_url"]

# Lazy-loaded models
_sbert_model = None
_local_llm = None
_local_llm_name: Optional[str] = None

def get_sbert():
    """Lazy-load SBERT model for embeddings"""
    global _sbert_model
    if _sbert_model is not None:
        return _sbert_model
    
    try:
        logger.info("🔄 Loading SBERT model for fallback embeddings...")
        from sentence_transformers import SentenceTransformer
        _sbert_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        logger.info("✅ SBERT model loaded successfully")
        return _sbert_model
    except Exception as e:
        logger.error(f"❌ Failed to load SBERT model: {e}")
        return None

def get_local_llm():
    """Lazy-load a local LLM via GPT4All"""
    global _local_llm, _local_llm_name
    if _local_llm is not None:
        return _local_llm
    
    try:
        from gpt4all import GPT4All
    except Exception as e:
        logger.info(f"Local LLM unavailable (GPT4All import failed): {e}")
        return None
    
    models_dir = os.path.join(os.path.dirname(__file__), "models")
    os.makedirs(models_dir, exist_ok=True)
    
    # Try to load preferred models
    preferred = [
        "mistral-7b-openorca.gguf2.Q4_0.gguf",
        "mistral-7b-instruct-v0.1.Q4_0.gguf",
        "orca-mini-3b-gguf2-q4_0.gguf",
    ]
    
    for model_name in preferred:
        model_path = os.path.join(models_dir, model_name)
        if os.path.isfile(model_path):
            try:
                _local_llm = GPT4All(model_name, model_path=models_dir)
                _local_llm_name = model_name
                logger.info(f"✅ Local LLM loaded: {model_name}")
                return _local_llm
            except Exception as e:
                logger.warning(f"⚠️ Failed to load {model_name}: {e}")
    
    logger.info("ℹ️ No local LLM available - using cloud providers only")
    return None

# ========== Pydantic Models ==========

class SessionCreate(BaseModel):
    session_name: str
    primary_llm: str = "gemini"  # "gemini" or "chatgpt"

class SessionResponse(BaseModel):
    session_id: str
    session_name: str
    primary_llm: str
    created_at: str
    last_activity: str
    document_count: int = 0
    conversation_count: int = 0

class SessionUpdate(BaseModel):
    session_name: Optional[str] = None
    primary_llm: Optional[str] = None

class UploadResponse(BaseModel):
    document_id: str
    session_id: str
    file_name: str
    chunks_indexed: int
    used_fallback: bool
    embed_provider: str
    embedding_model: str  # Specific model name used for embeddings

class QueryRequest(BaseModel):
    session_id: str
    question: str
    k: int = 5

class QueryResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: List[Dict[str, Any]]
    llm_used: str
    used_fallback: bool
    embedding_model: str  # Specific model used for query embedding
    llm_model: str  # Specific model used for answer generation

class ConfigSet(BaseModel):
    key_name: str
    key_value: Any

# ========== Document Processing Utils ==========

def normalize_text(text: str) -> str:
    """Normalize text by removing headers/footers and extra whitespace"""
    lines = [l.strip() for l in text.splitlines()]
    filtered = []
    for l in lines:
        if len(l) <= 2:
            continue
        if re.fullmatch(r"\d+|\d+\s*/\s*\d+", l):
            continue
        filtered.append(l)
    t = " ".join(filtered)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def approx_tokens(text: str) -> int:
    """Approximate token count based on words"""
    return max(1, len(text.split()))

def smart_chunk(text: str, doc_name: str, chunk_size: int = 700) -> List[Dict[str, Any]]:
    """Smart text chunking with overlap"""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks = []
    idx = 0
    
    for p in paragraphs:
        p = normalize_text(p)
        if not p:
            continue
        
        tokens = approx_tokens(p)
        if tokens <= chunk_size:
            chunks.append({"text": p, "doc": doc_name, "chunk": idx})
            idx += 1
            continue
        
        # Sentence split for large paragraphs
        sents = sent_tokenize(p)
        current = []
        current_tokens = 0
        
        for s in sents:
            st = approx_tokens(s)
            if current_tokens + st > chunk_size and current:
                chunk_text = " ".join(current)
                chunks.append({"text": chunk_text, "doc": doc_name, "chunk": idx})
                idx += 1
                # Overlap ~50 tokens
                overlap_words = " ".join(chunk_text.split()[-50:])
                current = [overlap_words, s]
                current_tokens = approx_tokens(" ".join(current))
            else:
                current.append(s)
                current_tokens += st
        
        if current:
            chunk_text = " ".join(current)
            chunks.append({"text": chunk_text, "doc": doc_name, "chunk": idx})
            idx += 1
    
    # Merge very small chunks (<100 tokens)
    merged: List[Dict[str, Any]] = []
    buffer = None
    for ch in chunks:
        if approx_tokens(ch["text"]) < 100:
            if buffer is None:
                buffer = ch
            else:
                buffer["text"] += " " + ch["text"]
        else:
            if buffer is not None:
                merged.append(buffer)
                buffer = None
            merged.append(ch)
    if buffer is not None:
        merged.append(buffer)
    
    return merged

def parse_pdf(file_bytes: bytes) -> str:
    """Parse PDF file"""
    doc = fitz.open(stream=file_bytes, filetype='pdf')
    parts = []
    for page in doc:
        text = page.get_text("text")
        parts.append(text)
    return "\n\n".join(parts)

def parse_docx(file_bytes: bytes) -> str:
    """Parse DOCX file"""
    f = io.BytesIO(file_bytes)
    doc = Document(f)
    parts = [p.text for p in doc.paragraphs]
    return "\n\n".join(parts)

def parse_txt(file_bytes: bytes) -> str:
    """Parse TXT file"""
    return file_bytes.decode('utf-8', errors='ignore')

def parse_markdown(file_bytes: bytes) -> str:
    """Parse Markdown file"""
    md_text = file_bytes.decode('utf-8', errors='ignore')
    # Convert markdown to plain text (remove formatting)
    html = markdown.markdown(md_text)
    # Simple HTML tag removal
    text = re.sub(r'<[^>]+>', ' ', html)
    return text

# ========== LLM Provider Functions ==========

def _model_path(name: str) -> str:
    """Accept either bare id or full path for Gemini models"""
    return name if "/" in name else f"models/{name}"

def embed_with_gemini(texts: List[str], api_key: str, model_name: str = "text-embedding-004") -> Optional[np.ndarray]:
    """Generate embeddings using Gemini API"""
    if not api_key:
        return None
    
    mp = _model_path(model_name)
    url = f"https://generativelanguage.googleapis.com/v1beta/{mp}:embedContent?key={api_key}"
    vectors = []
    
    try:
        for t in texts:
            payload = {
                "model": mp,
                "content": {"parts": [{"text": t}]}
            }
            r = requests.post(url, json=payload, timeout=30)
            if not r.ok:
                logger.warning(f"Gemini embed error: {r.status_code} {r.text[:200]}")
                return None
            data = r.json()
            vec = data.get("embedding", {}).get("values")
            if not vec:
                return None
            vectors.append(np.array(vec, dtype=np.float32))
        return np.vstack(vectors)
    except Exception as e:
        logger.warning(f"Gemini embed exception: {e}")
        return None

def embed_with_chatgpt(texts: List[str], api_key: str, model_name: str = "text-embedding-3-small") -> Optional[np.ndarray]:
    """Generate embeddings using OpenAI/ChatGPT API"""
    if not api_key:
        return None
    
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    vectors = []
    try:
        for text in texts:
            payload = {
                "model": model_name,
                "input": text
            }
            r = requests.post(url, json=payload, headers=headers, timeout=30)
            if not r.ok:
                logger.warning(f"OpenAI embed error: {r.status_code} {r.text[:200]}")
                return None
            data = r.json()
            vec = data.get("data", [{}])[0].get("embedding")
            if not vec:
                return None
            vectors.append(np.array(vec, dtype=np.float32))
        return np.vstack(vectors)
    except Exception as e:
        logger.warning(f"OpenAI embed exception: {e}")
        return None

def embed_with_sbert(texts: List[str]) -> Optional[np.ndarray]:
    """Generate embeddings using SBERT"""
    model = get_sbert()
    if model is None:
        return None
    
    try:
        embeddings = model.encode(texts, normalize_embeddings=True)
        return np.array(embeddings, dtype=np.float32)
    except Exception as e:
        logger.error(f"SBERT embedding failed: {e}")
        return None

def generate_with_gemini(prompt: str, api_key: str, model_name: str = "gemini-2.0-flash-exp") -> Optional[str]:
    """Generate text using Gemini API"""
    if not api_key:
        return None
    
    mp = _model_path(model_name)
    url = f"https://generativelanguage.googleapis.com/v1beta/{mp}:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 512,
        }
    }
    
    try:
        r = requests.post(url, json=payload, timeout=60)
        if not r.ok:
            logger.warning(f"Gemini generate error: {r.status_code} {r.text[:200]}")
            return None
        data = r.json()
        cands = data.get("candidates", [])
        if not cands:
            return None
        parts = cands[0].get("content", {}).get("parts", [])
        out = "".join(p.get("text", "") for p in parts)
        return out.strip() or None
    except Exception as e:
        logger.warning(f"Gemini generate exception: {e}")
        return None

def generate_with_chatgpt(prompt: str, api_key: str, model_name: str = "gpt-4o-mini") -> Optional[str]:
    """Generate text using OpenAI/ChatGPT API"""
    if not api_key:
        return None
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 512
    }
    
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=60)
        if not r.ok:
            logger.warning(f"OpenAI generate error: {r.status_code} {r.text[:200]}")
            return None
        data = r.json()
        choices = data.get("choices", [])
        if not choices:
            return None
        content = choices[0].get("message", {}).get("content", "")
        return content.strip() or None
    except Exception as e:
        logger.warning(f"OpenAI generate exception: {e}")
        return None

def generate_with_groq(prompt: str, api_key: Optional[str] = None) -> Optional[str]:
    """Generate text using Groq API - FAST and FREE fallback LLM"""
    # Groq is extremely fast (faster than Gemini) and offers free tier
    # Uses Llama 3 70B - high quality, open source
    
    if not api_key:
        # Try to get from database
        api_key = db.get_config("groq_api_key")
    
    if not api_key:
        logger.info("No Groq API key - skipping Groq fallback")
        return None
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": GROQ_GEN_MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 512
        }
        
        response = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content.strip() or None
        else:
            logger.warning(f"Groq API error: {response.status_code}")
            return None
            
    except Exception as e:
        logger.warning(f"Groq generation failed: {e}")
        return None

def generate_with_local_llm(question: str, chunks: List[Dict[str, Any]]) -> Optional[str]:
    """Generate with fallback LLM - tries Groq (fast, free) then heuristic"""
    # Build context from chunks
    context_parts = []
    for i, c in enumerate(chunks[:3]):
        context_parts.append(f"[Source {i+1}] {c.get('text', '').strip()}")
    context = "\n\n".join(context_parts)
    
    prompt = f"""Based on the following context, answer the question concisely and cite sources.

Context:
{context}

Question: {question}

Answer (cite sources as [Source N]):"""
    
    # Try Groq first (very fast, high quality)
    logger.info("Trying Groq API fallback...")
    answer = generate_with_groq(prompt)
    if answer:
        logger.info("✅ Groq fallback successful")
        return answer
    
    # Groq failed or no API key - will use heuristic
    logger.info("Groq not available - will use heuristic fallback")
    return None

def heuristic_answer(question: str, chunks: List[Dict[str, Any]]) -> str:
    """Generate an intelligent answer from chunks using smart extraction"""
    if not chunks:
        return "I couldn't find relevant information in the documents to answer your question."
    
    # Enhanced heuristic - extract the most relevant information
    # This is much smarter than just dumping raw chunks
    
    # Simple extractive answer from top chunks
    sentences = []
    for i, chunk in enumerate(chunks[:3]):
        text = chunk.get("text", "")
        sents = sent_tokenize(text)
        for s in sents[:2]:
            if len(s.split()) > 5:
                sentences.append(f"{s} [Source {i+1}]")
    
    if not sentences:
        return "I couldn't find enough information in the documents to answer that question."
    
    return " ".join(sentences[:5])

# ========== API Endpoints ==========

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "storage_path": STORAGE_PATH}

# ========== Session Management ==========

@app.post("/sessions", response_model=SessionResponse)
async def create_session(session: SessionCreate):
    """Create a new session"""
    try:
        new_session = db.create_session(session.session_name, session.primary_llm)
        return SessionResponse(
            session_id=new_session["session_id"],
            session_name=new_session["session_name"],
            primary_llm=new_session["primary_llm"],
            created_at=new_session["created_at"],
            last_activity=new_session["last_activity"],
            document_count=0,
            conversation_count=0
        )
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@app.get("/sessions", response_model=List[SessionResponse])
async def list_sessions():
    """List all sessions"""
    try:
        sessions = db.list_sessions()
        result = []
        for s in sessions:
            doc_count = len(db.get_documents(s["session_id"]))
            conv_count = len(db.get_conversations(s["session_id"]))
            result.append(SessionResponse(
                session_id=s["session_id"],
                session_name=s["session_name"],
                primary_llm=s["primary_llm"],
                created_at=s["created_at"],
                last_activity=s["last_activity"],
                document_count=doc_count,
                conversation_count=conv_count
            ))
        return result
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")

@app.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get a specific session"""
    try:
        session = db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        doc_count = len(db.get_documents(session_id))
        conv_count = len(db.get_conversations(session_id))
        
        return SessionResponse(
            session_id=session["session_id"],
            session_name=session["session_name"],
            primary_llm=session["primary_llm"],
            created_at=session["created_at"],
            last_activity=session["last_activity"],
            document_count=doc_count,
            conversation_count=conv_count
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")

@app.put("/sessions/{session_id}")
async def update_session(session_id: str, updates: SessionUpdate):
    """Update a session"""
    try:
        session = db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        update_dict = {}
        if updates.session_name is not None:
            update_dict["session_name"] = updates.session_name
        if updates.primary_llm is not None:
            update_dict["primary_llm"] = updates.primary_llm
        
        db.update_session(session_id, update_dict)
        return {"status": "ok", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update session: {str(e)}")

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and all its data"""
    try:
        session = db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Delete session data from database
        db.delete_session(session_id)
        
        # Delete FAISS index
        faiss_manager.delete_index(session_id)
        
        # Delete uploaded documents from disk
        session_docs_dir = os.path.join(DOCS_PATH, session_id)
        if os.path.exists(session_docs_dir):
            import shutil
            shutil.rmtree(session_docs_dir)
        
        return {"status": "ok", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

# ========== Document Upload ==========

@app.post("/sessions/{session_id}/upload", response_model=UploadResponse)
async def upload_document(
    session_id: str,
    file: UploadFile = File(...)
):
    """Upload a document to a session"""
    try:
        # Verify session exists
        session = db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Read file
        content = await file.read()
        filename = file.filename or "document"
        ext = os.path.splitext(filename)[1].lower()
        
        # Parse file based on type
        if ext == ".pdf":
            text = parse_pdf(content)
        elif ext == ".docx":
            text = parse_docx(content)
        elif ext == ".txt":
            text = parse_txt(content)
        elif ext in [".md", ".markdown"]:
            text = parse_markdown(content)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
        
        text = normalize_text(text)
        if not text.strip():
            raise HTTPException(status_code=400, detail="File appears to be empty")
        
        # Chunk the text
        chunks = smart_chunk(text, filename)
        if not chunks:
            raise HTTPException(status_code=400, detail="Could not create text chunks")
        
        # Get API keys from config
        gemini_key = db.get_config("gemini_api_key")
        chatgpt_key = db.get_config("chatgpt_api_key")
        
        # Determine which embedding provider to use based on session's primary LLM
        primary_llm = session["primary_llm"]
        texts = [c["text"] for c in chunks]
        vecs = None
        used_fallback = False
        embed_provider = primary_llm
        embedding_model = ""
        
        # Try primary LLM first
        if primary_llm == "gemini" and gemini_key:
            vecs = embed_with_gemini(texts, gemini_key)
            if vecs is not None:
                embedding_model = GEMINI_EMBED_MODEL
        elif primary_llm == "chatgpt" and chatgpt_key:
            vecs = embed_with_chatgpt(texts, chatgpt_key)
            if vecs is not None:
                embedding_model = OPENAI_EMBED_MODEL
        
        # Fallback to local SBERT
        if vecs is None:
            vecs = embed_with_sbert(texts)
            if vecs is not None:
                used_fallback = True
                embed_provider = "sbert"
                embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
                logger.info("Using SBERT fallback for embeddings")
            else:
                raise HTTPException(status_code=500, detail="Failed to generate embeddings")
        
        # Save document to disk
        session_docs_dir = os.path.join(DOCS_PATH, session_id)
        os.makedirs(session_docs_dir, exist_ok=True)
        doc_id = str(uuid.uuid4())
        file_path = os.path.join(session_docs_dir, f"{doc_id}_{filename}")
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Add vectors to FAISS index
        metadata = [{"text": c["text"], "doc": c["doc"], "chunk": c["chunk"]} for c in chunks]
        faiss_manager.add_vectors(session_id, vecs, metadata)
        
        # Save document info to database
        document = db.add_document(session_id, filename, ext, file_path, len(chunks))
        
        logger.info(f"Uploaded {filename} to session {session_id} with {len(chunks)} chunks")
        
        return UploadResponse(
            document_id=document["document_id"],
            session_id=session_id,
            file_name=filename,
            chunks_indexed=len(chunks),
            used_fallback=used_fallback,
            embed_provider=embed_provider,
            embedding_model=embedding_model
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")

@app.get("/sessions/{session_id}/documents")
async def list_documents(session_id: str):
    """List documents in a session"""
    try:
        session = db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        documents = db.get_documents(session_id)
        return documents
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

# ========== Query / Conversation ==========

@app.post("/sessions/{session_id}/query", response_model=QueryResponse)
async def query_session(session_id: str, query: QueryRequest):
    """Query a session's documents"""
    try:
        # Verify session exists
        session = db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get API keys
        gemini_key = db.get_config("gemini_api_key")
        chatgpt_key = db.get_config("chatgpt_api_key")
        
        primary_llm = session["primary_llm"]
        question = query.question
        
        # Embed the question
        q_vec = None
        used_fallback = False
        embedding_model = ""
        
        if primary_llm == "gemini" and gemini_key:
            q_vec = embed_with_gemini([question], gemini_key)
            if q_vec is not None:
                embedding_model = GEMINI_EMBED_MODEL
        elif primary_llm == "chatgpt" and chatgpt_key:
            q_vec = embed_with_chatgpt([question], chatgpt_key)
            if q_vec is not None:
                embedding_model = OPENAI_EMBED_MODEL
        
        if q_vec is None:
            q_vec = embed_with_sbert([question])
            if q_vec is not None:
                used_fallback = True
                embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
                logger.info("Using SBERT fallback for query embedding")
            else:
                raise HTTPException(status_code=500, detail="Failed to generate query embedding")
        
        # Search FAISS index
        top_chunks = faiss_manager.search(session_id, q_vec, k=query.k)
        
        # Check if we have any chunks at all
        llm_model = ""
        if not top_chunks:
            # No chunks found at all - truly out of context
            answer = "I'm sorry, but I couldn't find relevant information in the documents to answer your question. The query appears to be out of context."
            llm_used = "out-of-context"
            llm_model = "N/A (out of context)"
            sources = []
        else:
            # We have chunks - try to answer even if similarity is low
            # This ensures fallback LLM still works with available context
            # Build prompt
            context = "\n\n".join(
                f"[Source {i+1} | {c['doc']}#{c['chunk']}]\n{c['text']}" 
                for i, c in enumerate(top_chunks)
            )
            system_prompt = (
                "You are a helpful assistant answering questions based only on the provided context. "
                "Cite sources as [Source N]. If the answer is not in the context, say so.\n\n"
            )
            prompt = f"{system_prompt}Context:\n{context}\n\nQuestion: {question}\nAnswer:"
            
            # Try primary LLM
            answer = None
            llm_used = primary_llm
            
            if primary_llm == "gemini" and gemini_key:
                answer = generate_with_gemini(prompt, gemini_key)
                if answer:
                    llm_model = GEMINI_GEN_MODEL
            elif primary_llm == "chatgpt" and chatgpt_key:
                answer = generate_with_chatgpt(prompt, chatgpt_key)
                if answer:
                    llm_model = OPENAI_GEN_MODEL
            
            # Fallback to Groq (fast, free LLM)
            if answer is None:
                answer = generate_with_local_llm(question, top_chunks)
                if answer:
                    used_fallback = True
                    llm_used = "groq-fallback"
                    llm_model = GROQ_GEN_MODEL
                    logger.info("Using Groq fallback for generation")
            
            # Final fallback to heuristic
            if answer is None:
                answer = heuristic_answer(question, top_chunks)
                used_fallback = True
                llm_used = "heuristic"
                llm_model = "rule-based-extraction"
                logger.info("Using heuristic fallback for generation")
            
            sources = top_chunks
        
        # Save conversation to database
        conversation = db.add_conversation(
            session_id, question, answer, llm_used, sources
        )
        
        return QueryResponse(
            conversation_id=conversation["conversation_id"],
            answer=answer,
            sources=sources,
            llm_used=llm_used,
            used_fallback=used_fallback,
            embedding_model=embedding_model,
            llm_model=llm_model
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query session: {str(e)}")

@app.get("/sessions/{session_id}/conversations")
async def get_conversations(session_id: str, limit: Optional[int] = None):
    """Get conversation history for a session"""
    try:
        session = db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        conversations = db.get_conversations(session_id, limit)
        return conversations
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversations: {str(e)}")

# ========== User Configuration / API Keys ==========

@app.post("/config")
async def set_config(config: ConfigSet):
    """Set a configuration value (e.g., API keys)"""
    try:
        db.set_config(config.key_name, config.key_value)
        return {"status": "ok", "key_name": config.key_name}
    except Exception as e:
        logger.error(f"Failed to set config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set config: {str(e)}")

@app.get("/config/{key_name}")
async def get_config(key_name: str):
    """Get a configuration value"""
    try:
        value = db.get_config(key_name)
        if value is None:
            raise HTTPException(status_code=404, detail="Config key not found")
        return {"key_name": key_name, "key_value": value}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}")

@app.get("/config")
async def get_all_config():
    """Get all configuration values (keys are masked for security)"""
    try:
        configs = db.get_all_configs()
        # Mask sensitive keys
        masked = {}
        for key, value in configs.items():
            if "api_key" in key.lower():
                masked[key] = "***" + str(value)[-4:] if value else None
            else:
                masked[key] = value
        return masked
    except Exception as e:
        logger.error(f"Failed to get all config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get all config: {str(e)}")

@app.delete("/config/{key_name}")
async def delete_config(key_name: str):
    """Delete a configuration value"""
    try:
        db.delete_config(key_name)
        return {"status": "ok", "key_name": key_name}
    except Exception as e:
        logger.error(f"Failed to delete config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete config: {str(e)}")

# ========== Diagnostics ==========

@app.get("/sessions/{session_id}/diagnostics")
async def session_diagnostics(session_id: str):
    """Get diagnostic information about a session"""
    try:
        session = db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        index_stats = faiss_manager.get_index_stats(session_id)
        documents = db.get_documents(session_id)
        conversations = db.get_conversations(session_id)
        
        return {
            "session": session,
            "faiss_index": index_stats,
            "document_count": len(documents),
            "conversation_count": len(conversations)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get diagnostics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get diagnostics: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)

