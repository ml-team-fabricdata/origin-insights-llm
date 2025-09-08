# app/agent/sqlgen.py
from __future__ import annotations
import os
import re
from typing import Optional, Dict, Any, List

from infra.config import SETTINGS
from infra.db import run_sql

# ---------- Whitelist de tablas/columnas permitidas ----------
# (Basado en tu esquema compartido)
_ALLOWED: Dict[str, List[str]] = {
    "ms.hits_presence_2": [
        "uid","imdb","country","content_type","date_hits","hits","week","title","year",
        "piracynormscore","piracyscore","imdbnormscore","imdbscore","twitterscore","twitternormscore",
        "youtubescore","youtubenormscore","input","piracyplatformsnumber","tmdb_id","cdbscore","cdbnormscore",
        "deltaposition","position","poster_image","deltapositionint","average","hits_relative","currentyear",
        "release_date","weeks_since_release","hits_local","hits_category","trend_category","trend_score",
        "twitter_nps","imputed_hits","hits_raw","topnormscore","topdetails","hits_new","hits_new2",
        "google_trends_show","googletrendsnormscore"
    ],
    "ms.hits_global": [
        "id","week","date","currentyear","uid","imdb","content_type","year","imdbscore",
        "imdbnormscore","piracyscore","piracynormscore","hits","piracyplatformsnumber","date_hits","hits_raw"
    ],
    "ms.new_cp_metadata_estandar": [
        "uid","title","full_title","original_title","type","source","year","title_year","age","duration",
        "duration_source","imdb_id","tmdb_id","tvdb_id","eidr_id","synopsis","url_imdb","url_tvdb","url_tmdb",
        "url_eidr","english_title","full_asset_title","release_date","primary_genre","genres","genre_weight",
        "scripted","languages","primary_language","countries","countries_iso","primary_country_iso",
        "primary_country","primary_company","production_companies","production_type","cast","full_cast",
        "directors","seasons","episodes","keywords","score","poster_image","backdrop_image","video","writers",
        "hispanic","hispanic_origen","hispanic_language","content_budget","content_gross_usa","content_gross_world"
    ],
    "ms.new_cp_presence": [
        "id","sql_unique","enter_on","out_on","global_id","iso_alpha2","iso_global","platform_country",
        "platform_name","platform_code","package_code","package_code2","content_id","hash_unique","uid","type",
        "clean_title","is_original","is_kids","is_local","isbranded","is_exclusive","imdb_id","tmdb_id",
        "eidr_id","tvdb_id","duration","content_status","registry_status","uid_updated","created_at",
        "plan_name","permalink","plat_uid","active_episodes","active_seasons","apac","europe","lionsgate",
        "sony_apac","total_time","pais_uid","sony_origin"
    ],
}

_ALLOWED_TABLES = set(_ALLOWED.keys())
_WRITE_WORDS = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|MERGE|CALL)\b", re.I)
_FORBIDDEN_TOKENS = re.compile(r";\s*--|/\*|\*/|\b(pg_)\w+", re.I)  # evitar comment tricks / funciones
_ONLY_SELECT = re.compile(r"^\s*SELECT\b", re.I)

def _is_column_allowed(tbl: str, col: str) -> bool:
    return col == "*" or col.lower() in {c.lower() for c in _ALLOWED.get(tbl, [])}

def _all_columns_allowed(sql: str) -> bool:
    """
    Validación muy simple: busca patrones 'FROM <tbl> ... SELECT ... col' y comprueba cols.
    Para seguridad real, parsear SQL (p.ej. sqlglot) y validar AST. Aquí mantenemos liviano.
    """
    # Rápido: no permitimos JOIN implícitos a tablas fuera de whitelist
    for m in re.finditer(r"\bFROM\s+([a-zA-Z0-9_.]+)", sql, re.I):
        if m.group(1) not in _ALLOWED_TABLES:
            return False
    for m in re.finditer(r"\bJOIN\s+([a-zA-Z0-9_.]+)", sql, re.I):
        if m.group(1) not in _ALLOWED_TABLES:
            return False
    # Columnas: heurística (aceptamos '*' y nombres simples)
    # Si necesitás granularidad, parseá con sqlglot en una versión futura.
    return True

def _build_llm_prompt(question: str) -> str:
    """
    Pide SOLO un SELECT seguro sobre las tablas whitelisteadas.
    """
    return (
        "You are a SQL assistant for Fabric. Generate ONE safe, readable SELECT query for PostgreSQL.\n"
        "Rules:\n"
        "- Only read data (no writes). Use SELECT only.\n"
        "- Allowed schemas/tables: ms.hits_presence_2, ms.hits_global, ms.new_cp_metadata_estandar, ms.new_cp_presence.\n"
        "- Prefer filters by year on date_hits when the question mentions a year.\n"
        "- Use explicit table names (schema.table).\n"
        "- Keep it deterministic. No vendor/model mentions. Do not add comments.\n"
        "- Limit rows to 50 when returning lists.\n"
        f"Question:\n{question}\n\n"
        "Return ONLY the SQL, nothing else."
    )

def _call_llm(question: str) -> Optional[str]:
    try:
        from infra.bedrock import call_bedrock_llm1  # type: ignore
        r = call_bedrock_llm1(_build_llm_prompt(question)) or {}
        raw = (r.get("completion") or r.get("text") or "").strip()
        # limpiar fences si las hubiera
        raw = re.sub(r"^```sql\s*|\s*```$", "", raw, flags=re.I|re.S).strip()
        return raw or None
    except Exception:
        return None

def _is_safe_sql(sql: str) -> bool:
    if not sql or len(sql) > 8000:
        return False
    if not _ONLY_SELECT.match(sql):
        return False
    if _WRITE_WORDS.search(sql):
        return False
    if _FORBIDDEN_TOKENS.search(sql):
        return False
    return _all_columns_allowed(sql)

def try_sql_answer(question: str) -> Optional[Dict[str, Any]]:
    """
    Si EXPERIMENTAL_SQLGEN=1 y ENABLE_FREEFORM_LLM=1: intenta generar un SQL seguro (solo SELECT).
    Si falla una validación o no hay backend, retorna None.
    """
    if os.getenv("EXPERIMENTAL_SQLGEN", "0") != "1":
        return None
    if not SETTINGS.enable_freeform_llm:
        return None

    sql = _call_llm(question)
    if not sql:
        return None
    if not _is_safe_sql(sql):
        return None

    try:
        rows = run_sql(sql) or []
        # Reducimos filas a 50 para evitar respuestas enormes
        rows = rows[:50]
        return {"sql": sql, "rows": rows}
    except Exception:
        return None