from src.sql.utils.db_utils_sql import *
from src.sql.utils.default_import import *
from src.sql.queries.business.queries_business import *
from src.sql.utils.validators_shared import *


def normalize_langgraph_params(*args, **kwargs) -> dict:
    """
    Normalize parameters from LangGraph tool calls.
    Handles nested kwargs format: {'kwargs': {'param1': 'value1', ...}}
    """
    # Handle LangGraph nested kwargs format
    if "kwargs" in kwargs and isinstance(kwargs["kwargs"], dict):
        nested_kwargs = kwargs["kwargs"]
        other_params = {k: v for k, v in kwargs.items() if k != "kwargs"}
        merged = dict(nested_kwargs)
        merged.update(other_params)
        kwargs = merged

    # Handle positional arguments
    if args:
        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, dict):
                merged = dict(arg)
                merged.update(kwargs)
                return merged
            elif isinstance(arg, str):
                parsed = json.loads(arg) if arg.startswith("{") else None
                if isinstance(parsed, dict):
                    parsed.update(kwargs)
                    return parsed
                # Treat as simple parameter
                merged = dict(kwargs)
                merged.setdefault("__arg1", arg)
                return merged
        # Multiple positional args
        merged = dict(kwargs)
        merged.setdefault("__arg1", args[0])
        return merged

    return kwargs or {}


def safe_tool_response(result: Any, operation_name: str = "operation") -> str:
    """
    Ensure tool response is never empty for Bedrock API compliance.
    """
    if result is None or (isinstance(result, list) and len(result) == 0):
        return json.dumps(
            {
                "status": "no_results",
                "message": f"No data found for {operation_name}.",
                "data": [],
                "count": 0,
            },
            ensure_ascii=False,
            indent=2,
        )

    if isinstance(result, str) and not result.strip():
        return json.dumps(
            {
                "status": "empty_response",
                "message": f"Empty response from {operation_name}.",
                "data": [],
                "count": 0,
            },
            ensure_ascii=False,
            indent=2,
        )

    if isinstance(result, (list, dict)):
        return json.dumps(
            {
                "status": "success",
                "data": result,
                "count": len(result) if isinstance(result, list) else 1,
                "operation": operation_name,
            },
            ensure_ascii=False,
            indent=2,
        )

    return str(result) or f"No content from {operation_name}."


def validate_days_back(days: Optional[int], default: int = DEFAULT_DAYS_BACK) -> int:
    """Validate and normalize days_back parameter."""
    if not isinstance(days, int) or days <= 0:
        return default
    return max(1, days)


def get_date_range(days_back: int) -> Tuple[str, str]:
    """Get ISO date range for the last N days."""
    today = date.today()
    date_from = (today - timedelta(days=days_back)).isoformat()
    date_to = today.isoformat()
    return date_from, date_to


def parse_genres(genres_in: Optional[object]) -> Optional[List[str]]:
    """Parse genres from various input formats."""
    if genres_in is None:
        return None

    if isinstance(genres_in, (list, tuple, set)):
        out = [str(g).strip() for g in genres_in if str(g).strip()]
        return out or None

    s = str(genres_in).strip()
    if not s:
        return None

    # Try parsing as JSON array
    if s.startswith("[") and s.endswith("]"):
        arr = json.loads(s) if s else None
        if isinstance(arr, list):
            out = [str(g).strip() for g in arr if str(g).strip()]
            return out or None

    # Fallback: split by comma or semicolon
    parts = [p.strip() for p in s.replace(";", ",").split(",")]
    out = [p for p in parts if p]
    return out or None


def compute_window_anchored_to_table(days_back: int) -> Optional[Tuple[str, str]]:
    """Compute date window anchored to MAX(date_hits) when no current data exists."""
    logger.info(
        f"Computing window anchored to table with days_back={days_back}")

    rows = db.execute_query(QUERY_MAX_DATE)
    if not rows:
        return None

    max_dt = rows[0]["max_date"] if isinstance(rows[0], dict) else rows[0][0]
    if not max_dt:
        return None

    if isinstance(max_dt, str):
        max_dt = datetime.fromisoformat(max_dt).date()
    elif isinstance(max_dt, datetime):
        max_dt = max_dt.date()

    validated_days_back = validate_days_back(days_back, default=7)
    date_from = (max_dt - timedelta(days=validated_days_back)).isoformat()
    date_to = max_dt.isoformat()
    return date_from, date_to


# =============================================================================
# GENRE AND PREMIERE FUNCTIONS
# =============================================================================


def get_recent_premieres_by_country(
    country: str, days_back: int = 7, limit: int = 30
) -> List[Dict]:
    """Get recent premieres available in a country within the last N days."""
    if not country:
        return [{"message": "Valid country (ISO-2) required."}]

    # Policy: restrict search to last 7 days only
    if days_back != 7:
        return [{"message": "Only 7-day lookback allowed (days_back=7)."}]

    days_back = validate_days_back(days_back, default=7)
    date_from, date_to = get_date_range(days_back)
    resolved_country = resolve_country_iso(country)

    logger.debug(f"Date range: {date_from} → {date_to}")
    logger.debug(
        f"[recent_premieres] country={resolved_country}, days_back={days_back}, range=({date_from},{date_to}), limit={limit}"
    )

    params = {
        "country": resolved_country,
        "date_from": date_from,
        "date_to": date_to,
        "limit": limit,
    }

    query = QUERY_RECENT_PREMIERES
    rows = db.execute_query(query, params)
    ident = f"{resolved_country} last {days_back}d"
    return handle_query_result(rows, "recent premieres by country", ident)


def get_recent_top_premieres_by_country(
    country: str,
    days_back: int = 7,
    limit: int = 30,
    content_type: Optional[str] = None,
    genre: Optional[str] = None,
) -> List[Dict]:
    """Get recent premieres ranked by peak hits within the time window."""
    if not country:
        return [{"message": "Valid country (ISO-2) required."}]

    days_back = validate_days_back(days_back, default=7)
    date_from, date_to = get_date_range(days_back)
    resolved_country = resolve_country_iso(country)

    params = [resolved_country, date_from, date_to]
    where_clauses = [
        "p.iso_alpha2 = %s",
        "(p.out_on IS NULL)",
        "m.release_date BETWEEN %s AND %s",
    ]

    if content_type:
        ct = resolve_content_type(content_type)
        if ct is None:
            return [{"message": f"Unknown type: '{content_type}'. Use movie/series."}]
        where_clauses.append("m.type = %s")
        params.append(ct)

    if genre:
        resolved_genre = resolve_primary_genre(genre)
        if resolved_genre is None:
            return [
                {
                    "message": f"Unknown genre: '{genre}'. Try Horror, Action, Comedy, Drama..."
                }
            ]
        where_clauses.append("m.primary_genre = %s")
        params.append(resolved_genre)

    query_template = QUERY_RECENT_TOP_PREMIERES
    query = query_template.format(
        where_clauses=" AND ".join(where_clauses), limit=limit
    )

    params_scored = params + [date_from, date_to, date_from, date_to]
    rows = db.execute_query(query, tuple(params_scored))
    ident = f"{resolved_country} last {days_back}d (top by hits)"
    return handle_query_result(rows, "recent top premieres by country", ident)



def _max_date_hits() -> date:
    row = db.execute_query(f"SELECT MAX(date_hits)::date AS mx FROM {HITS_PRESENCE_TBL};", []) or []
    return row[0]["mx"] or datetime.now().date()

def _clamp_rolling(max_d: date, days: int, prev_days: int):
    cur_to   = max_d
    cur_from = max_d - timedelta(days=days-1)
    prev_to  = cur_from - timedelta(days=1)
    prev_from= prev_to  - timedelta(days=prev_days-1)
    return cur_from, cur_to, prev_from, prev_to

def get_genre_momentum(
    country: Optional[str],
    days: int = 30,
    prev_days: Optional[int] = None,
    content_type: Optional[str] = None,
    limit: int = 20,
) -> List[Dict]:
    """
    Ranking de géneros por momentum (ventana actual vs previa).
    - country: ISO-2 o None para global. Acepta aliases: GLOBAL, WORLD, ALL.
    - days / prev_days: tamaño de ventanas (en días). Si prev_days es None, usa days.
    - content_type: 'movie' | 'series' | None
    - limit: 1..200
    """

    # Normaliza país
    if country and country.strip().upper() in {"GLOBAL", "WORLD", "ALL", "NONE", "NULL"}:
        country = None

    # Valida ventanas
    days = validate_days_back(days, default=30)
    prev_days = validate_days_back(prev_days if prev_days is not None else days, default=days)

    # Rango de fechas
    max_d = _max_date_hits()
    cur_from, cur_to, prev_from, prev_to = _clamp_rolling(max_d, days, prev_days)
    min_from, max_to = min(cur_from, prev_from), max(cur_to, prev_to)

    # Tablas y filtro de país
    if not country:
        hits_table     = HITS_GLOBAL_TBL
        country_clause = ""
        country_label  = ""
    else:
        iso = resolve_country_iso(country or "")
        if not iso:
            return [{"message": f"Unknown country: '{country}'"}]
        hits_table     = HITS_PRESENCE_TBL
        country_clause = " AND h.iso_alpha2 = %s"
        country_label  = iso

    # Filtros por tipo de contenido
    ct_hits_clause = ""
    ct_meta_clause = ""
    params: List[object] = [cur_from, cur_to, prev_from, prev_to, min_from, max_to]
    if country:
        params.append(country_label)

    if content_type:
        ct = resolve_content_type(content_type)
        if not ct:
            return [{"message": f"Unknown type: '{content_type}'. Use movie/series."}]
        ct_hits_clause = " AND h.content_type = %s"
        ct_meta_clause = " AND m.type = %s"
        params.extend([ct, ct])

    # Clamp de límite
    try:
        limit_int = int(limit)
    except Exception:
        limit_int = 20
    limit_int = max(1, min(limit_int, 200))
    params.append(limit_int)

    # SQL (solo interpolar identificadores/clauses; valores con %s)
    sql = QUERY_GENRE_MOMENTUM.format(
        HITS_TABLE=hits_table,
        META_TBL=META_TBL,
        COUNTRY_CLAUSE=country_clause,
        CT_HITS_CLAUSE=ct_hits_clause,
        CT_META_CLAUSE=ct_meta_clause,
    )

    # Log seguro (sin aplicar % sobre el SQL)
    logger.debug(
        "genre_momentum cur=%s..%s prev=%s..%s country=%s type=%s limit=%s",
        cur_from, cur_to, prev_from, prev_to, country_label or "GLOBAL", content_type or "-", limit_int
    )

    rows = db.execute_query(sql, tuple(params)) or []
    ident = f"{country_label or 'GLOBAL'} cur[{cur_from}..{cur_to}] vs prev[{prev_from}..{prev_to}]"
    return handle_query_result(rows, "genre momentum", ident)
# =============================================================================
# PRESENCE (PLATFORM) FUNCTIONS
# =============================================================================


# def query_platforms_for_title(uid: str, limit: int = 50) -> List[Dict]:
#     """Get all platforms carrying a specific title."""
#     logger.info(
#         f"query_platforms_for_title called with uid={uid}, limit={limit}")

#     if not uid:
#         return [{"message": "uid required"}]

#     query = QUERY_PLATFORMS_FOR_TITLE
#     result = db.execute_query(query, (uid, limit))

#     logger.info(
#         f"Platforms queried for {uid}, results: {len(result) if result else 0}")
#     return handle_query_result(result, "platforms for title (uid)", uid)


# def query_platforms_for_uid_by_country(uid: str, country: str = None) -> List[Dict]:
#     """Get platforms for a UID within a specific country."""
#     logger.info(
#         f"query_platforms_for_uid_by_country called with uid={uid}, country={country}"
#     )

#     if not uid:
#         return [{"message": "uid required"}]

#     # If no country provided, fall back to generic platforms query
#     if not country:
#         logger.info(
#             "No country provided, falling back to generic platforms query")
#         return query_platforms_for_title(uid)

#     resolved_country = resolve_country_iso(country)
#     if not resolved_country:
#         return [{"message": f"Invalid country code: {country}"}]

#     query = QUERY_PLATFORMS_FOR_TITLE_BY_COUNTRY
#     result = db.execute_query(query, (uid, resolved_country))
#     return handle_query_result(
#         result, "platforms for title by country", f"{uid} @ {resolved_country}"
#     )


def get_platform_exclusives(platform_name: str, country: str = "US", limit: int = 30):
    """
    Get titles exclusive to a platform within a country.
    """
    logger.info(
        f"get_platform_exclusives called with platform_name={platform_name}, country={country}, limit={limit}"
    )
    if not platform_name:
        return [{"message": "Platform name required"}]

    resolved_country = resolve_country_iso(country)
    resolved_platform = resolve_platform_name(platform_name)
    ident = f"exclusives {resolved_platform} @ {resolved_country}"

    rows = db.execute_query(
        PLATFORM_EXCLUSIVES_SQL, (resolved_platform, resolved_country, limit)
    )
    return handle_query_result(rows, "platform exclusives", ident)


def compare_platforms_for_title(title_: str):
    """
    Compare which platforms carry a given title (exact match).
    """
    logger.info(f"compare_platforms_for_title called with title_={title_}")
    if not title_:
        return [{"message": "Title required"}]

    rows = db.execute_query(COMPARE_PLATFORMS_FOR_TITLE_SQL, (title_,))
    logger.info(
        f"Platforms queried for {title_}, results: {len(rows) if rows else 0}")
    return handle_query_result(rows, "compare platforms for title", title_)


# =============================================================================
# TOP GLOBAL FUNCTIONS
# =============================================================================


def get_top_by_uid(uid: str):
    if not uid:
        return [{"message": "UID required"}]
    rows = db.execute_query(UID_RATING_SQL, (uid,))
    return handle_query_result(rows, "Rating by uid", f"{uid}")


def get_top_by_country(
    country_input: str = None, year: int | None = None, date_range=None, limit: int = 20
):
    """
    Get top titles by country with optional year filter.
    """
    logger.info(
        f"get_top_by_country called with country_input={country_input}, year={year}, date_range={date_range}, limit={limit}"
    )

    if not country_input:
        return [{"message": "Valid country required."}]

    resolved_country = resolve_country_iso(country_input)
    logger.debug(f"Resolved country: {resolved_country}")

    if not resolved_country:
        return [
            {
                "message": f"No valid country found for '{country_input}'. Try: US, UK, CA, etc."
            }
        ]

    if year is not None:
        # con año
        rows = db.execute_query(
            TOP_BY_COUNTRY_SQL, (resolved_country, year, limit))
    else:
        # sin año
        rows = db.execute_query(
            TOP_BY_COUNTRY_NO_YEAR_SQL, (resolved_country, limit))

    return handle_query_result(rows, "top by country", f"{country_input}")


def get_top_generic(
    country: Optional[str] = None,
    platform: Optional[str] = None,
    genre: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: Optional[int] = None,
    days_back: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    currentyear: Optional[int] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    *,
    region: Optional[str] = None,
    countries_list: Optional[List[str]] = None,
    # Aliases
    type: Optional[str] = None,   # alias de content_type
    year: Optional[int] = None,   # alias de currentyear
) -> List[Dict[str, Any]]:
    """Generic top titles query with flexible filtering, sin helpers extra."""

    # -------- Normalizaciones únicas --------
    normalized_content_type = resolve_content_type(
        content_type) or resolve_content_type(type)

    resolved_currentyear = (
        int(currentyear) if currentyear is not None
        else (int(year) if year is not None else None)
    )

    normalized_platform = resolve_platform_name(platform) if platform else None
    normalized_genre = resolve_primary_genre(genre) if genre else None

    # Límite seguro inline
    try:
        limit_val = int(limit) if limit is not None else 20
    except (TypeError, ValueError):
        limit_val = 20
    if limit_val < 1:
        limit_val = 1
    if limit_val > 200:
        limit_val = 200

    # Geografía inline
    resolved_country = resolve_country_iso(country) if country else None
    iso_set: List[str] = []
    if not resolved_country and (region or countries_list):
        if region:
            iso_set = resolve_region_isos(region) or []
        if not iso_set and countries_list:
            iso_set = [c.strip().upper()
                       for c in countries_list if isinstance(c, str) and c.strip()]

    print(
        f"[DEBUG] get_top_generic | ct={normalized_content_type} platform={normalized_platform} "
        f"genre={normalized_genre} country={resolved_country} iso_set={iso_set} "
        f"year={resolved_currentyear} y_from={year_from} y_to={year_to} "
        f"days_back={days_back} date_from={date_from} date_to={date_to} limit={limit_val}"
    )

    # Routing
    if resolved_country or iso_set:
        return get_top_presence(
            resolved_country=resolved_country,
            iso_set=iso_set,
            platform=normalized_platform,
            genre=normalized_genre,
            content_type=normalized_content_type,
            limit=limit_val,
            days_back=days_back,
            date_from=date_from,
            date_to=date_to,
            currentyear=resolved_currentyear,
            year_from=year_from,
            year_to=year_to,
        )
    else:
        return get_top_global(
            platform=normalized_platform,
            genre=normalized_genre,
            content_type=normalized_content_type,
            limit=limit_val,
            days_back=days_back,
            date_from=date_from,
            date_to=date_to,
            currentyear=resolved_currentyear,
            year_from=year_from,
            year_to=year_to,
        )


def get_top_presence(
    resolved_country: Optional[str],
    iso_set: List[str],
    platform: Optional[str],
    genre: Optional[str],
    content_type: Optional[str],
    limit: int,
    days_back: Optional[int],
    date_from: Optional[str],
    date_to: Optional[str],
    currentyear: Optional[int],
    year_from: Optional[int],
    year_to: Optional[int],
) -> List[Dict[str, Any]]:
    """Optimized version that applies filters in JOINs for maximum performance (sin helpers)."""

    params: List[Any] = []
    where: List[str] = []
    joins: List[str] = []

    needs_metadata = bool(resolved_country or iso_set or genre)
    if needs_metadata:
        joins.append(f"INNER JOIN {PRES_TBL} AS np ON np.uid = h.uid")
        if genre:
            joins.append(f"INNER JOIN {META_TBL} AS m ON m.uid = h.uid")

    if resolved_country:
        where.append("np.iso_alpha2 = %s")
        params.append(resolved_country)
    elif iso_set:
        if len(iso_set) == 1:
            where.append("np.iso_alpha2 = %s")
            params.append(iso_set[0])
        else:
            conds = []
            for iso in iso_set:
                conds.append("np.iso_alpha2 ILIKE %s")
                params.append(f"%{iso}%")
            if conds:
                where.append("(" + " OR ".join(conds) + ")")

    # Contenido
    if content_type:
        where.append("h.content_type = %s")
        params.append(content_type)
    if platform:
        where.append("np.platform_name ILIKE %s")
        params.append(platform)
    if genre:
        where.append("m.primary_genre ILIKE %s")
        params.append(genre)

    # Temporal inline (columna de presence: h.date_hits)
    if days_back is not None:
        validated = validate_days_back(days_back, default=7)
        window = compute_window_anchored_to_table(validated)
        if window:
            df, dt = window
            where.append("h.date_hits BETWEEN %s AND %s")
            params.extend([df, dt])
    else:
        if date_from:
            where.append("h.date_hits >= %s")
            params.append(date_from)
        if date_to:
            where.append("h.date_hits <= %s")
            params.append(date_to)

    # Año inline (presence usa h.year)
    if currentyear is not None:
        where.append("h.year = %s")
        params.append(int(currentyear))
    if year_from is not None:
        where.append("h.year >= %s")
        params.append(int(year_from))
    if year_to is not None:
        where.append("h.year <= %s")
        params.append(int(year_to))

    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    joins = list(dict.fromkeys(joins))
    print(joins)
    joins_clause = " ".join(joins)

    query_template = QUERY_TOP_PRESENCE_WITH_METADATA if needs_metadata else QUERY_TOP_PRESENCE_NO_METADATA
    query = query_template.format(
        joins_clause=joins_clause, where_clause=where_clause)

    params.append(limit)

    print(f"[PRESENCE SQL] {query}")
    print(f"[PRESENCE params] {tuple(params)}")

    rows = db.execute_query(query, tuple(params))
    return build_result(
        rows, "presence", resolved_country, iso_set, platform,
        genre, content_type, limit, days_back, date_from, date_to,
        currentyear, year_from, year_to
    )


def get_top_global(
    platform: Optional[str],
    genre: Optional[str],
    content_type: Optional[str],
    limit: int,
    days_back: Optional[int],
    date_from: Optional[str],
    date_to: Optional[str],
    currentyear: Optional[int],
    year_from: Optional[int],
    year_to: Optional[int],
) -> List[Dict[str, Any]]:
    """
    Top global (sin país). Si se pide género o se selecciona campo de metadata,
    agrega JOIN a metadata (m). Evita referenciar m.* sin haberlo unido.
    """
    params: List[Any] = []
    where: List[str] = []
    joins: List[str] = []

    # ¿Necesitamos metadata?
    needs_meta = bool(genre)

    needs_metadata = bool(genre)
    if needs_metadata:
        joins.append(f"INNER JOIN {PRES_TBL} AS np ON np.uid = h.uid INNER JOIN {META_TBL} AS m ON m.uid = h.uid")
    if days_back is not None:
        validated = validate_days_back(days_back, default=7)
        window = compute_window_anchored_to_table(validated)
        if window:
            df, dt = window
            where.append("h.date_hits BETWEEN %s AND %s")
            params.extend([df, dt])
    else:
        if date_from:
            where.append("h.date_hits >= %s")
            params.append(date_from)
        if date_to:
            where.append("h.date_hits <= %s")
            params.append(date_to)

    if currentyear is not None:
        where.append("h.year = %s")
        params.append(int(currentyear))
    if year_from is not None:
        where.append("h.year >= %s")
        params.append(int(year_from))
    if year_to is not None:
        where.append("h.year <= %s")
        params.append(int(year_to))

    if content_type:
        where.append("m.type = %s")
        params.append(content_type)

    if genre:
        where.append("m.primary_genre ILIKE %s")
        params.append(genre)

    if platform:
        where.append("np.platform_name ILIKE %s")
        params.append(platform)

    joins_clause = " ".join(dict.fromkeys(joins))
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    query_template = QUERY_TOP_GLOBAL_WITH_META if needs_metadata else QUERY_TOP_GLOBAL_NO_META
    query = query_template.format(joins_clause=joins_clause, where_clause=where_clause)

    params.append(limit)

    # Debug opcional
    print(f"[GLOBAL SQL] {query}")
    print(f"[GLOBAL params] {tuple(params)}")

    rows = db.execute_query(query, tuple(params)) or []
    return rows


def build_result(
    rows: List[Any],
    query_type: str,
    resolved_country: Optional[str],
    iso_set: List[str],
    platform: Optional[str],
    genre: Optional[str],
    content_type: Optional[str],
    limit: int,
    days_back: Optional[int],
    date_from: Optional[str],
    date_to: Optional[str],
    currentyear: Optional[int],
    year_from: Optional[int],
    year_to: Optional[int],
) -> List[Dict[str, Any]]:
    """Build result with logging and year/currentyear normalization."""

    window_id = (
        f"rolling_{days_back}d"
        if days_back is not None
        else ("custom_range" if (date_from or date_to) else "all_time")
    )
    if query_type == "presence":
        loc_id = (
            f"country={resolved_country}"
            if resolved_country
            else f"countries={iso_set}"
        )
    else:
        loc_id = "global"

    ident_parts = [
        loc_id,
        f"platform={platform or ''}",
        f"genre={genre or ''}",
        f"type={content_type or ''}",
        f"window={window_id}",
        (f"currentyear={currentyear}" if currentyear is not None else ""),
        (f"year_from={year_from}" if year_from is not None else ""),
        (f"year_to={year_to}" if year_to is not None else ""),
    ]
    ident = " ".join(p for p in ident_parts if p)

    logger.info(f"{query_type.upper()}: {ident}")
    logger.info(f"rows={len(rows or [])}")

    # Normalize to ensure year/currentyear in final payload
    norm_rows: List[Dict[str, Any]] = []
    for r in rows or []:
        d = dict(r) if not isinstance(r, dict) else r.copy()

        # year: take alias hit_year if it exists
        if "year" not in d and d.get("hit_year") is not None:
            d["year"] = d["hit_year"]
        # currentyear: take alias current_year if it exists
        if "currentyear" not in d and d.get("current_year") is not None:
            d["currentyear"] = d["current_year"]

        # clean internal aliases
        d.pop("hit_year", None)
        d.pop("current_year", None)

        norm_rows.append(d)

    return handle_query_result(norm_rows, f"top ({query_type})", ident)


# =============================================================================
# CONVENIENCE WRAPPER FUNCTIONS
# =============================================================================


def get_top_by_genre(genre_input: str, limit: int = 10) -> List[Dict]:
    """Simple wrapper for top titles by genre."""
    return get_top_generic(genre=genre_input, limit=limit)


def get_top_by_type(content_type: str, limit: int = 10) -> List[Dict]:
    """Simple wrapper for top titles by content type."""
    return get_top_generic(content_type=content_type, limit=limit)


def get_top_by_genre_in_platform_country(
    genre_input: str, platform_name: str, country_iso: str, limit: int = 10
) -> List[Dict]:
    """Get top titles by genre within a specific platform and country."""
    genre_input = resolve_primary_genre(genre_input)

    return get_top_generic(
        genre=genre_input,
        platform=platform_name,
        country=country_iso,
        limit=limit,
    )


# =============================================================================
# TOOL-SAFE WRAPPER FUNCTIONS
# =============================================================================


def get_recent_premieres_by_country_tool(
    country: str, days_back: int = 7, limit: int = 30
) -> str:
    """Tool-safe wrapper for recent premieres query."""
    rows = get_recent_premieres_by_country(country, days_back, limit)
    return safe_tool_response(
        rows, f"recent_premieres {country} {days_back}d limit={limit}"
    )


def get_recent_top_premieres_by_country_tool(
    country: str,
    days_back: int = 7,
    limit: int = 30,
    content_type: Optional[str] = None,
    genre: Optional[str] = None,
) -> str:
    """Tool-safe wrapper for recent top premieres query."""
    rows = get_recent_top_premieres_by_country(
        country, days_back, limit, content_type, genre
    )
    return safe_tool_response(
        rows,
        f"recent_top {country} {days_back}d type={content_type or 'any'} genre={genre or 'any'} limit={limit}",
    )


# def query_platforms_for_title_tool(*args, **kwargs) -> str:
#     """Tool-safe wrapper for platforms by title query."""
#     # Normalize parameters from LangGraph
#     params = normalize_langgraph_params(*args, **kwargs)

#     # Extract uid from various possible parameter formats
#     uid = (
#         params.get("uid")
#         or params.get("__arg1")
#         or params.get("title_uid")
#         or (args[0] if args and isinstance(args[0], str) else None)
#     )

#     limit = params.get("limit", 10)

#     if not uid:
#         return safe_tool_response(
#             [{"message": "UID parameter required"}
#              ], "platforms_for_title_missing_uid"
#         )

#     # Call the main function
#     rows = query_platforms_for_title(uid, limit)
#     operation_name = f"platforms_for_uid {uid} limit={limit}"
#     return safe_tool_response(rows, operation_name)


# def query_platforms_for_uid_by_country_tool(*args, **kwargs) -> str:
#     """Tool-safe wrapper for platforms by title and country query."""
#     # Normalize parameters from LangGraph
#     params = normalize_langgraph_params(*args, **kwargs)

#     # Extract uid from various possible parameter formats
#     uid = (
#         params.get("uid")
#         or params.get("__arg1")
#         or params.get("title_uid")
#         or (args[0] if args and isinstance(args[0], str) else None)
#     )

#     country = (
#         params.get("country") or params.get(
#             "iso_alpha2") or params.get("country_code")
#     )

#     if not uid:
#         return safe_tool_response(
#             [{"message": "UID parameter required"}
#              ], "platforms_by_country_missing_uid"
#         )

#     # Call the main function
#     rows = query_platforms_for_uid_by_country(uid, country)
#     operation_name = f"platforms_for_uid_by_country {uid}@{country or 'all'}"
#     return safe_tool_response(rows, operation_name)


def get_platform_exclusives_tool(
    platform_name: str, country: str = "US", limit: int = 30
) -> str:
    """Tool-safe wrapper for platform exclusives query."""
    rows = get_platform_exclusives(platform_name, country, limit)
    return safe_tool_response(
        rows, f"platform_exclusives {platform_name}@{country} limit={limit}"
    )


def     get_top_generic_tool(*args, **kwargs) -> str:
    """Tool-safe wrapper for generic top query specific for LangGraph."""
    # Normalize parameters from LangGraph
    params = normalize_langgraph_params(*args, **kwargs)
    print(f"[DEBUG] get_top_generic_tool params: {params}")

    # Extract parameters with default values
    country = params.get("country")
    platform = params.get("platform")
    genre = params.get("genre")
    content_type = params.get("content_type") or params.get("type")
    limit = params.get("limit", 10)
    days_back = params.get("days_back")
    date_from = params.get("date_from")
    date_to = params.get("date_to")

    # Extract year parameters
    currentyear = params.get("currentyear")
    year = params.get("year")
    year_from = params.get("year_from")
    year_to = params.get("year_to")
    region = params.get("region")

    print(
        f"[DEBUG] Wrapper - year: {year}, currentyear: {currentyear}, content_type: {content_type}, genre: {genre}"
    )

    # Call main function
    rows = get_top_generic(
        country=country,
        platform=platform,
        genre=genre,
        content_type=content_type,
        limit=limit,
        days_back=days_back,
        date_from=date_from,
        date_to=date_to,
        currentyear=currentyear,
        year=year,
        year_from=year_from,
        year_to=year_to,
        region=region,
    )

    # Create structured response
    response = {
        "status": "success",
        "operation": "top_generic",
        "filters_applied": {
            "country": country,
            "platform": platform,
            "genre": genre,
            "content_type": content_type,
            "currentyear": currentyear,
            "year": year,
            "limit": limit,
            "days_back": days_back,
            "date_from": date_from,
            "date_to": date_to,
        },
        "data": rows if isinstance(rows, list) else [],
        "count": len(rows) if isinstance(rows, list) else 0,
        "timestamp": datetime.now().isoformat(),
    }

    return json.dumps(response, ensure_ascii=False, indent=2, default=str)


def new_top_generic_tool(*args, **kwargs) -> str:
    """New function specific for LangGraph that handles generic tops."""
    return get_top_generic_tool(*args, **kwargs)


def new_top_by_country_tool(*args, **kwargs) -> str:
    """New function specific for LangGraph for tops by country."""
    params = normalize_langgraph_params(*args, **kwargs)

    country = params.get("country") or params.get("iso_alpha2")
    year = params.get("year")
    limit = params.get("limit", 20)

    if not country:
        return json.dumps(
            {
                "status": "error",
                "operation": "new_top_by_country",
                "error": "Country parameter required",
                "data": [],
                "count": 0,
            },
            ensure_ascii=False,
            indent=2,
        )

    rows = get_top_by_country(country, year=year, limit=limit)

    response = {
        "status": "success",
        "operation": "new_top_by_country",
        "filters_applied": {"country": country, "year": year, "limit": limit},
        "data": rows if isinstance(rows, list) else [],
        "count": len(rows) if isinstance(rows, list) else 0,
        "timestamp": datetime.now().isoformat(),
    }

    return json.dumps(response, ensure_ascii=False, indent=2, default=str)


# =============================================================================
# LEGACY COMPATIBILITY FUNCTIONS
# =============================================================================


def tool_top_generic(*args, **kwargs) -> str:
    """Legacy compatibility wrapper"""
    return get_top_generic_tool(*args, **kwargs)


def tool_top_by_country(*args, **kwargs) -> str:
    """Legacy compatibility wrapper"""
    return new_top_by_country_tool(*args, **kwargs)


def get_top_by_type_tool(*args, **kwargs) -> str:
    """Tool-safe wrapper for top by type query."""
    params = normalize_langgraph_params(*args, **kwargs)

    # Extract parameters
    content_type = (
        params.get("content_type") or params.get(
            "type") or params.get("__arg1")
    )
    limit = params.get("limit", 10)

    # If content_type looks like JSON, try to parse it
    if isinstance(content_type, str) and content_type.startswith("{"):
        try:
            parsed = json.loads(content_type)
            content_type = parsed.get("type") or parsed.get("content_type")
            limit = parsed.get("limit", limit)
        except:
            pass

    if not content_type:
        return json.dumps(
            {
                "status": "error",
                "operation": "top_by_type",
                "error": "content_type parameter required",
                "data": [],
                "count": 0,
            },
            ensure_ascii=False,
            indent=2,
        )

    # Call main function
    rows = get_top_by_type(content_type, limit)

    response = {
        "status": "success",
        "operation": "top_by_type",
        "filters_applied": {"content_type": content_type, "limit": limit},
        "data": rows if isinstance(rows, list) else [],
        "count": len(rows) if isinstance(rows, list) else 0,
        "timestamp": datetime.now().isoformat(),
    }

    return json.dumps(response, ensure_ascii=False, indent=2, default=str)


def get_top_by_genre_tool(*args, **kwargs) -> str:
    """Tool-safe wrapper for top by genre query."""
    params = normalize_langgraph_params(*args, **kwargs)

    # Extract parameters
    genre = params.get("genre") or params.get(
        "genre_input") or params.get("__arg1")
    limit = params.get("limit", 10)

    # If genre looks like JSON, try to parse it
    if isinstance(genre, str) and genre.startswith("{"):
        try:
            parsed = json.loads(genre)
            genre = parsed.get("genre") or parsed.get("genre_input")
            limit = parsed.get("limit", limit)
        except:
            pass

    if not genre:
        return json.dumps(
            {
                "status": "error",
                "operation": "top_by_genre",
                "error": "genre parameter required",
                "data": [],
                "count": 0,
            },
            ensure_ascii=False,
            indent=2,
        )

    # Call main function
    rows = get_top_by_genre(genre, limit)

    response = {
        "status": "success",
        "operation": "top_by_genre",
        "filters_applied": {"genre": genre, "limit": limit},
        "data": rows if isinstance(rows, list) else [],
        "count": len(rows) if isinstance(rows, list) else 0,
        "timestamp": datetime.now().isoformat(),
    }

    return json.dumps(response, ensure_ascii=False, indent=2, default=str)


# def get_top_global_tool(*args, **kwargs) -> str:
#     """Tool-safe wrapper for top global query."""
#     params = normalize_langgraph_params(*args, **kwargs)

#     # If first arg is JSON string, parse it
#     arg1 = params.get("__arg1")
#     if isinstance(arg1, str) and arg1.startswith("{"):
#         try:
#             parsed = json.loads(arg1)
#             params.update(parsed)
#         except:
#             pass

#     # Extract parameters
#     platform = params.get("platform")
#     genre = params.get("genre")
#     content_type = params.get("content_type") or params.get("type")
#     limit = params.get("limit", 10)
#     days_back = params.get("days_back")
#     date_from = params.get("date_from")
#     date_to = params.get("date_to")
#     currentyear = params.get("currentyear") or params.get("year")
#     year_from = params.get("year_from")
#     year_to = params.get("year_to")

#     # Call main function
#     rows = get_top_global(
#         platform=platform,
#         genre=genre,
#         content_type=content_type,
#         limit=limit,
#         days_back=days_back,
#         date_from=date_from,
#         date_to=date_to,
#         currentyear=currentyear,
#         year_from=year_from,
#         year_to=year_to,
#     )

#     response = {
#         "status": "success",
#         "operation": "top_global",
#         "filters_applied": {
#             "platform": platform,
#             "genre": genre,
#             "content_type": content_type,
#             "limit": limit,
#             "days_back": days_back,
#             "date_from": date_from,
#             "date_to": date_to,
#             "currentyear": currentyear,
#             "year_from": year_from,
#             "year_to": year_to,
#         },
#         "data": rows if isinstance(rows, list) else [],
#         "count": len(rows) if isinstance(rows, list) else 0,
#         "timestamp": datetime.now().isoformat(),
#     }

#     return json.dumps(response, ensure_ascii=False, indent=2, default=str)


# def get_top_presence_tool(*args, **kwargs) -> str:
#     """Tool-safe wrapper for top presence query."""
#     params = normalize_langgraph_params(*args, **kwargs)

#     # If first arg is JSON string, parse it
#     arg1 = params.get("__arg1")
#     if isinstance(arg1, str) and arg1.startswith("{"):
#         try:
#             parsed = json.loads(arg1)
#             params.update(parsed)
#         except:
#             pass

#     # Extract parameters
#     resolved_country = params.get("country") or params.get("resolved_country")
#     iso_set = params.get("iso_set", [])
#     platform = params.get("platform")
#     genre = params.get("genre")
#     content_type = params.get("content_type") or params.get("type")
#     limit = params.get("limit", 10)
#     days_back = params.get("days_back")
#     date_from = params.get("date_from")
#     date_to = params.get("date_to")
#     currentyear = params.get("currentyear") or params.get("year")
#     year_from = params.get("year_from")
#     year_to = params.get("year_to")

#     # Resolve country if provided
#     if resolved_country:
#         resolved_country = resolve_country_iso(resolved_country)

#     # Call main function
#     rows = get_top_presence(
#         resolved_country=resolved_country,
#         iso_set=iso_set,
#         platform=platform,
#         genre=genre,
#         content_type=content_type,
#         limit=limit,
#         days_back=days_back,
#         date_from=date_from,
#         date_to=date_to,
#         currentyear=currentyear,
#         year_from=year_from,
#         year_to=year_to,
#     )

#     response = {
#         "status": "success",
#         "operation": "top_presence",
#         "filters_applied": {
#             "country": resolved_country,
#             "iso_set": iso_set,
#             "platform": platform,
#             "genre": genre,
#             "content_type": content_type,
#             "limit": limit,
#             "days_back": days_back,
#             "date_from": date_from,
#             "date_to": date_to,
#             "currentyear": currentyear,
#             "year_from": year_from,
#             "year_to": year_to,
#         },
#         "data": rows if isinstance(rows, list) else [],
#         "count": len(rows) if isinstance(rows, list) else 0,
#         "timestamp": datetime.now().isoformat(),
#     }

#     return json.dumps(response, ensure_ascii=False, indent=2, default=str)
