# app/modules/hits.py
import os
import re
import datetime as dt
from typing import Optional, Tuple, List, Dict, Any

from infra.db import get_conn  # asumiendo que ya lo tienes (igual que db_health)
from app.modules import metadata as m_meta

# ===================== Utilidades de fechas =====================

_YEAR_RE = re.compile(r"\b(20\d{2}|19\d{2})\b")

def extract_date_range(text: str) -> Tuple[Optional[dt.date], Optional[dt.date]]:
    """
    Detecta año en el texto. Si encuentra un año Y, devuelve [Y-01-01, Y-12-31].
    Si no hay año, devuelve (None, None) para que el caller decida.
    """
    if not text:
        return None, None
    m = _YEAR_RE.search(text)
    if not m:
        return None, None
    y = int(m.group(1))
    y = max(1900, min(2100, y))
    return dt.date(y, 1, 1), dt.date(y, 12, 31)

def ensure_hits_range(df: Optional[dt.date], dt_to: Optional[dt.date], country_iso2: Optional[str]) -> Tuple[dt.date, dt.date, int]:
    """
    Si no vino rango, usar año actual.
    Devuelve (date_from, date_to, used_year).
    """
    today = dt.date.today()
    if df and dt_to:
        return df, dt_to, df.year
    return dt.date(today.year, 1, 1), dt.date(today.year, 12, 31), today.year

# ===================== Consultas =====================

def _resolve_uid(uid: Optional[str], imdb_id: Optional[str]) -> Optional[str]:
    if uid:
        return uid
    if imdb_id:
        return m_meta.resolve_uid_by_imdb(imdb_id)
    return None

def get_title_hits_sum(
    uid: Optional[str] = None,
    imdb_id: Optional[str] = None,
    country_iso2: Optional[str] = None,
    date_from: Optional[dt.date] = None,
    date_to: Optional[dt.date] = None,
) -> float:
    """
    Suma HITS para un título:
      - si country_iso2 está presente → usa ms.hits_presence_2 filtrando por country
      - si no hay país:
          * si HITS_GLOBAL_TABLE está configurada, usa esa tabla (col: uid, date_hits, hits)
          * si no, suma en hits_presence_2 sin filtrar país (agrega todos los países)
    """
    the_uid = _resolve_uid(uid, imdb_id)
    if not the_uid:
        return 0.0

    df = date_from or dt.date(dt.date.today().year, 1, 1)
    dtf = date_to or dt.date(dt.date.today().year, 12, 31)

    global_table = os.getenv("HITS_GLOBAL_TABLE", "").strip()  # ej: "ms.hits_presence_global"
    sql = ""
    params: List[Any] = []

    if country_iso2:
        sql = """
            SELECT COALESCE(SUM(hits),0)
            FROM ms.hits_presence_2
            WHERE uid = %s
              AND country = %s
              AND date_hits BETWEEN %s AND %s
        """
        params = [the_uid, country_iso2.upper(), df, dtf]
    else:
        if global_table:
            # usa tabla global si existe (columnas: uid, date_hits, hits)
            sql = f"""
                SELECT COALESCE(SUM(hits),0)
                FROM {global_table}
                WHERE uid = %s
                  AND date_hits BETWEEN %s AND %s
            """
            params = [the_uid, df, dtf]
        else:
            # fallback: agrega sobre todos los países
            sql = """
                SELECT COALESCE(SUM(hits),0)
                FROM ms.hits_presence_2
                WHERE uid = %s
                  AND date_hits BETWEEN %s AND %s
            """
            params = [the_uid, df, dtf]

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return float(row[0] or 0.0)

def get_top_hits_by_period(
    country_iso2: Optional[str],
    date_from: dt.date,
    date_to: dt.date,
    limit: int = 20,
    content_type: Optional[str] = None,  # "movie" | "series" | None
) -> List[Dict[str, Any]]:
    """
    Ranking por periodo. Agrega HITS de ms.hits_presence_2 (filtrado por país si se provee)
    y joinea metadatos básicos desde ms.new_cp_metadata_estandar.
    """
    base = """
        SELECT hp.uid,
               COALESCE(SUM(hp.hits),0) AS hits_sum
        FROM ms.hits_presence_2 hp
        WHERE hp.date_hits BETWEEN %s AND %s
    """
    params: List[Any] = [date_from, date_to]

    if country_iso2:
        base += " AND hp.country = %s"
        params.append(country_iso2.upper())

    base += " GROUP BY hp.uid"

    # envolvemos para unir metadatos
    sql = f"""
        WITH agg AS (
            {base}
        )
        SELECT a.uid,
               a.hits_sum,
               m.title,
               m.year,
               m.type,
               m.directors,
               m.imdb_id
        FROM agg a
        LEFT JOIN ms.new_cp_metadata_estandar m
          ON m.uid = a.uid
    """

    # filtro por tipo si se requiere
    if content_type in ("movie", "series"):
        sql += " WHERE LOWER(COALESCE(m.type,'')) = %s"
        params.append(content_type.lower())

    sql += " ORDER BY a.hits_sum DESC NULLS LAST LIMIT %s"
    params.append(limit)

    out: List[Dict[str, Any]] = []
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        for row in cur.fetchall():
            out.append({
                "uid": row[0],
                "hits_sum": float(row[1] or 0.0),
                "title": row[2],
                "year": row[3],
                "type": row[4],
                "directors": row[5],
                "imdb_id": row[6],
            })
    return out

# ===================== Render helpers =====================

def render_top_hits(
    items: List[Dict[str, Any]],
    country: Optional[str],
    lang: str,
    year_used: Optional[int] = None,
    series_only: bool = False,
    top_n: Optional[int] = None,
) -> str:
    label = "series" if series_only else "títulos"
    if lang.startswith("es"):
        hdr = f"TOP {top_n or len(items)} {label} por HITS" + (f" en {country}" if country else "")
        if year_used:
            hdr += f" ({year_used})"
    else:
        lbl = "series" if series_only else "titles"
        hdr = f"TOP {top_n or len(items)} {lbl} by HITS" + (f" in {country}" if country else "")
        if year_used:
            hdr += f" ({year_used})"

    lines = [hdr + ":"]
    for i, it in enumerate(items, start=1):
        t = it.get("title") or "-"
        y = it.get("year")
        s = int(round(it.get("hits_sum") or 0))
        imdb = it.get("imdb_id") or "-"
        lines.append(f"{i}. {t}{f' ({y})' if y else ''} — HITS={s} — IMDb: {imdb}")
    return "\n".join(lines)

def render_title_hits_with_context(
    meta: Dict[str, Any],
    hits_sum: float,
    lang: str,
    country_pretty: Optional[str] = None,
    year_used: Optional[int] = None,
) -> str:
    t = meta.get("title") or "(título)"
    y = meta.get("year")
    scope = f"en {country_pretty}" if (country_pretty) else "global"
    s = int(round(hits_sum or 0))
    if lang.startswith("es"):
        head = f"Popularidad (HITS) de «{t}»{f' ({y})' if y else ''} — {scope}"
        if year_used:
            head += f" — {year_used}"
        body = f"Suma anual de HITS: {s}"
        tail = "¿Quieres comparar con otro título o ver el TOP por país/año?"
        return f"{head}\n{body}\n{tail}"
    else:
        head = f"Popularity (HITS) for “{t}”{f' ({y})' if y else ''} — {scope}"
        if year_used:
            head += f" — {year_used}"
        body = f"Yearly HITS sum: {s}"
        tail = "Would you like to compare with another title or see the country/year TOP?"
        return f"{head}\n{body}\n{tail}"