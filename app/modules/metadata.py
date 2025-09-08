# app/modules/metadata.py
from typing import Any, Dict, Optional
from infra.db import run_sql
from infra.config import SETTINGS

__all__ = [
    "get_metadata_by_uid",
    "get_metadata_by_imdb",
    "resolve_uid_by_imdb",
    "get_metadata_by_uid_or_imdb",
]


def get_metadata_by_uid(uid: str) -> Optional[Dict[str, Any]]:
    """
    Lee metadatos de ms.new_cp_metadata_estandar por UID.
    Devuelve dict con: uid, imdb_id, title, year, type, directors, synopsis
    """
    if SETTINGS.offline_mode or not uid:
        return None
    rows = run_sql(
        """
        SELECT uid, imdb_id, title, year, type, directors, synopsis
        FROM ms.new_cp_metadata_estandar
        WHERE uid = %(u)s
        LIMIT 1;
        """,
        {"u": uid},
    )
    return rows[0] if rows else None


def get_metadata_by_imdb(imdb_id: str) -> Optional[Dict[str, Any]]:
    """
    Lee metadatos de ms.new_cp_metadata_estandar por IMDb ID (ttXXXXXX).
    """
    if SETTINGS.offline_mode or not imdb_id:
        return None
    rows = run_sql(
        """
        SELECT uid, imdb_id, title, year, type, directors, synopsis
        FROM ms.new_cp_metadata_estandar
        WHERE imdb_id = %(imdb)s
        LIMIT 1;
        """,
        {"imdb": imdb_id},
    )
    return rows[0] if rows else None


def resolve_uid_by_imdb(imdb_id: str) -> Optional[str]:
    """
    Devuelve el UID a partir de un IMDb ID.
    """
    m = get_metadata_by_imdb(imdb_id)
    return (m or {}).get("uid")


def get_metadata_by_uid_or_imdb(
    *, uid: Optional[str] = None, imdb_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Conveniencia: intenta primero por UID; si no hay UID y se pasa imdb_id, resuelve por IMDb.
    """
    if uid:
        return get_metadata_by_uid(uid)
    if imdb_id:
        return get_metadata_by_imdb(imdb_id)
    return None