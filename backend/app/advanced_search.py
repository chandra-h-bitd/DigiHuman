"""
Advanced Search System
Implements hybrid search (semantic + keyword) with advanced filtering
"""

import asyncio
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, 
    MatchValue, MatchText, Range, GeoRadius, GeoBoundingBox
)
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    text: str
    score: float
    document_id: str
    chunk_index: int
    metadata: Dict[str, Any]
    search_type: str  # 'semantic', 'keyword', 'hybrid'

@dataclass
class SearchFilters:
    document_ids: Optional[List[str]] = None
    date_range: Optional[Tuple[str, str]] = None
    file_types: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    min_score: float = 0.3
    max_results: int = 10

class AdvancedSearchEngine:
    def __init__(self, qdrant_client: QdrantClient, embedder: SentenceTransformer):
        self.qdrant = qdrant_client
        self.embedder = embedder
        self.keyword_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
    async def hybrid_search(
        self, 
        query: str, 
        session_id: str,
        filters: SearchFilters = None,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining semantic and keyword search
        """
        if filters is None:
            filters = SearchFilters()
        
        collection_name = f"doc_chunks_{session_id}"
        
        # Perform both searches in parallel
        semantic_task = asyncio.create_task(
            self._semantic_search(query, collection_name, filters)
        )
        keyword_task = asyncio.create_task(
            self._keyword_search(query, collection_name, filters)
        )
        
        semantic_results, keyword_results = await asyncio.gather(
            semantic_task, keyword_task, return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(semantic_results, Exception):
            logger.error(f"Semantic search failed: {semantic_results}")
            semantic_results = []
        if isinstance(keyword_results, Exception):
            logger.error(f"Keyword search failed: {keyword_results}")
            keyword_results = []
        
        # Combine and rank results
        combined_results = self._combine_search_results(
            semantic_results, keyword_results, semantic_weight, keyword_weight
        )
        
        # Apply final filters and limit
        final_results = self._apply_final_filters(combined_results, filters)
        
        logger.info(f"✅ Hybrid search returned {len(final_results)} results for query: {query[:50]}...")
        return final_results
    
    async def _semantic_search(
        self, 
        query: str, 
        collection_name: str, 
        filters: SearchFilters
    ) -> List[SearchResult]:
        """Perform semantic vector search"""
        try:
            # Generate query embedding
            query_embedding = self.embedder.encode([query])[0].tolist()
            
            # Build Qdrant filter
            qdrant_filter = self._build_qdrant_filter(filters)
            
            # Perform search
            search_results = self.qdrant.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=filters.max_results * 2,  # Get more for filtering
                query_filter=qdrant_filter,
                with_payload=True,
                with_vectors=False,
                score_threshold=filters.min_score
            )
            
            results = []
            for result in search_results:
                if result.score >= filters.min_score:
                    search_result = SearchResult(
                        text=result.payload.get("text", ""),
                        score=result.score,
                        document_id=result.payload.get("document_id", ""),
                        chunk_index=result.payload.get("chunk_index", 0),
                        metadata=result.payload.get("metadata", {}),
                        search_type="semantic"
                    )
                    results.append(search_result)
            
            return results
            
        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return []
    
    async def _keyword_search(
        self, 
        query: str, 
        collection_name: str, 
        filters: SearchFilters
    ) -> List[SearchResult]:
        """Perform keyword-based search using Qdrant's text matching"""
        try:
            # Extract keywords from query
            keywords = self._extract_keywords(query)
            if not keywords:
                return []
            
            # Build keyword filter
            keyword_conditions = []
            for keyword in keywords:
                keyword_conditions.append(
                    FieldCondition(
                        key="text",
                        match=MatchText(text=keyword)
                    )
                )
            
            # Combine with other filters
            qdrant_filter = self._build_qdrant_filter(filters)
            if keyword_conditions:
                if qdrant_filter:
                    qdrant_filter.must.extend(keyword_conditions)
                else:
                    qdrant_filter = Filter(must=keyword_conditions)
            
            # Perform search with dummy vector (we're using filters)
            dummy_vector = [0.0] * 384  # Assuming 384-dimensional embeddings
            
            search_results = self.qdrant.search(
                collection_name=collection_name,
                query_vector=dummy_vector,
                limit=filters.max_results * 2,
                query_filter=qdrant_filter,
                with_payload=True,
                with_vectors=False,
                score_threshold=0.1  # Lower threshold for keyword search
            )
            
            results = []
            for result in search_results:
                # Calculate keyword relevance score
                keyword_score = self._calculate_keyword_score(
                    result.payload.get("text", ""), keywords
                )
                
                if keyword_score >= filters.min_score:
                    search_result = SearchResult(
                        text=result.payload.get("text", ""),
                        score=keyword_score,
                        document_id=result.payload.get("document_id", ""),
                        chunk_index=result.payload.get("chunk_index", 0),
                        metadata=result.payload.get("metadata", {}),
                        search_type="keyword"
                    )
                    results.append(search_result)
            
            return results
            
        except Exception as e:
            logger.error(f"Keyword search error: {e}")
            return []
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract meaningful keywords from query"""
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'what', 'when', 'where', 'why', 'how', 'who', 'which', 'that', 'this'
        }
        
        # Clean and tokenize
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return keywords[:10]  # Limit to top 10 keywords
    
    def _calculate_keyword_score(self, text: str, keywords: List[str]) -> float:
        """Calculate keyword relevance score"""
        text_lower = text.lower()
        total_score = 0.0
        
        for keyword in keywords:
            # Count occurrences
            count = text_lower.count(keyword)
            if count > 0:
                # Score based on frequency and position
                score = count * 0.1
                if text_lower.startswith(keyword):
                    score += 0.2  # Bonus for keyword at start
                total_score += score
        
        # Normalize score
        return min(total_score, 1.0)
    
    def _combine_search_results(
        self, 
        semantic_results: List[SearchResult], 
        keyword_results: List[SearchResult],
        semantic_weight: float,
        keyword_weight: float
    ) -> List[SearchResult]:
        """Combine and re-rank search results"""
        # Create a map of results by unique identifier
        result_map = {}
        
        # Add semantic results
        for result in semantic_results:
            key = f"{result.document_id}_{result.chunk_index}"
            result_map[key] = result
            result.score *= semantic_weight
        
        # Add or combine keyword results
        for result in keyword_results:
            key = f"{result.document_id}_{result.chunk_index}"
            if key in result_map:
                # Combine scores
                result_map[key].score += result.score * keyword_weight
                result_map[key].search_type = "hybrid"
            else:
                result.score *= keyword_weight
                result_map[key] = result
        
        # Convert back to list and sort by score
        combined_results = list(result_map.values())
        combined_results.sort(key=lambda x: x.score, reverse=True)
        
        return combined_results
    
    def _apply_final_filters(self, results: List[SearchResult], filters: SearchFilters) -> List[SearchResult]:
        """Apply final filtering and limiting"""
        filtered_results = []
        
        for result in results:
            # Apply document ID filter
            if filters.document_ids and result.document_id not in filters.document_ids:
                continue
            
            # Apply file type filter
            if filters.file_types:
                file_type = result.metadata.get("file_type", "").lower()
                if file_type not in [ft.lower() for ft in filters.file_types]:
                    continue
            
            # Apply tags filter
            if filters.tags:
                result_tags = result.metadata.get("tags", [])
                if not any(tag in result_tags for tag in filters.tags):
                    continue
            
            # Apply score threshold
            if result.score >= filters.min_score:
                filtered_results.append(result)
        
        # Limit results
        return filtered_results[:filters.max_results]
    
    def _build_qdrant_filter(self, filters: SearchFilters) -> Optional[Filter]:
        """Build Qdrant filter from search filters"""
        conditions = []
        
        # Document ID filter
        if filters.document_ids:
            conditions.append(
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=filters.document_ids[0])  # Qdrant limitation
                )
            )
        
        # Date range filter
        if filters.date_range:
            start_date, end_date = filters.date_range
            conditions.append(
                FieldCondition(
                    key="uploaded_at",
                    range=Range(gte=start_date, lte=end_date)
                )
            )
        
        # File type filter
        if filters.file_types:
            conditions.append(
                FieldCondition(
                    key="metadata.file_type",
                    match=MatchValue(value=filters.file_types[0])
                )
            )
        
        # Tags filter
        if filters.tags:
            conditions.append(
                FieldCondition(
                    key="metadata.tags",
                    match=MatchValue(value=filters.tags[0])
                )
            )
        
        return Filter(must=conditions) if conditions else None
    
    async def get_search_suggestions(self, query: str, session_id: str, limit: int = 5) -> List[str]:
        """Get search suggestions based on existing content"""
        try:
            collection_name = f"doc_chunks_{session_id}"
            
            # Get some random samples from the collection
            scroll_result = self.qdrant.scroll(
                collection_name=collection_name,
                limit=100,
                with_payload=True
            )
            
            # Extract common terms
            all_text = " ".join([point.payload.get("text", "") for point in scroll_result[0]])
            words = re.findall(r'\b\w+\b', all_text.lower())
            
            # Count word frequencies
            word_freq = {}
            for word in words:
                if len(word) > 3:  # Only meaningful words
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # Get top words that match query
            query_words = set(self._extract_keywords(query))
            suggestions = []
            
            for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True):
                if word not in query_words and len(suggestions) < limit:
                    suggestions.append(word)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Search suggestions error: {e}")
            return []
    
    async def get_search_analytics(self, session_id: str) -> Dict[str, Any]:
        """Get search analytics for a session"""
        try:
            collection_name = f"doc_chunks_{session_id}"
            
            # Get collection info
            collection_info = self.qdrant.get_collection(collection_name)
            
            # Get some sample data for analysis
            scroll_result = self.qdrant.scroll(
                collection_name=collection_name,
                limit=1000,
                with_payload=True
            )
            
            points = scroll_result[0]
            if not points:
                return {"error": "No data found"}
            
            # Analyze content
            all_text = " ".join([point.payload.get("text", "") for point in points])
            words = re.findall(r'\b\w+\b', all_text.lower())
            
            # Calculate statistics
            word_count = len(words)
            unique_words = len(set(words))
            avg_chunk_length = sum(len(point.payload.get("text", "")) for point in points) / len(points)
            
            # Most common terms
            word_freq = {}
            for word in words:
                if len(word) > 3:
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            top_terms = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "total_chunks": len(points),
                "total_words": word_count,
                "unique_words": unique_words,
                "avg_chunk_length": round(avg_chunk_length, 2),
                "top_terms": [{"term": term, "count": count} for term, count in top_terms],
                "collection_size": collection_info.points_count,
                "vector_size": collection_info.config.params.vectors.size
            }
            
        except Exception as e:
            logger.error(f"Search analytics error: {e}")
            return {"error": str(e)}
