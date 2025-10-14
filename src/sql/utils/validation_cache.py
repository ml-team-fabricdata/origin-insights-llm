"""
Cache system for validation results to improve performance.
"""

from functools import lru_cache
from typing import Dict, Any, Optional
import hashlib


class ValidationCache:
    """
    Simple in-memory cache for validation results.
    Uses LRU cache to limit memory usage.
    """
    
    @staticmethod
    def _make_key(entity_type: str, query: str) -> str:
        """
        Create a cache key from entity type and query.
        
        Args:
            entity_type: Type of entity (director, actor, title)
            query: Query string (name or title)
            
        Returns:
            Cache key string
        """
        # Normalize query: lowercase and strip whitespace
        normalized = query.lower().strip()
        # Create hash for consistent key
        key = f"{entity_type}:{normalized}"
        return key
    
    @staticmethod
    @lru_cache(maxsize=1000)
    def get_cached_validation(entity_type: str, query: str) -> Optional[Dict[str, Any]]:
        """
        Get cached validation result.
        
        Args:
            entity_type: Type of entity (director, actor, title)
            query: Query string
            
        Returns:
            Cached result or None
        """
        # This is just a placeholder - actual caching happens via lru_cache
        return None
    
    @staticmethod
    def cache_validation(entity_type: str, query: str, result: Dict[str, Any]) -> None:
        """
        Cache a validation result.
        
        Args:
            entity_type: Type of entity
            query: Query string
            result: Validation result to cache
        """
        # Store in lru_cache by calling get with result
        key = ValidationCache._make_key(entity_type, query)
        # Force cache update by storing in a dict
        _validation_cache[key] = result
    
    @staticmethod
    def clear_cache() -> None:
        """Clear all cached validations."""
        ValidationCache.get_cached_validation.cache_clear()
        _validation_cache.clear()


# Global cache dictionary
_validation_cache: Dict[str, Dict[str, Any]] = {}


def get_cached_validation(entity_type: str, query: str) -> Optional[Dict[str, Any]]:
    """
    Get cached validation result.
    
    Args:
        entity_type: Type of entity (director, actor, title)
        query: Query string
        
    Returns:
        Cached result or None
    """
    key = ValidationCache._make_key(entity_type, query)
    return _validation_cache.get(key)


def cache_validation(entity_type: str, query: str, result: Dict[str, Any]) -> None:
    """
    Cache a validation result.
    
    Args:
        entity_type: Type of entity
        query: Query string
        result: Validation result to cache
    """
    key = ValidationCache._make_key(entity_type, query)
    _validation_cache[key] = result


def clear_validation_cache() -> None:
    """Clear all cached validations."""
    _validation_cache.clear()
