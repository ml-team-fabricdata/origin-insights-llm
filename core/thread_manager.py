# thread_manager.py
import uuid
import time
import hashlib
from datetime import datetime
from typing import Optional, Dict, List
import psycopg
from sql.utils.sql_db import SQLConnectionManager

class ThreadManager:
    """Gestor de thread_ids únicos para sesiones"""
    
    @staticmethod
    def generate_thread_id(user_id: Optional[str] = None, session_type: str = "chat") -> str:
        """
        Genera un thread_id único para cada sesión
        
        Formatos posibles:
        - Con user_id: user_{user_id}_{timestamp}_{random}
        - Sin user_id: session_{type}_{timestamp}_{random}
        """
        timestamp = int(time.time())
        random_part = uuid.uuid4().hex[:8]
        
        if user_id:
            # Hash del user_id para privacidad si es muy largo
            if len(user_id) > 20:
                user_hash = hashlib.md5(user_id.encode()).hexdigest()[:10]
                thread_id = f"user_{user_hash}_{timestamp}_{random_part}"
            else:
                thread_id = f"user_{user_id}_{timestamp}_{random_part}"
        else:
            thread_id = f"session_{session_type}_{timestamp}_{random_part}"
        
        return thread_id
    
    @staticmethod
    def generate_daily_thread_id(user_id: str) -> str:
        """
        Genera un thread_id que se mantiene igual durante todo el día
        Útil para conversaciones continuas diarias
        """
        today = datetime.now().strftime("%Y%m%d")
        user_hash = hashlib.md5(user_id.encode()).hexdigest()[:10]
        return f"daily_{user_hash}_{today}"
    
    @staticmethod
    def generate_context_thread_id(context: str, user_id: Optional[str] = None) -> str:
        """
        Genera thread_id basado en contexto específico
        Ej: proyecto, tema, departamento, etc.
        """
        context_clean = context.lower().replace(" ", "_")[:20]
        timestamp = int(time.time())
        
        if user_id:
            return f"{context_clean}_{user_id}_{timestamp}"
        else:
            random_part = uuid.uuid4().hex[:6]
            return f"{context_clean}_{timestamp}_{random_part}"

class ThreadRepository:
    """Repositorio para operaciones con threads en PostgreSQL"""
    
    def __init__(self):
        self.db = SQLConnectionManager()
    
    def _get_psycopg_connection(self):
        """Obtener conexión psycopg3 para consultas directas"""
        cfg = self.db.conn_params
        return psycopg.connect(
            host=cfg["host"],
            port=cfg["port"],
            dbname=cfg["dbname"],
            user=cfg["user"],
            password=cfg["password"],
            options="-c search_path=ms,public",
            autocommit=True
        )
    
    def get_thread_exists(self, thread_id: str) -> bool:
        """Verificar si un thread existe en la base de datos"""
        conn = self._get_psycopg_connection()
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM ms.checkpoints 
                    WHERE thread_id = %s
                    LIMIT 1
                )
            """, (thread_id,))
            exists = cur.fetchone()[0]
        
        conn.close()
        return exists
    
    def get_user_threads(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Obtener threads de un usuario específico"""
        conn = self._get_psycopg_connection()
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT
                    thread_id,
                    MIN(checkpoint_ts) as created_at,
                    MAX(checkpoint_ts) as last_activity,
                    COUNT(*) as message_count
                FROM ms.checkpoints
                WHERE thread_id LIKE %s
                GROUP BY thread_id
                ORDER BY last_activity DESC
                LIMIT %s
            """, (f"%{user_id}%", limit))
            
            results = cur.fetchall()
        
        conn.close()
        
        threads = []
        for row in results:
            threads.append({
                'thread_id': row[0],
                'created_at': row[1].isoformat() if row[1] else None,
                'last_activity': row[2].isoformat() if row[2] else None,
                'message_count': row[3]
            })
        
        return threads
    
    def get_recent_threads(self, hours: int = 24) -> List[str]:
        """Obtener threads activos en las últimas N horas"""
        conn = self._get_psycopg_connection()
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT thread_id
                FROM ms.checkpoints
                WHERE checkpoint_ts > NOW() - INTERVAL '%s hours'
                ORDER BY thread_id
            """, (hours,))
            
            results = cur.fetchall()
        
        conn.close()
        
        return [row[0] for row in results]
    
    def cleanup_old_threads(self, days: int = 30) -> int:
        """Limpiar threads antiguos"""
        conn = self._get_psycopg_connection()
        
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM ms.checkpoints
                WHERE checkpoint_ts < NOW() - INTERVAL '%s days'
            """, (days,))
            deleted = cur.rowcount
        
        conn.close()
        return deleted

# Singleton global para fácil acceso
_thread_manager = ThreadManager()
_thread_repository = ThreadRepository()

def get_new_thread_id(user_id: Optional[str] = None, session_type: str = "chat") -> str:
    """Función helper para obtener un nuevo thread_id único"""
    return _thread_manager.generate_thread_id(user_id, session_type)

def get_or_create_thread_id(user_id: Optional[str] = None, 
                           use_daily: bool = False,
                           context: Optional[str] = None) -> str:
    """
    Obtener o crear thread_id según la estrategia deseada
    
    Args:
        user_id: ID del usuario
        use_daily: Si True, usa el mismo thread para todo el día
        context: Contexto específico para el thread
    """
    if use_daily and user_id:
        return _thread_manager.generate_daily_thread_id(user_id)
    elif context:
        return _thread_manager.generate_context_thread_id(context, user_id)
    else:
        return _thread_manager.generate_thread_id(user_id)

# Para importación directa
__all__ = [
    'ThreadManager',
    'ThreadRepository', 
    'get_new_thread_id',
    'get_or_create_thread_id'
]