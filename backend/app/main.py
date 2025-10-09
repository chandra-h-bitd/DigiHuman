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

app = FastAPI(title="Doc Q&A (Gemini + SBERT Fallback)")

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

# Local SBERT model (lazy loaded)
_sbert_model = None  # lazy-loaded SentenceTransformer instance
_local_llm = None   # lazy-loaded GPT4All model instance

def get_sbert():
    global _sbert_model
    if _sbert_model is None:
        # Lazy import to avoid heavy startup cost
        from sentence_transformers import SentenceTransformer
        _sbert_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _sbert_model

def get_local_llm():
    """Lazy-load a small local LLM using GPT4All. Falls back to None if not available.
    Downloads model automatically on first use (internet required only once).
    """
    global _local_llm
    if _local_llm is not None:
        return _local_llm
    try:
        from gpt4all import GPT4All  # type: ignore
        # Prefer a smaller, widely compatible model; adjust name if you have another local model
        model_name = os.environ.get("LOCAL_LLM_MODEL", "ggml-gpt4all-j-v1.3-groovy")
        _local_llm = GPT4All(model_name)
        logger.info(f"Local LLM loaded: {model_name}")
        return _local_llm
    except Exception as e:
        logger.info(f"Local LLM unavailable (GPT4All not installed or model failed to load): {e}")
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
    gemini_api_key: Optional[str] = None

class AskResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    used_fallback: bool
    gen_provider: str
    generation_model: Optional[str]
    embed_provider: str
    embedding_model: Optional[str]

class ModelsResponse(BaseModel):
    embedding_model: Optional[str]
    generation_model: Optional[str]
    available_models: List[str]

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

def get_gemini_models(api_key: str) -> Dict[str, Any]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        models = [m.get("name", "") for m in data.get("models", [])]
        # Separate candidates
        lower_map = {m: m.lower() for m in models}
        emb_candidates = [m for m in models if "embedding" in lower_map[m]]

        # Filter out non-text or specialized generations
        banned_tokens = [
            "embedding",  # embeddings
            "tts",        # text-to-speech
            "image",      # image generation
            "computer-use",
            "robotics",
            "learnlm",
            "gemma",
            "imagen",
            "aqa",
        ]
        gen_candidates = [
            m for m in models
            if ("gemini" in lower_map[m] and not any(b in lower_map[m] for b in banned_tokens))
        ]

        # Prefer stable non-preview models with a clear priority
        priority_prefixes = [
            "models/gemini-2.5-pro",
            "models/gemini-2.5-flash",
            "models/gemini-2.0-pro",
            "models/gemini-2.0-flash",
            "models/gemini-pro",
            "models/gemini-flash",
        ]

        def pick_generation(cands: List[str]) -> Optional[str]:
            # prefer non-preview variants first by priority list
            non_preview = [c for c in cands if "preview" not in lower_map[c]]
            for pref in priority_prefixes:
                for pool in (non_preview, cands):
                    match = next((c for c in pool if lower_map[c].startswith(pref)), None)
                    if match:
                        return match
            # fallback: last sorted candidate
            return sorted(cands)[-1] if cands else None

        emb = sorted(emb_candidates)[-1] if emb_candidates else None
        gen = pick_generation(gen_candidates)
        return {"embedding_model": emb, "generation_model": gen, "available_models": models}
    except Exception:
        return {"embedding_model": None, "generation_model": None, "available_models": []}


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


def embed_with_sbert(texts: List[str]) -> np.ndarray:
    model = get_sbert()
    return np.array(model.encode(texts, normalize_embeddings=True), dtype=np.float32)


# ---------- Generation ----------

def generate_with_gemini(prompt: str, api_key: str, model_name: Optional[str]) -> Optional[str]:
    if not api_key or not model_name:
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
    mp = _model_path(model_name)
    url = f"https://generativelanguage.googleapis.com/v1beta/{mp}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
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


# ---------- API ----------
@app.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...), session_id: Optional[str] = Form(None), gemini_api_key: Optional[str] = Form(None)):
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

    if ext == ".pdf":
        text = parse_pdf(content)
    else:
        text = parse_docx(content)

    text = normalize_text(text)
    chunks = smart_chunk(text, filename)

    # Embeddings: try Gemini first
    used_fallback = False
    gem_models = get_gemini_models(gemini_api_key) if gemini_api_key else {"embedding_model": None, "generation_model": None}
    emb_model = gem_models.get("embedding_model") if gem_models else None

    texts = [c["text"] for c in chunks]
    logger.info(f"/upload: session={session_id} file={filename} key_provided={bool(gemini_api_key)} emb_model={emb_model}")
    vecs = embed_with_gemini(texts, gemini_api_key, emb_model)
    if vecs is None:
        vecs = embed_with_sbert(texts)
        used_fallback = True
        embed_provider = "sbert"
        logger.info(f"/upload: fallback embeddings used (SBERT)")
    else:
        embed_provider = "gemini"
        logger.info(f"/upload: embeddings via Gemini model={emb_model}")

    # Determine embedding model name for response/logs
    embedding_model_name: Optional[str] = None
    if embed_provider == "gemini":
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
    SESSIONS[session_id]["gemini_models"] = gem_models
    session_log(session_id, "upload", {
        "doc": filename,
        "chunks_indexed": len(points),
        "embed_provider": embed_provider,
        "embedding_model": embedding_model_name,
        "vector_dim": int(vecs.shape[1]) if hasattr(vecs, 'shape') else None,
        "key_provided": bool(gemini_api_key),
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
    # embed question with available method (prefer Gemini)
    gem_models = SESSIONS.get(req.session_id, {}).get("gemini_models", {})
    emb_model = gem_models.get("embedding_model") if gem_models else None

    logger.info(f"/ask: session={req.session_id} key_provided={bool(req.gemini_api_key)} k={req.k} gen_model={(SESSIONS.get(req.session_id, {}).get('gemini_models') or {}).get('generation_model')}")
    q_vec = embed_with_gemini([req.question], req.gemini_api_key, emb_model)
    used_fallback = False
    if q_vec is None:
        q_vec = embed_with_sbert([req.question])
        used_fallback = True
        embed_provider = "sbert"
        logger.info("/ask: fallback question embedding used (SBERT)")
    else:
        embed_provider = "gemini"
        logger.info("/ask: question embedding via Gemini")

    # Embedding model name used for the question
    embedding_model_name: Optional[str] = emb_model if embed_provider == "gemini" else "sentence-transformers/all-MiniLM-L6-v2"

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

    gen_model = gem_models.get("generation_model") if gem_models else None
    answer = generate_with_gemini(prompt, req.gemini_api_key, gen_model)
    generation_model_name: Optional[str] = None
    if answer is None:
        # Try local LLM first
        local_answer = generate_with_local_llm(req.question, top_chunks)
        if local_answer:
            answer = local_answer
            used_fallback = True or used_fallback
            gen_provider = "local-llm"
            generation_model_name = os.environ.get("LOCAL_LLM_MODEL", "ggml-gpt4all-j-v1.3-groovy")
            logger.info("/ask: fallback generation used (local LLM via GPT4All)")
        else:
            # Final resort: heuristic extractive answer
            answer = heuristic_answer(req.question, top_chunks)
            used_fallback = True or used_fallback
            gen_provider = "heuristic"
            generation_model_name = None
            logger.info("/ask: fallback generation used (heuristic)")
    else:
        gen_provider = "gemini"
        generation_model_name = gen_model
        logger.info(f"/ask: generation via Gemini model={gen_model}")

    session_log(req.session_id, "ask", {
        "question": req.question,
        "embed_provider": embed_provider,
        "embedding_model": embedding_model_name,
        "gen_provider": gen_provider,
        "used_fallback": used_fallback,
        "top_k": req.k,
        "returned_sources": len(top_chunks),
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
async def models(gemini_api_key: Optional[str] = None):
    if not gemini_api_key:
        return ModelsResponse(embedding_model=None, generation_model=None, available_models=[])
    m = get_gemini_models(gemini_api_key)
    return ModelsResponse(
        embedding_model=m.get("embedding_model"),
        generation_model=m.get("generation_model"),
        available_models=m.get("available_models", []),
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


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
        "gemini_models": info.get("gemini_models"),
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
