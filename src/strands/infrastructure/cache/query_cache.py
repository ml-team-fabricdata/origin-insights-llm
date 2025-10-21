"""Query result caching with TTL support."""

from typing import Any, Optional, Dict, Tuple
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class QueryCache:
    """Thread-safe cache for query results with TTL."""
    
    def __init__(self, ttl_minutes: int = 60, max_size: int = 1000):
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get_cache_key(self, func_name: str, *args, **kwargs) -> str:
        key_data = {
            'func': func_name,
            'args': args,
            'kwargs': kwargs
        }
        try:
            key_str = json.dumps(key_data, sort_keys=True, default=str)
            return hashlib.md5(key_str.encode()).hexdigest()
        except (TypeError, ValueError) as e:
            logger.warning(f"Error generating cache key: {e}")
            return hashlib.md5(str(key_data).encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            self.misses += 1
            return None
        
        value, timestamp = self.cache[key]
        
        if datetime.now() - timestamp > self.ttl:
            del self.cache[key]
            self.misses += 1
            return None
        
        self.hits += 1
        return value
    
    def set(self, key: str, value: Any) -> None:
        if len(self.cache) >= self.max_size:
            self.clear_expired()
            
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.items(), key=lambda x: x[1][1])[0]
                del self.cache[oldest_key]
        
        self.cache[key] = (value, datetime.now())
    
    def clear(self) -> None:
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def clear_expired(self) -> int:
        now = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if now - timestamp > self.ttl
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)
    
    def get_stats(self) -> dict:
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'total_requests': total,
            'hit_rate': f"{hit_rate:.1f}%",
            'cache_size': len(self.cache),
            'max_size': self.max_size,
            'ttl_minutes': self.ttl.total_seconds() / 60
        }


def cached_query(cache_instance: QueryCache):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = cache_instance.get_cache_key(func.__name__, *args, **kwargs)
            
            cached_result = cache_instance.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache HIT for {func.__name__}")
                return cached_result
            
            logger.debug(f"Cache MISS for {func.__name__}")
            result = func(*args, **kwargs)
            
            cache_instance.set(cache_key, result)
            return result
        
        return wrapper
    return decorator


intelligence_cache = QueryCache(ttl_minutes=60, max_size=500)
rankings_cache = QueryCache(ttl_minutes=30, max_size=500)
pricing_cache = QueryCache(ttl_minutes=15, max_size=500)
general_cache = QueryCache(ttl_minutes=30, max_size=1000)
