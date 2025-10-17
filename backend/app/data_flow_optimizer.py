"""
Data Flow Optimizer for Enhanced Performance
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import numpy as np
from functools import lru_cache

logger = logging.getLogger(__name__)

@dataclass
class ProcessingStage:
    """Processing stage with timing and optimization info"""
    name: str
    start_time: float
    end_time: float
    input_size: int
    output_size: int
    optimization_applied: Optional[str] = None
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time
    
    @property
    def compression_ratio(self) -> float:
        return self.output_size / max(self.input_size, 1)

class DataFlowOptimizer:
    """
    Optimizes data flow through the system:
    - Chunk optimization
    - Embedding batching
    - Context compression
    - Memory management
    """
    
    def __init__(self):
        self.processing_stages = []
        self.optimization_cache = {}
        
    def optimize_chunks(self, chunks: List[Dict[str, Any]], target_size: int = 1000) -> List[Dict[str, Any]]:
        """Optimize chunks for better processing"""
        start_time = time.time()
        
        optimized_chunks = []
        current_chunk = {"text": "", "meta": {"doc": "", "chunk": 0}}
        
        for chunk in chunks:
            chunk_text = chunk.get("text", "").strip()
            if not chunk_text:
                continue
            
            # If adding this chunk would exceed target size, finalize current chunk
            if len(current_chunk["text"]) + len(chunk_text) > target_size and current_chunk["text"]:
                optimized_chunks.append(current_chunk)
                current_chunk = {"text": "", "meta": {"doc": "", "chunk": 0}}
            
            # Add to current chunk
            if not current_chunk["text"]:
                current_chunk["meta"] = chunk.get("meta", {})
                current_chunk["text"] = chunk_text
            else:
                current_chunk["text"] += " " + chunk_text
        
        # Add final chunk
        if current_chunk["text"]:
            optimized_chunks.append(current_chunk)
        
        end_time = time.time()
        self._record_stage("chunk_optimization", start_time, end_time, 
                          len(chunks), len(optimized_chunks), "size_optimization")
        
        logger.info(f"Chunk optimization: {len(chunks)} -> {len(optimized_chunks)} chunks")
        return optimized_chunks
    
    def batch_embeddings(self, texts: List[str], batch_size: int = 32) -> List[List[str]]:
        """Batch texts for efficient embedding processing"""
        start_time = time.time()
        
        batches = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batches.append(batch)
        
        end_time = time.time()
        self._record_stage("embedding_batching", start_time, end_time, 
                          len(texts), len(batches), f"batch_size_{batch_size}")
        
        return batches
    
    def compress_context(self, context: str, max_length: int = 4000) -> str:
        """Intelligently compress context while preserving important information"""
        start_time = time.time()
        
        if len(context) <= max_length:
            return context
        
        # Split into sentences
        sentences = context.split('. ')
        if len(sentences) <= 1:
            # If no sentence breaks, truncate
            return context[:max_length] + "..."
        
        # Score sentences by importance (simple heuristic)
        sentence_scores = []
        for sentence in sentences:
            score = 0
            # Longer sentences often more informative
            score += len(sentence.split()) * 0.1
            # Sentences with numbers, dates, or specific terms
            if any(char.isdigit() for char in sentence):
                score += 2
            # Sentences with proper nouns (capitalized words)
            proper_nouns = sum(1 for word in sentence.split() if word[0].isupper() and len(word) > 1)
            score += proper_nouns * 0.5
            sentence_scores.append((score, sentence))
        
        # Sort by importance
        sentence_scores.sort(key=lambda x: x[0], reverse=True)
        
        # Build compressed context
        compressed = ""
        for score, sentence in sentence_scores:
            if len(compressed) + len(sentence) + 2 <= max_length:
                compressed += sentence + ". "
            else:
                break
        
        # Ensure we have something
        if not compressed.strip():
            compressed = context[:max_length] + "..."
        
        end_time = time.time()
        self._record_stage("context_compression", start_time, end_time, 
                          len(context), len(compressed), f"max_length_{max_length}")
        
        return compressed.strip()
    
    def optimize_retrieval(self, question: str, chunks: List[Dict], k: int = 5) -> List[Dict]:
        """Optimize chunk retrieval for better relevance"""
        start_time = time.time()
        
        if len(chunks) <= k:
            return chunks
        
        # Simple relevance scoring
        question_words = set(question.lower().split())
        chunk_scores = []
        
        for chunk in chunks:
            chunk_text = chunk.get("text", "").lower()
            chunk_words = set(chunk_text.split())
            
            # Calculate overlap
            overlap = len(question_words & chunk_words)
            # Normalize by question length
            relevance = overlap / max(len(question_words), 1)
            
            # Boost score for chunks with question words at the beginning
            if chunk_text.startswith(tuple(question_words)):
                relevance += 0.2
            
            chunk_scores.append((relevance, chunk))
        
        # Sort by relevance and take top k
        chunk_scores.sort(key=lambda x: x[0], reverse=True)
        optimized_chunks = [chunk for score, chunk in chunk_scores[:k]]
        
        end_time = time.time()
        self._record_stage("retrieval_optimization", start_time, end_time, 
                          len(chunks), len(optimized_chunks), f"top_{k}")
        
        return optimized_chunks
    
    def _record_stage(self, name: str, start: float, end: float, 
                     input_size: int, output_size: int, optimization: str):
        """Record processing stage for analysis"""
        stage = ProcessingStage(
            name=name,
            start_time=start,
            end_time=end,
            input_size=input_size,
            output_size=output_size,
            optimization_applied=optimization
        )
        self.processing_stages.append(stage)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary of all stages"""
        if not self.processing_stages:
            return {"message": "No processing stages recorded"}
        
        total_time = sum(stage.duration for stage in self.processing_stages)
        avg_compression = sum(stage.compression_ratio for stage in self.processing_stages) / len(self.processing_stages)
        
        return {
            "total_processing_time": total_time,
            "stages_count": len(self.processing_stages),
            "average_compression_ratio": avg_compression,
            "stages": [
                {
                    "name": stage.name,
                    "duration": stage.duration,
                    "compression_ratio": stage.compression_ratio,
                    "optimization": stage.optimization_applied
                }
                for stage in self.processing_stages
            ]
        }
    
    def clear_history(self):
        """Clear processing history"""
        self.processing_stages.clear()

# Global optimizer instance
data_optimizer = DataFlowOptimizer()
