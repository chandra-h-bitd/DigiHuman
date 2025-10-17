import os
import io
import re
import uuid
import json
from typing import List, Optional, Dict, Any
import logging

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import fitz  # PyMuPDF
from docx import Document

import nltk
from nltk.tokenize import sent_tokenize

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue

import requests
import json as _json

# Ensure punkt + punkt_tab for NLTK 3.9
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

app = FastAPI(title="Finquest Q&A (Multi-LLM Support)")

# Basic logging setup (no secrets)
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state per session key (a simple session id sent from frontend)
SESSIONS: Dict[str, Dict[str, Any]] = {}

# Qdrant in-memory client
qdrant = QdrantClient(path=":memory:")

def collection_name(session_id: str) -> str:
    return f"doc_chunks_{session_id}"


def session_log(session_id: str, event_type: str, data: Dict[str, Any]):
    try:
        sess = SESSIONS.setdefault(session_id, {})
        events = sess.setdefault("events", [])
        data = dict(data)
        # never include secrets in logs
        if "gemini_api_key" in data:
            data["gemini_api_key"] = bool(data["gemini_api_key"])  # redact
        events.append({"type": event_type, "data": data})
        # keep only last 100
        if len(events) > 100:
            del events[:-100]
    except Exception:
        pass

# Config loader (JSON file with env overrides)
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
_CONFIG: Dict[str, Any] = {}
try:
    if os.path.isfile(_CONFIG_PATH):
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            _CONFIG = _json.load(f)
except Exception as _e:
    logger.info(f"Config load failed: {_e}")

# Provider configurations
def get_provider_config(provider: str) -> Dict[str, Any]:
    """Get configuration for a specific provider"""
    return _CONFIG.get(provider, {})

def get_available_models(provider: str) -> Dict[str, List[str]]:
    """Get available models for a provider"""
    config = get_provider_config(provider)
    return config.get("available_models", {"embedding": [], "generation": []})

# Default models for each provider
DEFAULT_GEMINI_EMBED = os.environ.get(
    "GEMINI_EMBED_MODEL",
    get_provider_config("gemini").get("embedding_model", "models/text-embedding-004"),
)
DEFAULT_GEMINI_GEN = os.environ.get(
    "GEMINI_GEN_MODEL",
    get_provider_config("gemini").get("generation_model", "models/gemini-2.5-flash"),
)

DEFAULT_OPENAI_EMBED = os.environ.get(
    "OPENAI_EMBED_MODEL",
    get_provider_config("openai").get("embedding_model", "text-embedding-3-small"),
)
DEFAULT_OPENAI_GEN = os.environ.get(
    "OPENAI_GEN_MODEL",
    get_provider_config("openai").get("generation_model", "gpt-4o-mini"),
)

# Local SBERT model (lazy loaded)
_sbert_model = None  # lazy-loaded SentenceTransformer instance
_local_llm = None   # lazy-loaded GPT4All model instance
_local_llm_name: Optional[str] = None  # selected local model name for diagnostics

def get_sbert():
    global _sbert_model
    if _sbert_model is None:
        # Lazy import to avoid heavy startup cost
        from sentence_transformers import SentenceTransformer
        _sbert_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _sbert_model

def get_local_llm():
    """Lazy-load a local LLM via GPT4All, preferring an on-disk GGUF before any downloads.
    Preference order:
      1) LOCAL_LLM_PATH (if it points to an existing file)
      2) A bundled GGUF in app/models with priority to 'orca-mini-3b-gguf2-q4_0.gguf', then any *.gguf
      3) Named models (LOCAL_LLM_MODEL or small defaults) which may trigger download
    """
    global _local_llm, _local_llm_name
    if _local_llm is not None:
        return _local_llm
    try:
        from gpt4all import GPT4All  # type: ignore
    except Exception as e:
        logger.info(f"Local LLM unavailable (GPT4All import failed): {e}")
        return None

    # Determine models directory inside backend/app, allow config override
    cfg_local = (_CONFIG.get("local_llm") or {})
    cfg_dir = cfg_local.get("dir")
    models_dir = cfg_dir or os.path.join(os.path.dirname(__file__), "models")
    try:
        os.makedirs(models_dir, exist_ok=True)
    except Exception:
        pass

    # 1) Explicit path override
    explicit_path = os.environ.get("LOCAL_LLM_PATH") or cfg_local.get("path")
    if explicit_path and os.path.isfile(explicit_path):
        name = os.path.basename(explicit_path)
        directory = os.path.dirname(explicit_path)
        try:
            _local_llm = GPT4All(name, model_path=directory)
            _local_llm_name = name
            logger.info(f"Local LLM loaded from explicit path: {explicit_path}")
            return _local_llm
        except Exception as e:
            logger.info(f"Failed to load local LLM from LOCAL_LLM_PATH={explicit_path}: {e}")

    # 2) Prefer bundled GGUF(s)
    preferred = [
        "orca-mini-3b-gguf2-q4_0.gguf",
    ]
    chosen_name: Optional[str] = None
    for nm in preferred:
        p = os.path.join(models_dir, nm)
        if os.path.isfile(p):
            chosen_name = nm
            break
    if chosen_name is None:
        # First available *.gguf in models_dir
        try:
            ggufs = [f for f in os.listdir(models_dir) if f.lower().endswith(".gguf")]
            if ggufs:
                ggufs.sort()
                chosen_name = ggufs[0]
        except Exception:
            pass
    if chosen_name:
        try:
            _local_llm = GPT4All(chosen_name, model_path=models_dir)
            _local_llm_name = chosen_name
            logger.info(f"Local LLM loaded: {chosen_name} (dir={models_dir})")
            return _local_llm
        except Exception as e:
            logger.info(f"Failed to load bundled local LLM '{chosen_name}': {e}")

    # 3) Fallback to named models (may download on first use)
    model_name = os.environ.get("LOCAL_LLM_MODEL") or cfg_local.get("model") or "ggml-gpt4all-j-v1.3-groovy"
    try:
        _local_llm = GPT4All(model_name, model_path=models_dir)
        _local_llm_name = model_name
        logger.info(f"Local LLM loaded by name: {model_name} (dir={models_dir})")
        return _local_llm
    except Exception as e:
        logger.info(f"Local LLM unavailable (failed to load '{model_name}'): {e}")
        return None

# ---------- Models ----------
class UploadResponse(BaseModel):
    session_id: str
    chunks_indexed: int
    used_fallback: bool
    embed_provider: str
    embedding_model: Optional[str]
    vector_dim: Optional[int]

class AskRequest(BaseModel):
    session_id: str
    question: str
    k: int = 5
    provider: str = "gemini"  # "gemini" or "openai"
    api_key: Optional[str] = None
    embedding_model: Optional[str] = None
    generation_model: Optional[str] = None

class AskResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    used_fallback: bool
    gen_provider: str
    generation_model: Optional[str]
    embed_provider: str
    embedding_model: Optional[str]

class ModelsResponse(BaseModel):
    provider: str
    embedding_model: Optional[str]
    generation_model: Optional[str]
    available_models: Dict[str, List[str]]
    api_valid: bool
    error_message: Optional[str] = None

class ProviderValidationRequest(BaseModel):
    provider: str
    api_key: str
    embedding_model: Optional[str] = None
    generation_model: Optional[str] = None

# ---------- Utils ----------

def normalize_text(text: str) -> str:
    # remove headers/footers simple heuristic: drop lines that are mostly digits or very short
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

# crude token estimate based on words

def approx_tokens(text: str) -> int:
    return max(1, len(text.split()))


def smart_chunk(text: str, doc_name: str) -> List[Dict[str, Any]]:
    # paragraph split
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks = []
    idx = 0
    for p in paragraphs:
        p = normalize_text(p)
        if not p:
            continue
        tokens = approx_tokens(p)
        if tokens <= 700:
            chunks.append({"text": p, "meta": {"doc": doc_name, "chunk": idx}})
            idx += 1
            continue
        # sentence split if large paragraph
        sents = sent_tokenize(p)
        current = []
        current_tokens = 0
        chunk_start = 0
        for s in sents:
            st = approx_tokens(s)
            if current_tokens + st > 650 and current:
                chunk_text = " ".join(current)
                chunks.append({"text": chunk_text, "meta": {"doc": doc_name, "chunk": idx}})
                idx += 1
                # overlap ~50 tokens
                overlap_words = " ".join(chunk_text.split()[-50:])
                current = [overlap_words, s]
                current_tokens = approx_tokens(" ".join(current))
            else:
                current.append(s)
                current_tokens += st
        if current:
            chunk_text = " ".join(current)
            chunks.append({"text": chunk_text, "meta": {"doc": doc_name, "chunk": idx}})
            idx += 1
    # merge very small chunks (<100 tokens)
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
    doc = fitz.open(stream=file_bytes, filetype='pdf')
    parts = []
    for page in doc:
        text = page.get_text("text")
        parts.append(text)
    return "\n\n".join(parts)


def parse_docx(file_bytes: bytes) -> str:
    f = io.BytesIO(file_bytes)
    doc = Document(f)
    parts = [p.text for p in doc.paragraphs]
    return "\n\n".join(parts)


# ---------- Embeddings ----------

def get_provider_models(provider: str, api_key: str) -> Dict[str, Any]:
    """Get models and validate API key for a provider"""
    if not api_key:
        return {
            "provider": provider,
            "embedding_model": None, 
            "generation_model": None, 
            "available_models": {"embedding": [], "generation": []},
            "api_valid": False,
            "error_message": "No API key provided"
        }
    
    config = get_provider_config(provider)
    available_models = get_available_models(provider)
    
    if provider == "gemini":
        return {
            "provider": provider,
            "embedding_model": config.get("embedding_model", DEFAULT_GEMINI_EMBED),
            "generation_model": config.get("generation_model", DEFAULT_GEMINI_GEN),
            "available_models": available_models,
            "api_valid": True,
            "error_message": None
        }
    elif provider == "openai":
        return {
            "provider": provider,
            "embedding_model": config.get("embedding_model", DEFAULT_OPENAI_EMBED),
            "generation_model": config.get("generation_model", DEFAULT_OPENAI_GEN),
            "available_models": available_models,
            "api_valid": True,
            "error_message": None
        }
    else:
        return {
            "provider": provider,
            "embedding_model": None,
            "generation_model": None,
            "available_models": {"embedding": [], "generation": []},
            "api_valid": False,
            "error_message": f"Unsupported provider: {provider}"
        }


def _model_path(name: str) -> str:
    # Accept either bare id (e.g., text-embedding-004) or full path (models/text-embedding-004)
    return name if "/" in name else f"models/{name}"


def embed_with_gemini(texts: List[str], api_key: str, model_name: Optional[str]) -> Optional[np.ndarray]:
    if not api_key or not model_name:
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
                logger.warning(f"Gemini embed error status={r.status_code} body={r.text[:200]}")
                r.raise_for_status()
            data = r.json()
            vec = data.get("embedding", {}).get("values")
            if not vec:
                logger.warning("Gemini embed returned no vector values")
                return None
            vectors.append(np.array(vec, dtype=np.float32))
        return np.vstack(vectors)
    except Exception as e:
        logger.warning(f"Gemini embed exception: {e}")
        return None


def embed_with_openai(texts: List[str], api_key: str, model_name: Optional[str]) -> Optional[np.ndarray]:
    """Generate embeddings using OpenAI API"""
    if not api_key or not model_name:
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
                logger.warning(f"OpenAI embed error status={r.status_code} body={r.text[:200]}")
                r.raise_for_status()
            data = r.json()
            vec = data.get("data", [{}])[0].get("embedding")
            if not vec:
                logger.warning("OpenAI embed returned no vector values")
                return None
            vectors.append(np.array(vec, dtype=np.float32))
        return np.vstack(vectors)
    except Exception as e:
        logger.warning(f"OpenAI embed exception: {e}")
        return None


def embed_with_sbert(texts: List[str]) -> np.ndarray:
    model = get_sbert()
    return np.array(model.encode(texts, normalize_embeddings=True), dtype=np.float32)


# ---------- Generation ----------

def generate_with_gemini(prompt: str, api_key: str, model_name: Optional[str]) -> Optional[str]:
    if not api_key or not model_name:
        return None
    mp = _model_path(model_name)
    url = f"https://generativelanguage.googleapis.com/v1beta/{mp}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 512,
        }
    }
    try:
        r = requests.post(url, json=payload, timeout=60)
        if not r.ok:
            logger.warning(f"Gemini generate error status={r.status_code} body={r.text[:200]}")
            r.raise_for_status()
        data = r.json()
        cands = data.get("candidates", [])
        if not cands:
            logger.warning("Gemini generate returned no candidates")
            return None
        parts = cands[0].get("content", {}).get("parts", [])
        out = "".join(p.get("text", "") for p in parts)
        return out.strip() or None
    except Exception as e:
        logger.warning(f"Gemini generate exception: {e}")
        return None


def generate_with_openai(prompt: str, api_key: str, model_name: Optional[str]) -> Optional[str]:
    """Generate text using OpenAI API"""
    if not api_key or not model_name:
        return None
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 512
    }
    
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=60)
        if not r.ok:
            logger.warning(f"OpenAI generate error status={r.status_code} body={r.text[:200]}")
            r.raise_for_status()
        data = r.json()
        choices = data.get("choices", [])
        if not choices:
            logger.warning("OpenAI generate returned no choices")
            return None
        content = choices[0].get("message", {}).get("content", "")
        return content.strip() or None
    except Exception as e:
        logger.warning(f"OpenAI generate exception: {e}")
        return None


def generate_with_local_llm(question: str, chunks: List[Dict[str, Any]], max_chars: int = 8000) -> Optional[str]:
    """Generate an answer with a local LLM (GPT4All) using provided chunks as context.
    Returns None if local LLM is not available or generation fails.
    """
    llm = get_local_llm()
    if llm is None:
        return None
    # Build compact context up to max_chars
    parts = []
    total = 0
    for i, c in enumerate(chunks):
        header = f"[Source {i+1} | {c.get('doc','')}#{c.get('chunk',-1)}]\n"
        body = c.get("text", "").strip()
        seg = header + body + "\n\n"
        if total + len(seg) > max_chars:
            break
        parts.append(seg)
        total += len(seg)

    context = "".join(parts)
    system = (
        "You are a helpful assistant. Answer the user's question using only the provided context. "
        "If the answer is not present, say you don't know. Cite sources as [Source N].\n\n"
    )
    prompt = f"{system}Context:\n{context}\nQuestion: {question}\nAnswer:"
    try:
        # GPT4All chat session keeps context local; deterministic-ish output
        with llm.chat_session():
            out = llm.generate(prompt, max_tokens=512, temp=0.2)
        return (out or "").strip() or None
    except Exception as e:
        logger.info(f"Local LLM generation failed: {e}")
        return None


def _bm25_rerank(question: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Optional BM25 re-ranking of retrieved chunks. Returns re-ordered list or original on error."""
    try:
        from rank_bm25 import BM25Okapi  # type: ignore
        tokenized = [re.findall(r"\w+", c.get("text", "").lower()) for c in chunks]
        bm = BM25Okapi(tokenized)
        q_tokens = re.findall(r"\w+", question.lower())
        scores = bm.get_scores(q_tokens)
        ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
        return [c for _, c in ranked]
    except Exception:
        return chunks


def heuristic_answer(question: str, chunks: List[Dict[str, Any]]) -> str:
    # Improved heuristic with BM25 sentence ranking and citations; falls back to keyword overlap.
    if not chunks:
        return "I couldn't find enough information in the document to answer that."

    # Build sentence pool with source mapping
    sent_pool: List[Dict[str, Any]] = []
    for i, ch in enumerate(chunks):
        src_tag = f"[Source {i+1}]"
        for s in sent_tokenize(ch.get("text", "")):
            s_clean = re.sub(r"\s+", " ", s).strip()
            if not s_clean:
                continue
            sent_pool.append({
                "text": s_clean,
                "src": src_tag,
                "doc": ch.get("doc", ""),
                "chunk": ch.get("chunk", -1),
            })

    if not sent_pool:
        return "I couldn't find enough information in the document to answer that."

    # Summary intent detection
    is_summary = bool(re.search(r"summari[sz]e|overview|bullet|key\s*takeaways|high\s*level|main\s*points", question, re.I))

    # Try BM25 scoring first
    bm25_scores: List[float] = []
    try:
        from rank_bm25 import BM25Okapi  # type: ignore
        tokenized = [re.findall(r"\w+", s["text"].lower()) for s in sent_pool]
        bm = BM25Okapi(tokenized)
        q_tokens = re.findall(r"\w+", question.lower())
        bm25_scores = bm.get_scores(q_tokens)
    except Exception:
        # Fallback: keyword overlap score
        q_words = set(w.lower() for w in re.findall(r"\w+", question))
        for s in sent_pool:
            sw = set(w.lower() for w in re.findall(r"\w+", s["text"]))
            bm25_scores.append(len(q_words & sw))

    # Rank sentences
    ranked = sorted(zip(bm25_scores, sent_pool), key=lambda x: x[0], reverse=True)

    # If summary requested, select diverse top sentences across different chunks
    if is_summary:
        picked: List[Dict[str, Any]] = []
        seen_chunks: set = set()
        for score, s in ranked:
            if len(picked) >= 5:
                break
            # prefer diversity of chunks and avoid very short sentences
            if s["chunk"] in seen_chunks:
                continue
            if len(s["text"].split()) < 5:
                continue
            picked.append(s)
            seen_chunks.add(s["chunk"])
        # If still few, fill from remaining
        if len(picked) < 5:
            for score, s in ranked:
                if len(picked) >= 5:
                    break
                if s in picked or len(s["text"].split()) < 5:
                    continue
                picked.append(s)
        if not picked:
            return "I couldn't find enough information in the document to summarize."
        bullets = "\n".join(f"- {s['text']} {s['src']}" for s in picked)
        return bullets

    # Otherwise, assemble an extractive answer from top sentences with citations
    top_n = 5
    selected = []
    for score, s in ranked:
        if len(selected) >= top_n:
            break
        if len(s["text"].split()) < 5:
            continue
        selected.append(s)

    if not selected:
        return "I couldn't find enough information in the document to answer that."

    # Join as a concise paragraph with inline citations
    answer = " ".join(f"{s['text']} {s['src']}" for s in selected)
    return answer.strip()


# ---------- API Validation ----------

def validate_api_key(provider: str, api_key: str, embedding_model: Optional[str] = None, generation_model: Optional[str] = None) -> Dict[str, Any]:
    """Validate API key by making test calls to the provider"""
    if not api_key:
        return {
            "valid": False,
            "error": "No API key provided"
        }
    
    try:
        if provider == "gemini":
            # Test embedding call
            test_embed_model = embedding_model or DEFAULT_GEMINI_EMBED
            test_vec = embed_with_gemini(["test"], api_key, test_embed_model)
            if test_vec is None:
                return {
                    "valid": False,
                    "error": "Failed to generate embeddings with provided key"
                }
            
            # Test generation call
            test_gen_model = generation_model or DEFAULT_GEMINI_GEN
            test_response = generate_with_gemini("Hello", api_key, test_gen_model)
            if test_response is None:
                return {
                    "valid": False,
                    "error": "Failed to generate text with provided key"
                }
            
            return {
                "valid": True,
                "error": None,
                "embedding_model": test_embed_model,
                "generation_model": test_gen_model
            }
            
        elif provider == "openai":
            # Test embedding call
            test_embed_model = embedding_model or DEFAULT_OPENAI_EMBED
            test_vec = embed_with_openai(["test"], api_key, test_embed_model)
            if test_vec is None:
                return {
                    "valid": False,
                    "error": "Failed to generate embeddings with provided key"
                }
            
            # Test generation call
            test_gen_model = generation_model or DEFAULT_OPENAI_GEN
            test_response = generate_with_openai("Hello", api_key, test_gen_model)
            if test_response is None:
                return {
                    "valid": False,
                    "error": "Failed to generate text with provided key"
                }
            
            return {
                "valid": True,
                "error": None,
                "embedding_model": test_embed_model,
                "generation_model": test_gen_model
            }
        else:
            return {
                "valid": False,
                "error": f"Unsupported provider: {provider}"
            }
    except Exception as e:
        return {
            "valid": False,
            "error": f"Validation error: {str(e)}"
        }


# ---------- API ----------
@app.post("/upload", response_model=UploadResponse)
async def upload(
    file: UploadFile = File(...), 
    session_id: Optional[str] = Form(None), 
    provider: str = Form("gemini"),
    api_key: Optional[str] = Form(None),
    embedding_model: Optional[str] = Form(None),
    generation_model: Optional[str] = Form(None)
):
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

    filename = file.filename or "document"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in [".pdf", ".docx"]:
        raise HTTPException(status_code=400, detail="Only .pdf and .docx supported")

    if not session_id:
        session_id = str(uuid.uuid4())

    try:
        if ext == ".pdf":
            text = parse_pdf(content)
        else:
            text = parse_docx(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}")

    text = normalize_text(text)
    if not text.strip():
        raise HTTPException(status_code=400, detail="File appears to be empty or could not extract text")
    
    chunks = smart_chunk(text, filename)
    if not chunks:
        raise HTTPException(status_code=400, detail="Could not create text chunks from document")

    # Embeddings: try provider first, fallback to SBERT
    used_fallback = False
    provider_config = get_provider_config(provider)
    
    if api_key and provider in ["gemini", "openai"]:
        # Use provider-specific embedding model
        if provider == "gemini":
            emb_model = embedding_model or provider_config.get("embedding_model", DEFAULT_GEMINI_EMBED)
            gen_model = generation_model or provider_config.get("generation_model", DEFAULT_GEMINI_GEN)
        else:  # openai
            emb_model = embedding_model or provider_config.get("embedding_model", DEFAULT_OPENAI_EMBED)
            gen_model = generation_model or provider_config.get("generation_model", DEFAULT_OPENAI_GEN)
    else:
        emb_model = None
        gen_model = None

    texts = [c["text"] for c in chunks]
    logger.info(f"/upload: session={session_id} file={filename} provider={provider} key_provided={bool(api_key)} emb_model={emb_model}")
    
    # Try provider-specific embedding
    vecs = None
    if provider == "gemini" and api_key:
        vecs = embed_with_gemini(texts, api_key, emb_model)
    elif provider == "openai" and api_key:
        vecs = embed_with_openai(texts, api_key, emb_model)
    
    if vecs is None:
        try:
            vecs = embed_with_sbert(texts)
            used_fallback = True
            embed_provider = "sbert"
            logger.info(f"/upload: fallback embeddings used (SBERT)")
        except Exception as e:
            logger.error(f"/upload: SBERT embedding failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate embeddings")
    else:
        embed_provider = provider
        logger.info(f"/upload: embeddings via {provider} model={emb_model}")

    # Determine embedding model name for response/logs
    embedding_model_name: Optional[str] = None
    if embed_provider == "gemini":
        embedding_model_name = emb_model
    elif embed_provider == "openai":
        embedding_model_name = emb_model
    else:
        embedding_model_name = "sentence-transformers/all-MiniLM-L6-v2"

    # upsert to qdrant with session-specific payload
    dim = int(vecs.shape[1])
    coll = collection_name(session_id)
    # (Re)create collection for this session with appropriate vector size
    try:
        qdrant.recreate_collection(
            collection_name=coll,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
    except Exception:
        # Fallback: try create if not exists
        try:
            qdrant.create_collection(
                collection_name=coll,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
        except Exception:
            pass

    points = []
    for i, (c, v) in enumerate(zip(chunks, vecs)):
        payload = {
            "session_id": session_id,
            "text": c["text"],
            "doc": c["meta"]["doc"],
            "chunk": c["meta"]["chunk"],
        }
        points.append(PointStruct(id=int(uuid.uuid4().int % (2**63)), vector=v.tolist(), payload=payload))

    qdrant.upsert(collection_name=coll, points=points)

    # store session config
    SESSIONS.setdefault(session_id, {})
    SESSIONS[session_id]["provider"] = provider
    SESSIONS[session_id]["api_key"] = api_key
    SESSIONS[session_id]["embedding_model"] = emb_model
    SESSIONS[session_id]["generation_model"] = gen_model
    session_log(session_id, "upload", {
        "doc": filename,
        "chunks_indexed": len(points),
        "provider": provider,
        "embed_provider": embed_provider,
        "embedding_model": embedding_model_name,
        "vector_dim": int(vecs.shape[1]) if hasattr(vecs, 'shape') else None,
        "key_provided": bool(api_key),
    })

    return UploadResponse(
        session_id=session_id,
        chunks_indexed=len(points),
        used_fallback=used_fallback,
        embed_provider=embed_provider,
        embedding_model=embedding_model_name,
        vector_dim=int(vecs.shape[1]) if hasattr(vecs, 'shape') else None,
    )


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    if not req.session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")
    if not req.question:
        raise HTTPException(status_code=400, detail="Missing question")

    # retrieve top-k for this session
    # embed question with available method (prefer provider from session or request)
    session_info = SESSIONS.get(req.session_id, {})
    session_provider = session_info.get("provider", req.provider)
    session_api_key = session_info.get("api_key", req.api_key)
    session_emb_model = session_info.get("embedding_model", req.embedding_model)
    session_gen_model = session_info.get("generation_model", req.generation_model)

    logger.info(f"/ask: session={req.session_id} provider={session_provider} key_provided={bool(session_api_key)} k={req.k}")
    
    # Try provider-specific embedding for question
    q_vec = None
    if session_provider == "gemini" and session_api_key:
        q_vec = embed_with_gemini([req.question], session_api_key, session_emb_model)
    elif session_provider == "openai" and session_api_key:
        q_vec = embed_with_openai([req.question], session_api_key, session_emb_model)
    
    used_fallback = False
    if q_vec is None:
        q_vec = embed_with_sbert([req.question])
        used_fallback = True
        embed_provider = "sbert"
        logger.info("/ask: fallback question embedding used (SBERT)")
    else:
        embed_provider = session_provider
        logger.info(f"/ask: question embedding via {session_provider}")

    # Embedding model name used for the question
    embedding_model_name: Optional[str] = None
    if embed_provider == "gemini":
        embedding_model_name = session_emb_model
    elif embed_provider == "openai":
        embedding_model_name = session_emb_model
    else:
        embedding_model_name = "sentence-transformers/all-MiniLM-L6-v2"

    coll = collection_name(req.session_id)
    top_chunks = []
    try:
        search = qdrant.search(
            collection_name=coll,
            query_vector=q_vec[0].tolist(),
            limit=req.k,
            query_filter=Filter(must=[FieldCondition(key="session_id", match=MatchValue(value=req.session_id))]),
        )
        for pt in search:
            payload = pt.payload or {}
            top_chunks.append({
                "text": payload.get("text", ""),
                "doc": payload.get("doc", ""),
                "chunk": payload.get("chunk", -1),
                "score": float(pt.score),
            })
    except Exception:
        # No collection or search error; proceed with heuristic only
        top_chunks = []

    # Optional: BM25 re-ranking of the retrieved chunks for better local generation
    if top_chunks:
        top_chunks = _bm25_rerank(req.question, top_chunks)

    context = "\n\n".join(f"[Source {i+1} | {c['doc']}#{c['chunk']}]\n{c['text']}" for i, c in enumerate(top_chunks))

    system_prompt = (
        "You are a helpful assistant answering questions based only on the provided context. "
        "Cite sources as [Source N]. If the answer is not in the context, say so.\n\n"
    )
    prompt = f"{system_prompt}Context:\n{context}\n\nQuestion: {req.question}\nAnswer:"

    # Try provider-specific generation
    answer = None
    generation_model_name: Optional[str] = None
    gen_provider = "heuristic"  # default fallback
    
    if session_provider == "gemini" and session_api_key:
        answer = generate_with_gemini(prompt, session_api_key, session_gen_model)
        if answer:
            gen_provider = "gemini"
            generation_model_name = session_gen_model
            logger.info(f"/ask: generation via Gemini model={generation_model_name}")
    elif session_provider == "openai" and session_api_key:
        answer = generate_with_openai(prompt, session_api_key, session_gen_model)
        if answer:
            gen_provider = "openai"
            generation_model_name = session_gen_model
            logger.info(f"/ask: generation via OpenAI model={generation_model_name}")
    
    if answer is None:
        # Try local LLM first
        local_answer = generate_with_local_llm(req.question, top_chunks)
        if local_answer:
            answer = local_answer
            used_fallback = True or used_fallback
            gen_provider = "local-llm"
            generation_model_name = _local_llm_name or os.environ.get("LOCAL_LLM_MODEL", "local-llm")
            logger.info("/ask: fallback generation used (local LLM via GPT4All)")
        else:
            # Final resort: heuristic extractive answer
            answer = heuristic_answer(req.question, top_chunks)
            used_fallback = True or used_fallback
            gen_provider = "heuristic"
            generation_model_name = None
            logger.info("/ask: fallback generation used (heuristic)")

    session_log(req.session_id, "ask", {
        "question": req.question,
        "provider": session_provider,
        "embed_provider": embed_provider,
        "embedding_model": embedding_model_name,
        "gen_provider": gen_provider,
        "generation_model": generation_model_name,
        "used_fallback": used_fallback,
        "top_k": req.k,
        "returned_sources": len(top_chunks),
        "api_key_provided": bool(session_api_key),
    })

    return AskResponse(
        answer=answer,
        sources=top_chunks,
        used_fallback=used_fallback,
        gen_provider=gen_provider,
        generation_model=generation_model_name,
        embed_provider=embed_provider,
        embedding_model=embedding_model_name,
    )


@app.get("/models", response_model=ModelsResponse)
async def models(provider: str = "gemini", api_key: Optional[str] = None):
    """Get available models for a provider"""
    if not api_key:
        return ModelsResponse(
            provider=provider,
            embedding_model=None, 
            generation_model=None, 
            available_models={"embedding": [], "generation": []},
            api_valid=False,
            error_message="No API key provided"
        )
    
    m = get_provider_models(provider, api_key)
    return ModelsResponse(
        provider=m.get("provider", provider),
        embedding_model=m.get("embedding_model"),
        generation_model=m.get("generation_model"),
        available_models=m.get("available_models", {"embedding": [], "generation": []}),
        api_valid=m.get("api_valid", False),
        error_message=m.get("error_message")
    )


@app.post("/validate", response_model=ModelsResponse)
async def validate_provider(req: ProviderValidationRequest):
    """Validate API key and return available models"""
    validation_result = validate_api_key(
        req.provider, 
        req.api_key, 
        req.embedding_model, 
        req.generation_model
    )
    
    if validation_result["valid"]:
        models_info = get_provider_models(req.provider, req.api_key)
        return ModelsResponse(
            provider=req.provider,
            embedding_model=validation_result.get("embedding_model"),
            generation_model=validation_result.get("generation_model"),
            available_models=models_info.get("available_models", {"embedding": [], "generation": []}),
            api_valid=True,
            error_message=None
        )
    else:
        return ModelsResponse(
            provider=req.provider,
            embedding_model=None,
            generation_model=None,
            available_models={"embedding": [], "generation": []},
            api_valid=False,
            error_message=validation_result.get("error", "Validation failed")
        )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/models/local")
async def local_model_status():
    """Quick diagnostic endpoint to check if a local GPT4All model is available."""
    llm = get_local_llm()
    if llm is None:
        return {"available": False}
    try:
        name = _local_llm_name or getattr(llm, "model_name", None) or os.environ.get("LOCAL_LLM_MODEL")
    except Exception:
        name = _local_llm_name or os.environ.get("LOCAL_LLM_MODEL")
    return {"available": True, "model": name}


@app.get("/session/{session_id}/diagnostics")
async def session_diagnostics(session_id: str):
    info = SESSIONS.get(session_id, {})
    coll = collection_name(session_id)
    vec_count = 0
    try:
        res = qdrant.count(collection_name=coll, count_filter=Filter(must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))]), exact=True)
        # qdrant-client can return CountResult with 'count' attribute or a dict
        vec_count = getattr(res, 'count', None) or (res.get('count') if isinstance(res, dict) else 0)
    except Exception:
        vec_count = 0
    return {
        "session_id": session_id,
        "provider": info.get("provider"),
        "embedding_model": info.get("embedding_model"),
        "generation_model": info.get("generation_model"),
        "vector_count": vec_count,
    }


@app.get("/session/{session_id}/events")
async def session_events(session_id: str, limit: int = 50):
    info = SESSIONS.get(session_id, {})
    events = info.get("events", [])
    return events[-limit:]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
