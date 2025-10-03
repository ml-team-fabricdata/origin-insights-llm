# origin_insights_llm/__init__.py
"""
Shim de compatibilidad para el código legacy que importaba `origin_insights_llm as oi`.
Redirige a los módulos nuevos en app.modules.*
"""

from typing import Any, Dict, List, Optional, Tuple
import json

from app.modules import titles as _titles
from app.modules import hits as _hits
from app.modules import countries as _countries
from app.modules import availability as _availability
from app.modules import metadata as _metadata


# ---------- BÚSQUEDA DE TÍTULOS ----------
def search_title_candidates(term: str, top_k: int = None, min_similarity: float = None) -> List[Dict[str, Any]]:
    return _titles.search_title_candidates(term, top_k=top_k, min_similarity=min_similarity)

def extract_title_query(text: str) -> Optional[str]:
    # strip_country=True y pasamos guess_country para que limpie nombres de país del texto
    return _titles.extract_title_query(text, strip_country=True, guess_country_fn=_countries.guess_country)


# ---------- METADATA ----------
class GetMetadataByUIDTool:
    """API esperada por router_query: ._run(uid, imdb_id) -> JSON(list[dict])"""
    def _run(self, uid: Optional[str] = None, imdb_id: Optional[str] = None) -> str:
        meta = None
        if uid:
            meta = _metadata.get_metadata_by_uid(uid)
        elif imdb_id:
            meta = _metadata.get_metadata_by_imdb(imdb_id)
        rows = [meta] if meta else []
        return json.dumps(rows, ensure_ascii=False)


# ---------- DISPONIBILIDAD ----------
class GetAvailabilityByUIDTool:
    """API esperada: ._run(uid, imdb_id, iso_alpha2, platform_country, with_prices) -> JSON(list[dict])"""
    def _run(
        self,
        uid: Optional[str] = None,
        imdb_id: Optional[str] = None,
        iso_alpha2: Optional[str] = None,
        platform_country: Optional[str] = None,
        with_prices: bool = False
    ) -> str:
        # Si llega sólo imdb_id, resolvemos uid
        if not uid and imdb_id:
            uid = _metadata.resolve_uid_by_imdb(imdb_id)
        rows = _availability.fetch_availability_by_uid(uid=uid or "", iso2=iso_alpha2 or platform_country, with_prices=with_prices)
        return json.dumps(rows, ensure_ascii=False)

def render_availability(
    rows: List[Dict[str, Any]],
    lang: str = "es",
    country_pretty: Optional[str] = None,
    include_details: bool = False,
    include_prices: bool = False
) -> str:
    return _availability.render_availability(rows, lang=lang, country_pretty=(country_pretty or ""), include_details=include_details, include_prices=include_prices)


# ---------- HITS (popularidad) ----------
def extract_date_range(text: str) -> Tuple[Optional[Any], Optional[Any]]:
    return _hits.extract_date_range(text)

def ensure_hits_range(date_from, date_to, country_iso2: Optional[str]):
    return _hits.ensure_hits_range(date_from, date_to, country_iso2)

def get_top_hits_by_period(
    country_iso2: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 20,
    content_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    return _hits.get_top_hits_by_period(country_iso2=country_iso2, date_from=date_from, date_to=date_to, limit=limit, content_type=content_type)

def render_top_hits(items: List[Dict[str, Any]], country: Optional[str] = None,
                    lang: str = "es", year_used: Optional[int] = None,
                    series_only: bool = False, top_n: Optional[int] = None) -> str:
    return _hits.render_top_hits(items, country=country, lang=lang, year_used=year_used, series_only=series_only, top_n=top_n)

def get_title_hits_sum(uid: Optional[str] = None, imdb_id: Optional[str] = None,
                       country_iso2: Optional[str] = None,
                       date_from: Optional[str] = None, date_to: Optional[str] = None) -> float:
    # Suma sobre filas devueltas por get_hits_by_uid
    if not uid and imdb_id:
        uid = _metadata.resolve_uid_by_imdb(imdb_id)
    if not uid:
        return 0.0
    rows = _hits.get_hits_by_uid(uid=uid, country_iso2=country_iso2, date_from=date_from, date_to=date_to) or []
    return float(sum(float(r.get("hits") or 0) for r in rows))

def render_title_hits_with_context(
    meta: Dict[str, Any],
    hits_sum: float,
    baseline: Optional[Dict[str, Any]],
    lang: str = "es",
    country_pretty: Optional[str] = None,
    year_used: Optional[int] = None
) -> str:
    # Render simple de contexto
    t = meta.get("title") or "-"
    y = meta.get("year")
    where = ""
    if country_pretty: where += f" en {country_pretty}" if lang.startswith("es") else f" in {country_pretty}"
    if year_used: where += f" en {year_used}" if lang.startswith("es") else f" in {year_used}"
    if lang.startswith("es"):
        head = f"HITS totales para {t}{f' ({y})' if y else ''}{where}: **{int(hits_sum)}**."
        if baseline:
            bt = baseline.get("title") or "-"
            bh = baseline.get("total_hits")
            head += f" (Referencia: más popular {bt} con HITS {int(bh) if bh is not None else '-'})"
        return head
    else:
        head = f"Total HITS for {t}{f' ({y})' if y else ''}{where}: **{int(hits_sum)}**."
        if baseline:
            bt = baseline.get("title") or "-"
            bh = baseline.get("total_hits")
            head += f" (Baseline: most popular {bt} with HITS {int(bh) if bh is not None else '-'})"
        return head


# ---------- PAÍSES ----------
def guess_country(text: str):
    return _countries.guess_country(text)