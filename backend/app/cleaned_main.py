"""
Cleaned and Optimized Main Implementation
Integrates all optimizations: intelligent model selection, enhanced local LLM, 
optimized data flow, and improved provider implementations
"""
import asyncio
import logging
import time
import os
import uuid
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from pydantic import BaseModel
import json

# Import optimized components
from .optimized_providers import OptimizedGeminiProvider, OptimizedOpenAIProvider, ProviderConfig
from .optimized_fallback import fallback_manager, enhanced_local_llm, ContextualInfo
from .data_flow_optimizer import data_optimizer

# Import existing utilities
from .main import (
    parse_pdf, parse_docx, normalize_text, smart_chunk,
    collection_name, qdrant, VectorParams, Distance, PointStruct,
    Filter, FieldCondition, MatchValue, SESSIONS, session_log,
    embed_with_sbert, heuristic_answer, get_local_llm, generate_with_local_llm
)

logger = logging.getLogger(__name__)

# Load configuration
_CONFIG = {}
try:
    with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as f:
        _CONFIG = json.load(f)
except Exception as e:
    logger.warning(f"Could not load config.json: {e}")

# Constants
DEFAULT_GEMINI_EMBED = "models/text-embedding-004"
DEFAULT_GEMINI_GEN = "models/gemini-2.5-flash"
DEFAULT_OPENAI_EMBED = "text-embedding-3-small"
DEFAULT_OPENAI_GEN = "gpt-4o-mini"

# Enhanced request/response models
class OptimizedUploadRequest(BaseModel):
    provider: str = "gemini"
    api_key: Optional[str] = None
    embedding_model: Optional[str] = None
    generation_model: Optional[str] = None
    enable_optimization: bool = True
    chunk_size: int = 1000
    batch_size: int = 16

class OptimizedAskRequest(BaseModel):
    session_id: str
    question: str
    k: int = 5
    provider: str = "gemini"
    api_key: Optional[str] = None
    embedding_model: Optional[str] = None
    generation_model: Optional[str] = None
    enable_optimization: bool = True
    enable_streaming: bool = False

class OptimizedResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    performance_stats: Dict[str, Any]
    optimization_applied: List[str]

class HealthResponse(BaseModel):
    status: str
    providers: Dict[str, Dict[str, Any]]
    optimization_stats: Dict[str, Any]
    recommendations: List[str]

# Provider configuration
provider_config = ProviderConfig(
    max_retries=3,
    retry_delay=1.0,
    timeout=30.0,
    batch_size=100,
    rate_limit_delay=0.1,
    connection_pool_size=10,
    enable_streaming=True
)

async def optimized_upload(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    provider: str = Form("gemini"),
    api_key: Optional[str] = Form(None),
    embedding_model: Optional[str] = Form(None),
    generation_model: Optional[str] = Form(None),
    enable_optimization: bool = Form(True),
    chunk_size: int = Form(1000),
    batch_size: int = Form(16)
):
    """
    Fully optimized upload with intelligent model selection and data optimization
    """
    start_time = time.time()
    optimization_applied = []
    
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

    filename = file.filename or "document"
    ext = filename.split('.')[-1].lower()

    if ext not in ["pdf", "docx"]:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files supported")

    if not session_id:
        session_id = str(uuid.uuid4())

    # Parse document
    try:
        if ext == "pdf":
            text = parse_pdf(content)
        else:
            text = parse_docx(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}")

    text = normalize_text(text)
    if not text.strip():
        raise HTTPException(status_code=400, detail="File appears to be empty")

    # Create initial chunks
    initial_chunks = smart_chunk(text, filename)
    
    # Optimize chunks if enabled
    if enable_optimization:
        chunks = data_optimizer.optimize_chunks(initial_chunks, chunk_size)
        optimization_applied.append("chunk_optimization")
    else:
        chunks = initial_chunks

    # Analyze context for intelligent model selection
    document_info = {"type": ext, "size": len(text), "filename": filename}
    context_info = fallback_manager.analyze_context("", chunks, document_info)
    
    # Select optimal models
    available_providers = []
    if api_key and provider in ["gemini", "openai"]:
        available_providers.append(provider)
    available_providers.append("local")  # Always available
    
    optimal_models = fallback_manager.select_optimal_models(context_info, available_providers)
    optimization_applied.append("intelligent_model_selection")
    
    # Generate embeddings with optimized provider
    texts = [c["text"] for c in chunks]
    
    embeddings = None
    embed_provider = "sbert"
    embedding_model_name = "sentence-transformers/all-MiniLM-L6-v2"
    
    if api_key and provider in ["gemini", "openai"]:
        # Use optimized provider with batching
        if enable_optimization:
            batches = data_optimizer.batch_embeddings(texts, batch_size)
            optimization_applied.append("embedding_batching")
        else:
            batches = [texts]
        
        all_embeddings = []
        
        async with _get_optimized_provider(provider) as provider_instance:
            for batch in batches:
                batch_embeddings = await _generate_embeddings_optimized(
                    batch, provider_instance, api_key, embedding_model, generation_model
                )
                if batch_embeddings is not None:
                    all_embeddings.extend(batch_embeddings)
                else:
                    # Fallback to SBERT for this batch
                    batch_embeddings = embed_with_sbert(batch)
                    all_embeddings.extend(batch_embeddings)
        
        if all_embeddings:
            embeddings = np.vstack(all_embeddings)
            embed_provider = provider
            embedding_model_name = embedding_model or (DEFAULT_GEMINI_EMBED if provider == "gemini" else DEFAULT_OPENAI_EMBED)
    
    # Final fallback to SBERT if no embeddings generated
    if embeddings is None:
        embeddings = embed_with_sbert(texts)
        optimization_applied.append("sbert_fallback")

    if embeddings is None:
        raise HTTPException(status_code=500, detail="Failed to generate embeddings")

    # Store in vector database
    dim = int(embeddings.shape[1])
    coll = collection_name(session_id)
    
    try:
        qdrant.recreate_collection(
            collection_name=coll,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
    except Exception:
        try:
            qdrant.create_collection(
                collection_name=coll,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
        except Exception:
            pass

    points = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        payload = {
            "session_id": session_id,
            "text": chunk["text"],
            "doc": chunk["meta"]["doc"],
            "chunk": chunk["meta"]["chunk"],
        }
        points.append(PointStruct(
            id=int(uuid.uuid4().int % (2**63)), 
            vector=embedding.tolist(), 
            payload=payload
        ))

    qdrant.upsert(collection_name=coll, points=points)

    # Store enhanced session config
    SESSIONS.setdefault(session_id, {})
    SESSIONS[session_id].update({
        "provider": provider,
        "api_key": api_key,
        "embedding_model": embedding_model,
        "generation_model": generation_model,
        "optimal_models": optimal_models,
        "context_info": context_info.__dict__,
        "enable_optimization": enable_optimization,
        "batch_size": batch_size
    })

    processing_time = time.time() - start_time
    
    session_log(session_id, "optimized_upload", {
        "doc": filename,
        "chunks_indexed": len(points),
        "processing_time": processing_time,
        "optimization_applied": optimization_applied,
        "embed_provider": embed_provider,
        "embedding_model": embedding_model_name,
        "context_analysis": context_info.__dict__
    })

    return {
        "session_id": session_id,
        "chunks_indexed": len(points),
        "processing_time": processing_time,
        "optimization_applied": optimization_applied,
        "embed_provider": embed_provider,
        "embedding_model": embedding_model_name,
        "context_analysis": context_info.__dict__,
        "performance_stats": data_optimizer.get_performance_summary()
    }

async def optimized_ask(req: OptimizedAskRequest):
    """
    Fully optimized ask with intelligent model selection and enhanced local LLM
    """
    start_time = time.time()
    optimization_applied = []
    
    if not req.session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")
    if not req.question:
        raise HTTPException(status_code=400, detail="Missing question")

    # Get session info
    session_info = SESSIONS.get(req.session_id, {})
    optimal_models = session_info.get("optimal_models", {})
    context_info_dict = session_info.get("context_info", {})
    enable_optimization = session_info.get("enable_optimization", req.enable_optimization)
    batch_size = session_info.get("batch_size", 16)
    
    # Reconstruct context info
    context_info = ContextualInfo(**context_info_dict) if context_info_dict else None
    
    # Generate question embeddings with optimized provider
    question_embeddings = None
    embed_provider = "sbert"
    embedding_model_name = "sentence-transformers/all-MiniLM-L6-v2"
    
    if req.api_key and req.provider in ["gemini", "openai"]:
        async with _get_optimized_provider(req.provider) as provider_instance:
            question_embeddings = await _generate_embeddings_optimized(
                [req.question], provider_instance, req.api_key, 
                req.embedding_model, req.generation_model
            )
        
        if question_embeddings is not None:
            embed_provider = req.provider
            embedding_model_name = req.embedding_model or (DEFAULT_GEMINI_EMBED if req.provider == "gemini" else DEFAULT_OPENAI_EMBED)
        else:
            question_embeddings = embed_with_sbert([req.question])
            optimization_applied.append("sbert_fallback")
    else:
        question_embeddings = embed_with_sbert([req.question])

    # Retrieve and optimize chunks
    coll = collection_name(req.session_id)
    top_chunks = []
    
    try:
        search = qdrant.search(
            collection_name=coll,
            query_vector=question_embeddings[0].tolist(),
            limit=req.k * 2,  # Get more chunks for optimization
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
    except Exception as e:
        logger.warning(f"Vector search failed: {e}")

    # Optimize chunk retrieval
    if enable_optimization and top_chunks:
        top_chunks = data_optimizer.optimize_retrieval(req.question, top_chunks, req.k)
        optimization_applied.append("retrieval_optimization")

    # Build context
    context = "\n\n".join(f"[Source {i+1} | {c['doc']}#{c['chunk']}]\n{c['text']}" for i, c in enumerate(top_chunks))
    
    # Compress context if needed
    if enable_optimization:
        context = data_optimizer.compress_context(context, max_length=4000)
        optimization_applied.append("context_compression")

    # Generate answer with optimal model
    answer = None
    generation_metadata = {}
    
    # Try optimized generation model first
    gen_model_info = optimal_models.get("generation", {})
    if gen_model_info.get("provider") in ["gemini", "openai"] and req.api_key:
        async with _get_optimized_provider(gen_model_info["provider"]) as provider_instance:
            if req.enable_streaming:
                # Streaming generation
                answer_parts = []
                async for chunk in provider_instance.generate_stream(
                    f"Context:\n{context}\n\nQuestion: {req.question}\nAnswer:",
                    req.api_key,
                    gen_model_info.get("model", DEFAULT_GEMINI_GEN if gen_model_info["provider"] == "gemini" else DEFAULT_OPENAI_GEN)
                ):
                    answer_parts.append(chunk)
                answer = "".join(answer_parts)
                optimization_applied.append("streaming_generation")
            else:
                # Non-streaming generation
                answer = await provider_instance.generate(
                    f"Context:\n{context}\n\nQuestion: {req.question}\nAnswer:",
                    req.api_key,
                    gen_model_info.get("model", DEFAULT_GEMINI_GEN if gen_model_info["provider"] == "gemini" else DEFAULT_OPENAI_GEN)
                )
        
        if answer:
            generation_metadata = {
                "provider": gen_model_info["provider"], 
                "model": gen_model_info.get("model"),
                "streaming": req.enable_streaming
            }
    
    # Enhanced local LLM fallback
    if answer is None:
        if context_info:
            answer = enhanced_local_llm.generate_enhanced_answer(
                req.question, top_chunks, context_info
            )
            optimization_applied.append("enhanced_local_llm")
        else:
            # Fallback to standard local LLM
            answer = generate_with_local_llm(req.question, top_chunks)
            optimization_applied.append("standard_local_llm")
        
        generation_metadata = {"provider": "local-llm", "model": "enhanced" if context_info else "standard"}
    
    # Final fallback to heuristic
    if answer is None:
        answer = heuristic_answer(req.question, top_chunks)
        generation_metadata = {"provider": "heuristic", "model": None}
        optimization_applied.append("heuristic_fallback")

    processing_time = time.time() - start_time
    
    session_log(req.session_id, "optimized_ask", {
        "question": req.question,
        "processing_time": processing_time,
        "generation_metadata": generation_metadata,
        "sources_count": len(top_chunks),
        "optimization_applied": optimization_applied,
        "embed_provider": embed_provider
    })

    return OptimizedResponse(
        answer=answer,
        sources=top_chunks,
        metadata={
            "generation_metadata": generation_metadata,
            "embed_provider": embed_provider,
            "embedding_model": embedding_model_name,
            "context_analysis": context_info.__dict__ if context_info else {},
            "optimization_enabled": enable_optimization,
            "streaming_enabled": req.enable_streaming
        },
        performance_stats=data_optimizer.get_performance_summary(),
        optimization_applied=optimization_applied
    )

async def _get_optimized_provider(provider: str):
    """Get optimized provider instance"""
    if provider == "gemini":
        return OptimizedGeminiProvider(provider_config)
    elif provider == "openai":
        return OptimizedOpenAIProvider(provider_config)
    else:
        raise ValueError(f"Unknown provider: {provider}")

async def _generate_embeddings_optimized(
    texts: List[str], 
    provider_instance, 
    api_key: str, 
    embedding_model: Optional[str], 
    generation_model: Optional[str]
) -> Optional[List[np.ndarray]]:
    """Generate embeddings using optimized provider"""
    
    if isinstance(provider_instance, OptimizedGeminiProvider):
        emb_model = embedding_model or DEFAULT_GEMINI_EMBED
        embeddings = await provider_instance.embed_batch(texts, api_key, emb_model)
        return embeddings.tolist() if embeddings is not None else None
        
    elif isinstance(provider_instance, OptimizedOpenAIProvider):
        emb_model = embedding_model or DEFAULT_OPENAI_EMBED
        embeddings = await provider_instance.embed_batch(texts, api_key, emb_model)
        return embeddings.tolist() if embeddings is not None else None
    
    return None

async def get_health_status() -> HealthResponse:
    """Get comprehensive health status"""
    
    # Test provider connectivity
    providers = {}
    recommendations = []
    
    # Test Gemini
    try:
        async with OptimizedGeminiProvider(provider_config) as gemini:
            # Quick test with minimal request
            test_embeddings = await gemini.embed_batch(["test"], "dummy_key", DEFAULT_GEMINI_EMBED)
            providers["gemini"] = {
                "status": "available",
                "embedding_models": _CONFIG.get("gemini", {}).get("available_models", {}).get("embedding", []),
                "generation_models": _CONFIG.get("gemini", {}).get("available_models", {}).get("generation", [])
            }
    except Exception as e:
        providers["gemini"] = {"status": "error", "error": str(e)}
        recommendations.append("Check Gemini API key and network connectivity")
    
    # Test OpenAI
    try:
        async with OptimizedOpenAIProvider(provider_config) as openai:
            test_embeddings = await openai.embed_batch(["test"], "dummy_key", DEFAULT_OPENAI_EMBED)
            providers["openai"] = {
                "status": "available",
                "embedding_models": _CONFIG.get("openai", {}).get("available_models", {}).get("embedding", []),
                "generation_models": _CONFIG.get("openai", {}).get("available_models", {}).get("generation", [])
            }
    except Exception as e:
        providers["openai"] = {"status": "error", "error": str(e)}
        recommendations.append("Check OpenAI API key and network connectivity")
    
    # Test local LLM
    local_llm = get_local_llm()
    providers["local_llm"] = {
        "status": "available" if local_llm else "unavailable",
        "model": "orca-mini-3b" if local_llm else None
    }
    
    if not local_llm:
        recommendations.append("Consider downloading a local LLM model for offline fallback")
    
    # Get optimization stats
    optimization_stats = data_optimizer.get_performance_summary()
    
    # Add performance recommendations
    if optimization_stats.get("total_processing_time", 0) > 10:
        recommendations.append("Consider enabling more optimizations for better performance")
    
    return HealthResponse(
        status="healthy",
        providers=providers,
        optimization_stats=optimization_stats,
        recommendations=recommendations
    )
