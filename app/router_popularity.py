# app/router_popularity.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Callable
import re
from datetime import datetime

from infra.config import SETTINGS
from infra.db import run_sql
from app.modules.hits import (
    render_title_hits_with_context,
    get_top_hits_by_period,
)
from app.modules.countries import guess_country

router = APIRouter(prefix="/v1/popularity", tags=["popularity"])

# =========================
# Modelos I/O
# =========================

class QueryIn(BaseModel):
    text: str
    # Opcionales para contexto/conversación:
    uid: Optional[str] = None           # si ya tienes el UID seleccionado, pásalo y se salta la desambiguación
    session_id: Optional[str] = None    # si manejas sesión en tu router principal, puedes pasar un id para resolver uid contextual
    content_type: Optional[str] = None  # "movie" | "series" | None (si tu front la conoce, fuerza aquí)

class PopularityResult(BaseModel):
    scope: str
    year: str | int
    content_type: Optional[str] = None
    table_used: str
    total_titles: int
    target: Optional[Dict[str, Any]] = None
    top: Optional[Dict[str, Any]] = None
    messages: Dict[str, str]

class TopItem(BaseModel):
    uid: str
    title: Optional[str] = None
    hits_sum: float

class TopResult(BaseModel):
    scope: str
    year: int
    content_type: Optional[str] = None
    table_used: str
    items: List[TopItem]

class QueryOut(BaseModel):
    kind: str  # "title_popularity" | "top_list" | "ambiguous" | "not_found"
    payload: Dict[str, Any]


# =========================
# Parsing liviano de intentos
# =========================

_YEAR_RE = re.compile(r"\((\d{4})\)|\b(19|20)\d{2}\b")
_TOP_RE = re.compile(r"\b(top\s*\d{0,3}|ranking|más\s+populares|mas\s+populares|populares)\b", re.IGNORECASE)
_MOVIE_RE = re.compile(r"\b(pel[ií]cula|pel[ií]culas|movie|movies)\b", re.IGNORECASE)
_SERIES_RE = re.compile(r"\b(serie|series|tv|show)\b", re.IGNORECASE)
_POP_RE = re.compile(r"\b(popularidad|hits?)\b", re.IGNORECASE)

def _current_year() -> int:
    try:
        return datetime.utcnow().year
    except Exception:
        return 2025

def extract_year(text: str) -> Optional[int]:
    m = _YEAR_RE.search(text)
    if not m:
        return None
    val = m.group(1) or m.group(0)
    try:
        y = int(re.sub(r"[^\d]", "", val))
        if 1900 <= y <= 2100:
            return y
    except Exception:
        pass
    return None

def extract_content_type(text: str) -> Optional[str]:
    if _MOVIE_RE.search(text) and not _SERIES_RE.search(text):
        return "movie"
    if _SERIES_RE.search(text) and not _MOVIE_RE.search(text):
        return "series"
    return None

def is_top_query(text: str) -> bool:
    return bool(_TOP_RE.search(text))

def is_popularity_query(text: str) -> bool:
    return bool(_POP_RE.search(text))


# =========================
# Helpers de título/UID
# =========================

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def extract_title_candidate(text: str) -> Optional[str]:
    """
    Heurística de extracción: comillas → antes de (YYYY) → limpieza de conectores.
    """
    t = text
    m = re.search(r"[\"“”‘’']([^\"“”‘’']+)[\"“”‘’']", t)
    if m:
        return _norm(m.group(1))
    m = re.search(r"(.+?)\s*\(\d{4}\)", t)
    if m:
        return _norm(m.group(1))
    t = re.sub(_MOVIE_RE, "", t)
    t = re.sub(_SERIES_RE, "", t)
    t = re.sub(_POP_RE, "", t, flags=re.IGNORECASE)
    t = re.sub(_TOP_RE, "", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(cual|cu[aá]l|que|qu[eé]|de|la|el|los|las|es|fue|del|sobre|en)\b", " ", t, flags=re.IGNORECASE)
    t = _norm(t)
    return t if len(t) >= 2 else None

def _import_titles_search() -> Optional[Callable[..., List[Dict[str, Any]]]]:
    """
    Intenta localizar el buscador determinista basado en trigramas en app/modules/titles.py.
    Acepta distintos nombres comunes para compatibilidad.
    Debe devolver una lista de candidatos con al menos: uid, title, year, type, imdb_id.
    """
    try:
        from app.modules import titles as m_titles  # type: ignore
    except Exception:
        return None

    # Preferencias de nombres habituales
    for name in (
        "search_candidates",
        "find_candidates",
        "search_titles",
        "search",
    ):
        f = getattr(m_titles, name, None)
        if callable(f):
            return f

    # Como último recurso, si exponen un "resolve" que devuelve 1 o más
    for name in ("resolve_title", "resolve", "lookup"):
        f = getattr(m_titles, name, None)
        if callable(f):
            return f

    return None

def resolve_uid_via_titles_module(title: str, year: Optional[int]) -> List[Dict[str, Any]]:
    """
    Usa el módulo determinista de títulos (pg_trgm) si está disponible.
    Si no, cae a una query simple ILIKE.
    """
    search_fn = _import_titles_search()
    if search_fn:
        try:
            # Firma flexible: soporta variantes con/ sin parámetros adicionales
            # Intentamos pasar top_k y min_similarity si Settings los expone.
            kwargs = {}
            if hasattr(SETTINGS, "top_k_default"):
                kwargs["top_k"] = int(getattr(SETTINGS, "top_k_default"))
            if hasattr(SETTINGS, "min_sim_default"):
                kwargs["min_similarity"] = float(getattr(SETTINGS, "min_sim_default"))
            if year:
                kwargs["year"] = year
            res = search_fn(query=title, **kwargs) if "query" in getattr(search_fn, "__code__", {}).co_varnames else search_fn(title, **kwargs)  # type: ignore
            # Normalizar shape
            out: List[Dict[str, Any]] = []
            for r in res or []:
                out.append({
                    "uid": r.get("uid"),
                    "title": r.get("title") or r.get("english_title"),
                    "year": r.get("year"),
                    "type": r.get("type"),
                    "imdb_id": r.get("imdb_id"),
                })
            return out
        except Exception:
            pass

    # Fallback ILIKE si no hay módulo o explota
    params: Dict[str, Any] = {"q": f"%{title}%"}
    where = "(title ILIKE %(q)s OR english_title ILIKE %(q)s OR original_title ILIKE %(q)s)"
    if year:
        where += " AND year = %(yy)s"
        params["yy"] = year
    sql = f"""
        SELECT uid, title, english_title, year, type, imdb_id
        FROM ms.new_cp_metadata_estandar
        WHERE {where}
        ORDER BY
            CASE WHEN {"%(yy)s" if year else "NULL"} IS NOT NULL AND year = %(yy)s THEN 0 ELSE 1 END,
            year DESC NULLS LAST,
            LENGTH(title) ASC
        LIMIT 10
    """
    rows = run_sql(sql, params)
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append({
            "uid": r.get("uid"),
            "title": r.get("title") or r.get("english_title"),
            "year": r.get("year"),
            "type": r.get("type"),
            "imdb_id": r.get("imdb_id"),
        })
    return out

def pick_uid_or_ambiguous(cands: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not cands:
        return {"status": "not_found"}
    if len(cands) == 1:
        return {"status": "resolved", "uid": cands[0]["uid"], "candidate": cands[0], "options": cands}
    return {"status": "ambiguous", "options": cands}

def _get_uid_from_session(session_id: Optional[str]) -> Optional[str]:
    """
    Punto de enganche opcional con tu manejador de sesión.
    Si existe una API tipo get_selected_uid(session_id) en tu proyecto, se usa.
    Si no existe/lanza, retorna None (no rompe).
    """
    if not session_id:
        return None
    try:
        # Intenta localizar helpers conocidos de tu router principal
        # (ajusta estos nombres si tu proyecto expone otros)
        from app.router_query import get_selected_uid  # type: ignore
        return get_selected_uid(session_id)  # debe devolver un str o None
    except Exception:
        pass
    try:
        from app.router_query import get_session  # type: ignore
        s = get_session(session_id)
        if isinstance(s, dict):
            return s.get("selected_uid") or s.get("uid")
    except Exception:
        pass
    return None


# =========================
# Endpoints
# =========================

@router.post("/ask", response_model=QueryOut)
def popularity_entrypoint(payload: QueryIn) -> QueryOut:
    """
    Intenta interpretar:
      - “popularidad/hits de <título> (YYYY) [en <país>] [película/serie]”
      - “top [N] [películas/series] [en <país>] [en YYYY]”
    Defaults:
      - año = actual si no se indica
      - país = GLOBAL si no se indica
      - tipo = ambos si no se indica
    Comportamiento de UID:
      - Si payload.uid está presente → se usa directo (contexto de conversación).
      - Si no, e incluye session_id → se intenta recuperar uid contextual.
      - Si no, se resuelve con buscador determinista (pg_trgm) de app/modules/titles.py.
    """
    text = (payload.text or "").strip()
    text_lc = text.lower()

    want_top = is_top_query(text_lc)
    want_pop = is_popularity_query(text_lc) or not want_top

    # Año por defecto
    explicit_year = extract_year(text_lc)
    year = explicit_year or _current_year()

    # País
    iso, pretty = guess_country(text)
    country_iso2 = iso if (iso and iso != "XX") else None  # XX => Global
    scope_pretty = pretty or ("Global" if not country_iso2 else country_iso2)

    # Tipo de contenido (payload.content_type tiene prioridad si viene)
    detected_ctype = extract_content_type(text_lc)
    content_type = payload.content_type or detected_ctype

    if want_top:
        # Top N (por defecto 10)
        limit = 10
        m = re.search(r"top\s*(\d{1,3})", text_lc)
        if m:
            try:
                limit = max(1, min(100, int(m.group(1))))
            except Exception:
                pass

        items = get_top_hits_by_period(
            year=year,
            country_iso2=country_iso2,
            content_type=content_type,
            limit=limit,
        )
        tbl = "ms.hits_presence_2" if country_iso2 else SETTINGS.hits_global_table
        out = {
            "scope": country_iso2 or "GLOBAL",
            "scope_pretty": scope_pretty,
            "year": year,
            "content_type": content_type,
            "table_used": tbl,
            "items": [{"uid": r["uid"], "title": r.get("title"), "hits_sum": float(r["hits_sum"])} for r in items],
        }
        return QueryOut(kind="top_list", payload=out)

    # Popularidad de un título
    # 1) UID contextual
    uid = payload.uid or _get_uid_from_session(payload.session_id)

    # 2) Resolver por título si no hay UID
    if not uid:
        title = extract_title_candidate(text_lc)
        if not title:
            return QueryOut(kind="not_found", payload={"reason": "no_title_detected"})
        cands = resolve_uid_via_titles_module(title, year=explicit_year)  # si vino (YYYY), lo respetamos
        decision = pick_uid_or_ambiguous(cands)

        if decision["status"] == "not_found":
            return QueryOut(kind="not_found", payload={"reason": "no_title_match", "title": title, "year": year})

        if decision["status"] == "ambiguous":
            return QueryOut(kind="ambiguous", payload={
                "title": title,
                "year": explicit_year,
                "options": decision["options"],
                "message": "Selecciona un ítem por número, UID o IMDb."
            })

        uid = decision["uid"]

    # 3) Calcular contexto de popularidad con las reglas pedidas
    ctx = render_title_hits_with_context(
        uid=uid,
        year=year,                   # por defecto, año actual si no lo dijeron
        country_iso2=country_iso2,   # GLOBAL si no hay país
        content_type=content_type,   # ambos si no hay tipo
    )

    # Agregamos pretty del país por conveniencia del front
    ctx["scope_pretty"] = scope_pretty
    return QueryOut(kind="title_popularity", payload=ctx)