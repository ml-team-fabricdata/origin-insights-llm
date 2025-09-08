# app/modules/hits.py
import re, datetime as dt
from typing import Any, Dict, List, Optional, Tuple
from infra.db import run_sql
from infra.config import SETTINGS

_year = re.compile(r"\b(19[0-9]{2}|20[0-3][0-9])\b")

def _date_to_str(d):
    if not d: return None
    return d.isoformat() if hasattr(d, "isoformat") else str(d)

def _full_year(df: Optional[str], dt_: Optional[str]) -> Optional[int]:
    try:
        if not df or not dt_: return None
        m1 = re.match(r"^(\d{4})-01-01$", df); m2 = re.match(r"^(\d{4})-12-31$", dt_)
        if m1 and m2 and m1.group(1) == m2.group(1): return int(m1.group(1))
    except Exception: pass
    return None

def get_default_hits_year(country_iso2: Optional[str] = None) -> Optional[int]:
    try:
        if SETTINGS.offline_mode: return dt.date.today().year
        if country_iso2:
            rows = run_sql("""
                SELECT MAX(currentyear)::int AS y
                FROM ms.hits_presence_2
                WHERE country = %(c1)s OR country = %(c2)s
            """, {"c1": country_iso2, "c2": country_iso2}) or []
            y = rows[0].get("y") if rows else None
            return int(y) if y is not None else dt.date.today().year
        rows = run_sql("SELECT MAX(currentyear)::int AS y FROM ms.hits_global;") or []
        y = rows[0].get("y") if rows else None
        return int(y) if y is not None else dt.date.today().year
    except Exception:
        return dt.date.today().year

def ensure_hits_range(date_from, date_to, country_iso2: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    df_str = _date_to_str(date_from); dt_str = _date_to_str(date_to)
    if df_str or dt_str: return df_str, dt_str, _full_year(df_str, dt_str)
    y = get_default_hits_year(country_iso2) or dt.date.today().year
    return f"{y}-01-01", f"{y}-12-31", y

def extract_date_range(text: str) -> Tuple[Optional[dt.date], Optional[dt.date]]:
    if not text: return None, None
    m = re.findall(r"\b(20[0-3]\d|19\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b", text)
    if m and len(m) >= 1:
        dates = []
        for y, mo, d in m[:2]:
            try: dates.append(dt.date(int(y), int(mo), int(d)))
            except Exception: pass
        if len(dates) == 2: return min(dates), max(dates)
        if len(dates) == 1: return dates[0], None
    y = _year.findall(text)
    if y:
        try:
            yy = int(y[0]); return dt.date(yy,1,1), dt.date(yy,12,31)
        except Exception: pass
    return None, None

def get_hits_by_uid(uid: str, country_iso2: Optional[str] = None,
                    date_from: Optional[dt.date] = None, date_to: Optional[dt.date] = None) -> List[Dict[str, Any]]:
    if SETTINGS.offline_mode or not uid: return []
    df = _date_to_str(date_from); dt_ = _date_to_str(date_to); full = _full_year(df, dt_)
    if country_iso2:
        dcol = "date_hits"; ccol = "country"
        if full is not None:
            return run_sql(f"""
                SELECT {dcol}::date AS date, hits
                FROM ms.hits_presence_2
                WHERE uid=%(u)s AND {ccol}=%(c)s AND currentyear = %(y)s
                ORDER BY date;
            """, {"u": uid, "c": country_iso2, "y": full})
        return run_sql(f"""
            SELECT {dcol}::date AS date, hits
            FROM ms.hits_presence_2
            WHERE uid=%(u)s AND {ccol}=%(c)s
              AND (%(df)s IS NULL OR {dcol}::date >= %(df)s)
              AND (%(dt)s IS NULL OR {dcol}::date <= %(dt)s)
            ORDER BY date;
        """, {"u": uid, "c": country_iso2, "df": date_from, "dt": date_to})
    gdcol = "date"
    if full is not None:
        return run_sql(f"""
            SELECT {gdcol}::date AS date, hits
            FROM ms.hits_global
            WHERE uid=%(u)s AND currentyear = %(y)s
            ORDER BY 1;
        """, {"u": uid, "y": full})
    return run_sql(f"""
        SELECT {gdcol}::date AS date, hits
        FROM ms.hits_global
        WHERE uid=%(u)s
          AND (%(df)s IS NULL OR {gdcol}::date >= %(df)s)
          AND (%(dt)s IS NULL OR {gdcol}::date <= %(dt)s)
        ORDER BY 1;
    """, {"u": uid, "df": date_from, "dt": date_to})

def _fmt_hits(x: Any) -> str:
    if x is None: return "0"
    from decimal import Decimal, ROUND_HALF_UP
    d = Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return str(int(d)) if d == d.to_integral_value() else f"{d:.2f}"

def get_top_hits_by_period(country_iso2: Optional[str] = None,
                           date_from: Optional[str] = None,
                           date_to: Optional[str] = None,
                           limit: int = 20,
                           content_type: Optional[str] = None) -> List[Dict[str, Any]]:
    if SETTINGS.offline_mode: return []
    df, dt_, full = date_from, date_to, None
    if df and dt_:
        m1 = re.match(r"^(\d{4})-01-01$", df); m2 = re.match(r"^(\d{4})-12-31$", dt_)
        if m1 and m2 and m1.group(1) == m2.group(1): full = int(m1.group(1))
    params: Dict[str, Any] = {"lim": limit, "df": df, "dt": dt_, "y": full}
    ctype_clause = ""
    if content_type:
        ctype_clause = " AND LOWER(m.type) = %(ctype)s "
        params["ctype"] = content_type.lower()
    if country_iso2:
        where_c = " AND country = %(c)s"
        params["c"] = country_iso2
        if full is not None:
            return run_sql(f"""
                WITH src AS (
                  SELECT uid, hits
                  FROM ms.hits_presence_2
                  WHERE uid IS NOT NULL AND currentyear = %(y)s {where_c}
                ), agg AS (
                  SELECT uid, ROUND(SUM(hits)::numeric, 2) AS total_hits
                  FROM src GROUP BY uid
                )
                SELECT a.uid, a.total_hits, m.title, m.year, m.imdb_id, m.type
                FROM agg a JOIN ms.new_cp_metadata_estandar m ON m.uid = a.uid
                WHERE 1=1 {ctype_clause}
                ORDER BY a.total_hits DESC LIMIT %(lim)s;
            """, params) or []
        return run_sql(f"""
            WITH src AS (
              SELECT uid, date_hits::date AS d, hits
              FROM ms.hits_presence_2
              WHERE uid IS NOT NULL {where_c}
                AND (%(df)s IS NULL OR date_hits >= %(df)s::date)
                AND (%(dt)s IS NULL OR date_hits <= %(dt)s::date)
            ), agg AS (
              SELECT uid, ROUND(SUM(hits)::numeric, 2) AS total_hits
              FROM src GROUP BY uid
            )
            SELECT a.uid, a.total_hits, m.title, m.year, m.imdb_id, m.type
            FROM agg a JOIN ms.new_cp_metadata_estandar m ON m.uid = a.uid
            WHERE 1=1 {ctype_clause}
            ORDER BY a.total_hits DESC LIMIT %(lim)s;
        """, params) or []
    if full is not None:
        return run_sql(f"""
            WITH src AS (
              SELECT uid, hits
              FROM ms.hits_global
              WHERE uid IS NOT NULL AND currentyear = %(y)s
            ), agg AS (
              SELECT uid, ROUND(SUM(hits)::numeric, 2) AS total_hits
              FROM src GROUP BY uid
            )
            SELECT a.uid, a.total_hits, m.title, m.year, m.imdb_id, m.type
            FROM agg a JOIN ms.new_cp_metadata_estandar m ON m.uid = a.uid
            WHERE 1=1 {ctype_clause}
            ORDER BY a.total_hits DESC LIMIT %(lim)s;
        """, params) or []
    return run_sql(f"""
        WITH src AS (
          SELECT uid, COALESCE(date, date_hits)::date AS d, hits
          FROM ms.hits_global
          WHERE uid IS NOT NULL
            AND (%(df)s IS NULL OR COALESCE(date, date_hits) >= %(df)s::date)
            AND (%(dt)s IS NULL OR COALESCE(date, date_hits) <= %(dt)s::date)
        ), agg AS (
          SELECT uid, ROUND(SUM(hits)::numeric, 2) AS total_hits
          FROM src GROUP BY uid
        )
        SELECT a.uid, a.total_hits, m.title, m.year, m.imdb_id, m.type
        FROM agg a JOIN ms.new_cp_metadata_estandar m ON m.uid = a.uid
        WHERE 1=1 {ctype_clause}
        ORDER BY a.total_hits DESC LIMIT %(lim)s;
    """, params) or []

def render_top_hits(items: List[Dict[str, Any]], country: Optional[str] = None,
                    lang: str = "es", year_used: Optional[int] = None,
                    series_only: bool = False, top_n: Optional[int] = None) -> str:
    if not items: return "Sin resultados de popularidad." if lang.startswith("es") else "No popularity results."
    n = top_n or len(items)
    pretty_country = country
    if lang.startswith("es"):
        head = ("La serie más popular" if series_only and n == 1 else
                f"Top {n} series más populares" if series_only else
                "El título más popular" if n == 1 else f"Top {n} títulos más populares")
        where = ""
        if pretty_country: where += f" en {pretty_country}"
        if year_used: where += f" en {year_used}"
        header = head + (where + ":" if where else ":")
        lines = []
        for i, it in enumerate(items[:n], start=1):
            t = it.get("title") or "-"; y = it.get("year"); hits = _fmt_hits(it.get("total_hits"))
            lines.append(f"{i}. {t}{f' ({y})' if y else ''} — HITS: {hits}")
        return header + "\n" + "\n".join(lines)
    else:
        head = ("The most popular series" if series_only and n == 1 else
                f"Top {n} most popular series" if series_only else
                "The most popular title" if n == 1 else f"Top {n} most popular titles")
        where = ""
        if pretty_country: where += f" in {pretty_country}"
        if year_used: where += f" in {year_used}"
        header = head + (where + ":" if where else ":")
        lines = []
        for i, it in enumerate(items[:n], start=1):
            t = it.get("title") or "-"; y = it.get("year"); hits = _fmt_hits(it.get("total_hits"))
            lines.append(f"{i}. {t}{f' ({y})' if y else ''} — HITS: {hits}")
        return header + "\n" + "\n".join(lines)

def render_hits(hits_rows: List[Dict[str, Any]], scope: str = "global", lang: str = "es") -> str:
    if not hits_rows:
        return "No hay HITS registrados." if lang == "es" else "No HITS recorded."
    total = sum(int(r.get("hits") or 0) for r in hits_rows)
    if lang == "es":
        return f"Puntuación (HITS) {('global' if scope=='global' else 'por país')}: **{total}** (últimos {len(hits_rows)} días)"
    return f"HITS score {('global' if scope=='global' else 'by country')}: **{total}** (last {len(hits_rows)} days)"

# --- NUEVO: texto de HITS para un título con contexto de #1 del período ---
def render_title_hits_with_context(
    meta: Dict[str, Any],
    hits_sum: float,
    baseline: Optional[Dict[str, Any]],
    *,
    lang: str = "es",
    country_pretty: Optional[str] = None,
    year_used: Optional[int] = None
) -> str:
    t = meta.get("title") or "-"
    y = meta.get("year")
    where = ""
    if country_pretty:
        where += (" en " if lang.startswith("es") else " in ") + str(country_pretty)
    if year_used:
        where += (" en " if lang.startswith("es") else " in ") + str(year_used)

    if lang.startswith("es"):
        head = f"{t}{f' ({y})' if y else ''} — HITS: {_fmt_hits(hits_sum)}{where}."
        if baseline:
            bt = baseline.get("title") or "-"
            by = baseline.get("year")
            bscore = _fmt_hits(baseline.get("total_hits"))
            ctx = f"Para referencia, el #1{(' en ' + country_pretty) if country_pretty else ''}{(' en ' + str(year_used)) if year_used else ''} fue {bt}{f' ({by})' if by else ''} con HITS {bscore}."
            return head + "\n" + ctx
        return head
    else:
        head = f"{t}{f' ({y})' if y else ''} — HITS: {_fmt_hits(hits_sum)}{where}."
        if baseline:
            bt = baseline.get("title") or "-"
            by = baseline.get("year")
            bscore = _fmt_hits(baseline.get("total_hits"))
            ctx = f"For context, the #1{(' in ' + country_pretty) if country_pretty else ''}{(' in ' + str(year_used)) if year_used else ''} was {bt}{f' ({by})' if by else ''} with HITS {bscore}."
            return head + "\n" + ctx
        return head