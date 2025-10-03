# app/router_determinista.py
from fastapi import APIRouter, Query
from typing import Optional
from app.modules.titles import search_title_candidates
from app.modules.metadata import get_metadata_by_uid, get_metadata_by_imdb
from app.modules.availability import fetch_availability_by_uid, render_availability
from app.modules.countries import guess_country
from app.modules.hits import (
    extract_date_range, ensure_hits_range, get_hits_by_uid,
    get_top_hits_by_period, render_top_hits
)

router = APIRouter()

@router.get("/v1/title/search")
def title_search(q: str, top_k: int = 20, min_sim: float = 0.80):
    rows = search_title_candidates(q, top_k=top_k, min_similarity=min_sim)
    return {"items": rows}

@router.get("/v1/metadata")
def metadata(uid: Optional[str] = None, imdb_id: Optional[str] = None):
    if not uid and imdb_id:
        m = get_metadata_by_imdb(imdb_id)
        return {"item": m}
    m = get_metadata_by_uid(uid or "")
    return {"item": m}

@router.get("/v1/availability")
def availability(uid: str, q: Optional[str] = None, with_prices: bool = False, lang: str = "es"):
    iso2, pretty = guess_country(q or "")
    rows = fetch_availability_by_uid(uid, iso2=iso2, with_prices=with_prices)
    text = render_availability(rows, lang=lang, country_pretty=(pretty or iso2), include_prices=with_prices)
    return {"items": rows, "text": text, "country": pretty or iso2}

@router.get("/v1/hits")
def hits(uid: Optional[str] = None,
         country: Optional[str] = None,
         date_from: Optional[str] = None,
         date_to: Optional[str] = None,
         lang: str = "es", top: int = 20, kind: Optional[str] = None):
    if uid:
        # serie/película específica
        df, dt = extract_date_range((date_from or "") + " " + (date_to or ""))
        df_s, dt_s, _ = ensure_hits_range(df, dt, country)
        rows = get_hits_by_uid(uid, country_iso2=country, date_from=df, date_to=dt)
        return {"items": rows}
    # ranking
    items = get_top_hits_by_period(country_iso2=country, date_from=date_from, date_to=date_to,
                                   limit=top, content_type=kind)
    text = render_top_hits(items, country=country, lang=lang, top_n=top, series_only=(kind == "series"))
    return {"items": items, "text": text}