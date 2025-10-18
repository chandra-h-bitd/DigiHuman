"""
Persistent Storage Configuration
Replaces in-memory storage with persistent Redis, PostgreSQL, and Qdrant
"""
import os
import logging
import redis
import asyncpg
from qdrant_client import QdrantClient
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)

class PersistentStorage:
    """Centralized persistent storage management"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.postgres_pool: Optional[asyncpg.Pool] = None
        self.qdrant_client: Optional[QdrantClient] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize all storage connections"""
        if self._initialized:
            return
            
        try:
            # Initialize Redis
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            
            # Test Redis connection
            await self._test_redis()
            logger.info("✅ Redis connection established")
            
            # Initialize PostgreSQL
            postgres_host = os.getenv("POSTGRES_HOST", "localhost")
            postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
            postgres_db = os.getenv("POSTGRES_DB", "docqa")
            postgres_user = os.getenv("POSTGRES_USER", "docqa_user")
            postgres_password = os.getenv("POSTGRES_PASSWORD", "docqa_password")
            
            database_url = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
            self.postgres_pool = await asyncpg.create_pool(database_url)
            
            # Test PostgreSQL connection
            await self._test_postgres()
            logger.info("✅ PostgreSQL connection established")
            
            # Initialize Qdrant
            qdrant_host = os.getenv("QDRANT_HOST", "localhost")
            qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
            qdrant_url = f"http://{qdrant_host}:{qdrant_port}"
            self.qdrant_client = QdrantClient(url=qdrant_url)
            
            # Test Qdrant connection
            await self._test_qdrant()
            logger.info("✅ Qdrant connection established")
            
            # Create database tables
            await self._create_tables()
            
            self._initialized = True
            logger.info("🚀 Persistent storage initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize persistent storage: {e}")
            # Fallback to in-memory for development
            await self._fallback_to_memory()
    
    async def _test_redis(self):
        """Test Redis connection"""
        if self.redis_client:
            self.redis_client.ping()
    
    async def _test_postgres(self):
        """Test PostgreSQL connection"""
        if self.postgres_pool:
            async with self.postgres_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
    
    async def _test_qdrant(self):
        """Test Qdrant connection"""
        if self.qdrant_client:
            self.qdrant_client.get_collections()
    
    async def _create_tables(self):
        """Create necessary database tables"""
        if not self.postgres_pool:
            return
            
        async with self.postgres_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255),
                    user_id VARCHAR(255),
                    provider VARCHAR(50),
                    api_key_hash VARCHAR(255),
                    embedding_model VARCHAR(255),
                    generation_model VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'active'
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id VARCHAR(255) PRIMARY KEY,
                    session_id VARCHAR(255) REFERENCES sessions(id),
                    filename VARCHAR(255),
                    file_type VARCHAR(50),
                    file_size BIGINT,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processing_status VARCHAR(50) DEFAULT 'pending',
                    metadata JSONB
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) REFERENCES sessions(id),
                    role VARCHAR(20),
                    content TEXT,
                    sources JSONB,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_documents_session_id ON documents(session_id);
                CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history(session_id);
            """)
    
    async def _fallback_to_memory(self):
        """Fallback to in-memory storage for development"""
        logger.warning("⚠️ Falling back to in-memory storage")
        from qdrant_client import QdrantClient
        self.qdrant_client = QdrantClient(path=":memory:")
        self.redis_client = None
        self.postgres_pool = None
        self._initialized = True
    
    # Redis operations
    async def cache_set(self, key: str, value: Any, ttl: int = 3600):
        """Set cache value in Redis"""
        if self.redis_client:
            try:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                self.redis_client.setex(key, ttl, value)
            except Exception as e:
                logger.warning(f"Redis cache set failed: {e}")
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """Get cache value from Redis"""
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
            except Exception as e:
                logger.warning(f"Redis cache get failed: {e}")
        return None
    
    async def cache_delete(self, key: str):
        """Delete cache value from Redis"""
        if self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Redis cache delete failed: {e}")
    
    # Session operations
    async def save_session(self, session_id: str, session_data: Dict[str, Any]):
        """Save session to PostgreSQL"""
        if not self.postgres_pool:
            return
            
        try:
            async with self.postgres_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO sessions (id, name, user_id, provider, embedding_model, generation_model, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        provider = EXCLUDED.provider,
                        embedding_model = EXCLUDED.embedding_model,
                        generation_model = EXCLUDED.generation_model,
                        updated_at = CURRENT_TIMESTAMP
                """, 
                session_id,
                session_data.get("name", "Untitled Session"),
                session_data.get("user_id", "default"),
                session_data.get("provider"),
                session_data.get("embedding_model"),
                session_data.get("generation_model"),
                session_data.get("status", "active")
                )
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session from PostgreSQL"""
        if not self.postgres_pool:
            return None
            
        try:
            async with self.postgres_pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM sessions WHERE id = $1", session_id)
                if row:
                    return dict(row)
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
        return None
    
    async def get_user_sessions(self, user_id: str) -> list:
        """Get all sessions for a user"""
        if not self.postgres_pool:
            return []
            
        try:
            async with self.postgres_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, name, provider, created_at, updated_at, status 
                    FROM sessions 
                    WHERE user_id = $1 
                    ORDER BY updated_at DESC
                """, user_id)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get user sessions: {e}")
        return []
    
    # Chat history operations
    async def save_chat_message(self, session_id: str, role: str, content: str, sources: list = None, metadata: dict = None):
        """Save chat message to PostgreSQL"""
        if not self.postgres_pool:
            return
            
        try:
            async with self.postgres_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO chat_history (session_id, role, content, sources, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                """, session_id, role, content, json.dumps(sources or []), json.dumps(metadata or {}))
        except Exception as e:
            logger.error(f"Failed to save chat message: {e}")
    
    async def get_chat_history(self, session_id: str, limit: int = 50) -> list:
        """Get chat history for a session"""
        if not self.postgres_pool:
            return []
            
        try:
            async with self.postgres_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT role, content, sources, metadata, created_at
                    FROM chat_history 
                    WHERE session_id = $1 
                    ORDER BY created_at DESC 
                    LIMIT $2
                """, session_id, limit)
                return [dict(row) for row in reversed(rows)]
        except Exception as e:
            logger.error(f"Failed to get chat history: {e}")
        return []

# Global storage instance
storage = PersistentStorage()
