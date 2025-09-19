# metadata_simple_all_tools.py
# -*- coding: utf-8 -*-
from typing import Optional, List, Any, Dict, Tuple
from dataclasses import dataclass
from src.sql_db import db
from src.sql.db_utils_sql import *
from src.sql.constants_sql import *
from src.sql.validators_shared import *
from src.sql.content.queries import *
import re as _re

# -------------------------------------------------------------------
# Normalizador para tolerar llamadas posicionales del orquestador
# -------------------------------------------------------------------
def _normalize_tool_call(args, kwargs):
    """
    Tolerancia a llamadas posicionales:
    - (dict)           → merge con kwargs
    - (str/int/...)    → se mapea a '__arg1'
    - >1 posicionales  → toma el primero como '__arg1'
    """
    if args:
        if len(args) == 1:
            a0 = args[0]
            if isinstance(a0, dict):
                merged = dict(a0)
                merged.update(kwargs or {})
                return merged
            merged = dict(kwargs or {})
            merged.setdefault("__arg1", a0)
            return merged
        merged = dict(kwargs or {})
        merged.setdefault("__arg1", args[0])
        return merged
    return kwargs or {}

# -------------------------------------------------------------------
# Procesamiento común de argumentos
# -------------------------------------------------------------------
def _process_primary_argument(kwargs, allow_type=True, allow_country=True):
    """
    Procesa __arg1 de manera consistente entre todas las funciones.
    """
    primary_arg = kwargs.get("__arg1")
    
    # Solo procesar si no hay filtros explícitos ya definidos
    if not primary_arg or kwargs.get("primary_country_iso") or kwargs.get("type"):
        return
    
    normalized_arg = str(primary_arg).strip().lower()
    
    # Casos especiales: sin filtros
    if normalized_arg in {"*", "all", "any"}:
        return
    
    # Detectar código ISO de país (2 letras alfabéticas)
    if allow_country and len(normalized_arg) == 2 and normalized_arg.isalpha():
        kwargs["primary_country_iso"] = normalized_arg
    elif allow_type:
        # Todo lo demás se trata como tipo
        kwargs["type"] = normalized_arg

def _build_filters_common(kwargs):
    """
    Construye filtros comunes utilizados por múltiples funciones.
    Retorna (conditions, params, applied_filters)
    """
    conditions, params, applied_filters = [], [], []
    
    # Filtro por tipo (maneja tanto 'type' como 'type_')
    type_param = kwargs.get("type")
    if type_param:
        content_type = resolve_content_type(type_param)
        if content_type:
            conditions.append("type = %s")
            params.append(content_type)
            applied_filters.append(f"type={content_type}")
    
    # Filtro por país
    country_iso = kwargs.get("primary_country_iso")
    if country_iso:
        iso_code = resolve_country_iso(country_iso)
        if iso_code:
            conditions.append("primary_country_iso = %s")
            params.append(iso_code)
            applied_filters.append(f"country={iso_code}")
    
    # Filtros por año con validación
    for year_param, operator, label in [
        ("year_from", ">=", "from"),
        ("year_to", "<=", "to")
    ]:
        year_value = kwargs.get(year_param)
        if year_value is not None:
            # Validación simple: si es entero o string que representa entero
            if isinstance(year_value, int) or (isinstance(year_value, str) and str(year_value).isdigit()):
                year_int = int(year_value)
                conditions.append(f"year {operator} %s")
                params.append(year_int)
                applied_filters.append(f"year_{label}={year_int}")
    
    return conditions, params, applied_filters

# -------------------------------------------------------------------
# COUNT
# -------------------------------------------------------------------
def tool_metadata_count(*args, **kwargs):
    """Cuenta de títulos (con filtros opcionales). Tolerante a posicionales y '*'/all/any."""
    kwargs = _normalize_tool_call(args, kwargs)
    _process_primary_argument(kwargs)
    
    conditions, params, applied_filters = _build_filters_common(kwargs)
    
    # Construcción y ejecución de query usando template
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = METADATA_COUNT_SQL.format(
        table_name=META_TBL,
        where_clause=where_clause
    )
    
    rows = db.execute_query(sql, tuple(params))
    filter_desc = ", ".join(applied_filters) or "no-filters"
    return as_tool_payload(rows, ident=f"metadata_simple_all.count | {filter_desc}")

# -------------------------------------------------------------------
# LIST
# -------------------------------------------------------------------
def tool_metadata_list(*args, **kwargs):
    """
    Listado básico (búsqueda, paginación y orden).
    Tolerante a posicionales: __arg1 → title_like si no viene explícito.
    """
    kwargs = _normalize_tool_call(args, kwargs)
    
    # __arg1 como búsqueda por título si no se pasó explícito
    if kwargs.get("__arg1") and not kwargs.get("title_like"):
        kwargs["title_like"] = str(kwargs["__arg1"]).strip()
    
    # Validación y normalización de parámetros
    limit = validate_limit(kwargs.get("limit", DEFAULT_LIMIT))
    order_by = str(kwargs.get("order_by", "title")).lower()
    order_dir = "DESC" if str(kwargs.get("order_dir", "ASC")).upper() == "DESC" else "ASC"
    
    # Validar order_by
    if order_by not in META_ALLOWED_ORDER:
        order_by = "title"
    
    conditions, params, applied_filters = _build_filters_common(kwargs)
    
    # Filtro adicional por título
    title_like = kwargs.get("title_like")
    if title_like:
        conditions.append("title ILIKE %s")
        params.append(f"%{title_like}%")
        applied_filters.append(f"title_like={title_like}")
    
    # Construcción de query usando template
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = METADATA_LIST_SQL.format(
        table_name=META_TBL,
        where_clause=where_clause,
        order_by=order_by,
        order_dir=order_dir
    )
    
    rows = db.execute_query(sql, tuple(params + [limit]))
    
    filter_desc = ", ".join(applied_filters) or "no-filters"
    ident = (
        f"metadata_simple_all.list | {filter_desc} | "
        f"order={order_by} {order_dir} | limit={limit}"
    )
    return as_tool_payload(rows, ident=ident)

# -------------------------------------------------------------------
# DISTINCT 
# -------------------------------------------------------------------
def tool_metadata_distinct(*args, **kwargs):
    """
    Valores únicos de columnas seguras.
    Tolerante a posicionales: __arg1 → column.
    """
    kwargs = _normalize_tool_call(args, kwargs)
    
    # __arg1 como columna si no se pasó 'column'
    if kwargs.get("__arg1") and not kwargs.get("column"):
        kwargs["column"] = str(kwargs["__arg1"]).strip()
    
    limit = validate_limit(kwargs.get("limit", MAX_LIMIT))
    column = str(kwargs.get("column", "")).strip()
    
    # Alias seguros para variantes/typos
    alias_map = {
        "primare_genre": "primary_genre",
        "genre": "primary_genre",
        "country": "primary_country_iso",
        "iso": "primary_country_iso",
    }
    
    # Normalizar columna con alias
    col_norm = alias_map.get(column.lower(), column)
    
    # Validar columna permitida
    if col_norm not in META_ALLOWED_SELECT:
        allowed_cols = sorted(META_ALLOWED_SELECT)
        raise ValueError(f"column '{column}' not allowed; choose one of {allowed_cols}")
    
    # Usar query template
    sql = METADATA_DISTINCT_SQL.format(
        column=col_norm,
        table_name=META_TBL
    )
    
    rows = db.execute_query(sql, (limit,))
    return as_tool_payload(rows, ident=f"metadata_simple_all.distinct | column={col_norm} limit={limit}")

# -------------------------------------------------------------------
# STATS 
# -------------------------------------------------------------------
def tool_metadata_stats(*args, **kwargs):
    """
    Pequeño resumen estadístico:
      total, min_year, max_year, avg_duration, median_duration
    Tolerante a posicionales (__arg1 como ISO2 o type_).
    """
    kwargs = _normalize_tool_call(args, kwargs)
    _process_primary_argument(kwargs)
    
    conditions, params, applied_filters = _build_filters_common(kwargs)
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = METADATA_STATS_SQL.format(where_clause=where_clause)
    
    rows = db.execute_query(sql, tuple(params))
    filter_desc = ", ".join(applied_filters) or "no-filters"
    return as_tool_payload(rows, ident=f"metadata_simple_all.stats | {filter_desc}")

# ---- Freeform __arg1 parser (mejorado) ----
_DEF_SEP = _re.compile(r"[\s,;/]+")

def _parse_arg1_basic(a1: str, kwargs: dict) -> dict:
    """Parser mejorado para __arg1 con más patrones reconocidos."""
    s = (a1 or "").strip()
    if not s: 
        return kwargs
        
    toks = [t for t in _DEF_SEP.split(s) if t]
    out = dict(kwargs)

    # Country ISO2
    if "primary_country_iso" not in out:
        iso = next((t.upper() for t in toks if len(t) == 2 and t.isalpha()), None)
        if iso:
            resolved_iso = resolve_country_iso(iso)
            if resolved_iso:
                out["primary_country_iso"] = resolved_iso

    # Años (patrones como "2020-2023", "desde 2020", etc.)
    year_pattern = _re.compile(r'\b(19|20)\d{2}\b')
    years = [int(m.group()) for m in year_pattern.finditer(s)]
    if len(years) >= 2:
        out.setdefault("year_from", min(years))
        out.setdefault("year_to", max(years))
    elif len(years) == 1:
        # Si hay palabras como "desde", "from", usar como year_from
        if any(word in s.lower() for word in ["desde", "from", "after"]):
            out.setdefault("year_from", years[0])
        else:
            out.setdefault("year_to", years[0])

    return out

# -------------------------------------------------------------------
# Utilidades mejoradas
# -------------------------------------------------------------------
def _like(value: str) -> str:
    """Envuelve valor para búsqueda LIKE, escapando caracteres especiales."""
    if not value:
        return "%"
    # Escapar caracteres especiales de SQL LIKE
    escaped = value.strip().replace('%', '\\%').replace('_', '\\_')
    return f"%{escaped}%"

def _validate_order_by(order_by: Optional[str], default: str = "year") -> str:
    """Validación más estricta de order_by."""
    if not order_by:
        return default
    fld = order_by.strip().lower()
    return fld if fld in META_ALLOWED_ORDER else default

def _validate_select(select: Optional[List[str]]) -> List[str]:
    """Validación mejorada de campos SELECT."""
    default_fields = ["uid", "title", "type", "year", "duration", "primary_genre", "primary_language", "countries_iso"]
    
    if not select:
        return default_fields
        
    # Filtrar solo campos seguros
    safe = [c for c in select if c in META_ALLOWED_SELECT]
    
    # Asegurar que siempre haya al menos uid y title
    if safe:
        if "uid" not in safe:
            safe.insert(0, "uid")
        if "title" not in safe:
            safe.insert(1, "title")
        return safe
    
    return ["uid", "title", "type", "year"]

# --------------------------------------------------------------------
# Builder de consulta con queries externas
# --------------------------------------------------------------------
@dataclass
class MetadataSimpleQuery:
    type: Optional[str] = None
    primary_country_iso: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    age: Optional[str] = None
    duration_min: Optional[int] = None
    duration_max: Optional[int] = None
    title_like: Optional[str] = None
    synopsis_like: Optional[str] = None
    primary_genre: Optional[str] = None
    languages_any: Optional[List[str]] = None
    countries_iso_any: Optional[List[str]] = None
    directors_any: Optional[List[str]] = None
    writers_any: Optional[List[str]] = None
    cast_any: Optional[List[str]] = None
    select: Optional[List[str]] = None
    order_by: Optional[str] = None
    order_dir: str = "DESC"
    limit: Optional[int] = DEFAULT_LIMIT
    offset: Optional[int] = 0
    count_only: bool = False

def _build_like_any(col: str, values: List[str], params: Dict[str, Any], ph_prefix: str) -> str:
    """Construcción mejorada de condiciones LIKE con múltiples valores."""
    if not values:
        return ""
        
    parts = []
    for i, v in enumerate(values):
        if not v or not str(v).strip():
            continue
        key = f"{ph_prefix}{i}"
        params[key] = _like(str(v))
        parts.append(f"{col} ILIKE %({key})s")
        
    return "(" + " OR ".join(parts) + ")" if parts else ""

def build_metadata_simple_all_query(q: MetadataSimpleQuery) -> Tuple[str, Dict[str, Any]]:
    """Builder de query mejorado usando templates externos."""
    params: Dict[str, Any] = {}
    where: List[str] = []

    # Filtros de año con validación
    if q.year_from is not None:
        year_from = int(q.year_from) if isinstance(q.year_from, (str, int)) and str(q.year_from).isdigit() else None
        if year_from:
            where.append("year >= %(y_from)s")
            params["y_from"] = year_from
            
    if q.year_to is not None:
        year_to = int(q.year_to) if isinstance(q.year_to, (str, int)) and str(q.year_to).isdigit() else None
        if year_to:
            where.append("year <= %(y_to)s")
            params["y_to"] = year_to

    # Otros filtros
    if q.type:
        where.append("LOWER(type) = %(type)s")
        params["type"] = q.type.strip().lower()
        
    if q.primary_country_iso:
        iso = resolve_country_iso(q.primary_country_iso)
        if iso:
            where.append("LOWER(primary_country_iso) = %(primary_country_iso)s")
            params["primary_country_iso"] = iso.lower()
            
    if q.age:
        where.append("age ILIKE %(age)s")
        params["age"] = _like(q.age)
        
    if q.duration_min is not None:
        where.append("duration >= %(dmin)s")
        params["dmin"] = int(q.duration_min)
        
    if q.duration_max is not None:
        where.append("duration <= %(dmax)s")
        params["dmax"] = int(q.duration_max)
        
    if q.title_like:
        where.append("title ILIKE %(tlike)s")
        params["tlike"] = _like(q.title_like)
        
    if q.synopsis_like:
        where.append("synopsis ILIKE %(slike)s")
        params["slike"] = _like(q.synopsis_like)
        
    if q.primary_genre:
        resolved_genre = resolve_primary_genre(q.primary_genre)
        where.append("primary_genre ILIKE %(pgen)s")
        params["pgen"] = _like(resolved_genre)

    # Condiciones de array con validación mejorada
    array_conditions = [
        ("languages", q.languages_any, "l_"),
        ("directors", q.directors_any, "dir_"),
        ("writers", q.writers_any, "wri_"),
        ("full_cast", q.cast_any, "cast_")
    ]
    
    for col, values, prefix in array_conditions:
        if values:
            cond = _build_like_any(col, values, params, prefix)
            if cond:
                where.append(cond)

    # Países con resolución de ISO
    if q.countries_iso_any:
        vals = q.countries_iso_any if isinstance(q.countries_iso_any, list) else [q.countries_iso_any]
        norm_vals = [resolve_country_iso(v) for v in vals if v]
        norm_vals = [v for v in norm_vals if v]  # Filtrar None
        if norm_vals:
            cond = _build_like_any("countries_iso", norm_vals, params, "ci_")
            if cond:
                where.append(cond)

    where_sql = " WHERE " + " AND ".join(where) if where else ""

    # Usar template para COUNT
    if q.count_only:
        sql = METADATA_ADVANCED_COUNT_SQL.format(where_clause=where_sql)
        return sql, params

    # Usar template para SELECT
    select_cols = _validate_select(q.select)
    order_by = _validate_order_by(q.order_by)
    order_dir = "DESC" if str(q.order_dir).upper() == "DESC" else "ASC"
    limit = validate_limit(q.limit)
    offset = max(0, int(q.offset or 0))

    sql = METADATA_ADVANCED_SELECT_SQL.format(
        select_cols=", ".join(select_cols),
        where_clause=where_sql,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset
    )

    return sql, params

# --------------------------------------------------------------------
# Runner + Tool mejorados
# --------------------------------------------------------------------
def query_metadata_simple_all(*args, **kwargs) -> List[Dict[str, Any]]:
    """Query runner con manejo mejorado de argumentos."""
    kwargs = _normalize_call_kwargs(args, kwargs)
    q = MetadataSimpleQuery(**kwargs)
    sql, params = build_metadata_simple_all_query(q)
    return db.execute_query(sql, params) or []

def _normalize_call_kwargs(args, kwargs):
    """Normalización mejorada de argumentos de llamada."""
    if args and len(args) == 1 and isinstance(args[0], str):
        kwargs = dict(kwargs or {})
        kwargs["__arg1"] = args[0]
        
    if "__arg1" in kwargs:
        kwargs = _parse_arg1_basic(kwargs.pop("__arg1"), kwargs)
        
    return kwargs

def query_metadata_simple_all_tool(*args, **kwargs) -> str:
    """
    Versión 'tool' mejorada con mejor identificación y manejo de errores.
    """
    kwargs = _normalize_call_kwargs(args, kwargs)
    rows = query_metadata_simple_all(**kwargs) or []
    
    # Construcción de identificador más informativo
    ident_parts = []
    important_params = ["type", "year_from", "year_to", "primary_genre", "title_like", "primary_country_iso"]
    
    for param in important_params:
        value = kwargs.get(param)
        if value not in (None, ""):
            ident_parts.append(f"{param}={value}")
    
    ident = "metadata_simple_all.query"
    if ident_parts:
        ident += " | " + " ".join(ident_parts)
        
    return as_tool_payload(rows, ident=ident)
