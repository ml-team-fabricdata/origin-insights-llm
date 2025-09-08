# infra/db.py
import os
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from infra.config import SETTINGS

try:
    import psycopg2
    from psycopg2.pool import SimpleConnectionPool
    from psycopg2.extras import RealDictCursor
except Exception:  # tests locales sin deps
    psycopg2 = None
    SimpleConnectionPool = None
    RealDictCursor = None

log = logging.getLogger("infra.db")

_pool: Optional[SimpleConnectionPool] = None


def _ensure_pool() -> None:
    """
    Inicializa el pool si:
      - no estamos en OFFLINE_MODE
      - hay credenciales (SETTINGS.db_ready)
      - psycopg2 está disponible
    """
    global _pool
    if SETTINGS.offline_mode:
        return
    if _pool is not None:
        return
    if not SETTINGS.db_ready:
        log.warning("DB not ready: missing credentials (db_ready=False).")
        return
    if not psycopg2:
        log.warning("psycopg2 not available; cannot initialize pool.")
        return

    minconn = int(os.getenv("AURORA_POOL_MIN", "1"))
    maxconn = int(os.getenv("AURORA_POOL_MAX", "5"))

    _pool = SimpleConnectionPool(
        minconn=minconn,
        maxconn=maxconn,
        user=SETTINGS.aurora_user,
        password=SETTINGS.aurora_pass,
        host=SETTINGS.aurora_host,
        port=SETTINGS.aurora_port,
        database=SETTINGS.aurora_db,
        connect_timeout=5,
        options=f"-c application_name=origin-insights-llm"
    )
    log.info(
        "PG pool initialized (min=%s max=%s host=%s db=%s, source=%s)",
        minconn, maxconn, SETTINGS.aurora_host, SETTINGS.aurora_db, SETTINGS.db_source
    )


def _conn():
    _ensure_pool()
    if SETTINGS.offline_mode:
        raise RuntimeError("DB not available: OFFLINE_MODE=1")
    if _pool is None:
        raise RuntimeError("DB not available: pool not initialized (db_ready=%s)" % SETTINGS.db_ready)
    return _pool.getconn()


def _put(conn) -> None:
    if _pool and conn:
        _pool.putconn(conn)


def run_sql(
    sql: str,
    params: Optional[Union[Dict[str, Any], Tuple[Any, ...]]] = None
) -> List[Dict[str, Any]]:
    """
    Ejecuta SQL y devuelve filas como dicts.
    - SET search_path a ms,public
    - SET LOCAL statement_timeout (ENV PG_STMT_TIMEOUT_MS -> SETTINGS.pg_stmt_timeout_ms)
    """
    if SETTINGS.offline_mode or not SETTINGS.db_ready:
        return []

    conn = None
    try:
        conn = _conn()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # esquema y timeout por sentencia
            cur.execute("SET search_path TO ms, public;")
            cur.execute(f"SET LOCAL statement_timeout = {SETTINGS.pg_stmt_timeout_ms};")

            if params is None:
                cur.execute(sql)
            else:
                cur.execute(sql, params)

            rows = cur.fetchall() if cur.description else []
            return [dict(r) for r in rows]
    finally:
        _put(conn)


def db_health() -> bool:
    """
    /healthz helper:
      - OFFLINE_MODE => True (no bloquear despliegue)
      - Sin DB lista => False
      - Con DB => SELECT 1
    """
    if SETTINGS.offline_mode:
        return True
    if not SETTINGS.db_ready:
        return False
    try:
        rows = run_sql("SELECT 1 AS ok;")
        # opcional: validar extensión pg_trgm, ignorando errores
        try:
            _ = run_sql("SELECT 1 FROM pg_extension WHERE extname='pg_trgm' LIMIT 1;")
        except Exception:
            pass
        return bool(rows)
    except Exception as e:
        log.warning("db_health check failed: %s", e)
        return False