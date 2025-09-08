# app/agent/tools.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

# Reutilizamos tus módulos deterministas
from app.modules import titles as m_titles
from app.modules import metadata as m_meta
from app.modules import availability as m_avail
from app.modules import hits as m_hits
from app.modules import countries as m_countries

# -------- Herramientas deterministas de alto nivel --------

def tool_titles_search(term: str, top_k: int = 20, min_similarity: float = 0.80) -> List[Dict[str, Any]]:
    """
    Busca candidatos por título (usa tu buscador SQL con trigram).
    Retorna [{uid, imdb_id, title, year, type, directors, sim}, ...]
    """
    rows = m_titles.search_title_candidates(term, top_k=top_k, min_similarity=min_similarity) or []
    out, seen = [], set()
    for r in rows:
        key = (r.get("uid") or r.get("imdb_id") or "").lower()
        if key and key not in seen:
            out.append(r); seen.add(key)
    return out

def tool_metadata(uid: Optional[str] = None, imdb_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Lee metadatos por UID o IMDb."""
    if uid:
        r = m_meta.get_metadata_by_uid(uid)
        if r:
            d = dict(r); d["uid"] = uid; return d
    if imdb_id:
        r = m_meta.get_metadata_by_imdb(imdb_id)
        if r:
            d = dict(r); d["imdb_id"] = imdb_id; return d
    return None

def tool_availability(uid: str, country_hint: Optional[str] = None, include_prices: bool = False) -> Dict[str, Any]:
    """
    Disponibilidad por UID, opcionalmente filtrando país (se adivina/normaliza).
    Retorna payload estructurado.
    """
    iso2, pretty = (None, None)
    if country_hint:
        try:
            iso2, pretty = m_countries.guess_country(country_hint)
        except Exception:
            iso2, pretty = None, None

    rows = m_avail.fetch_availability_by_uid(uid, iso2=iso2, with_prices=include_prices) or []
    items = []
    for r in rows:
        items.append({
            "platform_name": r.get("platform_name"),
            "platform_country": r.get("platform_country"),
            "permalink": r.get("permalink"),
            "enter_on": r.get("enter_on"),
            "out_on": r.get("out_on"),
            "plan_name": r.get("plan_name"),
            "price": r.get("price") if include_prices else None,
        })
    return {
        "uid": uid,
        "country_pretty": (pretty or (iso2 if (iso2 and len(str(iso2)) == 2) else None)),
        "include_prices": include_prices,
        "items": items,
    }

def tool_hits_title_with_context(
    uid: str,
    user_text: str,
) -> Dict[str, Any]:
    """
    Suma anual de HITS con contexto:
      - Si la consulta trae año → usa ese año (si no, año actual).
      - Si trae país → usa hits_presence_2; si no, hits_global.
      - Incluye baseline del top (mismos filtros) para dar escala.
    """
    df, dt_ = m_hits.extract_date_range(user_text)
    try:
        iso2, pretty = m_countries.guess_country(user_text)
    except Exception:
        iso2, pretty = None, None
    df_s, dt_s, used_year = m_hits.ensure_hits_range(df, dt_, iso2)

    # tipo de contenido (para el baseline)
    meta = tool_metadata(uid=uid) or {}
    ctype = (meta.get("type") or "").lower()
    ctype = ctype if ctype in ("movie", "series") else None

    hits_sum = m_hits.get_title_hits_sum(uid=uid, imdb_id=None, country_iso2=iso2, date_from=df_s, date_to=dt_s)
    bench_rows = m_hits.get_top_hits_by_period(country_iso2=iso2, date_from=df_s, date_to=dt_s, limit=1, content_type=ctype)
    bench = bench_rows[0] if bench_rows else None

    text = m_hits.render_title_hits_with_context(
        meta=dict(meta),
        hits_sum=hits_sum,
        lang="es",  # se reescribe luego al idioma del usuario
        country_pretty=(pretty or iso2),
        year_used=used_year,
        baseline=bench,
    )
    return {
        "text": text,
        "meta": {
            "uid": uid,
            "year_used": used_year,
            "country": (pretty or iso2),
            "content_type": ctype,
            "baseline": bench,
        }
    }

def tool_hits_top(
    user_text: str,
    default_limit: int = 20,
) -> Optional[str]:
    """
    TOP N por período. Si el usuario no especifica, asume año actual y scope global.
    Devuelve un string renderizado (ES) que luego se reescribe al idioma del usuario.
    """
    df, dt_ = m_hits.extract_date_range(user_text)
    try:
        iso2, pretty = m_countries.guess_country(user_text)
    except Exception:
        iso2, pretty = None, None
    df_s, dt_s, used_year = m_hits.ensure_hits_range(df, dt_, iso2)

    # tamaño del top
    asked_topn = None
    import re as _re
    mmm = _re.search(r"\btop\s*(\d{1,3})\b", user_text, _re.I)
    if mmm:
        try: asked_topn = int(mmm.group(1))
        except: pass
    series_only = bool(_re.search(r"\b(serie|series)\b", user_text, _re.I))
    movie_only  = bool(_re.search(r"\b(pel[ií]cula|pelicula|movie|film)\b", user_text, _re.I))
    content_type = "series" if (series_only and not movie_only) else ("movie" if (movie_only and not series_only) else None)

    items = m_hits.get_top_hits_by_period(country_iso2=iso2, date_from=df_s, date_to=dt_s,
                                          limit=(asked_topn or default_limit), content_type=content_type) or []
    if not items:
        return None
    return m_hits.render_top_hits(items, country=(pretty or iso2), lang="es",
                                  year_used=used_year, series_only=(content_type == "series"), top_n=asked_topn)