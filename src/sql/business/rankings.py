from src.sql.db_utils_sql import *
from src.sql.default_import import *
from src.sql.business.queries import *
from src.sql.validators_shared import *


def normalize_langgraph_params(*args, **kwargs) -> dict:
    """
    Normalize parameters from LangGraph tool calls.
    Handles nested kwargs format: {'kwargs': {'param1': 'value1', ...}}
    """
    # Handle LangGraph nested kwargs format
    if 'kwargs' in kwargs and isinstance(kwargs['kwargs'], dict):
        nested_kwargs = kwargs['kwargs']
        other_params = {k: v for k, v in kwargs.items() if k != 'kwargs'}
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
                parsed = json.loads(arg) if arg.startswith('{') else None
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
        return json.dumps({
            "status": "no_results",
            "message": f"No data found for {operation_name}.",
            "data": [],
            "count": 0
        }, ensure_ascii=False, indent=2)

    if isinstance(result, str) and not result.strip():
        return json.dumps({
            "status": "empty_response",
            "message": f"Empty response from {operation_name}.",
            "data": [],
            "count": 0
        }, ensure_ascii=False, indent=2)

    if isinstance(result, (list, dict)):
        return json.dumps({
            "status": "success",
            "data": result,
            "count": len(result) if isinstance(result, list) else 1,
            "operation": operation_name
        }, ensure_ascii=False, indent=2)

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
    if s.startswith('[') and s.endswith(']'):
        arr = json.loads(s) if s else None
        if isinstance(arr, list):
            out = [str(g).strip() for g in arr if str(g).strip()]
            return out or None

    # Fallback: split by comma or semicolon
    parts = [p.strip() for p in s.replace(';', ',').split(',')]
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

def get_recent_premieres_by_country(country: str, days_back: int = 7, limit: int = 30) -> List[Dict]:
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
        f"[recent_premieres] country={resolved_country}, days_back={days_back}, range=({date_from},{date_to}), limit={limit}")

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
            return [{"message": f"Unknown genre: '{genre}'. Try Horror, Action, Comedy, Drama..."}]
        where_clauses.append("m.primary_genre = %s")
        params.append(resolved_genre)

    query_template = QUERY_RECENT_TOP_PREMIERES
    query = query_template.format(
        where_clauses=" AND ".join(where_clauses),
        limit=limit
    )

    params_scored = params + [date_from, date_to, date_from, date_to]
    rows = db.execute_query(query, tuple(params_scored))
    ident = f"{resolved_country} last {days_back}d (top by hits)"
    return handle_query_result(rows, "recent top premieres by country", ident)


def get_genre_momentum(
    country: str,
    days: int = 30,
    prev_days: Optional[int] = None,
    content_type: Optional[str] = None,
    limit: int = 20,
) -> List[Dict]:
    """Get genre ranking by growth: current window vs previous adjacent window."""
    if not country:
        return [{"message": "Country (ISO-2) required."}]

    days = validate_days_back(days, default=30)
    prev_days = validate_days_back(
        prev_days if prev_days else days, default=days)

    today = datetime.now().date()
    cur_from = today - timedelta(days=days)
    cur_to = today
    prev_to = cur_from - timedelta(days=1)
    prev_from = prev_to - timedelta(days=prev_days - 1)

    resolved_country = resolve_country_iso(country)

    # Build content type filters
    ct_hits = None
    ct_meta = None
    if content_type:
        ct = resolve_content_type(content_type)
        if ct is None:
            return [{"message": f"Unknown type: '{content_type}'. Use movie/series."}]
        ct_meta = ct
        ct_hits = ct

    # Build WHERE clauses and parameters
    where_hits_cur = ["h.country = %s",
                      "h.date_hits BETWEEN %s AND %s"]
    where_hits_prev = ["h.country = %s",
                       "h.date_hits BETWEEN %s AND %s"]

    params_cur = [resolved_country, cur_from.isoformat(), cur_to.isoformat()]
    params_prev = [resolved_country,
                   prev_from.isoformat(), prev_to.isoformat()]

    if ct_hits:
        where_hits_cur.append("h.content_type = %s")
        where_hits_prev.append("h.content_type = %s")
        params_cur.append(ct_hits)
        params_prev.append(ct_hits)

    where_meta = []
    params_meta: List[str] = []
    if ct_meta:
        where_meta.append("m.type = %s")
        params_meta.append(ct_meta)

    # Build SQL query
    meta_join = " AND " + " AND ".join(where_meta) if where_meta else ""

    query_template = QUERY_GENRE_MOMENTUM
    query = query_template.format(
        where_hits_cur=" AND ".join(where_hits_cur),
        where_hits_prev=" AND ".join(where_hits_prev),
        meta_join=meta_join,
        limit=limit
    )

    all_params = tuple(params_cur + params_meta + params_prev + params_meta)
    rows = db.execute_query(query, all_params)

    ident = f"{resolved_country} cur[{cur_from}..{cur_to}] vs prev[{prev_from}..{prev_to}]"
    return handle_query_result(rows, "genre momentum", ident)


def get_platform_exclusivity_by_country(platform_name: str, country: str, limit: int = 100) -> List[Dict]:
    """Get platform exclusives within a country scope."""
    logger.info(
        f"get_platform_exclusivity_by_country called with platform_name={platform_name}, country={country}, limit={limit}")

    if not platform_name or not country:
        return [{"message": "platform_name and country (ISO-2) required."}]

    resolved_country = resolve_country_iso(country)
    resolved_platform = resolve_platform_name(platform_name)

    query_template = QUERY_PLATFORM_EXCLUSIVITY
    query = query_template.format(limit=limit)

    params = (resolved_country, resolved_platform,
              resolved_platform, resolved_platform)
    rows = db.execute_query(query, params)
    ident = f"{resolved_platform} @ {resolved_country}"
    return handle_query_result(rows, "platform exclusivity (country)", ident)


# =============================================================================
# PRESENCE (PLATFORM) FUNCTIONS
# =============================================================================

def query_platforms_for_title(uid: str, limit: int = 50) -> List[Dict]:
    """Get all platforms carrying a specific title."""
    logger.info(
        f"query_platforms_for_title called with uid={uid}, limit={limit}")

    if not uid:
        return [{"message": "uid required"}]

    query = QUERY_PLATFORMS_FOR_TITLE
    result = db.execute_query(query, (uid, limit))

    logger.info(
        f"Platforms queried for {uid}, results: {len(result) if result else 0}")
    return handle_query_result(result, "platforms for title (uid)", uid)


def query_platforms_for_uid_by_country(uid: str, country: str = None) -> List[Dict]:
    """Get platforms for a UID within a specific country."""
    logger.info(
        f"query_platforms_for_uid_by_country called with uid={uid}, country={country}")

    if not uid:
        return [{"message": "uid required"}]

    # If no country provided, fall back to generic platforms query
    if not country:
        logger.info(
            "No country provided, falling back to generic platforms query")
        return query_platforms_for_title(uid)

    resolved_country = resolve_country_iso(country)
    if not resolved_country:
        return [{"message": f"Invalid country code: {country}"}]

    query = QUERY_PLATFORMS_FOR_TITLE_BY_COUNTRY
    result = db.execute_query(query, (uid, resolved_country))
    return handle_query_result(result, "platforms for title by country", f"{uid} @ {resolved_country}")


def get_platform_exclusives(platform_name: str, country: str = "US", limit: int = 30) -> List[Dict]:
    """Get titles exclusive to a platform within a country."""
    logger.info(
        f"get_platform_exclusives called with platform_name={platform_name}, country={country}, limit={limit}")

    if not platform_name:
        return [{"message": "Platform name required"}]

    resolved_country = resolve_country_iso(country)
    resolved_platform = resolve_platform_name(platform_name)
    ident = f"exclusives {resolved_platform} @ {resolved_country}"

    query = PresenceQueryBuilder.build_platform_exclusives_query(limit=limit)
    result = db.execute_query(query, (resolved_platform, resolved_country))
    return handle_query_result(result, "platform exclusives", ident)


def compare_platforms_for_title(title_: str) -> List[Dict]:
    """Compare which platforms carry a given title (exact match)."""
    logger.info(f"compare_platforms_for_title called with title_={title_}")

    if not title_:
        return [{"message": "Title required"}]

    query = PresenceQueryBuilder.build_compare_platforms_for_title_query()
    result = db.execute_query(query, (title_,))
    logger.info(f"Platforms queried for {title_}, results: {result}")
    return handle_query_result(result, "compare platforms for title", title_)


# =============================================================================
# TOP GLOBAL FUNCTIONS
# =============================================================================

def get_top_by_uid(uid: str) -> List[Dict]:
    """Get top/rating information for a title by UID."""
    logger.info(f"get_top_by_uid called with uid={uid}")
    query = QUERY_RATING_BY_UID()
    result = db.execute_query(query, (uid,))
    return handle_query_result(result, "Rating by uid", f"{uid}")


def get_top_by_country(
    country_input: str = None,
    year: Optional[int] = None,
    date_range: Optional[Tuple[str, str]] = None,
    limit: int = 20
) -> List[Dict]:
    """Get top titles by country with optional year filter."""
    logger.info(
        f"get_top_by_country called with country_input={country_input}, year={year}, date_range={date_range}, limit={limit}")

    if not country_input:
        return [{"message": "Valid country required."}]

    resolved_country = resolve_country_iso(country_input)
    logger.debug(f"Resolved country: {resolved_country}")

    if resolved_country:
        if year is not None:
            query = HitsQueryBuilder.build_top_by_country_query(limit=limit)
            result = db.execute_query(query, (resolved_country, year))
        else:
            query = HitsQueryBuilder.build_top_by_country_no_year_query(
                limit=limit)
            result = db.execute_query(query, (resolved_country,))
        return handle_query_result(result, "top by country", f"{country_input}")
    else:
        return [{"message": f"No valid country found for '{country_input}'. Try: US, UK, CA, etc."}]


def get_top_generic(
    country: Optional[str] = None,
    platform: Optional[str] = None,
    genre: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = 10,
    days_back: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    currentyear: Optional[int] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    *,
    region: Optional[str] = None,
    countries_list: Optional[List[str]] = None,
    # Aliases que suelen venir desde el wrapper/tool
    type: Optional[str] = None,   # alias de content_type
    year: Optional[int] = None,   # alias de currentyear
) -> List[Dict[str, Any]]:
    """Generic top titles query with flexible filtering."""

    # Normalization of params / Aliases
    if content_type is None and type is not None:
        content_type = type

    # Resolver alias de año: year -> currentyear
    resolved_currentyear = currentyear
    if currentyear is None and year is not None:
        resolved_currentyear = int(year)

    print(
        f"[DEBUG] get_top_generic - year: {year}, currentyear: {currentyear}, resolved_currentyear: {resolved_currentyear}")

    # Geographic resolution
    resolved_country = resolve_country_iso(country) if country else None
    iso_set: List[str] = []
    if not resolved_country and (region or countries_list):
        if region:
            iso_set = resolve_region_isos(region) or []
        if not iso_set and countries_list:
            iso_set = [c.strip().upper()
                       for c in countries_list if isinstance(c, str) and c.strip()]

    # Routing
    if resolved_country or iso_set:
        return get_top_presence(
            resolved_country, iso_set, platform, genre, content_type,
            limit, days_back, date_from, date_to,
            year, year_from, year_to
        )
    else:
        return get_top_global(
            platform, genre, content_type, limit, days_back,
            date_from, date_to, year, year_from, year_to
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
    """Optimized version that applies filters in JOINs for maximum performance."""

    params: List[Any] = []
    where: List[str] = []
    joins: List[str] = []

    needs_metadata = bool(resolved_country or iso_set or genre)
    if needs_metadata:
        joins.append(
            f"INNER JOIN {PRES_TBL} p ON h.uid = p.uid INNER JOIN {META_TBL} m ON h.uid = m.uid")

    # Geographic filters
    if resolved_country:
        where.append("m.countries_iso = %s")
        params.append(resolved_country)
    elif iso_set:
        if len(iso_set) == 1:
            where.append("m.countries_iso = %s")
            params.append(iso_set[0])
        else:
            conds = []
            for iso in iso_set:
                conds.append("m.countries_iso LIKE %s")
                params.append(f"%{iso}%")
            if conds:
                where.append(f"({' OR '.join(conds)})")

    # Content filters
    if content_type:
        if isinstance(content_type, list):
            placeholders = ",".join(["%s"] * len(content_type))
            where.append(f"h.content_type IN ({placeholders})")
            params.extend([resolve_content_type(ct) for ct in content_type])
        else:
            where.append("h.content_type = %s")
            params.append(resolve_content_type(content_type))

    if platform:
        where.append("h.platform_name = %s")
        params.append(resolve_platform_name(platform))

    if genre:
        where.append("m.primary_genre ILIKE %s")
        params.append(resolve_primary_genre(genre))

    # Temporal filters integrated
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

    # Year filters
    if currentyear is not None:
        where.append("h.year = %s")
        params.append(currentyear)

    if year_from is not None:
        where.append("h.year >= %s")
        params.append(year_from)

    if year_to is not None:
        where.append("h.year <= %s")
        params.append(year_to)

    print(f"[DEBUG presence] where: {where}")
    print(f"[DEBUG presence] params: {tuple(params)}")

    # Query construction
    where_clause = f"WHERE {' AND '.join(where)} AND p.out_on IS NULL " if where else " WHERE p.out_on IS NULL  "
    joins_clause = " ".join(joins)

    query_template = QUERY_TOP_PRESENCE_WITH_METADATA if needs_metadata else QUERY_TOP_PRESENCE_NO_METADATA
    query = query_template.format(
        joins_clause=joins_clause, where_clause=where_clause)

    params.append(limit)

    print(f"PRESENCE SQL: {query}")
    print(f"PRESENCE Params: {tuple(params)}")

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
    """Query ms.hits_global for global data."""

    params: List[Any] = []
    where: List[str] = []
    joins: List[str] = []

    # Basic join for clean_title
    joins.append(
        f"INNER JOIN {PRES_TBL} p ON h.uid = p.uid INNER JOIN {META_TBL} m ON h.uid = m.uid")

    # Content filters
    if content_type:
        if isinstance(content_type, list):
            placeholders = ",".join(["%s"] * len(content_type))
            where.append(f"h.content_type IN ({placeholders})")
            params.extend([resolve_content_type(ct)
                          for ct in content_type])
        else:
            where.append("h.content_type = %s")
            params.append(resolve_content_type(content_type))

    if platform:
        where.append("p.platform_name = %s")
        params.append(resolve_platform_name(platform))

    if genre:
        where.append("m.primary_genre ILIKE %s")
        params.append(resolve_primary_genre(genre))

    # Temporal filters integrated
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

    # Year filters
    if currentyear is not None:
        where.append("h.currentyear = %s")
        params.append(currentyear)

    if year_from is not None:
        where.append("h.currentyear >= %s")
        params.append(year_from)

    if year_to is not None:
        where.append("h.currentyear <= %s")
        params.append(year_to)

    print(f"[DEBUG global] where: {where}")
    print(f"[DEBUG global] params: {tuple(params)}")

    # Query construction
    where_clause = f"WHERE {' AND '.join(where)} AND p.out_on IS NULL " if where else " WHERE p.out_on IS NULL  "
    joins_clause = " ".join(j for j in joins if j)

    query_template = QUERY_TOP_GLOBAL_WITH_GENRE if bool(
        genre) else QUERY_TOP_GLOBAL_NO_GENRE
    query = query_template.format(
        joins_clause=joins_clause, where_clause=where_clause)

    params.append(limit)

    print(f"GLOBAL SQL: {query}")
    print(f"GLOBAL Params: {tuple(params)}")

    rows = db.execute_query(query, tuple(params))
    return build_result(
        rows, "global", None, [], platform, genre, content_type,
        limit, days_back, date_from, date_to, currentyear, year_from, year_to
    )


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
    year_to: Optional[int]
) -> List[Dict[str, Any]]:
    """Build result with logging and year/currentyear normalization."""

    window_id = (
        f"rolling_{days_back}d" if days_back is not None
        else ("custom_range" if (date_from or date_to) else "all_time")
    )
    if query_type == "presence":
        loc_id = f"country={resolved_country}" if resolved_country else f"countries={iso_set}"
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
    for r in (rows or []):
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
    genre_input: str,
    platform_name: str,
    country_iso: str,
    limit: int = 10
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

def get_recent_premieres_by_country_tool(country: str, days_back: int = 7, limit: int = 30) -> str:
    """Tool-safe wrapper for recent premieres query."""
    rows = get_recent_premieres_by_country(country, days_back, limit)
    return safe_tool_response(rows, f"recent_premieres {country} {days_back}d limit={limit}")


def get_recent_top_premieres_by_country_tool(
    country: str,
    days_back: int = 7,
    limit: int = 30,
    content_type: Optional[str] = None,
    genre: Optional[str] = None
) -> str:
    """Tool-safe wrapper for recent top premieres query."""
    rows = get_recent_top_premieres_by_country(
        country, days_back, limit, content_type, genre)
    return safe_tool_response(
        rows,
        f"recent_top {country} {days_back}d type={content_type or 'any'} genre={genre or 'any'} limit={limit}"
    )


def query_platforms_for_title_tool(*args, **kwargs) -> str:
    """Tool-safe wrapper for platforms by title query."""
    # Normalize parameters from LangGraph
    params = normalize_langgraph_params(*args, **kwargs)

    # Extract uid from various possible parameter formats
    uid = (
        params.get("uid") or
        params.get("__arg1") or
        params.get("title_uid") or
        (args[0] if args and isinstance(args[0], str) else None)
    )

    limit = params.get("limit", 10)

    if not uid:
        return safe_tool_response(
            [{"message": "UID parameter required"}],
            "platforms_for_title_missing_uid"
        )

    # Call the main function
    rows = query_platforms_for_title(uid, limit)
    operation_name = f"platforms_for_uid {uid} limit={limit}"
    return safe_tool_response(rows, operation_name)


def query_platforms_for_uid_by_country_tool(*args, **kwargs) -> str:
    """Tool-safe wrapper for platforms by title and country query."""
    # Normalize parameters from LangGraph
    params = normalize_langgraph_params(*args, **kwargs)

    # Extract uid from various possible parameter formats
    uid = (
        params.get("uid") or
        params.get("__arg1") or
        params.get("title_uid") or
        (args[0] if args and isinstance(args[0], str) else None)
    )

    country = (
        params.get("country") or
        params.get("iso_alpha2") or
        params.get("country_code")
    )

    if not uid:
        return safe_tool_response(
            [{"message": "UID parameter required"}],
            "platforms_by_country_missing_uid"
        )

    # Call the main function
    rows = query_platforms_for_uid_by_country(uid, country)
    operation_name = f"platforms_for_uid_by_country {uid}@{country or 'all'}"
    return safe_tool_response(rows, operation_name)


def get_platform_exclusives_tool(platform_name: str, country: str = "US", limit: int = 30) -> str:
    """Tool-safe wrapper for platform exclusives query."""
    rows = get_platform_exclusives(platform_name, country, limit)
    return safe_tool_response(rows, f"platform_exclusives {platform_name}@{country} limit={limit}")


def get_top_generic_tool(*args, **kwargs) -> str:
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

    print(f"[DEBUG] Wrapper - year: {year}, currentyear: {currentyear}")

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
        region=region
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
            "date_to": date_to
        },
        "data": rows if isinstance(rows, list) else [],
        "count": len(rows) if isinstance(rows, list) else 0,
        "timestamp": datetime.now().isoformat()
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
        return json.dumps({
            "status": "error",
            "operation": "new_top_by_country",
            "error": "Country parameter required",
            "data": [],
            "count": 0
        }, ensure_ascii=False, indent=2)

    rows = get_top_by_country(country, year=year, limit=limit)

    response = {
        "status": "success",
        "operation": "new_top_by_country",
        "filters_applied": {
            "country": country,
            "year": year,
            "limit": limit
        },
        "data": rows if isinstance(rows, list) else [],
        "count": len(rows) if isinstance(rows, list) else 0,
        "timestamp": datetime.now().isoformat()
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
