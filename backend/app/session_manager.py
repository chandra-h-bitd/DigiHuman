"""
Advanced Session Management System
Handles multi-session persistence, metadata, and document management
"""

import os
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import logging
import redis
import asyncpg
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class SessionStatus(Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

@dataclass
class SessionMetadata:
    id: str
    name: str
    description: Optional[str]
    provider: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    last_activity: datetime
    document_count: int
    total_chunks: int
    tags: List[str]
    settings: Dict[str, Any]

@dataclass
class DocumentInfo:
    id: str
    filename: str
    original_name: str
    file_type: str
    file_size: int
    upload_date: datetime
    chunk_count: int
    processing_status: str
    metadata: Dict[str, Any]

class SessionManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True
        )
        self.postgres_host = os.getenv("POSTGRES_HOST", "localhost")
        self.postgres_port = int(os.getenv("POSTGRES_PORT", 5432))
        self.postgres_db = os.getenv("POSTGRES_DB", "docqa")
        self.postgres_user = os.getenv("POSTGRES_USER", "docqa_user")
        self.postgres_password = os.getenv("POSTGRES_PASSWORD", "docqa_password")
        
    async def get_db_connection(self):
        """Get PostgreSQL connection"""
        return await asyncpg.connect(
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
            user=self.postgres_user,
            password=self.postgres_password
        )

    async def create_session(self, name: str, description: str = None, 
                           provider: str = "ollama", tags: List[str] = None,
                           settings: Dict[str, Any] = None) -> SessionMetadata:
        """Create a new session with metadata"""
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        session = SessionMetadata(
            id=session_id,
            name=name or f"Session {session_id[:8]}",
            description=description,
            provider=provider,
            status=SessionStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            last_activity=now,
            document_count=0,
            total_chunks=0,
            tags=tags or [],
            settings=settings or {}
        )
        
        # Store in Redis for fast access
        session_dict = {
            "id": session.id,
            "name": session.name,
            "description": session.description,
            "provider": session.provider,
            "status": session.status.value,  # Store the value, not the enum
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "document_count": session.document_count,
            "total_chunks": session.total_chunks,
            "tags": session.tags,
            "settings": session.settings
        }
        self.redis_client.hset(
            f"session:{session_id}",
            mapping={
                "metadata": json.dumps(session_dict),
                "last_activity": now.isoformat()
            }
        )
        
        # Store in PostgreSQL for persistence
        conn = await self.get_db_connection()
        try:
            await conn.execute("""
                INSERT INTO sessions (id, name, description, provider, status, 
                                    created_at, updated_at, last_activity, 
                                    document_count, total_chunks, tags, settings)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """, session_id, session.name, session.description, session.provider,
                session.status.value, session.created_at, session.updated_at,
                session.last_activity, session.document_count, session.total_chunks,
                json.dumps(session.tags), json.dumps(session.settings))
        finally:
            await conn.close()
        
        logger.info(f"Created session {session_id}: {session.name}")
        return session

    async def get_session(self, session_id: str) -> Optional[SessionMetadata]:
        """Get session metadata"""
        # Try Redis first
        session_data = self.redis_client.hget(f"session:{session_id}", "metadata")
        if session_data:
            session_dict = json.loads(session_data)
            session_dict["status"] = SessionStatus(session_dict["status"])
            session_dict["created_at"] = datetime.fromisoformat(session_dict["created_at"])
            session_dict["updated_at"] = datetime.fromisoformat(session_dict["updated_at"])
            session_dict["last_activity"] = datetime.fromisoformat(session_dict["last_activity"])
            return SessionMetadata(**session_dict)
        
        # Fallback to PostgreSQL
        conn = await self.get_db_connection()
        try:
            row = await conn.fetchrow("""
                SELECT * FROM sessions WHERE id = $1
            """, session_id)
            
            if row:
                session = SessionMetadata(
                    id=str(row["id"]),
                    name=row["name"],
                    description=row["description"],
                    provider=row["provider"],
                    status=SessionStatus(row["status"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    last_activity=row["last_activity"],
                    document_count=row["document_count"],
                    total_chunks=row["total_chunks"],
                    tags=json.loads(row["tags"]) if row["tags"] else [],
                    settings=json.loads(row["settings"]) if row["settings"] else {}
                )
                
                # Cache in Redis
                session_dict = {
                    "id": session.id,
                    "name": session.name,
                    "description": session.description,
                    "provider": session.provider,
                    "status": session.status.value,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "last_activity": session.last_activity.isoformat(),
                    "document_count": session.document_count,
                    "total_chunks": session.total_chunks,
                    "tags": session.tags,
                    "settings": session.settings
                }
                self.redis_client.hset(
                    f"session:{session_id}",
                    mapping={
                        "metadata": json.dumps(session_dict),
                        "last_activity": session.last_activity.isoformat()
                    }
                )
                return session
        finally:
            await conn.close()
        
        return None

    async def update_session_activity(self, session_id: str):
        """Update session last activity timestamp"""
        now = datetime.now(timezone.utc)
        
        # Update Redis
        self.redis_client.hset(f"session:{session_id}", "last_activity", now.isoformat())
        
        # Update PostgreSQL
        conn = await self.get_db_connection()
        try:
            await conn.execute("""
                UPDATE sessions SET last_activity = $1, updated_at = $1 
                WHERE id = $2
            """, now, session_id)
        finally:
            await conn.close()

    async def list_sessions(self, status: SessionStatus = None, 
                          limit: int = 50, offset: int = 0) -> List[SessionMetadata]:
        """List sessions with optional filtering"""
        conn = await self.get_db_connection()
        try:
            query = "SELECT * FROM sessions"
            params = []
            
            if status:
                query += " WHERE status = $1"
                params.append(status.value)
            
            query += " ORDER BY last_activity DESC LIMIT $" + str(len(params) + 1) + " OFFSET $" + str(len(params) + 2)
            params.extend([limit, offset])
            
            rows = await conn.fetch(query, *params)
            sessions = []
            
            for row in rows:
                session = SessionMetadata(
                    id=str(row["id"]),
                    name=row["name"],
                    description=row["description"],
                    provider=row["provider"],
                    status=SessionStatus(row["status"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    last_activity=row["last_activity"],
                    document_count=row["document_count"],
                    total_chunks=row["total_chunks"],
                    tags=json.loads(row["tags"]) if row["tags"] else [],
                    settings=json.loads(row["settings"]) if row["settings"] else {}
                )
                sessions.append(session)
            
            return sessions
        finally:
            await conn.close()

    async def add_document_to_session(self, session_id: str, document_info: DocumentInfo):
        """Add document to session and update counts"""
        # Update session document count
        conn = await self.get_db_connection()
        try:
            await conn.execute("""
                UPDATE sessions 
                SET document_count = document_count + 1,
                    total_chunks = total_chunks + $1,
                    updated_at = $2
                WHERE id = $3
            """, document_info.chunk_count, datetime.now(timezone.utc), session_id)
            
            # Store document info
            await conn.execute("""
                INSERT INTO session_documents (session_id, document_id, filename, 
                                             original_name, file_type, file_size,
                                             upload_date, chunk_count, processing_status, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, session_id, document_info.id, document_info.filename,
                document_info.original_name, document_info.file_type,
                document_info.file_size, document_info.upload_date,
                document_info.chunk_count, document_info.processing_status,
                json.dumps(document_info.metadata))
        finally:
            await conn.close()
        
        # Update Redis cache
        await self.update_session_activity(session_id)

    async def get_session_documents(self, session_id: str) -> List[DocumentInfo]:
        """Get all documents in a session"""
        conn = await self.get_db_connection()
        try:
            rows = await conn.fetch("""
                SELECT * FROM session_documents 
                WHERE session_id = $1 
                ORDER BY upload_date DESC
            """, session_id)
            
            documents = []
            for row in rows:
                doc = DocumentInfo(
                    id=row["document_id"],
                    filename=row["filename"],
                    original_name=row["original_name"],
                    file_type=row["file_type"],
                    file_size=row["file_size"],
                    upload_date=row["upload_date"],
                    chunk_count=row["chunk_count"],
                    processing_status=row["processing_status"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                )
                documents.append(doc)
            
            return documents
        finally:
            await conn.close()

    async def delete_session(self, session_id: str):
        """Delete a session (soft delete)"""
        conn = await self.get_db_connection()
        try:
            await conn.execute("""
                UPDATE sessions SET status = $1, updated_at = $2 
                WHERE id = $3
            """, SessionStatus.DELETED.value, datetime.now(timezone.utc), session_id)
        finally:
            await conn.close()
        
        # Remove from Redis
        self.redis_client.delete(f"session:{session_id}")

    async def archive_session(self, session_id: str):
        """Archive a session"""
        conn = await self.get_db_connection()
        try:
            await conn.execute("""
                UPDATE sessions SET status = $1, updated_at = $2 
                WHERE id = $3
            """, SessionStatus.ARCHIVED.value, datetime.now(timezone.utc), session_id)
        finally:
            await conn.close()

# Global session manager instance
session_manager = SessionManager()
