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
        """
        Initialize cache.
        
        Args:
            ttl_minutes: Time to live for cached entries in minutes
            max_size: Maximum number of entries to cache
        """
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get_cache_key(self, func_name: str, *args, **kwargs) -> str:
        """
        Generate unique cache key from function name and parameters.
        
        Args:
            func_name: Name of the function
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            MD5 hash of the serialized key data
        """
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
        """
        Get cached result if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key is None:
            return None
            
        if key in self.cache:
            result, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                self.hits += 1
                logger.debug(f"Cache HIT: {key}")
                return result
            else:
                # Expired
                del self.cache[key]
                logger.debug(f"Cache EXPIRED: {key}")
        
        self.misses += 1
        logger.debug(f"Cache MISS: {key}")
        return None
    
    def set(self, key: str, value: Any) -> None:
        """
        Cache result with timestamp.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        if key is None:
            return
            
        # Evict oldest entry if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
            logger.debug(f"Cache EVICT (size limit): {oldest_key}")
        
        self.cache[key] = (value, datetime.now())
        logger.debug(f"Cache SET: {key}")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Cache CLEARED")
    
    def clear_expired(self) -> int:
        """
        Remove expired cache entries.
        
        Returns:
            Number of expired entries removed
        """
        now = datetime.now()
        expired = [k for k, (_, ts) in self.cache.items() 
                  if now - ts >= self.ttl]
        
        for k in expired:
            del self.cache[k]
        
        if expired:
            logger.info(f"Cache cleanup: removed {len(expired)} expired entries")
        
        return len(expired)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache stats
        """
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
    
    def print_stats(self) -> None:
        """Print cache statistics."""
        stats = self.get_stats()
        logger.info(f"Cache stats: {stats}")


# Global cache instances for different use cases
# Intelligence queries (platform exclusivity, catalog similarity)
intelligence_cache = QueryCache(ttl_minutes=60, max_size=500)

# Rankings queries (top lists change more frequently)
rankings_cache = QueryCache(ttl_minutes=30, max_size=500)

# Pricing queries (prices can change)
pricing_cache = QueryCache(ttl_minutes=15, max_size=500)

# General purpose cache
general_cache = QueryCache(ttl_minutes=60, max_size=1000)


def cached_query(cache_instance: QueryCache = None, ttl_minutes: int = None):
    """
    Decorator to cache query results.
    
    Args:
        cache_instance: Cache instance to use (default: general_cache)
        ttl_minutes: Override TTL for this specific function
        
    Usage:
        @cached_query(intelligence_cache)
        def my_query_function(param1, param2):
            return db.execute_query(...)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Use provided cache or default
            cache = cache_instance or general_cache
            
            # Generate cache key
            cache_key = cache.get_cache_key(func.__name__, *args, **kwargs)
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"Using cached result for {func.__name__}")
                return cached_result
            
            # Execute function
            logger.info(f"Executing {func.__name__} (cache miss)")
            result = func(*args, **kwargs)
            
            # Cache result
            cache.set(cache_key, result)
            
            return result
        
        return wrapper
    return decorator


# Periodic cleanup (can be called from a background task)
def cleanup_all_caches() -> Dict[str, int]:
    """
    Clean up expired entries from all caches.
    
    Returns:
        Dict with cleanup counts per cache
    """
    return {
        "intelligence": intelligence_cache.clear_expired(),
        "rankings": rankings_cache.clear_expired(),
        "pricing": pricing_cache.clear_expired(),
        "general": general_cache.clear_expired()
    }


def get_all_cache_stats() -> Dict[str, Dict[str, Any]]:
    """Get statistics from all caches."""
    return {
        "intelligence": intelligence_cache.get_stats(),
        "rankings": rankings_cache.get_stats(),
        "pricing": pricing_cache.get_stats(),
        "general": general_cache.get_stats()
    }


def clear_all_caches() -> None:
    """Clear all caches."""
    intelligence_cache.clear()
    rankings_cache.clear()
    pricing_cache.clear()
    general_cache.clear()
    logger.info("All caches cleared")
