"""
Enterprise Document Q&A System
==============================

A high-performance document Q&A system with optimized vector search.
Features:
- FastAPI backend with async operations
- Qdrant vector database with optimized indexing
- Ollama local LLM integration
- Redis caching and PostgreSQL persistence
- Enterprise-grade monitoring and load balancing

Author: AI Assistant
Version: 2.0.0
"""

import os
import time
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

# FastAPI and web framework imports
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# ML and vector database imports
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

# HTTP client for Ollama API
import requests
import json

# Phase 3 Advanced Features
from app.advanced_session_manager import AdvancedSessionManager, SessionMetadata, DocumentMetadata
from app.advanced_search import AdvancedSearchEngine, SearchFilters, SearchResult
from app.performance_optimizer import PerformanceOptimizer
from app.security_manager import SecurityManager, SecurityEvent

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# =============================================================================
# FASTAPI APPLICATION SETUP
# =============================================================================

app = FastAPI(
    title="Enterprise Document Q&A System",
    description="High-performance document Q&A with optimized vector search and local LLM",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# GLOBAL VARIABLES
# =============================================================================

# Global instances for services
qdrant_client: Optional[QdrantClient] = None
embedder: Optional[SentenceTransformer] = None

# Phase 3 Advanced Features
session_manager: Optional[AdvancedSessionManager] = None
search_engine: Optional[AdvancedSearchEngine] = None
performance_optimizer: Optional[PerformanceOptimizer] = None
security_manager: Optional[SecurityManager] = None

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class AskRequest(BaseModel):
    """Request model for asking questions"""
    session_id: str
    question: str
    k: int = 5  # Number of relevant chunks to retrieve
    provider: str = "ollama"  # LLM provider: ollama, gemini, openai
    api_key: Optional[str] = None  # API key for external providers
    embedding_model: Optional[str] = None  # Embedding model to use
    generation_model: Optional[str] = None  # Generation model to use

class AskResponse(BaseModel):
    """Response model for question answers"""
    answer: str
    sources: List[Dict[str, Any]]  # Source chunks with metadata
    used_fallback: bool  # Whether fallback was used
    gen_provider: str  # Generation provider used
    generation_model: Optional[str]  # Model name
    embed_provider: str  # Embedding provider
    embedding_model: str  # Embedding model name

# Phase 3 Advanced Models
class SessionCreateRequest(BaseModel):
    """Request model for creating sessions"""
    name: str
    description: Optional[str] = None
    user_id: Optional[str] = None
    tags: Optional[List[str]] = None

class SessionResponse(BaseModel):
    """Response model for sessions"""
    id: str
    name: str
    description: Optional[str]
    status: str
    created_at: str
    updated_at: str
    document_count: int
    total_chunks: int
    last_activity: str
    user_id: Optional[str]
    tags: List[str]

class AdvancedSearchRequest(BaseModel):
    """Request model for advanced search"""
    session_id: str
    query: str
    search_filters: Optional[Dict[str, Any]] = None
    semantic_weight: float = 0.7
    keyword_weight: float = 0.3
    max_results: int = 10

class AdvancedSearchResponse(BaseModel):
    """Response model for advanced search"""
    results: List[Dict[str, Any]]
    total_results: int
    search_type: str
    query_time_ms: float
    suggestions: List[str]

class PerformanceMetricsResponse(BaseModel):
    """Response model for performance metrics"""
    metrics: List[Dict[str, Any]]
    endpoint_stats: Dict[str, Any]
    cache_stats: Dict[str, Any]
    system_health: Dict[str, Any]

class SecurityStatsResponse(BaseModel):
    """Response model for security statistics"""
    security_events: List[Dict[str, Any]]
    security_stats: Dict[str, Any]
    rate_limit_status: Dict[str, Any]

class UploadResponse(BaseModel):
    """Response model for document uploads"""
    message: str
    filename: str
    size: int
    chunks_created: int
    session_id: str
    used_fallback: bool
    embedding_model: str
    api_valid: bool

class HealthResponse(BaseModel):
    """Response model for health checks"""
    status: str
    timestamp: float
    services: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ModelResponse(BaseModel):
    """Response model for available models"""
    embedding_models: List[str]
    generation_models: List[str]

# =============================================================================
# SERVICE INITIALIZATION
# =============================================================================

async def initialize_services():
    """
    Initialize all required services:
    - Qdrant vector database client
    - Sentence transformer embedder
    - Phase 3 Advanced Features
    """
    global qdrant_client, embedder, session_manager, search_engine, performance_optimizer, security_manager
    
    try:
        # Initialize Qdrant client with optimized settings
        qdrant_client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", 6333)),
            timeout=30,
            prefer_grpc=True  # Use gRPC for better performance
        )
        logger.info("✅ Qdrant client initialized with gRPC")
        
        # Initialize sentence transformer embedder
        embedder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        logger.info("✅ Sentence transformer embedder initialized")
        
        # Phase 3: Initialize Redis client
        import redis
        redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True
        )
        logger.info("✅ Redis client initialized")
        
        # Phase 3: Initialize PostgreSQL pool
        import asyncpg
        postgres_pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            database=os.getenv("POSTGRES_DB", "docqa"),
            user=os.getenv("POSTGRES_USER", "docqa_user"),
            password=os.getenv("POSTGRES_PASSWORD", "docqa_password"),
            min_size=5,
            max_size=20
        )
        logger.info("✅ PostgreSQL connection pool initialized")
        
        # Phase 3: Initialize database tables
        from app.init_phase3_database import init_phase3_database
        await init_phase3_database()
        logger.info("✅ Phase 3 database tables initialized")
        
        # Phase 3: Initialize advanced features
        session_manager = AdvancedSessionManager(redis_client, postgres_pool, qdrant_client)
        search_engine = AdvancedSearchEngine(qdrant_client, embedder)
        performance_optimizer = PerformanceOptimizer(redis_client, postgres_pool, qdrant_client)
        security_manager = SecurityManager(redis_client)
        
        logger.info("✅ Phase 3 advanced features initialized")
            
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        raise

# =============================================================================
# STARTUP EVENT
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services when the application starts"""
    logger.info("🚀 Starting Enterprise Document Q&A System...")
    await initialize_services()
    logger.info("🎉 Enterprise system ready!")

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def chunk_text(text: str, chunk_size: int = 1500, chunk_overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks for better context preservation.
    
    Args:
        text: Input text to chunk
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:])
            break
        
        # Try to break at sentence boundary for better context
        chunk = text[start:end]
        last_period = chunk.rfind('.')
        last_newline = chunk.rfind('\n')
        
        # Prefer breaking at sentence end
        if last_period > chunk_size * 0.7:
            end = start + last_period + 1
        elif last_newline > chunk_size * 0.7:
            end = start + last_newline + 1
        
        chunks.append(text[start:end])
        start = end - chunk_overlap
    
        return chunks

async def generate_with_ollama(question: str, context: str) -> str:
    """
    Generate answer using Ollama local LLM.
    
    Args:
        question: User's question
        context: Relevant context from documents
    
    Returns:
        Generated answer
    """
    ollama_host = os.getenv("OLLAMA_HOST", "localhost")
    ollama_port = os.getenv("OLLAMA_PORT", "11434")
    
    # Construct prompt with context
    prompt = f"""Based on the following context, answer the question. 
If the answer is not in the context, say "I couldn't find enough information in the provided context."

Context: {context}

Question: {question}

Answer:"""
    
    # Make request to Ollama API
    try:
        response = requests.post(
            f"http://{ollama_host}:{ollama_port}/api/generate",
            json={
                "model": "tinyllama:1.1b",
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "No response generated")
        else:
            logger.warning(f"Ollama request failed: {response.status_code}")
            return "I couldn't generate an answer at this time."
            
    except Exception as e:
        logger.error(f"Ollama generation failed: {e}")
        return "I couldn't generate an answer at this time."

def create_optimized_collection(collection_name: str) -> None:
    """
    Create a Qdrant collection with optimized settings for performance.
    
    Args:
        collection_name: Name of the collection to create
    """
    try:
        # Check if collection already exists
        qdrant_client.get_collection(collection_name)
        logger.info(f"Collection {collection_name} already exists")
    except:
        # Create collection with optimized settings
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=384,  # Sentence transformer embedding size
                distance=Distance.COSINE
            ),
            optimizers_config=models.OptimizersConfigDiff(
                indexing_threshold=1,  # Index immediately
                flush_interval_sec=1,  # Flush every second
                max_optimization_threads=8  # Use more threads
            )
        )
        logger.info(f"✅ Created optimized collection: {collection_name}")

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify system status.
    
    Returns:
        Health status of all services
    """
    try:
        # Test Qdrant connection
        collections = qdrant_client.get_collections()
        
        # Test embedder
        test_embedding = embedder.encode(["test"])[0]
        
        return HealthResponse(
            status="ok",
            timestamp=time.time(),
            services={
                "qdrant": {
                    "status": "connected",
                    "collections_count": len(collections.collections)
                },
                "embedder": {
                    "status": "working",
                    "vector_size": len(test_embedding)
                }
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="error",
            error=str(e),
            timestamp=time.time()
        )

@app.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...), 
    session_id: Optional[str] = Form(None), 
    chunk_size: int = Form(1500),
    chunk_overlap: int = Form(200),
    provider: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
    embedding_model: Optional[str] = Form(None),
    generation_model: Optional[str] = Form(None)
):
    """
    Upload and process a document for Q&A.
    
    Args:
        file: Uploaded file
        session_id: Session identifier
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
    
    Returns:
        Upload confirmation with processing details
    """
    try:
        # Generate session_id if not provided
        if not session_id:
            session_id = "test-session-" + str(int(time.time()))
        
        # Read file content
        content = await file.read()
        filename = file.filename
        file_size = len(content)
        
        # Extract text content (simple UTF-8 decoding)
        text_content = content.decode('utf-8', errors='ignore')
        
        # Chunk the content
        chunks = chunk_text(text_content, chunk_size, chunk_overlap)
        
        # Create collection name for this session
        collection_name = f"doc_chunks_{session_id}"
        
        # Ensure collection exists with optimized settings
        create_optimized_collection(collection_name)
        
        # Generate embeddings and create points for Qdrant
        points = []
        logger.info(f"About to generate document_id for filename: {filename}")
        document_id = f"doc_{filename}_{int(time.time())}"  # Generate document ID once
        logger.info(f"Generated document_id: {document_id}")
        
        for i, chunk in enumerate(chunks):
            # Generate embedding for chunk
            embedding = embedder.encode([chunk])[0].tolist()
            
            # Create unique point ID
            point_id = hash(f"{session_id}_{filename}_{i}") % (2**63 - 1)
            
            # Create point with metadata
            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload={
            "session_id": session_id,
                    "document_id": document_id,
                    "chunk_index": i,
                    "text": chunk,
                    "metadata": {"filename": filename}
                }
            ))
        
        # Store points in Qdrant with wait for indexing
        qdrant_client.upsert(
            collection_name=collection_name,
            points=points,
            wait=True  # Wait for indexing to complete
        )
        
        logger.info(f"✅ Processed {filename}: {len(chunks)} chunks stored")

        # Determine embedding model and fallback status
        if provider == "gemini" and api_key:
            embedding_model_used = embedding_model or "models/embedding-001"
            used_fallback = False
            api_valid = True
        elif provider == "openai" and api_key:
            embedding_model_used = embedding_model or "text-embedding-ada-002"
            used_fallback = False
            api_valid = True
        else:
            # Ollama or fallback
            embedding_model_used = "sentence-transformers/all-MiniLM-L6-v2"
            used_fallback = True
            api_valid = False

        return UploadResponse(
            message=f"File {filename} uploaded and processed successfully",
            filename=filename,
            size=file_size,
            chunks_created=len(chunks),
            session_id=session_id,
            used_fallback=used_fallback,
            embedding_model=embedding_model_used,
            api_valid=api_valid
    )

    except Exception as e:
        logger.error(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Ask a question and get an answer based on uploaded documents.
    
    Args:
        request: Question request with session ID and parameters
    
    Returns:
        Answer with sources and metadata
    """
    try:
        start_time = time.time()
        
        # Collection name for this session
        collection_name = f"doc_chunks_{request.session_id}"
        
        # Generate query embedding with fallback chain
        query_embedding = None
        
        # Try API providers first for embedding
        if request.provider == "gemini" and request.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=request.api_key)
                result = genai.embed_content(
                    model=request.embedding_model or "models/embedding-001",
                    content=request.question,
                    task_type="retrieval_document"
                )
                query_embedding = result['embedding']
                logger.info("✅ Used Gemini API for embedding")
            except Exception as e:
                logger.warning(f"Gemini embedding failed: {str(e)[:200]}..., falling back to local embedding")
                query_embedding = None
        
        elif request.provider == "openai" and request.api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=request.api_key)
                response = client.embeddings.create(
                    model=request.embedding_model or "text-embedding-ada-002",
                    input=[request.question]
                )
                query_embedding = response.data[0].embedding
                logger.info("✅ Used OpenAI API for embedding")
            except Exception as e:
                logger.warning(f"OpenAI embedding failed: {e}, falling back to local embedding")
                query_embedding = None
        
        # Fallback to local embedding if API failed or no API key
        if query_embedding is None:
            query_embedding = embedder.encode([request.question])[0].tolist()
            logger.info("✅ Used local embedding (sentence-transformers)")
        
        # Perform vector search with optimized parameters
        search_results = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=request.k * 2,  # Get more results for filtering
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="session_id",
                        match=MatchValue(value=request.session_id)
                    )
                ]
            ),
            with_payload=True,
            with_vectors=False,  # Don't return vectors to save bandwidth
            score_threshold=0.3  # Minimum similarity score
        )
        
        # Handle case where no results found
        if not search_results:
            logger.warning(f"No search results found for session {request.session_id}")
            return AskResponse(
                answer="I couldn't find relevant information in the uploaded documents.",
                sources=[],
                used_fallback=True,
                gen_provider="heuristic",
                generation_model=None,
                embed_provider="sbert",
                embedding_model="sentence-transformers/all-MiniLM-L6-v2"
            )
        
        # Process search results
        sources = []
        context_parts = []
        
        for result in search_results:
            if result.score >= 0.3:  # Filter by similarity score
                sources.append({
                    "text": result.payload.get("text", ""),
                    "score": result.score,
                    "document_id": result.payload.get("document_id", ""),
                    "chunk_index": result.payload.get("chunk_index", 0)
                })
                context_parts.append(result.payload.get("text", ""))
        
        # Limit to requested number of sources
        sources = sources[:request.k]
        context = "\n\n".join(context_parts[:request.k])
        
        # Generate answer based on provider with proper fallback chain
        answer = None
        gen_provider = None
        generation_model_used = None
        embed_provider = None
        embedding_model_used = None
        used_fallback = False
        
        # Try API providers first (Gemini or OpenAI)
        if request.provider == "gemini" and request.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=request.api_key)
                model = genai.GenerativeModel(request.generation_model or "models/gemini-2.5-flash")
                prompt = f"Based on the following context, answer the question:\n\nContext:\n{context}\n\nQuestion: {request.question}\n\nAnswer:"
                response = model.generate_content(prompt)
                answer = response.text
                gen_provider = "gemini"
                generation_model_used = request.generation_model or "models/gemini-2.5-flash"
                embed_provider = "gemini"
                embedding_model_used = request.embedding_model or "models/embedding-001"
                used_fallback = False
                logger.info("✅ Used Gemini API for generation")
            except Exception as e:
                logger.warning(f"Gemini API failed: {str(e)[:200]}..., falling back to local LLM")
                answer = None
        
        elif request.provider == "openai" and request.api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=request.api_key)
                response = client.chat.completions.create(
                    model=request.generation_model or "gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided context."},
                        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {request.question}"}
                    ]
                )
                answer = response.choices[0].message.content
                gen_provider = "openai"
                generation_model_used = request.generation_model or "gpt-3.5-turbo"
                embed_provider = "openai"
                embedding_model_used = request.embedding_model or "text-embedding-ada-002"
                used_fallback = False
                logger.info("✅ Used OpenAI API for generation")
            except Exception as e:
                logger.warning(f"OpenAI API failed: {e}, falling back to local LLM")
                answer = None
        
        # Fallback 1: Try local LLM (Ollama) if API failed or no API key
        if answer is None:
            try:
                answer = await generate_with_ollama(request.question, context)
                gen_provider = "ollama"
                generation_model_used = "tinyllama:1.1b"
                embed_provider = "sbert"
                embedding_model_used = "sentence-transformers/all-MiniLM-L6-v2"
                used_fallback = True
                logger.info("✅ Used Ollama (local LLM) for generation")
            except Exception as e:
                logger.warning(f"Ollama failed: {e}, falling back to heuristic")
                answer = None
        
        # Fallback 2: Use heuristic if local LLM also failed
        if answer is None:
            answer = "I couldn't generate an answer at this time. Please try again or check your configuration."
            gen_provider = "heuristic"
            generation_model_used = None
            embed_provider = "sbert"
            embedding_model_used = "sentence-transformers/all-MiniLM-L6-v2"
            used_fallback = True
            logger.warning("⚠️ Used heuristic fallback for generation")
        
        response_time = int((time.time() - start_time) * 1000)
        
        logger.info(f"✅ Question answered in {response_time}ms with {len(sources)} sources using {gen_provider}")

        return AskResponse(
            answer=answer,
            sources=sources,
            used_fallback=used_fallback,
            gen_provider=gen_provider,
            generation_model=generation_model_used,
            embed_provider=embed_provider,
            embedding_model=embedding_model_used
        )
        
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        # If it's a Google API quota error, try fallback
        if "quota" in str(e).lower() or "429" in str(e):
            logger.warning("API quota exceeded, trying fallback")
            try:
                # Try with local embedding and Ollama
                query_embedding = embedder.encode([request.question])[0].tolist()
                search_results = qdrant_client.search(
                    collection_name=f"doc_chunks_{request.session_id}",
                    query_vector=query_embedding,
                    limit=request.k * 2,
                    score_threshold=0.3
                )
                
                if search_results:
                    context_parts = [result.payload.get("text", "") for result in search_results if result.score >= 0.3]
                    context = "\n\n".join(context_parts[:request.k])
                    answer = await generate_with_ollama(request.question, context)
                    return AskResponse(
                        answer=answer,
                        sources=[{"text": result.payload.get("text", ""), "score": result.score} for result in search_results[:request.k]],
                        used_fallback=True,
                        gen_provider="ollama",
                        generation_model="tinyllama:1.1b",
                        embed_provider="sbert",
                        embedding_model="sentence-transformers/all-MiniLM-L6-v2"
                    )
                else:
                    return AskResponse(
                        answer="I couldn't find relevant information in the uploaded documents.",
                        sources=[],
                        used_fallback=True,
                        gen_provider="heuristic",
                        generation_model=None, 
                        embed_provider="sbert",
                        embedding_model="sentence-transformers/all-MiniLM-L6-v2"
                    )
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                raise HTTPException(status_code=500, detail=str(e))
        else:
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/models", response_model=ModelResponse)
async def get_models():
    """
    Get list of available models.
    
    Returns:
        Available embedding and generation models
    """
    return ModelResponse(
        embedding_models=["sentence-transformers/all-MiniLM-L6-v2"],
        generation_models=["ollama-llama3:8b", "gemini-pro", "gpt-3.5-turbo"]
    )

class ValidateRequest(BaseModel):
    """Request model for API key validation"""
    provider: str
    api_key: Optional[str] = None
    embedding_model: Optional[str] = None
    generation_model: Optional[str] = None

class ValidateResponse(BaseModel):
    """Response model for validation matching frontend ModelsResponse"""
    provider: str
    embedding_model: Optional[str] = None
    generation_model: Optional[str] = None
    available_models: Dict[str, List[str]]
    api_valid: bool
    error_message: Optional[str] = None

@app.post("/validate", response_model=ValidateResponse)
async def validate_api_key(request: ValidateRequest):
    """
    Validate API key for a specific provider.
    
    Args:
        request: Validation request with provider and API key
    
    Returns:
        Validation result with available models
    """
    try:
        if request.provider == "ollama":
            # Test Ollama connection
            try:
                ollama_host = os.getenv("OLLAMA_HOST", "localhost")
                ollama_port = os.getenv("OLLAMA_PORT", "11434")
                response = requests.get(f"http://{ollama_host}:{ollama_port}/api/tags", timeout=5)
                if response.status_code == 200:
                    models_data = response.json().get("models", [])
                    generation_models = [model.get("name", "unknown") for model in models_data]
                    return ValidateResponse(
                        provider=request.provider,
                        embedding_model=request.embedding_model or "sentence-transformers/all-MiniLM-L6-v2",
                        generation_model=request.generation_model or (generation_models[0] if generation_models else None),
                        available_models={
                            "embedding": ["sentence-transformers/all-MiniLM-L6-v2"],
                            "generation": generation_models
                        },
                        api_valid=True
            )
                else:
                    return ValidateResponse(
                        provider=request.provider,
                        embedding_model=request.embedding_model,
                        generation_model=request.generation_model,
                        available_models={"embedding": [], "generation": []},
                        api_valid=False,
                        error_message=f"Ollama connection failed: HTTP {response.status_code}"
                    )
            except Exception as e:
                return ValidateResponse(
                    provider=request.provider,
                    embedding_model=request.embedding_model,
                    generation_model=request.generation_model,
                    available_models={"embedding": [], "generation": []},
                    api_valid=False,
                    error_message=f"Ollama connection error: {str(e)}"
                )
        
        elif request.provider == "gemini":
            # Test Gemini API key
            if not request.api_key:
                return ValidateResponse(
                    provider=request.provider,
                    embedding_model=request.embedding_model,
                    generation_model=request.generation_model,
                    available_models={"embedding": [], "generation": []},
                    api_valid=False,
                    error_message="API key is required for Gemini"
                )
            
            try:
                import google.generativeai as genai
                genai.configure(api_key=request.api_key)
                models = genai.list_models()
                generation_models = [model.name for model in models if 'generateContent' in model.supported_generation_methods]
                return ValidateResponse(
                    provider=request.provider,
                    embedding_model=request.embedding_model or "models/embedding-001",
                    generation_model=request.generation_model or (generation_models[0] if generation_models else None),
                    available_models={
                        "embedding": ["models/embedding-001"],
                        "generation": generation_models
                    },
                    api_valid=True
                )
            except Exception as e:
                return ValidateResponse(
                    provider=request.provider,
                    embedding_model=request.embedding_model,
                    generation_model=request.generation_model,
                    available_models={"embedding": [], "generation": []},
                    api_valid=False,
                    error_message=f"Failed to validate Gemini API key: {str(e)}"
                )
        
        elif request.provider == "openai":
            # Test OpenAI API key
            if not request.api_key:
                return ValidateResponse(
                    provider=request.provider,
                    embedding_model=request.embedding_model,
                    generation_model=request.generation_model,
                    available_models={"embedding": [], "generation": []},
                    api_valid=False,
                    error_message="API key is required for OpenAI"
                )
            
            try:
                import openai
                client = openai.OpenAI(api_key=request.api_key)
                models = client.models.list()
                generation_models = [model.id for model in models.data if model.id.startswith('gpt')]
                embedding_models = [model.id for model in models.data if 'embedding' in model.id]
                return ValidateResponse(
                    provider=request.provider,
                    embedding_model=request.embedding_model or (embedding_models[0] if embedding_models else None),
                    generation_model=request.generation_model or (generation_models[0] if generation_models else None),
                    available_models={
                        "embedding": embedding_models,
                        "generation": generation_models
                    },
                    api_valid=True
                )
            except Exception as e:
                return ValidateResponse(
                    provider=request.provider,
                    embedding_model=request.embedding_model,
                    generation_model=request.generation_model,
                    available_models={"embedding": [], "generation": []},
                    api_valid=False,
                    error_message=f"Failed to validate OpenAI API key: {str(e)}"
                )
        
        else:
            return ValidateResponse(
                provider=request.provider,
                embedding_model=request.embedding_model,
                generation_model=request.generation_model,
                available_models={"embedding": [], "generation": []},
                api_valid=False,
                error_message=f"Unknown provider: {request.provider}"
            )
            
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return ValidateResponse(
            provider=request.provider,
            embedding_model=request.embedding_model,
            generation_model=request.generation_model,
            available_models={"embedding": [], "generation": []},
            api_valid=False,
            error_message=f"Validation failed: {str(e)}"
        )

# =============================================================================
# PHASE 3 ADVANCED API ENDPOINTS
# =============================================================================

@app.post("/sessions", response_model=SessionResponse)
async def create_session(request: SessionCreateRequest):
    """Create a new session with advanced metadata"""
    try:
        session = await session_manager.create_session(
            name=request.name,
            description=request.description,
            user_id=request.user_id,
            tags=request.tags
        )
        
        return SessionResponse(
            id=session.id,
            name=session.name,
            description=session.description,
            status=session.status.value,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            document_count=session.document_count,
            total_chunks=session.total_chunks,
            last_activity=session.last_activity.isoformat(),
            user_id=session.user_id,
            tags=session.tags
        )
        
    except Exception as e:
        logger.error(f"Session creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List sessions with filtering and pagination"""
    try:
        from app.advanced_session_manager import SessionStatus
        
        status_enum = None
        if status:
            status_enum = SessionStatus(status)
        
        sessions = await session_manager.list_sessions(
            user_id=user_id,
            status=status_enum,
            limit=limit,
            offset=offset
        )
        
        return [
            SessionResponse(
                id=session.id,
                name=session.name,
                description=session.description,
                status=session.status.value,
                created_at=session.created_at.isoformat(),
                updated_at=session.updated_at.isoformat(),
                document_count=session.document_count,
                total_chunks=session.total_chunks,
                last_activity=session.last_activity.isoformat(),
                user_id=session.user_id,
                tags=session.tags
            )
            for session in sessions
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session listing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session details"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return SessionResponse(
            id=session.id,
            name=session.name,
            description=session.description,
            status=session.status.value,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            document_count=session.document_count,
            total_chunks=session.total_chunks,
            last_activity=session.last_activity.isoformat(),
            user_id=session.user_id,
            tags=session.tags
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search/advanced", response_model=AdvancedSearchResponse)
async def advanced_search(request: AdvancedSearchRequest):
    """Perform advanced hybrid search"""
    try:
        # Build search filters
        filters = SearchFilters(
            document_ids=request.search_filters.get("document_ids") if request.search_filters else None,
            date_range=request.search_filters.get("date_range") if request.search_filters else None,
            file_types=request.search_filters.get("file_types") if request.search_filters else None,
            tags=request.search_filters.get("tags") if request.search_filters else None,
            min_score=request.search_filters.get("min_score", 0.3) if request.search_filters else 0.3,
            max_results=request.max_results
        )
        
        # Perform hybrid search
        start_time = time.time()
        results = await search_engine.hybrid_search(
            query=request.query,
            session_id=request.session_id,
            filters=filters,
            semantic_weight=request.semantic_weight,
            keyword_weight=request.keyword_weight
        )
        query_time = (time.time() - start_time) * 1000
        
        # Get search suggestions
        suggestions = await search_engine.get_search_suggestions(
            query=request.query,
            session_id=request.session_id
        )
        
        # Convert results to dict format
        result_dicts = [
            {
                "text": result.text,
                "score": result.score,
                "document_id": result.document_id,
                "chunk_index": result.chunk_index,
                "metadata": result.metadata,
                "search_type": result.search_type
            }
            for result in results
        ]
        
        return AdvancedSearchResponse(
            results=result_dicts,
            total_results=len(results),
            search_type="hybrid",
            query_time_ms=query_time,
            suggestions=suggestions
        )
        
    except Exception as e:
        logger.error(f"Advanced search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/performance/metrics", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(limit: int = 100):
    """Get performance metrics and system health"""
    try:
        metrics = await performance_optimizer.get_performance_metrics(limit=limit)
        endpoint_stats = await performance_optimizer.get_endpoint_stats()
        cache_stats = await performance_optimizer.get_cache_stats()
        system_health = await performance_optimizer.get_system_health()
        
        return PerformanceMetricsResponse(
            metrics=metrics,
            endpoint_stats=endpoint_stats,
            cache_stats=cache_stats,
            system_health=system_health
        )
        
    except Exception as e:
        logger.error(f"Performance metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/security/stats", response_model=SecurityStatsResponse)
async def get_security_stats(limit: int = 100):
    """Get security statistics and events"""
    try:
        security_events = await security_manager.get_security_events(limit=limit)
        security_stats = await security_manager.get_security_stats()
        
        # Get rate limit status (simplified)
        rate_limit_status = {
            "active_rules": len(security_manager.rate_limit_rules),
            "blocked_ips": len(await asyncio.get_event_loop().run_in_executor(
                None, security_manager.redis.keys, "blocked_ip:*"
            ))
        }
        
        return SecurityStatsResponse(
            security_events=security_events,
            security_stats=security_stats,
            rate_limit_status=rate_limit_status
        )
        
    except Exception as e:
        logger.error(f"Security stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/analytics/{session_id}")
async def get_search_analytics(session_id: str):
    """Get search analytics for a session"""
    try:
        analytics = await search_engine.get_search_analytics(session_id)
        return analytics
        
    except Exception as e:
        logger.error(f"Search analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{session_id}/analytics")
async def get_session_analytics(session_id: str):
    """Get analytics for a session"""
    try:
        analytics = await session_manager.get_session_analytics(session_id)
        return analytics
        
    except Exception as e:
        logger.error(f"Session analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and all associated data"""
    try:
        await session_manager.delete_session(session_id)
        return {"message": f"Session {session_id} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Session deletion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/performance/optimize")
async def optimize_performance():
    """Trigger performance optimization"""
    try:
        await performance_optimizer.optimize_connections()
        return {"message": "Performance optimization completed"}
        
    except Exception as e:
        logger.error(f"Performance optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cache/clear")
async def clear_cache(cache_type: Optional[str] = None):
    """Clear cache entries"""
    try:
        await performance_optimizer.clear_cache(cache_type)
        return {"message": f"Cache cleared: {cache_type or 'all'}"}
        
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )
