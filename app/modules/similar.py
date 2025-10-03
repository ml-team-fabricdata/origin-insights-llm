# app/modules/similar.py
from typing import Any, Dict, List, Optional
from infra.config import SETTINGS
from infra.db import run_sql

__all__ = [
    "kb_semantic_search",
    "search_titles_by_topic",
    "render_similar_list",
    "search_similar",  # helper: primero KB, luego trigram
]


def kb_semantic_search(query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Placeholder para Bedrock KB / Retrieve.
    Devuelve [] para forzar el fallback determinista.
    """
    return []


def _clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


def search_titles_by_topic(topic: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Fallback temático: trigram sobre ms.akas.clean_title con join a metadatos.
    """
    if SETTINGS.offline_mode:
        return []
    t = (topic or "").strip()
    if not t:
        return []
    k = _clamp(int(top_k or 10), 1, 100)

    sql = """
    WITH c AS (
      SELECT a.uid, similarity(a.clean_title, %(t)s) AS sim
      FROM ms.akas a
      WHERE a.clean_title %% %(t)s
      ORDER BY 2 DESC
      LIMIT %(k)s
    )
    SELECT m.uid, m.imdb_id, m.title, m.year, m.type, m.directors, c.sim
    FROM c
    JOIN ms.new_cp_metadata_estandar m ON m.uid = c.uid
    ORDER BY c.sim DESC, m.year DESC NULLS LAST;
    """
    return run_sql(sql, {"t": t, "k": k}) or []


def search_similar(query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Estrategia compuesta:
      1) Intentar KB semántica (cuando se habilite).
      2) Fallback determinista por trigram.
    """
    # (1) KB semántica (placeholder)
    try:
        kb = kb_semantic_search(query, top_k=top_k) or []
        if kb:
            return kb[:_clamp(top_k or 10, 1, 100)]
    except Exception:
        # no bloquea el fallback
        pass

    # (2) Trigram / títulos reales
    return search_titles_by_topic(query, top_k=top_k)


def render_similar_list(items: List[Dict[str, Any]], lang: str = "es") -> str:
    """
    Lista amigable para el usuario. Limita a 10 entradas.
    """
    if not items:
        return "No encontré títulos reales para ese tema." if lang.startswith("es") else "No real titles found for that topic."

    head = "Algunas opciones relacionadas:" if lang.startswith("es") else "Some related options:"
    lines = [head]
    for it in items[:10]:
        title = it.get("title", "") or ""
        year = it.get("year", "") or ""
        imdb = it.get("imdb_id") or ""
        imdb_s = f" — IMDb {imdb}" if imdb else ""
        lines.append(f"- {title} ({year}){imdb_s}")
    return "\n".join(lines)