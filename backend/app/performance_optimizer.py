"""
Advanced Performance Optimization System
Implements caching, connection pooling, and performance monitoring
"""

import asyncio
import time
import json
import psutil
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import redis
import asyncpg
from qdrant_client import QdrantClient
from pydantic import BaseModel
import logging
from functools import wraps
import threading
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    timestamp: datetime
    endpoint: str
    response_time_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    active_connections: int
    cache_hit_rate: float
    error_count: int

@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    total_requests: int = 0
    hit_rate: float = 0.0

class PerformanceOptimizer:
    def __init__(self, redis_client: redis.Redis, postgres_pool: asyncpg.Pool, qdrant_client: QdrantClient):
        self.redis = redis_client
        self.postgres = postgres_pool
        self.qdrant = qdrant_client
        
        # Performance tracking
        self.metrics_history = deque(maxlen=1000)
        self.cache_stats = CacheStats()
        self.endpoint_stats = defaultdict(lambda: {"count": 0, "total_time": 0, "errors": 0})
        
        # Connection pools
        self.connection_pools = {
            "redis": redis_client,
            "postgres": postgres_pool,
            "qdrant": qdrant_client
        }
        
        # Cache configuration
        self.cache_config = {
            "embeddings": {"ttl": 3600, "max_size": 10000},
            "search_results": {"ttl": 300, "max_size": 1000},
            "session_data": {"ttl": 1800, "max_size": 5000},
            "api_responses": {"ttl": 60, "max_size": 2000}
        }
        
        # Start monitoring
        self._start_monitoring()
    
    def _start_monitoring(self):
        """Start background monitoring tasks"""
        asyncio.create_task(self._monitor_system_health())
        asyncio.create_task(self._cleanup_expired_cache())
    
    async def _monitor_system_health(self):
        """Monitor system health metrics"""
        while True:
            try:
                # Collect system metrics
                memory = psutil.virtual_memory()
                cpu = psutil.cpu_percent()
                
                # Collect connection metrics
                active_connections = await self._get_active_connections()
                
                # Update cache stats
                self.cache_stats.hit_rate = (
                    self.cache_stats.hits / max(self.cache_stats.total_requests, 1)
                )
                
                # Store metrics
                metrics = PerformanceMetrics(
                    timestamp=datetime.now(timezone.utc),
                    endpoint="system_health",
                    response_time_ms=0,
                    memory_usage_mb=memory.used / 1024 / 1024,
                    cpu_usage_percent=cpu,
                    active_connections=active_connections,
                    cache_hit_rate=self.cache_stats.hit_rate,
                    error_count=sum(stats["errors"] for stats in self.endpoint_stats.values())
                )
                
                self.metrics_history.append(metrics)
                
                # Log if performance is degraded
                if cpu > 80 or memory.percent > 85:
                    logger.warning(f"High resource usage: CPU {cpu}%, Memory {memory.percent}%")
                
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_expired_cache(self):
        """Clean up expired cache entries"""
        while True:
            try:
                # Get all cache keys
                keys = await asyncio.get_event_loop().run_in_executor(
                    None, self.redis.keys, "cache:*"
                )
                
                # Check TTL for each key
                for key in keys:
                    ttl = await asyncio.get_event_loop().run_in_executor(
                        None, self.redis.ttl, key
                    )
                    if ttl == -1:  # No expiration set
                        await asyncio.get_event_loop().run_in_executor(
                            None, self.redis.delete, key
                        )
                
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                await asyncio.sleep(300)
    
    async def _get_active_connections(self) -> int:
        """Get number of active connections"""
        try:
            # Count Redis connections
            redis_info = await asyncio.get_event_loop().run_in_executor(
                None, self.redis.info, "clients"
            )
            redis_connections = redis_info.get("connected_clients", 0)
            
            # Count PostgreSQL connections
            async with self.postgres.acquire() as conn:
                postgres_connections = await conn.fetchval(
                    "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
                )
            
            return redis_connections + postgres_connections
            
        except Exception as e:
            logger.error(f"Connection counting error: {e}")
            return 0
    
    def cache_result(self, cache_type: str, key: str, data: Any, ttl: Optional[int] = None):
        """Cache a result with automatic TTL"""
        try:
            cache_config = self.cache_config.get(cache_type, {"ttl": 300, "max_size": 1000})
            cache_ttl = ttl or cache_config["ttl"]
            
            cache_key = f"cache:{cache_type}:{key}"
            serialized_data = json.dumps(data, default=str)
            
            # Use Redis pipeline for efficiency
            pipe = self.redis.pipeline()
            pipe.set(cache_key, serialized_data, ex=cache_ttl)
            pipe.expire(cache_key, cache_ttl)
            pipe.execute()
            
        except Exception as e:
            logger.error(f"Cache write error: {e}")
    
    async def get_cached_result(self, cache_type: str, key: str) -> Optional[Any]:
        """Get a cached result"""
        try:
            cache_key = f"cache:{cache_type}:{key}"
            
            cached_data = await asyncio.get_event_loop().run_in_executor(
                None, self.redis.get, cache_key
            )
            
            if cached_data:
                self.cache_stats.hits += 1
                self.cache_stats.total_requests += 1
                return json.loads(cached_data)
            else:
                self.cache_stats.misses += 1
                self.cache_stats.total_requests += 1
                return None
                
        except Exception as e:
            logger.error(f"Cache read error: {e}")
            self.cache_stats.misses += 1
            self.cache_stats.total_requests += 1
            return None
    
    def performance_monitor(self, endpoint_name: str):
        """Decorator to monitor endpoint performance"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                start_memory = psutil.virtual_memory().used
                
                try:
                    result = await func(*args, **kwargs)
                    
                    # Record success metrics
                    end_time = time.time()
                    end_memory = psutil.virtual_memory().used
                    
                    response_time = (end_time - start_time) * 1000
                    memory_delta = (end_memory - start_memory) / 1024 / 1024
                    
                    # Update endpoint stats
                    self.endpoint_stats[endpoint_name]["count"] += 1
                    self.endpoint_stats[endpoint_name]["total_time"] += response_time
                    
                    # Store metrics
                    metrics = PerformanceMetrics(
                        timestamp=datetime.now(timezone.utc),
                        endpoint=endpoint_name,
                        response_time_ms=response_time,
                        memory_usage_mb=memory_delta,
                        cpu_usage_percent=psutil.cpu_percent(),
                        active_connections=await self._get_active_connections(),
                        cache_hit_rate=self.cache_stats.hit_rate,
                        error_count=0
                    )
                    
                    self.metrics_history.append(metrics)
                    
                    # Log slow requests
                    if response_time > 1000:  # > 1 second
                        logger.warning(f"Slow request: {endpoint_name} took {response_time:.2f}ms")
                    
                    return result
                    
                except Exception as e:
                    # Record error metrics
                    self.endpoint_stats[endpoint_name]["errors"] += 1
                    
                    metrics = PerformanceMetrics(
                        timestamp=datetime.now(timezone.utc),
                        endpoint=endpoint_name,
                        response_time_ms=(time.time() - start_time) * 1000,
                        memory_usage_mb=0,
                        cpu_usage_percent=psutil.cpu_percent(),
                        active_connections=await self._get_active_connections(),
                        cache_hit_rate=self.cache_stats.hit_rate,
                        error_count=1
                    )
                    
                    self.metrics_history.append(metrics)
                    raise
                    
            return wrapper
        return decorator
    
    async def get_performance_metrics(self, endpoint: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get performance metrics"""
        metrics = list(self.metrics_history)
        
        if endpoint:
            metrics = [m for m in metrics if m.endpoint == endpoint]
        
        # Convert to dict and limit
        return [asdict(m) for m in metrics[-limit:]]
    
    async def get_endpoint_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get endpoint performance statistics"""
        stats = {}
        
        for endpoint, data in self.endpoint_stats.items():
            if data["count"] > 0:
                avg_time = data["total_time"] / data["count"]
                error_rate = data["errors"] / data["count"]
                
                stats[endpoint] = {
                    "total_requests": data["count"],
                    "average_response_time_ms": round(avg_time, 2),
                    "error_count": data["errors"],
                    "error_rate": round(error_rate * 100, 2)
                }
        
        return stats
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        return {
            "hits": self.cache_stats.hits,
            "misses": self.cache_stats.misses,
            "total_requests": self.cache_stats.total_requests,
            "hit_rate": round(self.cache_stats.hit_rate * 100, 2)
        }
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status"""
        try:
            # System metrics
            memory = psutil.virtual_memory()
            cpu = psutil.cpu_percent()
            disk = psutil.disk_usage('/')
            
            # Connection metrics
            active_connections = await self._get_active_connections()
            
            # Recent performance
            recent_metrics = list(self.metrics_history)[-10:]
            avg_response_time = sum(m.response_time_ms for m in recent_metrics) / max(len(recent_metrics), 1)
            
            # Health status
            health_status = "healthy"
            if cpu > 80 or memory.percent > 85 or avg_response_time > 2000:
                health_status = "degraded"
            if cpu > 95 or memory.percent > 95 or avg_response_time > 5000:
                health_status = "critical"
            
            return {
                "status": health_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "system": {
                    "cpu_percent": cpu,
                    "memory_percent": memory.percent,
                    "memory_used_mb": round(memory.used / 1024 / 1024, 2),
                    "disk_percent": disk.percent,
                    "disk_free_gb": round(disk.free / 1024 / 1024 / 1024, 2)
                },
                "connections": {
                    "active": active_connections,
                    "max_postgres": 200,  # From docker-compose
                    "max_redis": 1000
                },
                "performance": {
                    "avg_response_time_ms": round(avg_response_time, 2),
                    "cache_hit_rate": round(self.cache_stats.hit_rate * 100, 2),
                    "total_requests": sum(stats["count"] for stats in self.endpoint_stats.values())
                }
            }
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def optimize_connections(self):
        """Optimize database connections"""
        try:
            # PostgreSQL optimization
            async with self.postgres.acquire() as conn:
                await conn.execute("""
                    -- Update statistics
                    ANALYZE;
                    
                    -- Vacuum if needed
                    VACUUM ANALYZE;
                """)
            
            # Redis optimization
            await asyncio.get_event_loop().run_in_executor(
                None, self.redis.bgrewriteaof
            )
            
            logger.info("✅ Connection optimization completed")
            
        except Exception as e:
            logger.error(f"Connection optimization error: {e}")
    
    async def clear_cache(self, cache_type: Optional[str] = None):
        """Clear cache entries"""
        try:
            if cache_type:
                pattern = f"cache:{cache_type}:*"
            else:
                pattern = "cache:*"
            
            keys = await asyncio.get_event_loop().run_in_executor(
                None, self.redis.keys, pattern
            )
            
            if keys:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.redis.delete, *keys
                )
            
            logger.info(f"✅ Cleared cache: {len(keys)} entries")
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
    
    async def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get performance optimization recommendations"""
        recommendations = []
        
        try:
            # Check cache hit rate
            if self.cache_stats.hit_rate < 0.7:
                recommendations.append({
                    "type": "cache",
                    "priority": "high",
                    "message": f"Low cache hit rate: {self.cache_stats.hit_rate:.2%}",
                    "suggestion": "Consider increasing cache TTL or improving cache keys"
                })
            
            # Check response times
            recent_metrics = list(self.metrics_history)[-50:]
            if recent_metrics:
                avg_response_time = sum(m.response_time_ms for m in recent_metrics) / len(recent_metrics)
                if avg_response_time > 1000:
                    recommendations.append({
                        "type": "performance",
                        "priority": "medium",
                        "message": f"High average response time: {avg_response_time:.2f}ms",
                        "suggestion": "Consider optimizing database queries or adding more caching"
                    })
            
            # Check error rates
            total_requests = sum(stats["count"] for stats in self.endpoint_stats.values())
            total_errors = sum(stats["errors"] for stats in self.endpoint_stats.values())
            if total_requests > 0:
                error_rate = total_errors / total_requests
                if error_rate > 0.05:  # 5% error rate
                    recommendations.append({
                        "type": "reliability",
                        "priority": "high",
                        "message": f"High error rate: {error_rate:.2%}",
                        "suggestion": "Investigate and fix error sources"
                    })
            
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 80:
                recommendations.append({
                    "type": "resources",
                    "priority": "medium",
                    "message": f"High memory usage: {memory.percent:.1f}%",
                    "suggestion": "Consider increasing memory or optimizing memory usage"
                })
            
        except Exception as e:
            logger.error(f"Recommendations error: {e}")
            recommendations.append({
                "type": "system",
                "priority": "low",
                "message": f"Could not generate recommendations: {e}",
                "suggestion": "Check system logs for issues"
            })
        
        return recommendations
