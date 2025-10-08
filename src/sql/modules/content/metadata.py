from src.sql.utils.default_import import *
from src.sql.utils.db_utils_sql import *
from src.sql.utils.constants_sql import *
from src.sql.utils.validators_shared import *
from src.sql.queries.content.queries_metadata import *


def _normalize_args_kwargs(args, kwargs, parse_arg1=False):
    kwargs = normalize_args_kwargs(args, kwargs)

    if parse_arg1 and "__arg1" in kwargs:
        arg1_value = kwargs.get("__arg1", "")
        if str(arg1_value).strip().lower() not in NO_FILTER_KEYWORDS:
            kwargs = _parse_arg1_basic(kwargs.pop("__arg1"), kwargs)
        else:
            kwargs.pop("__arg1", None)

    return kwargs


NO_FILTER_KEYWORDS = {
    "*", "all", "any", "todos", "todo",
    "metadata", "titles", "content", "catalog",
    "database", "db", "full", "complete", "everything",
    "total", "general", "global", "universe"
}


def _process_primary_argument(kwargs, allow_type=True, allow_country=True):
    primary_arg = kwargs.get("__arg1")

    if not primary_arg or kwargs.get("countries_iso") or kwargs.get("type"):
        return

    normalized_arg = str(primary_arg).strip().lower()

    if normalized_arg in NO_FILTER_KEYWORDS:
        return

    if allow_country and len(normalized_arg) == 2 and normalized_arg.isalpha():
        iso_code = resolve_country_iso(normalized_arg)
        if iso_code:
            kwargs["countries_iso"] = normalized_arg
    elif allow_type:
        content_type = resolve_content_type(normalized_arg)
        if content_type in ["Movie", "Series"]:
            kwargs["type"] = normalized_arg


def _build_filters_common(kwargs):
    conditions, params, applied_filters = [], [], []

    type_param = kwargs.get("type")
    if type_param:
        content_type = resolve_content_type(type_param)
        if content_type:
            conditions.append("type = %s")
            params.append(content_type)
            applied_filters.append(f"type={content_type}")

    country_iso = kwargs.get("countries_iso")
    if country_iso:
        # Try to resolve as region first
        region_isos = get_region_iso_list(country_iso)
        if region_isos:
            if len(region_isos) == 1:
                conditions.append("countries_iso = %s")
                params.append(region_isos[0])
                applied_filters.append(f"country={region_isos[0]}")
            else:
                # Multiple countries - use IN clause
                placeholders = ", ".join(["%s"] * len(region_isos))
                conditions.append(f"countries_iso IN ({placeholders})")
                params.extend(region_isos)
                applied_filters.append(f"region={country_iso}")
        else:
            # Try as individual country
            iso_code = resolve_country_iso(country_iso)
            if iso_code:
                conditions.append("countries_iso = %s")
                params.append(iso_code)
                applied_filters.append(f"country={iso_code}")

    for year_param, operator, label in [
        ("year_from", ">=", "from"),
        ("year_to", "<=", "to")
    ]:
        year_value = kwargs.get(year_param)
        if year_value is not None:
            if isinstance(year_value, int) or (isinstance(year_value, str) and str(year_value).isdigit()):
                year_int = int(year_value)
                if 1900 <= year_int <= 2100:
                    conditions.append(f"year {operator} %s")
                    params.append(year_int)
                    applied_filters.append(f"year_{label}={year_int}")

    return conditions, params, applied_filters


@tool
def tool_metadata_count(*args, **kwargs):
    kwargs = _normalize_args_kwargs(args, kwargs)

    primary_arg = str(kwargs.get("__arg1", "")).strip().lower()
    if primary_arg in NO_FILTER_KEYWORDS:
        kwargs.pop("__arg1", None)
    else:
        _process_primary_argument(kwargs)

    conditions, params, applied_filters = _build_filters_common(kwargs)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = METADATA_COUNT_SQL.format(
        table_name=META_TBL,
        where_clause=where_clause
    )

    logger.debug(f"Executing count query: {sql} with params: {params}")

    rows = db.execute_query(sql, tuple(params))
    filter_desc = ", ".join(applied_filters) or "no-filters"
    return handle_query_result(rows, "metadata_simple_all.count", filter_desc)


@tool
def tool_metadata_list(*args, **kwargs):
    kwargs = _normalize_args_kwargs(args, kwargs)

    primary_arg = kwargs.get("__arg1")
    if primary_arg and not kwargs.get("title_like"):
        kwargs["title_like"] = str(primary_arg).strip()
        kwargs["column"] = str(kwargs["__arg1"]).strip()

    limit = validate_limit(kwargs.get("limit", MAX_LIMIT))
    column = str(kwargs.get("column", "")).strip()

    alias_map = {
        "primare_genre": "primary_genre",
        "genre": "primary_genre",
        "country": "countries_iso",
        "iso": "countries_iso",
        "language": "primary_language",
        "lang": "primary_language",
    }

    col_norm = alias_map.get(column.lower(), column)

    if col_norm not in META_ALLOWED_SELECT:
        allowed_cols = sorted(META_ALLOWED_SELECT)
        raise ValueError(
            f"column '{column}' not allowed; choose one of {allowed_cols}")

    sql = METADATA_DISTINCT_SQL.format(
        column=col_norm,
        table_name=META_TBL
    )

    rows = db.execute_query(sql, (limit,))
    return handle_query_result(rows, "metadata_simple_all.distinct", f"column={col_norm} limit={limit}")


@tool
def tool_metadata_stats(*args, **kwargs):
    kwargs = _normalize_args_kwargs(args, kwargs)

    primary_arg = str(kwargs.get("__arg1", "")).strip().lower()
    if primary_arg in NO_FILTER_KEYWORDS:
        kwargs.pop("__arg1", None)
    else:
        _process_primary_argument(kwargs)

    conditions, params, applied_filters = _build_filters_common(kwargs)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = METADATA_STATS_SQL.format(where_clause=where_clause)

    logger.debug(f"Executing stats query: {sql} with params: {params}")

    rows = db.execute_query(sql, tuple(params))
    filter_desc = ", ".join(applied_filters) or "no-filters"
    return handle_query_result(rows, "metadata_simple_all.stats", filter_desc)


_DEF_SEP = re.compile(r"[\s,;/]+")


def _parse_arg1_basic(a1: str, kwargs: dict) -> dict:
    s = (a1 or "").strip()
    if not s:
        return kwargs

    if s.lower() in NO_FILTER_KEYWORDS:
        return kwargs

    toks = [t for t in _DEF_SEP.split(s) if t]
    out = dict(kwargs)

    if "countries_iso" not in out:
        iso = next((t.upper()
                   for t in toks if len(t) == 2 and t.isalpha()), None)
        if iso:
            resolved_iso = resolve_country_iso(iso)
            if resolved_iso:
                out["countries_iso"] = resolved_iso

    year_pattern = re.compile(r'\b(19|20)\d{2}\b')
    years = [int(m.group()) for m in year_pattern.finditer(s)]
    if len(years) >= 2:
        out.setdefault("year_from", min(years))
        out.setdefault("year_to", max(years))
    elif len(years) == 1:
        if any(word in s.lower() for word in ["desde", "from", "after", "since"]):
            out.setdefault("year_from", years[0])
        elif any(word in s.lower() for word in ["hasta", "until", "before", "to"]):
            out.setdefault("year_to", years[0])

    return out


def _validate_order_by(order_by: Optional[str], default: str = "year") -> str:
    if not order_by:
        return default
    fld = order_by.strip().lower()
    return fld if fld in META_ALLOWED_ORDER else default


def _validate_select(select: Optional[List[str]]) -> List[str]:
    default_fields = ["uid", "title", "type", "year", "duration",
                      "primary_genre", "primary_language", "countries_iso"]

    if not select:
        return default_fields

    safe = [c for c in select if c in META_ALLOWED_SELECT]

    if safe:
        if "uid" not in safe:
            safe.insert(0, "uid")
        if "title" not in safe:
            safe.insert(1, "title")
        return safe

    return ["uid", "title", "type", "year"]


@dataclass
class MetadataSimpleQuery:
    type: Optional[str] = None
    countries_iso: Optional[str] = None
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


def build_metadata_simple_all_query(q: MetadataSimpleQuery) -> Tuple[str, Dict[str, Any]]:
    params: Dict[str, Any] = {}
    where: List[str] = []

    if q.year_from is not None:
        year_from = int(q.year_from) if isinstance(
            q.year_from, (str, int)) and str(q.year_from).isdigit() else None
        if year_from and 1900 <= year_from <= 2100:
            where.append("year >= %(y_from)s")
            params["y_from"] = year_from

    if q.year_to is not None:
        year_to = int(q.year_to) if isinstance(
            q.year_to, (str, int)) and str(q.year_to).isdigit() else None
        if year_to and 1900 <= year_to <= 2100:
            where.append("year <= %(y_to)s")
            params["y_to"] = year_to

    if q.type:
        content_type = resolve_content_type(q.type)
        if content_type in ["Movie", "Series"]:
            where.append("type = %(type)s")
            params["type"] = content_type

    if q.countries_iso:
        iso = resolve_country_iso(q.countries_iso)
        if iso:
            where.append("countries_iso = %(countries_iso)s")
            params["countries_iso"] = iso

    if q.age:
        where.append("age ILIKE %(age)s")
        params["age"] = build_like_pattern(q.age)

    if q.duration_min is not None:
        where.append("duration >= %(dmin)s")
        params["dmin"] = int(q.duration_min)

    if q.duration_max is not None:
        where.append("duration <= %(dmax)s")
        params["dmax"] = int(q.duration_max)

    if q.title_like:
        where.append("title ILIKE %(tlike)s")
        params["tlike"] = build_like_pattern(q.title_like)
    if q.synopsis_like:
        where.append("synopsis ILIKE %(slike)s")
        params["slike"] = build_like_pattern(q.synopsis_like)

    if q.primary_genre:
        resolved_genre = resolve_primary_genre(q.primary_genre)
        if resolved_genre:
            where.append("primary_genre = %(pgen)s")
            params["pgen"] = resolved_genre

    array_conditions = [
        ("languages", q.languages_any, "l_"),
        ("directors", q.directors_any, "dir_"),
        ("writers", q.writers_any, "wri_"),
        ("countries_iso", q.countries_iso_any, "ci_")
    ]

    for col, values, prefix in array_conditions:
        if values:
            cond = build_like_any(col, values, params, prefix)
            if cond:
                where.append(cond)

    if q.countries_iso_any:
        vals = q.countries_iso_any if isinstance(q.countries_iso_any, list) else [
            q.countries_iso_any]
        norm_vals = [resolve_country_iso(v) for v in vals if v]
        norm_vals = [v for v in norm_vals if v]
        if norm_vals:
            cond = build_like_any("countries_iso", norm_vals, params, "ci_")
            if cond:
                where.append(cond)

    where_sql = " WHERE " + " AND ".join(where) if where else ""

    if q.count_only:
        sql = METADATA_ADVANCED_COUNT_SQL.format(where_clause=where_sql)
        return sql, params

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


@tool
def query_metadata_simple_all(*args, **kwargs) -> List[Dict[str, Any]]:
    kwargs = _normalize_args_kwargs(args, kwargs, parse_arg1=True)
    q = MetadataSimpleQuery(**kwargs)
    sql, params = build_metadata_simple_all_query(q)
    logger.debug(f"Executing query: {sql} with params: {params}")

    return db.execute_query(sql, params) or []


@tool
def query_metadata_simple_all_tool(*args, **kwargs) -> List[Dict]:
    kwargs = _normalize_args_kwargs(args, kwargs, parse_arg1=True)
    rows = query_metadata_simple_all(**kwargs) or []

    ident_parts = []
    important_params = ["type", "year_from", "year_to",
                        "primary_genre", "title_like", "countries_iso"]

    for param in important_params:
        value = kwargs.get(param)
        if value not in (None, ""):
            ident_parts.append(f"{param}={value}")

    ident = " | ".join(ident_parts) if ident_parts else "all"

    return handle_query_result(rows, "metadata_simple_all.query", ident)
