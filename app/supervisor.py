# app/supervisor.py
from typing import Dict
from app.modules import titles, hits, countries, metadata

def _lang_from_text(s: str) -> str:
    s = (s or "").lower()
    # heurística muy simple; /query ya hace detección real
    if any(w in s for w in [" dónde ", " donde ", "película", "pelicula", "serie", "sinopsis", "popularidad", "hits"]):
        return "es"
    return "en"

def is_popularity_query(q: str) -> bool:
    s = (q or "").lower()
    return any(k in s for k in ["hits", "popularidad", "top ", " ranking", "más popular", "most popular"])

def is_metadata_query(q: str) -> bool:
    s = (q or "").lower()
    return any(k in s for k in ["sinopsis", "de qué trata", "de que trata", "plot", "synopsis"])

def handle_query(query: str) -> Dict:
    """
    Ruta liviana para /ask y /llm/ask.
    Nota: la lógica completa vive en /query (router_query). Esto sólo da respuestas básicas
    y evita fallar en import-time.
    """
    lang = _lang_from_text(query)

    # 1) HITS simple (TOP títulos por país/año si aparecen en el texto)
    if is_popularity_query(query):
        df, dt = hits.extract_date_range(query)
        iso2, pretty = countries.guess_country(query)
        df_s, dt_s, used_year = hits.ensure_hits_range(df, dt, iso2)
        items = hits.get_top_hits_by_period(country_iso2=iso2, date_from=df_s, date_to=dt_s, limit=10)
        text = hits.render_top_hits(items, country=(pretty or iso2), lang=lang, year_used=used_year)
        return {"ok": True, "type": "hits", "data": text}

    # 2) Metadata muy básica (autopick + sinopsis si está)
    if is_metadata_query(query):
        term = titles.extract_title_query(query, strip_country=True, guess_country_fn=countries.guess_country) or query
        cands = titles.search_title_candidates(term, top_k=10, min_similarity=None)
        pick = titles.safe_autopick(cands) or (cands[0] if cands else None)
        if not pick:
            msg = "No encontré coincidencias." if lang == "es" else "No matches found."
            return {"ok": True, "type": "metadata", "data": msg}
        m = metadata.get_metadata_by_uid(pick.get("uid"))
        if not m:
            msg = "No se encontraron metadatos." if lang == "es" else "No metadata found."
            return {"ok": True, "type": "metadata", "data": msg}
        # Resumen cortito
        t = m.get("title") or "-"
        y = m.get("year")
        syn = (m.get("synopsis") or "").strip()
        if lang == "es":
            out = f"{t}{f' ({y})' if y else ''}. Sinopsis: {syn or 'Sin sinopsis disponible.'}"
        else:
            out = f"{t}{f' ({y})' if y else ''}. Synopsis: {syn or 'No synopsis available.'}"
        return {"ok": True, "type": "metadata", "data": out}

    # 3) Fallback: sugerir usar /query (que es el flujo completo)
    if lang == "es":
        return {"ok": True, "type": "fallback",
                "data": "Usa el endpoint /query para disponibilidad, HITS y desambiguación (el chat web ya lo usa)."}
    else:
        return {"ok": True, "type": "fallback",
                "data": "Use the /query endpoint for availability, HITS and disambiguation (the web chat already uses it)."}