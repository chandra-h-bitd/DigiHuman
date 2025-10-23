"""
Storage module for managing FAISS vector indexes
Handles per-session FAISS index creation, loading, and persistence
"""
import os
import pickle
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import numpy as np
import faiss
import logging

logger = logging.getLogger(__name__)

# Default storage path
DEFAULT_STORAGE_PATH = os.path.expanduser("~/.rag-assistant")

class FAISSManager:
    """Manages FAISS indexes for multiple sessions"""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or DEFAULT_STORAGE_PATH
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
        
        # Cache loaded indexes
        self._index_cache: Dict[str, Tuple[faiss.Index, List[Dict[str, Any]]]] = {}
    
    def _get_index_path(self, session_id: str) -> str:
        """Get the file path for a session's FAISS index"""
        return os.path.join(self.storage_path, f"faiss_{session_id}.index")
    
    def _get_metadata_path(self, session_id: str) -> str:
        """Get the file path for a session's metadata"""
        return os.path.join(self.storage_path, f"faiss_{session_id}.metadata.pkl")
    
    def create_index(self, session_id: str, dimension: int, 
                    metric: str = "cosine") -> faiss.Index:
        """Create a new FAISS index for a session"""
        logger.info(f"Creating new FAISS index for session {session_id} with dimension {dimension}")
        
        # Create index based on metric
        if metric == "cosine":
            # Normalize vectors for cosine similarity using inner product
            index = faiss.IndexFlatIP(dimension)
        elif metric == "euclidean":
            index = faiss.IndexFlatL2(dimension)
        else:
            raise ValueError(f"Unsupported metric: {metric}")
        
        # Initialize empty metadata
        metadata: List[Dict[str, Any]] = []
        
        # Cache the index
        self._index_cache[session_id] = (index, metadata)
        
        # Save to disk
        self.save_index(session_id)
        
        return index
    
    def load_index(self, session_id: str) -> Optional[Tuple[faiss.Index, List[Dict[str, Any]]]]:
        """Load a FAISS index from disk"""
        # Check cache first
        if session_id in self._index_cache:
            return self._index_cache[session_id]
        
        index_path = self._get_index_path(session_id)
        metadata_path = self._get_metadata_path(session_id)
        
        if not os.path.exists(index_path):
            logger.warning(f"Index file not found for session {session_id}")
            return None
        
        try:
            # Load FAISS index
            index = faiss.read_index(index_path)
            
            # Load metadata
            metadata: List[Dict[str, Any]] = []
            if os.path.exists(metadata_path):
                with open(metadata_path, "rb") as f:
                    metadata = pickle.load(f)
            
            # Cache the loaded index
            self._index_cache[session_id] = (index, metadata)
            
            logger.info(f"Loaded FAISS index for session {session_id} with {index.ntotal} vectors")
            return (index, metadata)
            
        except Exception as e:
            logger.error(f"Failed to load index for session {session_id}: {e}")
            return None
    
    def save_index(self, session_id: str):
        """Save a FAISS index to disk"""
        if session_id not in self._index_cache:
            logger.warning(f"No index in cache for session {session_id}")
            return
        
        index, metadata = self._index_cache[session_id]
        
        index_path = self._get_index_path(session_id)
        metadata_path = self._get_metadata_path(session_id)
        
        try:
            # Save FAISS index
            faiss.write_index(index, index_path)
            
            # Save metadata
            with open(metadata_path, "wb") as f:
                pickle.dump(metadata, f)
            
            logger.info(f"Saved FAISS index for session {session_id} with {index.ntotal} vectors")
            
        except Exception as e:
            logger.error(f"Failed to save index for session {session_id}: {e}")
    
    def add_vectors(self, session_id: str, vectors: np.ndarray, 
                   metadata: List[Dict[str, Any]], normalize: bool = True):
        """Add vectors to a session's index"""
        # Get or load index
        result = self.load_index(session_id)
        if result is None:
            # Create new index with the dimension of the first vector
            dimension = vectors.shape[1]
            self.create_index(session_id, dimension)
            result = self._index_cache[session_id]
        
        index, existing_metadata = result
        
        # Normalize vectors if using cosine similarity
        if normalize:
            faiss.normalize_L2(vectors)
        
        # Add vectors to index
        index.add(vectors)
        
        # Update metadata
        existing_metadata.extend(metadata)
        self._index_cache[session_id] = (index, existing_metadata)
        
        # Save to disk
        self.save_index(session_id)
        
        logger.info(f"Added {len(vectors)} vectors to session {session_id}")
    
    def search(self, session_id: str, query_vector: np.ndarray, 
              k: int = 5, normalize: bool = True) -> List[Dict[str, Any]]:
        """Search for similar vectors in a session's index"""
        result = self.load_index(session_id)
        if result is None:
            logger.warning(f"No index found for session {session_id}")
            return []
        
        index, metadata = result
        
        if index.ntotal == 0:
            logger.warning(f"Index for session {session_id} is empty")
            return []
        
        # Check dimension compatibility
        query_dim = query_vector.shape[1]
        index_dim = index.d
        if query_dim != index_dim:
            error_msg = (
                f"Dimension mismatch! Query vector dimension ({query_dim}) "
                f"does not match index dimension ({index_dim}). "
                f"This typically happens when:\n"
                f"  - Documents were uploaded with one embedding model (e.g., Gemini: 768D)\n"
                f"  - Query is using a different embedding model (e.g., SBERT: 384D)\n"
                f"Solution: Re-upload your documents with the current embedding model, "
                f"or restore the original API key."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Normalize query vector if using cosine similarity
        query = query_vector.copy()
        if normalize:
            faiss.normalize_L2(query)
        
        # Search
        k = min(k, index.ntotal)  # Can't retrieve more than available
        distances, indices = index.search(query, k)
        
        # Build results with metadata
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx >= 0 and idx < len(metadata):
                result_dict = metadata[idx].copy()
                result_dict["score"] = float(dist)
                result_dict["rank"] = i + 1
                results.append(result_dict)
        
        return results
    
    def delete_index(self, session_id: str):
        """Delete a session's FAISS index from disk and cache"""
        # Remove from cache
        if session_id in self._index_cache:
            del self._index_cache[session_id]
        
        # Delete files
        index_path = self._get_index_path(session_id)
        metadata_path = self._get_metadata_path(session_id)
        
        try:
            if os.path.exists(index_path):
                os.remove(index_path)
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
            logger.info(f"Deleted FAISS index for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to delete index for session {session_id}: {e}")
    
    def get_index_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics about a session's index"""
        result = self.load_index(session_id)
        if result is None:
            return {
                "exists": False,
                "vector_count": 0,
                "dimension": 0
            }
        
        index, metadata = result
        return {
            "exists": True,
            "vector_count": index.ntotal,
            "dimension": index.d,
            "metric": "cosine" if isinstance(index, faiss.IndexFlatIP) else "euclidean"
        }
    
    def clear_cache(self):
        """Clear the in-memory index cache"""
        self._index_cache.clear()
        logger.info("Cleared FAISS index cache")


# Global FAISS manager instance
_faiss_manager: Optional[FAISSManager] = None

def get_faiss_manager(storage_path: Optional[str] = None) -> FAISSManager:
    """Get or create the global FAISS manager instance"""
    global _faiss_manager
    if _faiss_manager is None:
        _faiss_manager = FAISSManager(storage_path)
    return _faiss_manager

