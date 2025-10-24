import time

class SessionMemory:
    """Memoria temporal por thread_id (se limpia automáticamente)."""
    def __init__(self, ttl_seconds: int = 600):
        self._store = {}
        self.ttl = ttl_seconds

    def _expired(self, key):
        return (time.time() - self._store[key]["timestamp"]) > self.ttl

    def get(self, thread_id: str) -> dict:
        if thread_id in self._store and not self._expired(thread_id):
            return self._store[thread_id]["data"]
        self._store.pop(thread_id, None)
        return {}

    def set(self, thread_id: str, data: dict):
        self._store[thread_id] = {"data": data, "timestamp": time.time()}

    def update(self, thread_id: str, **kwargs):
        data = self.get(thread_id)
        data.update(kwargs)
        self.set(thread_id, data)


# instancia global
session_memory = SessionMemory()