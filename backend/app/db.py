"""
Database module for managing TinyDB persistence
Handles sessions, documents, conversations, and user config
"""
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from tinydb import TinyDB, Query

# Default storage path
DEFAULT_STORAGE_PATH = os.path.expanduser("~/.rag-assistant")

class Database:
    """TinyDB wrapper for managing all persistent data"""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or DEFAULT_STORAGE_PATH
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
        
        db_path = os.path.join(self.storage_path, "db.json")
        self.db = TinyDB(db_path, indent=2)
        
        # Collections
        self.sessions = self.db.table("sessions")
        self.documents = self.db.table("documents")
        self.conversations = self.db.table("conversations")
        self.user_config = self.db.table("user_config")
        self.session_summaries = self.db.table("session_summaries")
        
    def close(self):
        """Close database connection"""
        self.db.close()
    
    # ========== Session Management ==========
    
    def create_session(self, session_name: str, primary_llm: str = "gemini") -> Dict[str, Any]:
        """Create a new session"""
        import uuid
        session_id = str(uuid.uuid4())
        session = {
            "session_id": session_id,
            "session_name": session_name,
            "primary_llm": primary_llm,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }
        self.sessions.insert(session)
        return session
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        Session = Query()
        result = self.sessions.search(Session.session_id == session_id)
        return result[0] if result else None
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions, sorted by last activity"""
        sessions = self.sessions.all()
        sessions.sort(key=lambda x: x.get("last_activity", ""), reverse=True)
        return sessions
    
    def update_session(self, session_id: str, updates: Dict[str, Any]):
        """Update session fields"""
        Session = Query()
        updates["last_activity"] = datetime.now().isoformat()
        self.sessions.update(updates, Session.session_id == session_id)
    
    def delete_session(self, session_id: str):
        """Delete session and all related data"""
        Session = Query()
        Document = Query()
        Conversation = Query()
        
        # Delete session
        self.sessions.remove(Session.session_id == session_id)
        # Delete documents
        self.documents.remove(Document.session_id == session_id)
        # Delete conversations
        self.conversations.remove(Conversation.session_id == session_id)
        # Delete summary
        self.delete_session_summary(session_id)
        # Delete Q&A
        self.delete_session_qa(session_id)
        # Delete curriculum
        self.delete_session_curriculum(session_id)
    
    # ========== Document Management ==========
    
    def add_document(self, session_id: str, file_name: str, file_type: str, 
                     file_path: str, chunk_count: int = 0, summary: Optional[str] = None, doc_type: str = "summary") -> Dict[str, Any]:
        """Add a document to a session"""
        import uuid
        document = {
            "document_id": str(uuid.uuid4()),
            "session_id": session_id,
            "file_name": file_name,
            "file_type": file_type,
            "file_path": file_path,
            "chunk_count": chunk_count,
            "summary": summary or "",
            "doc_type": doc_type,
            "uploaded_at": datetime.now().isoformat()
        }
        self.documents.insert(document)
        self.update_session(session_id, {})  # Update last_activity
        return document
    
    def get_documents(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all documents for a session"""
        Document = Query()
        return self.documents.search(Document.session_id == session_id)
    
    def delete_document(self, document_id: str):
        """Delete a document"""
        Document = Query()
        self.documents.remove(Document.document_id == document_id)
    
    def update_document_summary(self, document_id: str, summary: str):
        """Update document summary"""
        Document = Query()
        self.documents.update(
            {"summary": summary}, 
            Document.document_id == document_id
        )
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID"""
        Document = Query()
        result = self.documents.search(Document.document_id == document_id)
        return result[0] if result else None
    
    def get_document_summary(self, document_id: str) -> Optional[str]:
        """Get summary for a specific document"""
        document = self.get_document(document_id)
        return document.get("summary") if document else None
    
    def get_summaries_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all documents with their summaries for a session"""
        Document = Query()
        documents = self.documents.search(Document.session_id == session_id)
        return [{
            "document_id": doc.get("document_id"),
            "file_name": doc.get("file_name"),
            "summary": doc.get("summary", ""),
            "uploaded_at": doc.get("uploaded_at")
        } for doc in documents]
    
    # ========== Session Summary Management ==========
    
    def set_session_summary(self, session_id: str, summary: str) -> Dict[str, Any]:
        """Set or update the consolidated summary for a session"""
        SessionSummary = Query()
        existing = self.session_summaries.search(SessionSummary.session_id == session_id)
        
        summary_obj = {
            "session_id": session_id,
            "summary": summary,
            "updated_at": datetime.now().isoformat()
        }
        
        if existing:
            # Update existing summary
            self.session_summaries.update(summary_obj, SessionSummary.session_id == session_id)
        else:
            # Create new summary
            self.session_summaries.insert(summary_obj)
        
        return summary_obj
    
    def get_session_summary(self, session_id: str) -> Optional[str]:
        """Get the consolidated summary for a session"""
        try:
            SessionSummary = Query()
            result = self.session_summaries.search(SessionSummary.session_id == session_id)
            return result[0].get("summary") if result else None
        except Exception as e:
            # If table doesn't exist or other error, return None gracefully
            import logging
            logging.warning(f"Error getting session summary: {e}")
            return None
    
    def delete_session_summary(self, session_id: str):
        """Delete session summary"""
        SessionSummary = Query()
        self.session_summaries.remove(SessionSummary.session_id == session_id)
    
    # ========== Q&A Management ==========
    
    def set_session_qa(self, session_id: str, qa_pairs: List[Dict[str, str]]) -> Dict[str, Any]:
        """Set or update the Q&A pairs for a session"""
        if not hasattr(self, 'session_qa'):
            self.session_qa = self.db.table("session_qa")
        
        SessionQA = Query()
        existing = self.session_qa.search(SessionQA.session_id == session_id)
        
        qa_obj = {
            "session_id": session_id,
            "qa_pairs": qa_pairs,
            "updated_at": datetime.now().isoformat()
        }
        
        if existing:
            self.session_qa.update(qa_obj, SessionQA.session_id == session_id)
        else:
            self.session_qa.insert(qa_obj)
        
        return qa_obj
    
    def get_session_qa(self, session_id: str) -> Optional[List[Dict[str, str]]]:
        """Get the Q&A pairs for a session"""
        try:
            if not hasattr(self, 'session_qa'):
                self.session_qa = self.db.table("session_qa")
            
            SessionQA = Query()
            result = self.session_qa.search(SessionQA.session_id == session_id)
            return result[0].get("qa_pairs") if result else None
        except Exception as e:
            import logging
            logging.warning(f"Error getting session Q&A: {e}")
            return None
    
    def delete_session_qa(self, session_id: str):
        """Delete session Q&A"""
        if not hasattr(self, 'session_qa'):
            self.session_qa = self.db.table("session_qa")
        
        SessionQA = Query()
        self.session_qa.remove(SessionQA.session_id == session_id)
    
    # ========== Training Curriculum Management ==========
    
    def set_session_curriculum(self, session_id: str, modules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Set or update the training curriculum for a session"""
        if not hasattr(self, 'session_curriculum'):
            self.session_curriculum = self.db.table("session_curriculum")
        
        SessionCurriculum = Query()
        existing = self.session_curriculum.search(SessionCurriculum.session_id == session_id)
        
        curriculum_obj = {
            "session_id": session_id,
            "modules": modules,
            "updated_at": datetime.now().isoformat()
        }
        
        if existing:
            self.session_curriculum.update(curriculum_obj, SessionCurriculum.session_id == session_id)
        else:
            self.session_curriculum.insert(curriculum_obj)
        
        return curriculum_obj
    
    def get_session_curriculum(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get the training curriculum for a session"""
        try:
            if not hasattr(self, 'session_curriculum'):
                self.session_curriculum = self.db.table("session_curriculum")
            
            SessionCurriculum = Query()
            result = self.session_curriculum.search(SessionCurriculum.session_id == session_id)
            return result[0].get("modules") if result else None
        except Exception as e:
            import logging
            logging.warning(f"Error getting session curriculum: {e}")
            return None
    
    def delete_session_curriculum(self, session_id: str):
        """Delete session curriculum"""
        if not hasattr(self, 'session_curriculum'):
            self.session_curriculum = self.db.table("session_curriculum")
        
        SessionCurriculum = Query()
        self.session_curriculum.remove(SessionCurriculum.session_id == session_id)
    
    # ========== Conversation Management ==========
    
    def add_conversation(self, session_id: str, query: str, response: str, 
                        llm_used: str, sources: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Add a conversation entry"""
        import uuid
        conversation = {
            "conversation_id": str(uuid.uuid4()),
            "session_id": session_id,
            "query": query,
            "response": response,
            "llm_used": llm_used,
            "sources": sources or [],
            "created_at": datetime.now().isoformat()
        }
        self.conversations.insert(conversation)
        self.update_session(session_id, {})  # Update last_activity
        return conversation
    
    def get_conversations(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        Conversation = Query()
        conversations = self.conversations.search(Conversation.session_id == session_id)
        conversations.sort(key=lambda x: x.get("created_at", ""))
        if limit:
            conversations = conversations[-limit:]
        return conversations
    
    def delete_conversation(self, conversation_id: str):
        """Delete a conversation entry"""
        Conversation = Query()
        self.conversations.remove(Conversation.conversation_id == conversation_id)
    
    # ========== User Config Management ==========
    
    def set_config(self, key_name: str, key_value: Any):
        """Set a user configuration value"""
        Config = Query()
        existing = self.user_config.search(Config.key_name == key_name)
        if existing:
            self.user_config.update({"key_value": key_value}, Config.key_name == key_name)
        else:
            self.user_config.insert({
                "key_name": key_name,
                "key_value": key_value,
                "updated_at": datetime.now().isoformat()
            })
    
    def get_config(self, key_name: str, default: Any = None) -> Any:
        """Get a user configuration value"""
        Config = Query()
        result = self.user_config.search(Config.key_name == key_name)
        if result:
            return result[0].get("key_value", default)
        return default
    
    def delete_config(self, key_name: str):
        """Delete a configuration entry"""
        Config = Query()
        self.user_config.remove(Config.key_name == key_name)
    
    def get_all_configs(self) -> Dict[str, Any]:
        """Get all configuration entries as a dictionary"""
        configs = self.user_config.all()
        return {c["key_name"]: c["key_value"] for c in configs}


# Global database instance
_db_instance: Optional[Database] = None

def get_db(storage_path: Optional[str] = None) -> Database:
    """Get or create the global database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(storage_path)
    return _db_instance

