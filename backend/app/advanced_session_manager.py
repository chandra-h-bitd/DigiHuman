"""
Advanced Session Management System
Handles multi-session, document management, and analytics
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import redis
import asyncpg
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class SessionStatus(Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

class DocumentStatus(Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class SessionMetadata:
    id: str
    name: str
    description: Optional[str]
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    document_count: int
    total_chunks: int
    last_activity: datetime
    user_id: Optional[str] = None
    tags: List[str] = None

@dataclass
class DocumentMetadata:
    id: str
    session_id: str
    filename: str
    file_size: int
    status: DocumentStatus
    chunks_count: int
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

class AdvancedSessionManager:
    def __init__(self, redis_client: redis.Redis, postgres_pool: asyncpg.Pool, qdrant_client: QdrantClient):
        self.redis = redis_client
        self.postgres = postgres_pool
        self.qdrant = qdrant_client
        self.cache_ttl = 3600  # 1 hour cache
        
    async def create_session(self, name: str, description: str = None, user_id: str = None, tags: List[str] = None) -> SessionMetadata:
        """Create a new session with advanced metadata"""
        session_id = f"session_{int(time.time())}_{hash(name) % 10000}"
        
        session = SessionMetadata(
            id=session_id,
            name=name,
            description=description,
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            document_count=0,
            total_chunks=0,
            last_activity=datetime.now(timezone.utc),
            user_id=user_id,
            tags=tags or []
        )
        
        # Store in PostgreSQL
        async with self.postgres.acquire() as conn:
            await conn.execute("""
                INSERT INTO sessions (id, name, description, status, created_at, updated_at, 
                                    document_count, total_chunks, last_activity, user_id, tags)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """, session.id, session.name, session.description, session.status.value,
                session.created_at, session.updated_at, session.document_count,
                session.total_chunks, session.last_activity, session.user_id, json.dumps(session.tags))
        
        # Cache in Redis
        await self._cache_session(session)
        
        logger.info(f"✅ Created session: {session_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[SessionMetadata]:
        """Get session with caching"""
        # Try cache first
        cached = await self._get_cached_session(session_id)
        if cached:
            return cached
        
        # Get from database
        async with self.postgres.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM sessions WHERE id = $1
            """, session_id)
            
            if not row:
                return None
            
            session = SessionMetadata(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                status=SessionStatus(row['status']),
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                document_count=row['document_count'],
                total_chunks=row['total_chunks'],
                last_activity=row['last_activity'],
                user_id=row['user_id'],
                tags=json.loads(row['tags']) if row['tags'] else []
            )
            
            # Cache the result
            await self._cache_session(session)
            return session
    
    async def list_sessions(self, user_id: str = None, status: SessionStatus = None, limit: int = 50, offset: int = 0) -> List[SessionMetadata]:
        """List sessions with filtering and pagination"""
        query = "SELECT * FROM sessions WHERE 1=1"
        params = []
        param_count = 0
        
        if user_id:
            param_count += 1
            query += f" AND user_id = ${param_count}"
            params.append(user_id)
        
        if status:
            param_count += 1
            query += f" AND status = ${param_count}"
            params.append(status.value)
        
        query += f" ORDER BY last_activity DESC LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
        params.extend([limit, offset])
        
        async with self.postgres.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
            sessions = []
            for row in rows:
                session = SessionMetadata(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    status=SessionStatus(row['status']),
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    document_count=row['document_count'],
                    total_chunks=row['total_chunks'],
                    last_activity=row['last_activity'],
                    user_id=row['user_id'],
                    tags=json.loads(row['tags']) if row['tags'] else []
                )
                sessions.append(session)
            
            return sessions
    
    async def update_session_activity(self, session_id: str):
        """Update session last activity timestamp"""
        now = datetime.now(timezone.utc)
        
        async with self.postgres.acquire() as conn:
            await conn.execute("""
                UPDATE sessions SET last_activity = $1, updated_at = $1 WHERE id = $2
            """, now, session_id)
        
        # Update cache
        session = await self.get_session(session_id)
        if session:
            session.last_activity = now
            session.updated_at = now
            await self._cache_session(session)
    
    async def add_document_to_session(self, session_id: str, document: DocumentMetadata):
        """Add document metadata to session"""
        async with self.postgres.acquire() as conn:
            await conn.execute("""
                INSERT INTO documents (id, session_id, filename, file_size, status, 
                                     chunks_count, uploaded_at, processed_at, error_message, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, document.id, document.session_id, document.filename, document.file_size,
                document.status.value, document.chunks_count, document.uploaded_at,
                document.processed_at, document.error_message, json.dumps(document.metadata or {}))
            
            # Update session document count
            await conn.execute("""
                UPDATE sessions SET document_count = document_count + 1, 
                                  total_chunks = total_chunks + $1,
                                  updated_at = $2
                WHERE id = $3
            """, document.chunks_count, datetime.now(timezone.utc), session_id)
        
        # Update session cache
        await self.update_session_activity(session_id)
    
    async def get_session_documents(self, session_id: str) -> List[DocumentMetadata]:
        """Get all documents for a session"""
        async with self.postgres.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM documents WHERE session_id = $1 ORDER BY uploaded_at DESC
            """, session_id)
            
            documents = []
            for row in rows:
                doc = DocumentMetadata(
                    id=row['id'],
                    session_id=row['session_id'],
                    filename=row['filename'],
                    file_size=row['file_size'],
                    status=DocumentStatus(row['status']),
                    chunks_count=row['chunks_count'],
                    uploaded_at=row['uploaded_at'],
                    processed_at=row['processed_at'],
                    error_message=row['error_message'],
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
                documents.append(doc)
            
            return documents
    
    async def delete_session(self, session_id: str):
        """Delete session and all associated data"""
        # Delete from Qdrant
        collection_name = f"doc_chunks_{session_id}"
        try:
            self.qdrant.delete_collection(collection_name)
        except Exception as e:
            logger.warning(f"Could not delete Qdrant collection {collection_name}: {e}")
        
        # Delete from PostgreSQL
        async with self.postgres.acquire() as conn:
            await conn.execute("DELETE FROM documents WHERE session_id = $1", session_id)
            await conn.execute("DELETE FROM sessions WHERE id = $1", session_id)
        
        # Delete from cache
        await self._delete_cached_session(session_id)
        
        logger.info(f"✅ Deleted session: {session_id}")
    
    async def get_session_analytics(self, session_id: str) -> Dict[str, Any]:
        """Get analytics for a session"""
        session = await self.get_session(session_id)
        if not session:
            return {}
        
        documents = await self.get_session_documents(session_id)
        
        # Calculate analytics
        total_size = sum(doc.file_size for doc in documents)
        processing_time = None
        if documents:
            completed_docs = [d for d in documents if d.status == DocumentStatus.COMPLETED and d.processed_at]
            if completed_docs:
                avg_processing_time = sum(
                    (d.processed_at - d.uploaded_at).total_seconds() 
                    for d in completed_docs
                ) / len(completed_docs)
                processing_time = avg_processing_time
        
        return {
            "session_id": session_id,
            "document_count": len(documents),
            "total_size_bytes": total_size,
            "total_chunks": session.total_chunks,
            "avg_processing_time_seconds": processing_time,
            "status_distribution": {
                status.value: len([d for d in documents if d.status == status])
                for status in DocumentStatus
            },
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat()
        }
    
    async def _cache_session(self, session: SessionMetadata):
        """Cache session in Redis"""
        cache_key = f"session:{session.id}"
        session_data = {
            "id": session.id,
            "name": session.name,
            "description": session.description,
            "status": session.status.value,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "document_count": session.document_count,
            "total_chunks": session.total_chunks,
            "last_activity": session.last_activity.isoformat(),
            "user_id": session.user_id,
            "tags": json.dumps(session.tags)
        }
        
        await asyncio.get_event_loop().run_in_executor(
            None, self.redis.hset, cache_key, mapping=session_data
        )
        await asyncio.get_event_loop().run_in_executor(
            None, self.redis.expire, cache_key, self.cache_ttl
        )
    
    async def _get_cached_session(self, session_id: str) -> Optional[SessionMetadata]:
        """Get session from cache"""
        cache_key = f"session:{session_id}"
        
        try:
            session_data = await asyncio.get_event_loop().run_in_executor(
                None, self.redis.hgetall, cache_key
            )
            
            if not session_data:
                return None
            
            return SessionMetadata(
                id=session_data[b'id'].decode(),
                name=session_data[b'name'].decode(),
                description=session_data[b'description'].decode() if session_data.get(b'description') else None,
                status=SessionStatus(session_data[b'status'].decode()),
                created_at=datetime.fromisoformat(session_data[b'created_at'].decode()),
                updated_at=datetime.fromisoformat(session_data[b'updated_at'].decode()),
                document_count=int(session_data[b'document_count']),
                total_chunks=int(session_data[b'total_chunks']),
                last_activity=datetime.fromisoformat(session_data[b'last_activity'].decode()),
                user_id=session_data[b'user_id'].decode() if session_data.get(b'user_id') else None,
                tags=json.loads(session_data[b'tags'].decode()) if session_data.get(b'tags') else []
            )
        except Exception as e:
            logger.warning(f"Cache read error for session {session_id}: {e}")
            return None
    
    async def _delete_cached_session(self, session_id: str):
        """Delete session from cache"""
        cache_key = f"session:{session_id}"
        await asyncio.get_event_loop().run_in_executor(
            None, self.redis.delete, cache_key
        )
