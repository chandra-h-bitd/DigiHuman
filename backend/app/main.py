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
from typing import List, Optional, Dict, Any, Tuple
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
from rank_bm25 import BM25Okapi

# Import our custom modules
from .db import get_db, Database
from .storage import get_faiss_manager, FAISSManager

# Logging setup (must be before NLTK downloads to use logger)
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Fix SSL certificate issues for corporate networks
# This applies to: NLTK downloads, Gemini API, Hugging Face, and all HTTPS requests
import ssl
import urllib3
import os

# Disable SSL warnings (we know we're disabling verification for corporate networks)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Disable SSL verification globally (safe for corporate networks)
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context
    logger.info("SSL verification disabled for all HTTPS requests (corporate network fix)")

# Set environment variables for Hugging Face to disable SSL verification
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['HF_HUB_DISABLE_SSL'] = '1'  # Disable SSL for Hugging Face Hub

# Configure requests library to not verify SSL
import requests
requests.packages.urllib3.disable_warnings()

# Download NLTK data with SSL fix
_nltk_available = False
try:
    nltk.data.find('tokenizers/punkt')
    _nltk_available = True
    logger.info("NLTK punkt tokenizer found")
except LookupError:
    try:
        logger.info("Downloading NLTK punkt tokenizer...")
        # Try downloading with SSL disabled (already configured above)
        nltk.download('punkt', quiet=True)
        # Verify it was downloaded
        nltk.data.find('tokenizers/punkt')
        _nltk_available = True
        logger.info("NLTK punkt tokenizer downloaded successfully")
    except Exception as e:
        logger.warning(f"Failed to download NLTK punkt: {e}")
        logger.warning("Will use fallback sentence splitting (period-based)")
        logger.warning("This is safe - chunking will still work, just with simpler sentence detection")

try:
    nltk.data.find('tokenizers/punkt_tab')
    logger.info("NLTK punkt_tab tokenizer found")
except LookupError:
    try:
        logger.info("Downloading NLTK punkt_tab tokenizer (optional)...")
        nltk.download('punkt_tab', quiet=True)
        logger.info("NLTK punkt_tab tokenizer downloaded successfully")
    except Exception as e:
        logger.warning(f"Failed to download NLTK punkt_tab (optional): {e}")
        # punkt_tab is optional, so we can continue without it

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

# Generation parameters from config
GENERATION_TEMPERATURE = CONFIG["generation"]["temperature"]
GENERATION_MAX_TOKENS = CONFIG["generation"]["max_output_tokens"]
SHOW_SOURCES = CONFIG["generation"].get("show_sources", False)

# Retrieval parameters from config
DEFAULT_K = CONFIG["retrieval"]["default_k"]
MAX_K = CONFIG["retrieval"]["max_k"]
SIMILARITY_THRESHOLD = CONFIG["retrieval"]["similarity_threshold"]

# Lazy-loaded models
_sbert_model = None
_local_llm = None
_local_llm_name: Optional[str] = None

def get_sbert():
    """Lazy-load SBERT model for embeddings - using 768D model to match Gemini"""
    global _sbert_model
    if _sbert_model is not None:
        return _sbert_model
    
    try:
        logger.info("🔄 Loading SBERT model for fallback embeddings (768D)...")
        from sentence_transformers import SentenceTransformer
        # Using all-mpnet-base-v2 (768D) to match Gemini embedding dimension
        _sbert_model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
        logger.info("✅ SBERT model loaded successfully (768D)")
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
    question: str
    k: int = DEFAULT_K  # Use config default, max MAX_K

class QueryResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: List[Dict[str, Any]]
    llm_used: str
    used_fallback: bool
    embedding_fallback: bool  # Whether embedding step used a fallback provider
    generation_fallback: bool  # Whether generation step used a fallback provider
    embed_provider: str  # Provider used for embeddings
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
        try:
            if _nltk_available:
                sents = sent_tokenize(p)
            else:
                # Fallback: simple sentence splitting by periods
                sents = [s.strip() + '.' for s in p.split('.') if s.strip()]
        except (LookupError, Exception) as e:
            logger.warning(f"NLTK sentence tokenization failed, using fallback: {e}")
            # Fallback: simple sentence splitting by periods
            sents = [s.strip() + '.' for s in p.split('.') if s.strip()]
        
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

def parse_html(file_bytes: bytes) -> str:
    """Parse HTML file into plain text"""
    html_text = file_bytes.decode('utf-8', errors='ignore')
    # Remove script/style content
    html_text = re.sub(r'<script[^>]*>.*?</script>', ' ', html_text, flags=re.DOTALL | re.IGNORECASE)
    html_text = re.sub(r'<style[^>]*>.*?</style>', ' ', html_text, flags=re.DOTALL | re.IGNORECASE)
    # Strip tags
    text = re.sub(r'<[^>]+>', ' ', html_text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
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
            r = requests.post(url, json=payload, timeout=30, verify=False)
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
            r = requests.post(url, json=payload, headers=headers, timeout=30, verify=False)
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

def generate_with_gemini(prompt: str, api_key: str, model_name: str = None) -> Optional[str]:
    """Generate text using Gemini API"""
    if not api_key:
        return None
    
    # Use config default if not provided
    if model_name is None:
        model_name = GEMINI_GEN_MODEL
    
    mp = _model_path(model_name)
    url = f"https://generativelanguage.googleapis.com/v1beta/{mp}:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": GENERATION_TEMPERATURE,
            "maxOutputTokens": GENERATION_MAX_TOKENS,
        }
    }
    
    try:
        r = requests.post(url, json=payload, timeout=60, verify=False)
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
        "temperature": GENERATION_TEMPERATURE,
        "max_tokens": GENERATION_MAX_TOKENS
    }
    
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=60, verify=False)
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
        logger.info(f"Retrieved Groq API key from DB: {'YES' if api_key else 'NO'}")
    
    if not api_key:
        logger.info("No Groq API key - skipping Groq fallback")
        return None
    
    try:
        logger.info(f"Attempting Groq API call with model: {GROQ_GEN_MODEL}")
        logger.info(f"Groq API URL: {GROQ_API_URL}")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": GROQ_GEN_MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": GENERATION_TEMPERATURE,
            "max_tokens": GENERATION_MAX_TOKENS
        }
        
        response = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=10, verify=False)
        
        logger.info(f"Groq API response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.info(f"✅ Groq API success! Got {len(content)} chars")
            return content.strip() or None
        else:
            logger.warning(f"Groq API error: {response.status_code} - {response.text[:200]}")
            return None
            
    except Exception as e:
        logger.warning(f"Groq generation failed: {type(e).__name__}: {e}")
        return None

def generate_with_ollama(prompt: str, model: str = "llama3") -> Optional[str]:
    """Generate text using Ollama (local LLM)"""
    try:
        import ollama
    except ImportError:
        logger.info("Ollama not available (pip install ollama)")
        return None
    
    try:
        logger.info(f"Trying Ollama with model: {model}")
        response = ollama.generate(model=model, prompt=prompt, options={
            "temperature": GENERATION_TEMPERATURE,
            "num_predict": GENERATION_MAX_TOKENS
        })
        answer = response.get("response", "").strip()
        if answer:
            logger.info("✅ Ollama generation successful")
            return answer
        return None
    except Exception as e:
        logger.warning(f"Ollama generation failed: {e}")
        return None

def generate_with_local_llm(question: str, chunks: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str]]:
    """Generate with fallback LLM - tries Groq, then Ollama, then heuristic
    Returns: (answer, provider) where provider is 'groq', 'ollama', or None"""
    # Build context from chunks
    context_parts = []
    for i, c in enumerate(chunks[:3]):
        if SHOW_SOURCES:
            context_parts.append(f"[Source {i+1}] {c.get('text', '').strip()}")
        else:
            context_parts.append(c.get('text', '').strip())
    context = "\n\n".join(context_parts)
    
    source_instruction = " and cite sources as [Source N]" if SHOW_SOURCES else ""
    prompt = f"""Based on the following context, answer the question concisely{source_instruction}.

Context:
{context}

Question: {question}

Answer{source_instruction}:"""
    
    # Try Groq first (very fast, high quality)
    logger.info("Trying Groq API fallback...")
    answer = generate_with_groq(prompt)
    if answer:
        logger.info("✅ Groq fallback successful")
        return answer, "groq"
    
    # Try Ollama (local LLM, privacy-focused)
    logger.info("Trying Ollama fallback...")
    answer = generate_with_ollama(prompt)
    if answer:
        logger.info("✅ Ollama fallback successful")
        return answer, "ollama"
    
    # Both failed - will use heuristic
    logger.info("Groq and Ollama not available - will use heuristic fallback")
    return None, None

def heuristic_answer(question: str, chunks: List[Dict[str, Any]]) -> str:
    """Generate an intelligent answer from chunks using BM25 + smart extraction"""
    if not chunks:
        return "I couldn't find relevant information in the documents to answer your question."
    
    # Use BM25 for better keyword matching
    try:
        # Tokenize question and chunks
        question_tokens = question.lower().split()
        
        # Prepare corpus for BM25
        corpus = []
        chunk_texts = []
        for chunk in chunks:
            text = chunk.get("text", "")
            chunk_texts.append(text)
            # Simple tokenization for BM25
            tokens = text.lower().split()
            corpus.append(tokens)
        
        if corpus and question_tokens:
            # Create BM25 index
            bm25 = BM25Okapi(corpus)
            # Get BM25 scores
            scores = bm25.get_scores(question_tokens)
            
            # Sort chunks by BM25 score
            scored_chunks = list(zip(chunks, scores, chunk_texts))
            scored_chunks.sort(key=lambda x: x[1], reverse=True)
            
            # Use top 3 chunks based on BM25
            top_chunks = scored_chunks[:3]
        else:
            # Fallback to original order if BM25 fails
            top_chunks = [(chunks[i], 0, chunk_texts[i]) for i in range(min(3, len(chunks)))]
    except Exception as e:
        logger.warning(f"BM25 processing failed, using simple extraction: {e}")
        # Fallback to simple extraction
        top_chunks = [(chunks[i], 0, chunks[i].get("text", "")) for i in range(min(3, len(chunks)))]
    
    # Extract relevant sentences from top chunks
    sentences = []
    for idx, (chunk, score, text) in enumerate(top_chunks):
        try:
            if _nltk_available:
                sents = sent_tokenize(text)
            else:
                # Fallback: simple sentence splitting by periods
                sents = [s.strip() + '.' for s in text.split('.') if s.strip()]
        except (LookupError, Exception) as e:
            logger.warning(f"NLTK sentence tokenization failed in heuristic, using fallback: {e}")
            # Fallback: simple sentence splitting by periods
            sents = [s.strip() + '.' for s in text.split('.') if s.strip()]
        
        # Prioritize sentences that contain question keywords
        question_words = set(question.lower().split())
        for s in sents:
            if len(s.split()) > 5:
                sent_words = set(s.lower().split())
                # Check if sentence contains question keywords
                if question_words.intersection(sent_words) or idx == 0:
                    if SHOW_SOURCES:
                        sentences.append(f"{s} [Source {idx+1}]")
                    else:
                        sentences.append(s)
                    if len(sentences) >= 5:
                        break
    
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
        elif ext in [".html", ".htm"]:
            text = parse_html(content)
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
            vecs = embed_with_gemini(texts, gemini_key, GEMINI_EMBED_MODEL)
            if vecs is not None:
                embedding_model = GEMINI_EMBED_MODEL
        elif primary_llm == "chatgpt" and chatgpt_key:
            vecs = embed_with_chatgpt(texts, chatgpt_key, OPENAI_EMBED_MODEL)
            if vecs is not None:
                embedding_model = OPENAI_EMBED_MODEL
        
        # Fallback to local SBERT
        if vecs is None:
            vecs = embed_with_sbert(texts)
            if vecs is not None:
                used_fallback = True
                embed_provider = "sbert"
                embedding_model = "sentence-transformers/all-mpnet-base-v2"
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
        # Validate and clamp k value (ensure it's between 1 and MAX_K)
        query.k = min(max(1, query.k), MAX_K)
        
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
        embedding_fallback = False
        embed_provider = primary_llm
        
        if primary_llm == "gemini" and gemini_key:
            q_vec = embed_with_gemini([question], gemini_key, GEMINI_EMBED_MODEL)
            if q_vec is not None:
                embedding_model = GEMINI_EMBED_MODEL
                embed_provider = "gemini"
        elif primary_llm == "chatgpt" and chatgpt_key:
            q_vec = embed_with_chatgpt([question], chatgpt_key, OPENAI_EMBED_MODEL)
            if q_vec is not None:
                embedding_model = OPENAI_EMBED_MODEL
                embed_provider = "chatgpt"
        
        if q_vec is None:
            q_vec = embed_with_sbert([question])
            if q_vec is not None:
                used_fallback = True
                embedding_fallback = True
                embedding_model = "sentence-transformers/all-mpnet-base-v2"
                embed_provider = "sbert"
                logger.info("Using SBERT fallback for query embedding")
            else:
                raise HTTPException(status_code=500, detail="Failed to generate query embedding")
        
        # Hybrid search: Vector (FAISS) + Keyword (BM25)
        try:
            # Vector search with FAISS
            vector_chunks = faiss_manager.search(session_id, q_vec, k=query.k * 2)  # Get more for hybrid
            
            # Get all chunks from index for BM25
            index_result = faiss_manager.load_index(session_id)
            bm25_scores_dict = {}
            bm25_chunks = []
            
            if index_result:
                _, all_metadata = index_result
                question_tokens = question.lower().split()
                
                if all_metadata and question_tokens:
                    # Prepare corpus for BM25
                    corpus = []
                    for meta in all_metadata:
                        text = meta.get("text", "")
                        tokens = text.lower().split()
                        corpus.append(tokens)
                    
                    if corpus:
                        # Perform BM25 keyword search
                        bm25 = BM25Okapi(corpus)
                        bm25_scores = bm25.get_scores(question_tokens)
                        
                        # Create BM25 scores dictionary
                        bm25_scores_dict = {all_metadata[i].get("text", ""): bm25_scores[i] for i in range(len(all_metadata))}
                        
                        # Score all chunks with BM25 and get top k
                        bm25_scored = [(all_metadata[i], bm25_scores[i]) for i in range(len(all_metadata))]
                        bm25_scored.sort(key=lambda x: x[1], reverse=True)
                        bm25_chunks = [chunk for chunk, score in bm25_scored[:query.k]]
            
            # Combine vector and BM25 results
            vector_scores = {chunk.get("text", ""): chunk.get("score", 0) for chunk in vector_chunks}
            
            # Normalize scores to 0-1 range for combination
            if vector_chunks:
                max_vec_score = max([c.get("score", 0) for c in vector_chunks]) or 1
                if max_vec_score > 0:
                    vector_scores = {k: v / max_vec_score for k, v in vector_scores.items()}
            
            if bm25_scores_dict:
                max_bm25_score = max(bm25_scores_dict.values()) or 1
                if max_bm25_score > 0:
                    bm25_scores_dict = {k: v / max_bm25_score for k, v in bm25_scores_dict.items()}
            
            # Combine scores (weighted: 70% vector, 30% BM25)
            combined_scores = {}
            all_chunks_dict = {}
            
            # Add vector chunks
            for chunk in vector_chunks:
                text = chunk.get("text", "")
                all_chunks_dict[text] = chunk
                combined_scores[text] = vector_scores.get(text, 0) * 0.7
            
            # Add BM25 scores to combined scores
            for text, bm25_score in bm25_scores_dict.items():
                if text in all_chunks_dict:
                    combined_scores[text] = combined_scores.get(text, 0) + (bm25_score * 0.3)
                elif bm25_chunks:
                    # Find chunk by text
                    for chunk in bm25_chunks:
                        if chunk.get("text", "") == text:
                            all_chunks_dict[text] = chunk
                            combined_scores[text] = (bm25_score * 0.3)
                            break
            
            # Sort by combined score and take top k
            sorted_chunks = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
            top_chunks = [all_chunks_dict[text] for text, score in sorted_chunks[:query.k] if text in all_chunks_dict]
            
            # If hybrid search didn't produce results, fallback to vector only
            if not top_chunks and vector_chunks:
                top_chunks = vector_chunks[:query.k]
                
        except ValueError as e:
            # Dimension mismatch - provide helpful error message
            if "Dimension mismatch" in str(e):
                error_detail = (
                    "Embedding model mismatch detected. Your documents were uploaded with a different "
                    "embedding model than what's currently being used for queries. "
                    "Please either: (1) Set your original API key back, or (2) Delete and re-upload "
                    "your documents with the current settings."
                )
                raise HTTPException(status_code=400, detail=error_detail)
            raise
        
        # Check if we have any chunks at all
        llm_model = ""
        generation_fallback = False
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
            if SHOW_SOURCES:
                context = "\n\n".join(
                    f"[Source {i+1} | {c['doc']}#{c['chunk']}]\n{c['text']}" 
                    for i, c in enumerate(top_chunks)
                )
                system_prompt = (
                    "You are a helpful assistant answering questions based only on the provided context. "
                    "Cite sources as [Source N]. If the answer is not in the context, say so.\n\n"
                )
            else:
                context = "\n\n".join(
                    f"{c['text']}" 
                    for c in top_chunks
                )
                system_prompt = (
                    "You are a helpful assistant answering questions based only on the provided context. "
                    "If the answer is not in the context, say so.\n\n"
                )
            prompt = f"{system_prompt}Context:\n{context}\n\nQuestion: {question}\nAnswer:"
            
            # Try primary LLM
            answer = None
            llm_used = primary_llm
            generation_fallback = False
            
            if primary_llm == "gemini" and gemini_key:
                answer = generate_with_gemini(prompt, gemini_key, GEMINI_GEN_MODEL)
                if answer:
                    llm_model = GEMINI_GEN_MODEL
            elif primary_llm == "chatgpt" and chatgpt_key:
                answer = generate_with_chatgpt(prompt, chatgpt_key, OPENAI_GEN_MODEL)
                if answer:
                    llm_model = OPENAI_GEN_MODEL
            
            # Fallback to Groq, then Ollama, then heuristic
            if answer is None:
                answer, fallback_provider = generate_with_local_llm(question, top_chunks)
                if answer:
                    used_fallback = True
                    generation_fallback = True
                    if fallback_provider == "groq":
                        llm_used = "groq-fallback"
                        llm_model = GROQ_GEN_MODEL
                        logger.info("Using Groq fallback for generation")
                    elif fallback_provider == "ollama":
                        llm_used = "ollama-fallback"
                        llm_model = "ollama-llama3"
                        logger.info("Using Ollama fallback for generation")
            
            # Final fallback to heuristic
            if answer is None:
                answer = heuristic_answer(question, top_chunks)
                used_fallback = True
                generation_fallback = True
                llm_used = "heuristic"
                llm_model = "rule-based-extraction"
                logger.info("Using heuristic fallback for generation")
            
            # Remove [Source N] tags from answer if sources are hidden
            if not SHOW_SOURCES and answer:
                answer = re.sub(r'\s*\[Source \d+\]\s*', ' ', answer)
                answer = re.sub(r'\s{2,}', ' ', answer).strip()
            
            # Return empty sources array if sources are hidden
            sources = top_chunks if SHOW_SOURCES else []
        
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
            embedding_fallback=embedding_fallback,
            generation_fallback=generation_fallback,
            embed_provider=embed_provider,
            embedding_model=embedding_model,
            llm_model=llm_model
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query session: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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

