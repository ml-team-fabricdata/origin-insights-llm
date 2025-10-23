import hashlib
import time
from typing import Dict, Tuple, List, Optional


class RouterCache:
    
    def __init__(self, ttl_seconds: int = 300, max_size: int = 1000):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: Dict[str, Tuple[dict, float]] = {}
        self._access_times: Dict[str, float] = {}
    
    def _generate_key(self, question: str, visited_graphs: List[str]) -> str:
        normalized_question = question.lower().strip()
        visited_str = ",".join(sorted(visited_graphs))
        key_str = f"{normalized_question}|{visited_str}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _is_expired(self, timestamp: float) -> bool:
        return time.time() - timestamp > self.ttl_seconds
    
    def _evict_oldest(self):
        oldest_key = min(self._access_times.items(), key=lambda x: x[1])[0]
        del self._cache[oldest_key]
        del self._access_times[oldest_key]
    
    def get(self, question: str, visited_graphs: List[str]) -> Optional[dict]:
        key = self._generate_key(question, visited_graphs)
        
        if key not in self._cache:
            return None
        
        cached_data, timestamp = self._cache[key]
        
        if self._is_expired(timestamp):
            del self._cache[key]
            if key in self._access_times:
                del self._access_times[key]
            return None
        
        self._access_times[key] = time.time()
        
        print(f"[ROUTER CACHE] HIT - Using cached decision for similar query")
        return cached_data
    
    def set(self, question: str, visited_graphs: List[str], 
            selected_graph: str, confidence: float, candidates: list):
        key = self._generate_key(question, visited_graphs)
        current_time = time.time()
        
        if len(self._cache) >= self.max_size:
            self._evict_oldest()
        
        cached_data = {
            "selected_graph": selected_graph,
            "confidence": confidence,
            "candidates": candidates
        }
        
        self._cache[key] = (cached_data, current_time)
        self._access_times[key] = current_time
        
        print(f"[ROUTER CACHE] SET - Cached decision for future queries")
    
    def clear(self):
        self._cache.clear()
        self._access_times.clear()
    
    def get_stats(self) -> dict:
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds
        }


_router_cache = RouterCache(ttl_seconds=300, max_size=1000)


def get_router_cache() -> RouterCache:
    return _router_cache