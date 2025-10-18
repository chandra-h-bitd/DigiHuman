"""
Multi-Document Upload and Processing System
Handles batch document processing, versioning, and cross-document search
"""

import os
import uuid
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor
import aiofiles

import numpy as np
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from .session_manager import session_manager, DocumentInfo

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def process_multiple_documents(self, 
                                       files: List[Any], 
                                       session_id: str,
                                       chunk_size: int = 1000,
                                       chunk_overlap: int = 200) -> Dict[str, Any]:
        """
        Process multiple documents concurrently
        
        Args:
            files: List of uploaded files
            session_id: Session ID to associate documents with
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            
        Returns:
            Processing results for all documents
        """
        results = {
            "session_id": session_id,
            "total_files": len(files),
            "processed_files": 0,
            "failed_files": 0,
            "total_chunks": 0,
            "documents": [],
            "errors": []
        }
        
        # Process documents concurrently
        tasks = []
        for file in files:
            task = self._process_single_document(
                file, session_id, chunk_size, chunk_overlap
            )
            tasks.append(task)
        
        # Wait for all processing to complete
        document_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        for i, result in enumerate(document_results):
            if isinstance(result, Exception):
                results["failed_files"] += 1
                results["errors"].append({
                    "file_index": i,
                    "filename": files[i].filename if hasattr(files[i], 'filename') else f"file_{i}",
                    "error": str(result)
                })
                logger.error(f"Failed to process file {i}: {result}")
            else:
                results["processed_files"] += 1
                results["total_chunks"] += result["chunk_count"]
                results["documents"].append(result)
        
        # Update session metadata
        await session_manager.update_session_activity(session_id)
        
        logger.info(f"Processed {results['processed_files']}/{results['total_files']} files "
                   f"with {results['total_chunks']} total chunks")
        
        return results
    
    async def _process_single_document(self, 
                                     file: Any, 
                                     session_id: str,
                                     chunk_size: int,
                                     chunk_overlap: int) -> Dict[str, Any]:
        """Process a single document"""
        document_id = str(uuid.uuid4())
        filename = file.filename or f"document_{document_id[:8]}"
        
        try:
            # Read file content
            content = await file.read()
            file_size = len(content)
            
            # Determine file type
            file_type = self._get_file_type(filename)
            
            # Process document content
            chunks = await self._extract_chunks(content, file_type, chunk_size, chunk_overlap)
            
            # Generate embeddings and store in vector database
            await self._store_chunks_in_vector_db(session_id, document_id, chunks)
            
            # Create document info
            document_info = DocumentInfo(
                id=document_id,
                filename=filename,
                original_name=filename,
                file_type=file_type,
                file_size=file_size,
                upload_date=datetime.now(timezone.utc),
                chunk_count=len(chunks),
                processing_status="completed",
                metadata={
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "processing_time": datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Add to session
            await session_manager.add_document_to_session(session_id, document_info)
            
            return {
                "document_id": document_id,
                "filename": filename,
                "file_type": file_type,
                "file_size": file_size,
                "chunk_count": len(chunks),
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Error processing document {filename}: {e}")
            raise e
    
    def _get_file_type(self, filename: str) -> str:
        """Determine file type from filename"""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        
        if ext in ['pdf']:
            return 'pdf'
        elif ext in ['docx', 'doc']:
            return 'docx'
        elif ext in ['txt']:
            return 'txt'
        elif ext in ['md', 'markdown']:
            return 'markdown'
        else:
            return 'unknown'
    
    async def _extract_chunks(self, content: bytes, file_type: str, 
                            chunk_size: int, chunk_overlap: int) -> List[Dict[str, Any]]:
        """Extract text chunks from document content"""
        # Run text extraction in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        chunks = await loop.run_in_executor(
            self.executor, 
            self._extract_text_chunks_sync, 
            content, file_type, chunk_size, chunk_overlap
        )
        return chunks
    
    def _extract_text_chunks_sync(self, content: bytes, file_type: str, 
                                chunk_size: int, chunk_overlap: int) -> List[Dict[str, Any]]:
        """Synchronous text extraction (runs in thread pool)"""
        try:
            if file_type == 'pdf':
                import fitz  # PyMuPDF
                doc = fitz.open(stream=content, filetype="pdf")
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
            elif file_type == 'docx':
                from docx import Document
                import io
                doc = Document(io.BytesIO(content))
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            elif file_type in ['txt', 'markdown']:
                text = content.decode('utf-8', errors='ignore')
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            # Split into chunks
            chunks = self._split_text_into_chunks(text, chunk_size, chunk_overlap)
            return chunks
            
        except Exception as e:
            logger.error(f"Error extracting text from {file_type} document: {e}")
            raise e
    
    def _split_text_into_chunks(self, text: str, chunk_size: int, 
                              chunk_overlap: int) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks"""
        import nltk
        from nltk.tokenize import sent_tokenize
        
        # Split into sentences
        sentences = sent_tokenize(text)
        
        chunks = []
        current_chunk = ""
        current_length = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If adding this sentence would exceed chunk size, save current chunk
            if current_length + sentence_length > chunk_size and current_chunk:
                chunks.append({
                    "text": current_chunk.strip(),
                    "chunk_index": chunk_index,
                    "metadata": {
                        "chunk_size": len(current_chunk),
                        "sentence_count": len(current_chunk.split('.')),
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                })
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk, chunk_overlap)
                current_chunk = overlap_text + " " + sentence
                current_length = len(current_chunk)
                chunk_index += 1
            else:
                current_chunk += " " + sentence if current_chunk else sentence
                current_length += sentence_length
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                "text": current_chunk.strip(),
                "chunk_index": chunk_index,
                "metadata": {
                    "chunk_size": len(current_chunk),
                    "sentence_count": len(current_chunk.split('.')),
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            })
        
        return chunks
    
    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """Get overlap text from the end of current chunk"""
        if len(text) <= overlap_size:
            return text
        
        # Find last complete sentence within overlap size
        sentences = text.split('.')
        overlap_text = ""
        
        for sentence in reversed(sentences):
            if len(overlap_text + sentence + '.') <= overlap_size:
                overlap_text = sentence + '.' + overlap_text
            else:
                break
        
        return overlap_text.strip()
    
    async def _store_chunks_in_vector_db(self, session_id: str, document_id: str, 
                                       chunks: List[Dict[str, Any]]):
        """Store document chunks in vector database"""
        try:
            qdrant = get_qdrant_client()
            embedder = get_embedder()
            
            # Generate embeddings for all chunks
            texts = [chunk["text"] for chunk in chunks]
            embeddings = embedder.encode(texts)
            
            # Prepare points for Qdrant
            points = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                # Use integer ID for Qdrant compatibility
                point_id = hash(f"{session_id}_{document_id}_{i}") % (2**63 - 1)
                
                point = {
                    "id": point_id,
                    "vector": embedding.tolist(),
                    "payload": {
                        "session_id": session_id,
                        "document_id": document_id,
                        "chunk_index": chunk["chunk_index"],
                        "text": chunk["text"],
                        "metadata": chunk["metadata"]
                    }
                }
                points.append(point)
            
            # Store in Qdrant
            # Use the same collection naming convention as the main app
            collection_name = f"doc_chunks_{session_id}"
            
            # Ensure collection exists
            try:
                qdrant.get_collection(collection_name)
            except:
                try:
                    qdrant.create_collection(
                        collection_name,
                        vectors_config={"size": len(embeddings[0]), "distance": "Cosine"}
                    )
                except Exception as e:
                    # If collection already exists, that's fine
                    if "already exists" not in str(e):
                        raise e
            
            # Upsert points
            qdrant.upsert(collection_name=collection_name, points=points)
            
            logger.info(f"Stored {len(points)} chunks for document {document_id} in session {session_id}")
            
        except Exception as e:
            logger.error(f"Error storing chunks in vector DB: {e}")
            raise e

# Helper functions to avoid circular imports
def get_qdrant_client():
    """Get Qdrant client"""
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
    return QdrantClient(host=qdrant_host, port=qdrant_port)

def get_embedder():
    """Get sentence transformer embedder"""
    return SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Global document processor instance
document_processor = DocumentProcessor()
