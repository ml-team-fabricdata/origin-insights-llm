from src.sql.utils.db_utils_sql import *
from src.sql.utils.default_import import *
from src.sql.utils.validators_shared import *
from src.sql.queries.business.rankings_queries import *

def compute_window_anchored_to_table(days_back: int) -> Optional[Tuple[str, str]]:
    """Compute date window anchored to MAX(date_hits) when no current data exists."""
    logger.debug(f"Computing window anchored to table with days_back={days_back}")

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
    return (date_from, date_to)

def max_date_hits() -> date:
    row = db.execute_query(
        f"SELECT MAX(date_hits)::date AS mx FROM {HITS_PRESENCE_TBL};", []) or []
    return row[0]["mx"] or datetime.now().date()

def _clamp_rolling(max_d: date, days: int, prev_days: int) -> Tuple[date, date, date, date]:
    cur_to = max_d
    cur_from = max_d - timedelta(days=days-1)
    prev_to = cur_from - timedelta(days=1)
    prev_from = prev_to - timedelta(days=prev_days-1)
    return (cur_from, cur_to, prev_from, prev_to)

def get_genre_momentum(
    country: Optional[str] = None,
    content_type: Optional[str] = None,
    limit: int = 20,
    days_back: Optional[int] = None,
    prev_days_back: Optional[int] = None
) -> List[Dict]:
    """Ranking de géneros por crecimiento comparando un período actual vs. uno previo.
    
    Si se especifica país, usa presencia (ms.hits_presence); sin país usa global.
    Parámetros: country (ISO-2 opcional), content_type ('Movie'/'Series' opcional),
    limit (por defecto 20), days_back (días del período actual; el previo replica ese tamaño).
    Las ventanas se anclan a MAX(date_hits) de la tabla.
    
    Args:
        country: Country ISO-2 code (optional)
        content_type: Content type - 'Movie' or 'Series' (optional)
        limit: Maximum results (default 20)
        days_back: Days for current period (optional)
        prev_days_back: Days for previous period (optional, defaults to days_back)
    
    Returns:
        List with genre momentum rankings and growth metrics
    """
    if days_back is None or days_back <= 0:
        days_back = 30
    if prev_days_back is None or prev_days_back <= 0:
        prev_days_back = days_back

    max_d = max_date_hits()

    cur_from, cur_to, prev_from, prev_to = _clamp_rolling(
        max_d, days_back, prev_days_back)
    logger.debug(f"Date ranges: prev={prev_from} → {prev_to}, cur={cur_from} → {cur_to}")

    country_clause = ""
    ct_hits_clause = ""
    ct_meta_clause = ""

    params = [
        cur_from.isoformat(), cur_to.isoformat(),
        prev_from.isoformat(), prev_to.isoformat(),
        prev_from.isoformat(), cur_to.isoformat()
    ]

    if country:
        resolved_country = resolve_country_iso(country)
        if resolved_country:
            country_clause = "AND h.country = %s"
            params.append(resolved_country)

    if content_type:
        resolved_type = resolve_content_type(content_type)
        if resolved_type:
            ct_hits_clause = "AND h.content_type = %s"
            ct_meta_clause = "AND m.type = %s"
            params.append(resolved_type)
            params.append(resolved_type)

    query = QUERY_GENRE_MOMENTUM.format(
        HITS_TABLE=HITS_PRESENCE_TBL,
        META_TBL=META_TBL,
        COUNTRY_CLAUSE=country_clause,
        CT_HITS_CLAUSE=ct_hits_clause,
        CT_META_CLAUSE=ct_meta_clause
    )

    query += f"\nLIMIT {limit}"

    rows = db.execute_query(query, tuple(params))

    ident_parts = []
    if country:
        ident_parts.append(f"country={country}")
        ident_parts.append(f"type={content_type}")
    ident_parts.append(f"current={days_back}d")
    ident_parts.append(f"prev={prev_days_back}d")
    ident = " ".join(ident_parts) if ident_parts else "all genres"

    return handle_query_result(rows, "genre_momentum", ident)

def get_top_by_uid(uid: str) -> List[Dict]:
    """Get top/rating information for a specific UID."""
    if not uid:
        return [{"message": "UID required"}]

    rows = db.execute_query(UID_RATING_SQL, (uid,))
    return handle_query_result(rows, "Rating by uid", f"{uid}")

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
    type: Optional[str] = None,
    year: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Top genérico con filtros flexibles; rutea automáticamente según geografía:
    - country/region/countries_list → presencia
    - sin geografía → global

    Filtros: platform, genre, content_type; ventana temporal (days_back o date_from/date_to); 
    año (currentyear/year o rango year_from/year_to); y limit.

    Ejemplos:
        get_top_generic(country="US", days_back=30)
        get_top_generic(country="US", date_from="2024-01-01", date_to="2024-12-31")
        get_top_generic(year=2024)
        get_top_generic(year_from=2020, year_to=2024)
    """

    normalized_content_type = resolve_content_type(
        content_type) or resolve_content_type(type)

    resolved_currentyear = (
        int(currentyear) if currentyear is not None
        else (int(year) if year is not None else None)
    )

    normalized_platform = resolve_platform_name(platform) if platform else None
    normalized_genre = resolve_primary_genre(genre) if genre else None
    limit_val = validate_limit(limit, default=20, max_limit=200)

    resolved_country = resolve_country_iso(country) if country else None
    iso_set: List[str] = []
    if not resolved_country and (region or countries_list):
        if region:
            iso_set = resolve_region_isos(region) or []
        if not iso_set and countries_list:
            iso_set = [resolve_country_iso(c) or c.strip().upper() for c in countries_list if isinstance(c, str) and c.strip()]

    logger.debug(
        f"get_top_generic | Time: days_back={days_back}, dates={date_from} to {date_to}, "
        f"year={resolved_currentyear}, years={year_from}-{year_to} | "
        f"Filters: ct={normalized_content_type}, platform={normalized_platform}, "
        f"genre={normalized_genre}, country={resolved_country}, limit={limit_val}"
    )

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
        placeholders = ','.join(['%s'] * len(iso_set))
        where.append(f"np.iso_alpha2 IN ({placeholders})")
        params.extend(iso_set)

    if content_type:
        where.append("h.content_type = %s")
        params.append(content_type)
    if platform:
        where.append("np.platform_name ILIKE %s")
        params.append(platform)
    if genre:
        where.append("m.primary_genre = %s")
        params.append(genre)

    if days_back is not None:
        validated = validate_days_back(days_back, default=7)
        logger.debug(f"get_top_presence | days_back={days_back} → validated={validated}")
        window = compute_window_anchored_to_table(validated)
        if window:
            df, dt = window
            logger.debug(f"get_top_presence | Computed window: {df} to {dt} ({validated} days)")
            where.append("h.date_hits BETWEEN %s AND %s")
            params.extend([df, dt])
    else:
        if date_from:
            logger.debug(f"get_top_presence | Using date_from: {date_from}")
            where.append("h.date_hits >= %s")
            params.append(date_from)
        if date_to:
            logger.debug(f"get_top_presence | Using date_to: {date_to}")
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

    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    joins = list(dict.fromkeys(joins))
    joins_clause = " ".join(joins)

    query_template = QUERY_TOP_PRESENCE_WITH_METADATA if needs_metadata else QUERY_TOP_PRESENCE_NO_METADATA
    query = query_template.format(
        joins_clause=joins_clause, where_clause=where_clause)

    params.append(limit)
    logger.debug(f"PRESENCE SQL with {len(params)} params")

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
    Top global (sin país). Agrega JOINs sólo cuando son necesarios:
    - platform → JOIN a presencia (np) para platform_name.
    - genre o content_type → JOIN a metadata (m) para primary_genre o type.
    """
    params: List[Any] = []
    where: List[str] = []
    joins: List[str] = []

    join_presence = bool(platform)
    join_meta = bool(genre or content_type)

    if join_presence:
        joins.append(f"INNER JOIN {PRES_TBL} AS np ON np.uid = h.uid")
    if join_meta:
        joins.append(f"INNER JOIN {META_TBL} AS m ON m.uid = h.uid")

    if days_back is not None:
        validated = validate_days_back(days_back, default=7)
        logger.debug(f"get_top_global | days_back={days_back} → validated={validated}")
        window = compute_window_anchored_to_table(validated)
        if window:
            df, dt = window
            logger.debug(f"get_top_global | Computed window: {df} to {dt} ({validated} days)")
            where.append("h.date_hits BETWEEN %s AND %s")
            params.extend([df, dt])
    else:
        if date_from:
            logger.debug(f"get_top_global | Using date_from: {date_from}")
            where.append("h.date_hits >= %s")
            params.append(date_from)
        if date_to:
            logger.debug(f"get_top_global | Using date_to: {date_to}")
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
        where.append("m.primary_genre = %s")
        params.append(genre)

    if platform:
        where.append("np.platform_name ILIKE %s")
        params.append(platform)

    joins_clause = " ".join(dict.fromkeys(joins))
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    query_template = QUERY_TOP_GLOBAL_WITH_META if join_meta else QUERY_TOP_GLOBAL_NO_META
    query = query_template.format(
        joins_clause=joins_clause, where_clause=where_clause)

    params.append(limit)
    logger.debug(f"GLOBAL SQL with {len(params)} params")

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
    logger.debug(f"{query_type.upper()}: {ident}, rows={len(rows or [])}")

    def _normalize_row(r: Any) -> Dict[str, Any]:
        """Normalize a single row efficiently."""
        d = dict(r) if not isinstance(r, dict) else r
        if "year" not in d:
            hit_year = d.pop("hit_year", None)
            if hit_year is not None:
                d["year"] = hit_year
        if "currentyear" not in d:
            current_year = d.pop("current_year", None)
            if current_year is not None:
                d["currentyear"] = current_year
        d.pop("hit_year", None)
        d.pop("current_year", None)
        return d

    norm_rows = [_normalize_row(r) for r in (rows or [])]
    return handle_query_result(norm_rows, f"top ({query_type})", ident)

def get_top_generic_tool(*args, **kwargs) -> str:
    """Tool-safe wrapper for generic top query specific for LangGraph."""
    params = normalize_langgraph_params(*args, **kwargs)
    logger.debug(f"get_top_generic_tool | Raw params received: {params}")

    country = params.get("country")
    platform = params.get("platform")
    genre = params.get("genre")
    content_type = params.get("content_type") or params.get("type")
    limit = params.get("limit", 10)
    days_back = params.get("days_back")
    date_from = params.get("date_from")
    date_to = params.get("date_to")
    currentyear = params.get("currentyear")
    year = params.get("year")
    year_from = params.get("year_from")
    year_to = params.get("year_to")
    region = params.get("region")

    logger.debug(
        f"get_top_generic_tool | Time: days_back={days_back}, dates={date_from} to {date_to}, "
        f"year={year}, years={year_from}-{year_to} | "
        f"Filters: country={country}, platform={platform}, genre={genre}, ct={content_type}, limit={limit}"
    )

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

def new_top_by_country_tool(*args, **kwargs) -> str:
    """New function specific for LangGraph for tops by country."""
    params = normalize_langgraph_params(*args, **kwargs)
    
    country = params.get("country") or params.get("iso_alpha2")
    year = params.get("year")
    limit = params.get("limit", 20)

    logger.debug(f"new_top_by_country_tool | country={country}, year={year}, limit={limit}")

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

    rows = get_top_generic(country=country, year=year, limit=limit)

    response = {
        "status": "success",
        "operation": "new_top_by_country",
        "filters_applied": {"country": country, "year": year, "limit": limit},
        "data": rows if isinstance(rows, list) else [],
        "count": len(rows) if isinstance(rows, list) else 0,
        "timestamp": datetime.now().isoformat(),
    }

    return json.dumps(response, ensure_ascii=False, indent=2, default=str)