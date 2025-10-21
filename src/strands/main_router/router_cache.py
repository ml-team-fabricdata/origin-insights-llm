"""Cache for router decisions to avoid redundant LLM calls."""
import hashlib
import time
from typing import Dict, Tuple, List, Optional


class RouterCache:
    """Simple in-memory cache for router decisions."""
    
    def __init__(self, ttl_seconds: int = 300, max_size: int = 1000):
        """
        Args:
            ttl_seconds: Time to live for cache entries (default 5 minutes)
            max_size: Maximum number of entries to cache
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: Dict[str, Tuple[dict, float]] = {}
        self._access_times: Dict[str, float] = {}
    
    def _generate_key(self, question: str, visited_graphs: List[str]) -> str:
        """Generate cache key from question and visited graphs."""
        # Normalize question (lowercase, strip whitespace)
        normalized_question = question.lower().strip()
        visited_str = ",".join(sorted(visited_graphs))
        
        # Create hash
        key_str = f"{normalized_question}|{visited_str}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, question: str, visited_graphs: List[str]) -> Optional[dict]:
        """
        Get cached router decision.
        
        Returns:
            dict with keys: selected_graph, confidence, candidates
            None if not found or expired
        """
        key = self._generate_key(question, visited_graphs)
        
        if key not in self._cache:
            return None
        
        cached_data, timestamp = self._cache[key]
        current_time = time.time()
        
        # Check if expired
        if current_time - timestamp > self.ttl_seconds:
            del self._cache[key]
            if key in self._access_times:
                del self._access_times[key]
            return None
        
        # Update access time
        self._access_times[key] = current_time
        
        print(f"[ROUTER CACHE] HIT - Using cached decision for similar query")
        return cached_data
    
    def set(self, question: str, visited_graphs: List[str], 
            selected_graph: str, confidence: float, candidates: list):
        """Cache router decision."""
        key = self._generate_key(question, visited_graphs)
        current_time = time.time()
        
        # Evict oldest entry if cache is full
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._access_times.items(), key=lambda x: x[1])[0]
            del self._cache[oldest_key]
            del self._access_times[oldest_key]
        
        cached_data = {
            "selected_graph": selected_graph,
            "confidence": confidence,
            "candidates": candidates
        }
        
        self._cache[key] = (cached_data, current_time)
        self._access_times[key] = current_time
        
        print(f"[ROUTER CACHE] SET - Cached decision for future queries")
    
    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        self._access_times.clear()
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds
        }


# Global cache instance
_router_cache = RouterCache(ttl_seconds=300, max_size=1000)


def get_router_cache() -> RouterCache:
    """Get the global router cache instance."""
    return _router_cache
