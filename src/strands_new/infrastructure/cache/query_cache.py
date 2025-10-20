"""Query cache implementation - MIGRATED."""

# TODO: Migrar desde src/strands/utils/query_cache.py
# Este archivo implementará CacheRepository interface

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
        """Generate unique cache key."""
        key_data = {
            'func': func_name,
            'args': args,
            'kwargs': kwargs
        }
        try:
            key_str = json.dumps(key_data, sort_keys=True, default=str)
            return hashlib.md5(key_str.encode()).hexdigest()
        except (TypeError, ValueError) as e:
            logger.warning(f"Could not serialize cache key: {e}")
            return None
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached result if not expired."""
        if key is None:
            return None
            
        if key in self.cache:
            result, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                self.hits += 1
                logger.debug(f"Cache HIT: {key}")
                return result
            else:
                del self.cache[key]
                logger.debug(f"Cache EXPIRED: {key}")
        
        self.misses += 1
        logger.debug(f"Cache MISS: {key}")
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Cache result with timestamp."""
        if key is None:
            return
            
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
            logger.debug(f"Cache EVICT: {oldest_key}")
        
        self.cache[key] = (value, datetime.now())
        logger.debug(f"Cache SET: {key}")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Cache CLEARED")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "ttl_minutes": self.ttl.total_seconds() / 60
        }


# Global cache instances
intelligence_cache = QueryCache(ttl_minutes=60, max_size=500)
rankings_cache = QueryCache(ttl_minutes=30, max_size=500)
pricing_cache = QueryCache(ttl_minutes=15, max_size=500)
general_cache = QueryCache(ttl_minutes=60, max_size=1000)
