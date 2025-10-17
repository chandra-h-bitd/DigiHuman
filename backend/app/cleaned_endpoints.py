"""
Cleaned and Optimized API Endpoints
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import StreamingResponse

from .cleaned_main import (
    optimized_upload, optimized_ask, get_health_status,
    OptimizedUploadRequest, OptimizedAskRequest, OptimizedResponse, HealthResponse
)

logger = logging.getLogger(__name__)

# Create router for cleaned endpoints
router = APIRouter(prefix="/v2", tags=["optimized"])

@router.post("/upload")
async def upload_optimized(
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
    Optimized upload endpoint with:
    - Intelligent model selection
    - Data flow optimization
    - Enhanced error handling
    - Performance monitoring
    """
    return await optimized_upload(
        file=file,
        session_id=session_id,
        provider=provider,
        api_key=api_key,
        embedding_model=embedding_model,
        generation_model=generation_model,
        enable_optimization=enable_optimization,
        chunk_size=chunk_size,
        batch_size=batch_size
    )

@router.post("/ask")
async def ask_optimized(req: OptimizedAskRequest):
    """
    Optimized ask endpoint with:
    - Enhanced local LLM
    - Streaming support
    - Intelligent fallback
    - Context optimization
    """
    return await optimized_ask(req)

@router.post("/ask/stream")
async def ask_stream_optimized(req: OptimizedAskRequest):
    """
    Streaming ask endpoint for real-time responses
    """
    # Enable streaming for this request
    req.enable_streaming = True
    
    async def generate_stream():
        try:
            # Get the optimized response
            response = await optimized_ask(req)
            
            # Stream the response
            yield f"data: {response.model_dump_json()}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            error_response = {
                "error": str(e),
                "answer": "Sorry, I encountered an error while processing your request.",
                "sources": [],
                "metadata": {"error": True}
            }
            yield f"data: {error_response}\n\n"
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@router.get("/health", response_model=HealthResponse)
async def health_optimized():
    """
    Comprehensive health check with:
    - Provider status
    - Optimization statistics
    - Performance recommendations
    """
    return await get_health_status()

@router.get("/models")
async def get_available_models():
    """
    Get available models for each provider
    """
    from .main import _CONFIG
    
    return {
        "gemini": {
            "embedding_models": _CONFIG.get("gemini", {}).get("available_models", {}).get("embedding", []),
            "generation_models": _CONFIG.get("gemini", {}).get("available_models", {}).get("generation", [])
        },
        "openai": {
            "embedding_models": _CONFIG.get("openai", {}).get("available_models", {}).get("embedding", []),
            "generation_models": _CONFIG.get("openai", {}).get("available_models", {}).get("generation", [])
        },
        "local": {
            "generation_models": ["orca-mini-3b", "llama-2-7b", "gpt4all-j"]
        }
    }

@router.post("/validate")
async def validate_provider(
    provider: str,
    api_key: str,
    embedding_model: Optional[str] = None,
    generation_model: Optional[str] = None
):
    """
    Validate provider API key and models
    """
    from .cleaned_main import _get_optimized_provider, DEFAULT_GEMINI_EMBED, DEFAULT_GEMINI_GEN, DEFAULT_OPENAI_EMBED, DEFAULT_OPENAI_GEN
    
    try:
        async with _get_optimized_provider(provider) as provider_instance:
            # Test embedding
            test_texts = ["This is a test"]
            emb_model = embedding_model or (DEFAULT_GEMINI_EMBED if provider == "gemini" else DEFAULT_OPENAI_EMBED)
            
            embeddings = await provider_instance.embed_batch(test_texts, api_key, emb_model)
            
            if embeddings is not None:
                return {
                    "valid": True,
                    "provider": provider,
                    "embedding_model": emb_model,
                    "generation_model": generation_model or (DEFAULT_GEMINI_GEN if provider == "gemini" else DEFAULT_OPENAI_GEN),
                    "message": f"Successfully connected to {provider.upper()}"
                }
            else:
                return {
                    "valid": False,
                    "provider": provider,
                    "error": "Failed to generate test embeddings"
                }
                
    except Exception as e:
        return {
            "valid": False,
            "provider": provider,
            "error": str(e)
        }

@router.get("/sessions/{session_id}/diagnostics")
async def get_session_diagnostics(session_id: str):
    """
    Get detailed diagnostics for a session
    """
    from .main import SESSIONS, session_log
    
    session_info = SESSIONS.get(session_id, {})
    if not session_info:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get session logs (this would need to be implemented in your logging system)
    logs = []  # Placeholder - implement based on your logging system
    
    return {
        "session_id": session_id,
        "session_info": session_info,
        "logs": logs,
        "optimization_enabled": session_info.get("enable_optimization", False),
        "context_analysis": session_info.get("context_info", {}),
        "optimal_models": session_info.get("optimal_models", {})
    }

@router.post("/optimize/clear-cache")
async def clear_optimization_cache():
    """
    Clear optimization caches
    """
    from .data_flow_optimizer import data_optimizer
    from .optimized_fallback import fallback_manager
    
    data_optimizer.clear_history()
    fallback_manager.clear_cache()
    
    return {"message": "Optimization caches cleared successfully"}

@router.get("/optimize/stats")
async def get_optimization_stats():
    """
    Get optimization performance statistics
    """
    from .data_flow_optimizer import data_optimizer
    from .optimized_fallback import fallback_manager
    
    return {
        "data_flow_stats": data_optimizer.get_performance_summary(),
        "fallback_stats": fallback_manager.get_provider_health(),
        "recommendations": [
            "Enable chunk optimization for better performance",
            "Use batch processing for large documents",
            "Consider streaming for real-time responses"
        ]
    }
