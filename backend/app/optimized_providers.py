"""
Optimized Provider Implementations for Gemini and OpenAI
"""
import asyncio
import logging
import time
import json
from typing import List, Optional, Dict, Any, Tuple, AsyncGenerator
import numpy as np
import aiohttp
import requests
from dataclasses import dataclass
from functools import lru_cache

logger = logging.getLogger(__name__)

@dataclass
class ProviderConfig:
    """Provider configuration with optimization settings"""
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 30.0
    batch_size: int = 100
    rate_limit_delay: float = 0.1
    connection_pool_size: int = 10
    enable_streaming: bool = True

class OptimizedGeminiProvider:
    """
    Optimized Gemini provider with:
    - Batch processing
    - Rate limiting
    - Retry logic
    - Connection pooling
    - Streaming support
    """
    
    def __init__(self, config: ProviderConfig = None):
        self.config = config or ProviderConfig()
        self.session = None
        self.rate_limiter = asyncio.Semaphore(10)  # Max 10 concurrent requests
        
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=self.config.connection_pool_size)
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def embed_batch(
        self, 
        texts: List[str], 
        api_key: str, 
        model_name: str = "models/text-embedding-004"
    ) -> Optional[np.ndarray]:
        """Optimized batch embedding with retry logic and rate limiting"""
        
        if not texts or not api_key:
            return None
            
        # Process in batches to avoid API limits
        all_embeddings = []
        batches = [texts[i:i + self.config.batch_size] for i in range(0, len(texts), self.config.batch_size)]
        
        for batch in batches:
            async with self.rate_limiter:
                embeddings = await self._embed_batch_with_retry(batch, api_key, model_name)
                if embeddings is not None:
                    all_embeddings.extend(embeddings)
                else:
                    logger.error(f"Failed to embed batch of {len(batch)} texts")
                    return None
                
                # Rate limiting delay
                await asyncio.sleep(self.config.rate_limit_delay)
        
        return np.vstack(all_embeddings) if all_embeddings else None
    
    async def _embed_batch_with_retry(
        self, 
        texts: List[str], 
        api_key: str, 
        model_name: str
    ) -> Optional[List[np.ndarray]]:
        """Embed batch with retry logic"""
        
        for attempt in range(self.config.max_retries):
            try:
                return await self._embed_batch_single(texts, api_key, model_name)
            except Exception as e:
                logger.warning(f"Gemini embed attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    logger.error(f"All Gemini embed attempts failed for batch of {len(texts)} texts")
                    return None
    
    async def _embed_batch_single(
        self, 
        texts: List[str], 
        api_key: str, 
        model_name: str
    ) -> List[np.ndarray]:
        """Single batch embedding request"""
        
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:embedContent?key={api_key}"
        
        # Process texts in parallel for better performance
        tasks = []
        for text in texts:
            payload = {
                "model": model_name,
                "content": {"parts": [{"text": text}]}
            }
            tasks.append(self._make_request(url, payload))
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        embeddings = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.error(f"Request failed for text {i}: {response}")
                raise response
            
            if response.get("embedding", {}).get("values"):
                vec = np.array(response["embedding"]["values"], dtype=np.float32)
                embeddings.append(vec)
            else:
                logger.error(f"No embedding values in response for text {i}")
                raise ValueError("No embedding values in response")
        
        return embeddings
    
    async def _make_request(self, url: str, payload: Dict) -> Dict:
        """Make HTTP request with proper error handling"""
        
        async with self.session.post(url, json=payload) as response:
            if response.status == 429:  # Rate limited
                retry_after = float(response.headers.get('Retry-After', 1))
                await asyncio.sleep(retry_after)
                raise aiohttp.ClientError("Rate limited")
            
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Gemini API error {response.status}: {error_text[:200]}")
                raise aiohttp.ClientError(f"API error {response.status}")
            
            return await response.json()
    
    async def generate_stream(
        self, 
        prompt: str, 
        api_key: str, 
        model_name: str = "models/gemini-2.5-flash"
    ) -> AsyncGenerator[str, None]:
        """Streaming text generation"""
        
        if not self.config.enable_streaming:
            # Fallback to non-streaming
            result = await self.generate(prompt, api_key, model_name)
            if result:
                yield result
            return
        
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:streamGenerateContent?key={api_key}"
        
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2048,
            }
        }
        
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Gemini streaming error {response.status}: {error_text}")
                    return
                
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            if "candidates" in data and data["candidates"]:
                                content = data["candidates"][0].get("content", {})
                                parts = content.get("parts", [])
                                for part in parts:
                                    if "text" in part:
                                        yield part["text"]
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
    
    async def generate(
        self, 
        prompt: str, 
        api_key: str, 
        model_name: str = "models/gemini-2.5-flash"
    ) -> Optional[str]:
        """Non-streaming text generation with retry logic"""
        
        for attempt in range(self.config.max_retries):
            try:
                return await self._generate_single(prompt, api_key, model_name)
            except Exception as e:
                logger.warning(f"Gemini generate attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                else:
                    logger.error(f"All Gemini generate attempts failed")
                    return None
    
    async def _generate_single(
        self, 
        prompt: str, 
        api_key: str, 
        model_name: str
    ) -> Optional[str]:
        """Single generation request"""
        
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
        
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2048,
            }
        }
        
        async with self.session.post(url, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Gemini generate error {response.status}: {error_text}")
                raise aiohttp.ClientError(f"API error {response.status}")
            
            data = await response.json()
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                return "".join(part.get("text", "") for part in parts)
            
            return None

class OptimizedOpenAIProvider:
    """
    Optimized OpenAI provider with:
    - Batch processing
    - Rate limiting
    - Retry logic
    - Connection pooling
    - Streaming support
    """
    
    def __init__(self, config: ProviderConfig = None):
        self.config = config or ProviderConfig()
        self.session = None
        self.rate_limiter = asyncio.Semaphore(10)
        
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=self.config.connection_pool_size)
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def embed_batch(
        self, 
        texts: List[str], 
        api_key: str, 
        model_name: str = "text-embedding-3-small"
    ) -> Optional[np.ndarray]:
        """Optimized batch embedding with retry logic"""
        
        if not texts or not api_key:
            return None
        
        # OpenAI supports batch embedding in single request
        for attempt in range(self.config.max_retries):
            try:
                return await self._embed_batch_single(texts, api_key, model_name)
            except Exception as e:
                logger.warning(f"OpenAI embed attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                else:
                    logger.error(f"All OpenAI embed attempts failed")
                    return None
    
    async def _embed_batch_single(
        self, 
        texts: List[str], 
        api_key: str, 
        model_name: str
    ) -> np.ndarray:
        """Single batch embedding request"""
        
        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_name,
            "input": texts,  # OpenAI supports batch input
            "encoding_format": "float"
        }
        
        async with self.rate_limiter:
            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status == 429:  # Rate limited
                    retry_after = float(response.headers.get('Retry-After', 1))
                    await asyncio.sleep(retry_after)
                    raise aiohttp.ClientError("Rate limited")
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"OpenAI API error {response.status}: {error_text[:200]}")
                    raise aiohttp.ClientError(f"API error {response.status}")
                
                data = await response.json()
                embeddings = [item["embedding"] for item in data.get("data", [])]
                return np.array(embeddings, dtype=np.float32)
    
    async def generate_stream(
        self, 
        prompt: str, 
        api_key: str, 
        model_name: str = "gpt-4o-mini"
    ) -> AsyncGenerator[str, None]:
        """Streaming text generation"""
        
        if not self.config.enable_streaming:
            result = await self.generate(prompt, api_key, model_name)
            if result:
                yield result
            return
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "temperature": 0.2,
            "max_tokens": 2048
        }
        
        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"OpenAI streaming error {response.status}: {error_text}")
                    return
                
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            if data_str == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                choices = data.get('choices', [])
                                if choices:
                                    delta = choices[0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
    
    async def generate(
        self, 
        prompt: str, 
        api_key: str, 
        model_name: str = "gpt-4o-mini"
    ) -> Optional[str]:
        """Non-streaming text generation with retry logic"""
        
        for attempt in range(self.config.max_retries):
            try:
                return await self._generate_single(prompt, api_key, model_name)
            except Exception as e:
                logger.warning(f"OpenAI generate attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                else:
                    logger.error(f"All OpenAI generate attempts failed")
                    return None
    
    async def _generate_single(
        self, 
        prompt: str, 
        api_key: str, 
        model_name: str
    ) -> Optional[str]:
        """Single generation request"""
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 2048
        }
        
        async with self.session.post(url, json=payload, headers=headers) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"OpenAI generate error {response.status}: {error_text}")
                raise aiohttp.ClientError(f"API error {response.status}")
            
            data = await response.json()
            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                return message.get("content", "")
            
            return None

# Global provider instances
gemini_provider = OptimizedGeminiProvider()
openai_provider = OptimizedOpenAIProvider()
