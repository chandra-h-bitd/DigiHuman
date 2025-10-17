"""
Optimized Fallback System with Intelligent Model Selection and Enhanced Local LLM
"""
import asyncio
import logging
import time
import json
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import numpy as np
from functools import lru_cache

logger = logging.getLogger(__name__)

@dataclass
class ModelCapability:
    """Model capability assessment"""
    embedding_quality: float  # 0-1 score
    generation_quality: float  # 0-1 score
    speed: float  # tokens/second
    cost_per_token: float  # relative cost
    context_length: int
    supports_streaming: bool = False

@dataclass
class ContextualInfo:
    """Enhanced context for better model selection"""
    document_type: str  # "pdf", "docx", "technical", "legal", etc.
    content_length: int
    question_complexity: float  # 0-1 score
    requires_citations: bool
    language: str = "en"
    domain: str = "general"  # "medical", "legal", "technical", etc.

class OptimizedFallbackManager:
    """
    Intelligent fallback system with:
    - Context-aware model selection
    - Enhanced local LLM optimization
    - Smart data flow optimization
    - Performance-based routing
    """
    
    def __init__(self):
        self.model_capabilities = self._initialize_model_capabilities()
        self.performance_history = {}
        self.context_cache = {}
        
    def _initialize_model_capabilities(self) -> Dict[str, ModelCapability]:
        """Initialize model capability matrix"""
        return {
            # Cloud Providers
            "gemini-2.5-flash": ModelCapability(
                embedding_quality=0.95, generation_quality=0.90, speed=50.0,
                cost_per_token=0.001, context_length=1000000, supports_streaming=True
            ),
            "gemini-1.5-pro": ModelCapability(
                embedding_quality=0.98, generation_quality=0.95, speed=30.0,
                cost_per_token=0.002, context_length=2000000, supports_streaming=True
            ),
            "gpt-4o": ModelCapability(
                embedding_quality=0.97, generation_quality=0.96, speed=40.0,
                cost_per_token=0.003, context_length=128000, supports_streaming=True
            ),
            "gpt-4o-mini": ModelCapability(
                embedding_quality=0.92, generation_quality=0.88, speed=60.0,
                cost_per_token=0.0005, context_length=128000, supports_streaming=True
            ),
            
            # Local Models
            "orca-mini-3b": ModelCapability(
                embedding_quality=0.0, generation_quality=0.65, speed=15.0,
                cost_per_token=0.0, context_length=2048, supports_streaming=False
            ),
            "llama-2-7b": ModelCapability(
                embedding_quality=0.0, generation_quality=0.75, speed=12.0,
                cost_per_token=0.0, context_length=4096, supports_streaming=False
            ),
            
            # Embedding Models
            "text-embedding-004": ModelCapability(
                embedding_quality=0.98, generation_quality=0.0, speed=100.0,
                cost_per_token=0.0001, context_length=2048, supports_streaming=False
            ),
            "text-embedding-3-small": ModelCapability(
                embedding_quality=0.95, generation_quality=0.0, speed=120.0,
                cost_per_token=0.00005, context_length=8191, supports_streaming=False
            ),
            "sbert-all-MiniLM-L6-v2": ModelCapability(
                embedding_quality=0.80, generation_quality=0.0, speed=200.0,
                cost_per_token=0.0, context_length=256, supports_streaming=False
            )
        }
    
    def analyze_context(self, question: str, chunks: List[Dict], document_info: Dict) -> ContextualInfo:
        """Analyze context to determine optimal model selection"""
        
        # Analyze question complexity
        question_complexity = self._analyze_question_complexity(question)
        
        # Determine document type and domain
        document_type = document_info.get("type", "general")
        domain = self._detect_domain(chunks, question)
        
        # Check if citations are needed
        requires_citations = any(word in question.lower() for word in 
                               ["cite", "source", "reference", "where", "which document"])
        
        return ContextualInfo(
            document_type=document_type,
            content_length=sum(len(c.get("text", "")) for c in chunks),
            question_complexity=question_complexity,
            requires_citations=requires_citations,
            domain=domain
        )
    
    def _analyze_question_complexity(self, question: str) -> float:
        """Analyze question complexity (0-1 scale)"""
        complexity_indicators = [
            len(question.split()) > 20,  # Long questions
            "?" in question and question.count("?") > 1,  # Multiple questions
            any(word in question.lower() for word in ["analyze", "compare", "explain", "summarize"]),
            any(word in question.lower() for word in ["why", "how", "what if"]),
            len([w for w in question.split() if len(w) > 8]) > 3  # Complex words
        ]
        return sum(complexity_indicators) / len(complexity_indicators)
    
    def _detect_domain(self, chunks: List[Dict], question: str) -> str:
        """Detect document domain based on content"""
        text = " ".join([c.get("text", "") for c in chunks[:5]]) + " " + question
        
        domain_keywords = {
            "medical": ["patient", "diagnosis", "treatment", "symptoms", "medical", "health"],
            "legal": ["contract", "agreement", "clause", "legal", "court", "law"],
            "technical": ["api", "code", "function", "system", "technical", "implementation"],
            "financial": ["revenue", "profit", "cost", "budget", "financial", "investment"],
            "academic": ["research", "study", "analysis", "methodology", "academic", "paper"]
        }
        
        text_lower = text.lower()
        domain_scores = {domain: sum(1 for keyword in keywords if keyword in text_lower) 
                        for domain, keywords in domain_keywords.items()}
        
        return max(domain_scores, key=domain_scores.get) if max(domain_scores.values()) > 0 else "general"
    
    def select_optimal_models(self, context: ContextualInfo, available_providers: List[str]) -> Dict[str, str]:
        """Select optimal models based on context and capabilities"""
        
        # Score each available model
        model_scores = {}
        
        for provider in available_providers:
            if provider == "gemini":
                # Choose between Gemini models based on complexity
                if context.question_complexity > 0.7 or context.content_length > 50000:
                    model = "gemini-1.5-pro"
                else:
                    model = "gemini-2.5-flash"
                    
            elif provider == "openai":
                # Choose between OpenAI models based on complexity
                if context.question_complexity > 0.8 or context.requires_citations:
                    model = "gpt-4o"
                else:
                    model = "gpt-4o-mini"
                    
            elif provider == "local":
                # Choose best local model available
                model = "orca-mini-3b"  # Default, could be enhanced with model detection
                
            else:
                continue
            
            # Calculate score based on context requirements
            capability = self.model_capabilities.get(model)
            if not capability:
                continue
                
            score = self._calculate_model_score(capability, context)
            model_scores[provider] = (model, score)
        
        # Select best models for embedding and generation
        best_embedding = max([(p, m, s) for p, (m, s) in model_scores.items() 
                            if self.model_capabilities.get(m).embedding_quality > 0], 
                           key=lambda x: x[2])
        
        best_generation = max([(p, m, s) for p, (m, s) in model_scores.items() 
                             if self.model_capabilities.get(m).generation_quality > 0], 
                            key=lambda x: x[2])
        
        return {
            "embedding": {"provider": best_embedding[0], "model": best_embedding[1]},
            "generation": {"provider": best_generation[0], "model": best_generation[1]}
        }
    
    def _calculate_model_score(self, capability: ModelCapability, context: ContextualInfo) -> float:
        """Calculate model score based on context requirements"""
        
        # Base scores
        embedding_score = capability.embedding_quality * 0.3
        generation_score = capability.generation_quality * 0.4
        speed_score = min(capability.speed / 100.0, 1.0) * 0.1
        cost_score = max(0, 1.0 - capability.cost_per_token * 1000) * 0.1
        
        # Context adjustments
        context_score = 0.1
        if context.content_length <= capability.context_length:
            context_score = 1.0
        elif context.content_length <= capability.context_length * 0.8:
            context_score = 0.8
        
        return embedding_score + generation_score + speed_score + cost_score + context_score

# Enhanced Local LLM with Better Context Handling
class EnhancedLocalLLM:
    """
    Enhanced local LLM with:
    - Better prompt engineering
    - Context optimization
    - Multi-step reasoning
    - Citation handling
    """
    
    def __init__(self, model_name: str = "orca-mini-3b"):
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the local model"""
        try:
            from gpt4all import GPT4All
            self.model = GPT4All(self.model_name)
            logger.info(f"Enhanced local LLM loaded: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load local LLM: {e}")
            self.model = None
    
    def generate_enhanced_answer(
        self, 
        question: str, 
        chunks: List[Dict[str, Any]], 
        context_info: ContextualInfo
    ) -> Optional[str]:
        """Generate enhanced answer with better context handling"""
        
        if not self.model:
            return None
        
        # Optimize context based on question type
        optimized_context = self._optimize_context(question, chunks, context_info)
        
        # Create enhanced prompt
        prompt = self._create_enhanced_prompt(question, optimized_context, context_info)
        
        try:
            with self.model.chat_session():
                # Use different parameters based on question complexity
                if context_info.question_complexity > 0.7:
                    # More tokens for complex questions
                    response = self.model.generate(
                        prompt, 
                        max_tokens=1024, 
                        temp=0.1,  # Lower temperature for consistency
                        top_p=0.9,
                        repeat_penalty=1.1
                    )
                else:
                    # Standard parameters
                    response = self.model.generate(
                        prompt, 
                        max_tokens=512, 
                        temp=0.2,
                        top_p=0.95
                    )
                
                return self._post_process_response(response, context_info)
                
        except Exception as e:
            logger.error(f"Enhanced local LLM generation failed: {e}")
            return None
    
    def _optimize_context(self, question: str, chunks: List[Dict], context_info: ContextualInfo) -> str:
        """Optimize context for better local LLM performance"""
        
        # Sort chunks by relevance to question
        question_words = set(question.lower().split())
        chunk_scores = []
        
        for chunk in chunks:
            chunk_text = chunk.get("text", "").lower()
            chunk_words = set(chunk_text.split())
            
            # Calculate relevance score
            word_overlap = len(question_words & chunk_words)
            chunk_length = len(chunk_text.split())
            relevance_score = word_overlap / max(len(question_words), 1) + (chunk_length / 100)
            
            chunk_scores.append((relevance_score, chunk))
        
        # Sort by relevance
        chunk_scores.sort(key=lambda x: x[0], reverse=True)
        
        # Build optimized context
        optimized_parts = []
        total_length = 0
        max_context = 4000  # Optimized for local LLM context window
        
        for score, chunk in chunk_scores:
            chunk_text = chunk.get("text", "").strip()
            if not chunk_text:
                continue
                
            # Truncate very long chunks
            if len(chunk_text) > 500:
                chunk_text = chunk_text[:500] + "..."
            
            source_info = f"[Source {len(optimized_parts)+1}]"
            formatted_chunk = f"{source_info} {chunk_text}\n"
            
            if total_length + len(formatted_chunk) > max_context:
                break
                
            optimized_parts.append(formatted_chunk)
            total_length += len(formatted_chunk)
        
        return "\n".join(optimized_parts)
    
    def _create_enhanced_prompt(self, question: str, context: str, context_info: ContextualInfo) -> str:
        """Create enhanced prompt based on context"""
        
        # Base system prompt
        if context_info.requires_citations:
            system_prompt = """You are a helpful assistant that answers questions based on provided context. 
IMPORTANT: Always cite your sources using [Source N] format. If you cannot find the answer in the context, say so clearly."""
        else:
            system_prompt = """You are a helpful assistant that answers questions based on provided context. 
Provide clear, concise answers. If the answer is not in the context, say so."""
        
        # Add domain-specific instructions
        if context_info.domain == "medical":
            system_prompt += "\n\nNote: This appears to be medical content. Be precise and cautious in your response."
        elif context_info.domain == "legal":
            system_prompt += "\n\nNote: This appears to be legal content. Be precise and cite specific clauses when possible."
        elif context_info.domain == "technical":
            system_prompt += "\n\nNote: This appears to be technical content. Be specific about implementation details."
        
        # Format the prompt
        prompt = f"""{system_prompt}

Context:
{context}

Question: {question}

Answer:"""
        
        return prompt
    
    def _post_process_response(self, response: str, context_info: ContextualInfo) -> str:
        """Post-process the response for better quality"""
        
        if not response:
            return "I couldn't generate a response."
        
        # Clean up the response
        response = response.strip()
        
        # Ensure citations are properly formatted
        if context_info.requires_citations and "[Source" not in response:
            response += "\n\nNote: This answer is based on the provided context."
        
        # Limit response length for local LLM
        if len(response) > 2000:
            response = response[:2000] + "..."
        
        return response

# Global instances
fallback_manager = OptimizedFallbackManager()
enhanced_local_llm = EnhancedLocalLLM()
