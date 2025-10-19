"""
Security Manager
Implements rate limiting, input validation, and security monitoring
"""

import asyncio
import time
import hashlib
import secrets
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import redis
import re
import logging
from collections import defaultdict, deque
import ipaddress
from pydantic import BaseModel

logger = logging.getLogger(__name__)

@dataclass
class SecurityEvent:
    timestamp: datetime
    event_type: str
    source_ip: str
    user_agent: str
    endpoint: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    details: Dict[str, Any]

@dataclass
class RateLimitRule:
    endpoint: str
    max_requests: int
    window_seconds: int
    block_duration: int = 300  # 5 minutes default

class SecurityManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.security_events = deque(maxlen=1000)
        
        # Rate limiting rules
        self.rate_limit_rules = {
            "/upload": RateLimitRule("/upload", 10, 60, 300),  # 10 uploads per minute
            "/ask": RateLimitRule("/ask", 30, 60, 180),        # 30 questions per minute
            "/validate": RateLimitRule("/validate", 20, 60, 120),  # 20 validations per minute
            "default": RateLimitRule("default", 100, 60, 60)   # 100 requests per minute
        }
        
        # Security patterns
        self.malicious_patterns = [
            r"<script[^>]*>.*?</script>",  # XSS
            r"javascript:",                # JavaScript injection
            r"on\w+\s*=",                 # Event handlers
            r"union\s+select",            # SQL injection
            r"drop\s+table",              # SQL injection
            r"exec\s*\(",                 # Command injection
            r"system\s*\(",               # Command injection
            r"\.\./",                     # Path traversal
            r"\.\.\\",                    # Path traversal
            r"eval\s*\(",                 # Code injection
        ]
        
        # IP whitelist/blacklist
        self.ip_whitelist = set()
        self.ip_blacklist = set()
        
        # Start security monitoring
        asyncio.create_task(self._monitor_security_events())
    
    async def _monitor_security_events(self):
        """Monitor security events and take actions"""
        while True:
            try:
                # Check for suspicious activity
                await self._check_suspicious_activity()
                
                # Clean up old rate limit data
                await self._cleanup_rate_limits()
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Security monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def check_rate_limit(self, client_ip: str, endpoint: str, user_agent: str = "") -> Tuple[bool, Dict[str, Any]]:
        """Check if request is within rate limits"""
        try:
            # Get rate limit rule
            rule = self.rate_limit_rules.get(endpoint, self.rate_limit_rules["default"])
            
            # Create rate limit key
            rate_key = f"rate_limit:{client_ip}:{endpoint}"
            
            # Get current count
            current_count = await asyncio.get_event_loop().run_in_executor(
                None, self.redis.get, rate_key
            )
            
            if current_count is None:
                # First request in window
                await asyncio.get_event_loop().run_in_executor(
                    None, self.redis.setex, rate_key, rule.window_seconds, 1
                )
                return True, {"remaining": rule.max_requests - 1, "reset_time": time.time() + rule.window_seconds}
            
            current_count = int(current_count)
            
            if current_count >= rule.max_requests:
                # Rate limit exceeded
                await self._log_security_event(
                    event_type="rate_limit_exceeded",
                    source_ip=client_ip,
                    user_agent=user_agent,
                    endpoint=endpoint,
                    severity="medium",
                    details={
                        "current_count": current_count,
                        "max_requests": rule.max_requests,
                        "window_seconds": rule.window_seconds
                    }
                )
                
                # Block IP temporarily
                await self._temporary_block_ip(client_ip, rule.block_duration)
                
                return False, {
                    "error": "Rate limit exceeded",
                    "retry_after": rule.window_seconds,
                    "block_duration": rule.block_duration
                }
            
            # Increment counter
            await asyncio.get_event_loop().run_in_executor(
                None, self.redis.incr, rate_key
            )
            
            remaining = rule.max_requests - current_count - 1
            ttl = await asyncio.get_event_loop().run_in_executor(
                None, self.redis.ttl, rate_key
            )
            
            return True, {
                "remaining": remaining,
                "reset_time": time.time() + ttl
            }
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True, {}  # Allow on error
    
    async def validate_input(self, data: Any, input_type: str = "general") -> Tuple[bool, List[str]]:
        """Validate input for security threats"""
        issues = []
        
        try:
            if isinstance(data, str):
                # Check for malicious patterns
                for pattern in self.malicious_patterns:
                    if re.search(pattern, data, re.IGNORECASE):
                        issues.append(f"Malicious pattern detected: {pattern}")
                
                # Check for excessive length
                if len(data) > 10000:  # 10KB limit
                    issues.append("Input too long")
                
                # Check for null bytes
                if '\x00' in data:
                    issues.append("Null byte injection detected")
            
            elif isinstance(data, dict):
                # Recursively validate dictionary values
                for key, value in data.items():
                    is_valid, sub_issues = await self.validate_input(value, input_type)
                    if not is_valid:
                        issues.extend([f"{key}: {issue}" for issue in sub_issues])
            
            elif isinstance(data, list):
                # Validate list items
                for i, item in enumerate(data):
                    is_valid, sub_issues = await self.validate_input(item, input_type)
                    if not is_valid:
                        issues.extend([f"item_{i}: {issue}" for issue in sub_issues])
            
            return len(issues) == 0, issues
            
        except Exception as e:
            logger.error(f"Input validation error: {e}")
            return False, [f"Validation error: {e}"]
    
    async def check_ip_reputation(self, client_ip: str) -> Tuple[bool, str]:
        """Check IP reputation and whitelist/blacklist status"""
        try:
            # Check blacklist
            if client_ip in self.ip_blacklist:
                return False, "IP is blacklisted"
            
            # Check whitelist
            if client_ip in self.ip_whitelist:
                return True, "IP is whitelisted"
            
            # Check for suspicious patterns
            if await self._is_suspicious_ip(client_ip):
                return False, "IP shows suspicious behavior"
            
            return True, "IP is clean"
            
        except Exception as e:
            logger.error(f"IP reputation check error: {e}")
            return True, "Could not check IP reputation"
    
    async def _is_suspicious_ip(self, client_ip: str) -> bool:
        """Check if IP shows suspicious behavior"""
        try:
            # Check recent security events
            recent_events = [event for event in self.security_events 
                           if event.source_ip == client_ip and 
                           event.timestamp > datetime.now(timezone.utc) - timedelta(hours=1)]
            
            # Count high severity events
            high_severity_count = len([e for e in recent_events if e.severity in ['high', 'critical']])
            
            # Check rate limit violations
            rate_limit_violations = len([e for e in recent_events if e.event_type == 'rate_limit_exceeded'])
            
            # Consider suspicious if:
            # - More than 3 high severity events in last hour
            # - More than 5 rate limit violations in last hour
            return high_severity_count > 3 or rate_limit_violations > 5
            
        except Exception as e:
            logger.error(f"Suspicious IP check error: {e}")
            return False
    
    async def _temporary_block_ip(self, client_ip: str, duration: int):
        """Temporarily block an IP address"""
        try:
            block_key = f"blocked_ip:{client_ip}"
            await asyncio.get_event_loop().run_in_executor(
                None, self.redis.setex, block_key, duration, "blocked"
            )
            
            logger.warning(f"Temporarily blocked IP: {client_ip} for {duration} seconds")
            
        except Exception as e:
            logger.error(f"IP blocking error: {e}")
    
    async def is_ip_blocked(self, client_ip: str) -> bool:
        """Check if IP is currently blocked"""
        try:
            block_key = f"blocked_ip:{client_ip}"
            blocked = await asyncio.get_event_loop().run_in_executor(
                None, self.redis.get, block_key
            )
            return blocked is not None
            
        except Exception as e:
            logger.error(f"IP block check error: {e}")
            return False
    
    async def _log_security_event(
        self, 
        event_type: str, 
        source_ip: str, 
        user_agent: str, 
        endpoint: str, 
        severity: str, 
        details: Dict[str, Any]
    ):
        """Log a security event"""
        try:
            event = SecurityEvent(
                timestamp=datetime.now(timezone.utc),
                event_type=event_type,
                source_ip=source_ip,
                user_agent=user_agent,
                endpoint=endpoint,
                severity=severity,
                details=details
            )
            
            self.security_events.append(event)
            
            # Log to Redis for persistence
            event_key = f"security_event:{int(time.time())}:{secrets.token_hex(8)}"
            event_data = {
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type,
                "source_ip": event.source_ip,
                "user_agent": event.user_agent,
                "endpoint": event.endpoint,
                "severity": event.severity,
                "details": str(event.details)
            }
            
            await asyncio.get_event_loop().run_in_executor(
                None, self.redis.hset, event_key, mapping=event_data
            )
            await asyncio.get_event_loop().run_in_executor(
                None, self.redis.expire, event_key, 86400  # 24 hours
            )
            
            # Log to application log
            logger.warning(f"Security event: {event_type} from {source_ip} - {severity}")
            
        except Exception as e:
            logger.error(f"Security event logging error: {e}")
    
    async def _check_suspicious_activity(self):
        """Check for suspicious activity patterns"""
        try:
            # Group events by IP
            ip_events = defaultdict(list)
            for event in self.security_events:
                if event.timestamp > datetime.now(timezone.utc) - timedelta(hours=1):
                    ip_events[event.source_ip].append(event)
            
            # Check for suspicious patterns
            for ip, events in ip_events.items():
                if len(events) > 50:  # More than 50 events in an hour
                    await self._log_security_event(
                        event_type="suspicious_activity",
                        source_ip=ip,
                        user_agent="",
                        endpoint="multiple",
                        severity="high",
                        details={"event_count": len(events), "time_window": "1 hour"}
                    )
                    
                    # Auto-block if very suspicious
                    if len(events) > 100:
                        await self._temporary_block_ip(ip, 3600)  # Block for 1 hour
            
        except Exception as e:
            logger.error(f"Suspicious activity check error: {e}")
    
    async def _cleanup_rate_limits(self):
        """Clean up expired rate limit entries"""
        try:
            # Redis automatically expires keys, but we can clean up any orphaned entries
            keys = await asyncio.get_event_loop().run_in_executor(
                None, self.redis.keys, "rate_limit:*"
            )
            
            for key in keys:
                ttl = await asyncio.get_event_loop().run_in_executor(
                    None, self.redis.ttl, key
                )
                if ttl == -1:  # No expiration set
                    await asyncio.get_event_loop().run_in_executor(
                        None, self.redis.delete, key
                    )
            
        except Exception as e:
            logger.error(f"Rate limit cleanup error: {e}")
    
    async def get_security_events(self, limit: int = 100, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent security events"""
        try:
            events = list(self.security_events)
            
            if severity:
                events = [e for e in events if e.severity == severity]
            
            # Convert to dict and limit
            return [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "event_type": e.event_type,
                    "source_ip": e.source_ip,
                    "user_agent": e.user_agent,
                    "endpoint": e.endpoint,
                    "severity": e.severity,
                    "details": e.details
                }
                for e in events[-limit:]
            ]
            
        except Exception as e:
            logger.error(f"Get security events error: {e}")
            return []
    
    async def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics"""
        try:
            # Count events by type and severity
            event_counts = defaultdict(int)
            severity_counts = defaultdict(int)
            
            for event in self.security_events:
                event_counts[event.event_type] += 1
                severity_counts[event.severity] += 1
            
            # Count unique IPs
            unique_ips = len(set(event.source_ip for event in self.security_events))
            
            # Count blocked IPs
            blocked_ips = await asyncio.get_event_loop().run_in_executor(
                None, self.redis.keys, "blocked_ip:*"
            )
            
            return {
                "total_events": len(self.security_events),
                "unique_ips": unique_ips,
                "blocked_ips": len(blocked_ips),
                "event_types": dict(event_counts),
                "severity_distribution": dict(severity_counts),
                "whitelisted_ips": len(self.ip_whitelist),
                "blacklisted_ips": len(self.ip_blacklist)
            }
            
        except Exception as e:
            logger.error(f"Security stats error: {e}")
            return {"error": str(e)}
    
    async def add_to_whitelist(self, ip: str):
        """Add IP to whitelist"""
        try:
            # Validate IP format
            ipaddress.ip_address(ip)
            self.ip_whitelist.add(ip)
            logger.info(f"Added IP to whitelist: {ip}")
            
        except ValueError:
            raise ValueError(f"Invalid IP address: {ip}")
        except Exception as e:
            logger.error(f"Whitelist add error: {e}")
    
    async def add_to_blacklist(self, ip: str):
        """Add IP to blacklist"""
        try:
            # Validate IP format
            ipaddress.ip_address(ip)
            self.ip_blacklist.add(ip)
            logger.info(f"Added IP to blacklist: {ip}")
            
        except ValueError:
            raise ValueError(f"Invalid IP address: {ip}")
        except Exception as e:
            logger.error(f"Blacklist add error: {e}")
    
    async def remove_from_whitelist(self, ip: str):
        """Remove IP from whitelist"""
        self.ip_whitelist.discard(ip)
        logger.info(f"Removed IP from whitelist: {ip}")
    
    async def remove_from_blacklist(self, ip: str):
        """Remove IP from blacklist"""
        self.ip_blacklist.discard(ip)
        logger.info(f"Removed IP from blacklist: {ip}")
    
    def generate_api_key(self, user_id: str) -> str:
        """Generate a secure API key"""
        timestamp = str(int(time.time()))
        random_part = secrets.token_hex(16)
        data = f"{user_id}:{timestamp}:{random_part}"
        api_key = hashlib.sha256(data.encode()).hexdigest()
        return f"ntt_{api_key[:32]}"
    
    async def validate_api_key(self, api_key: str) -> Tuple[bool, Optional[str]]:
        """Validate API key format and structure"""
        try:
            if not api_key.startswith("ntt_"):
                return False, "Invalid API key format"
            
            if len(api_key) != 36:  # ntt_ + 32 chars
                return False, "Invalid API key length"
            
            # Check if key exists in Redis (if we're storing them)
            key_exists = await asyncio.get_event_loop().run_in_executor(
                None, self.redis.exists, f"api_key:{api_key}"
            )
            
            return bool(key_exists), None
            
        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return False, "Validation error"
