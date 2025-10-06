from src.sql.utils.db_utils_sql import *
from src.sql.utils.default_import import *
from src.sql.queries.business.pricing_queries import *
from src.sql.utils.validators_shared import *
from src.sql.modules.content.metadata import _validate_select

def _resolve_definition(values: Optional[List[str]]) -> Optional[List[str]]:
    """Normaliza/valida definiciones (e.g., "sd hd" -> "SD/HD")."""
    if not values:
        return None
    resolved: List[str] = []
    for value in values:
        key = normalize(value)
        canonical = DEF_ALIASES.get(key)
        if not canonical:
            upper_val = value.strip().upper()
            canonical = upper_val.replace(" ", "")
            if canonical == "SDHD":
                canonical = "SD/HD"
        if canonical and canonical in VALID_DEFINITIONS:
            resolved.append(canonical)
        else:
            logger.warning(f"Definición no válida ignorada: {value}")
    return resolved or None

def _resolve_license(values: Optional[List[str]]) -> Optional[List[str]]:
    """Normaliza/valida licencias."""
    if not values:
        return None
    resolved: List[str] = []
    for value in values:
        key = normalize(value)
        canonical = LIC_ALIASES.get(key, value.strip().upper())
        if canonical in VALID_LICENSES:
            resolved.append(canonical)
        else:
            logger.warning(f"Licencia no válida ignorada: {value}")
    return resolved or None

def _normalize_price_filters(
    country: Optional[str] = None,
    platform_name: Optional[str] = None,
    price_type: Optional[Union[str, List[str]]] = None,
    currency: Optional[Union[str, List[str]]] = None,
) -> Tuple[Optional[str], Optional[str], Optional[List[str]], Optional[List[str]]]:
    """Normaliza filtros comunes de precio.

    Returns:
        (iso, plat_name, price_type_list, currency_list)
    """
    iso = resolve_country_iso(country) if country else None
    plat_name = resolve_platform_name(platform_name) if platform_name else None

    if isinstance(price_type, str):
        price_type = [price_type]

    if isinstance(currency, str):
        currency = [currency]
    currency_list = [c.upper() for c in (currency or [])]

    return iso, plat_name, price_type, currency_list

def _build_filters_and_params(
    definition: Optional[List[str]],
    license_: Optional[List[str]],
) -> Tuple[str, str, List[str]]:
    """Construye filtros SQL y parámetros para las columnas derivadas (x.*)."""
    params: List[str] = []

    def_clause, def_params = build_in_clause(
        "COALESCE(x.definition,'')", definition)
    def_filter = f"AND {def_clause}" if def_clause else ""
    params.extend(def_params)

    lic_clause, lic_params = build_in_clause(
        "COALESCE(x.license,'')", license_)
    lic_filter = f"AND {lic_clause}" if lic_clause else ""
    params.extend(lic_params)

    return def_filter, lic_filter, params

def _build_sql_hits_quality(
    country: Optional[str],
    uid: str,
    limit: int,
    definition: Optional[List[str]],
    license_: Optional[List[str]],
) -> Tuple[str, Tuple[Any, ...]]:
    """Genera SQL parametrizado para hits con calidad (scoped a país o global)."""
    def_filter, lic_filter, filter_params = _build_filters_and_params(
        definition, license_)
    def_filter_fmt = f"\n  {def_filter}\n" if def_filter else ""
    lic_filter_fmt = f"\n  {lic_filter}\n" if lic_filter else ""

    if country:
        sql = (
            SQL_HITS_Q_BY_COUNTRY
            .replace("{PRES}", PRES_TBL)
            .replace("{PRICES}", PRICES_TBL)
            .replace("{DEF_FILTER}", def_filter_fmt)
            .replace("{LIC_FILTER}", lic_filter_fmt)
        )
        params = (country, uid, *filter_params, limit)
    else:
        sql = (
            SQL_HITS_Q_GLOBAL
            .replace("{PRES}", PRES_TBL)
            .replace("{PRICES}", PRICES_TBL)
            .replace("{DEF_FILTER}", def_filter_fmt)
            .replace("{LIC_FILTER}", lic_filter_fmt)
        )
        params = (uid, *filter_params, limit)

    return sql, params

def tool_hits_with_quality(
    uid: Optional[str] = None,
    country_input: Optional[str] = None,
    definition: Optional[List[str]] = None,
    license_: Optional[List[str]] = None,
    limit: int = 50,
    *,
    scoped_by_country: bool = True,
    fallback_when_empty: bool = True,
) -> List[Dict]:
    """Hits (popularidad) con filtros de calidad.
    
    Scope global o por país ISO-2. Si 'fallback_when_empty' está activo,
    reintenta sin 'definition' cuando no hay resultados.
    Returns popularity/hits data with quality filters (definition/license).
    
    Args:
        uid: Unique identifier for the title
        country_input: Country ISO-2 code (optional)
        definition: List of definitions to filter (e.g., ['HD', '4K'])
        license_: List of licenses to filter
        limit: Maximum number of results (default 50, max 200)
        scoped_by_country: Scope by country if True
        fallback_when_empty: Retry without definition filter if no results
    
    Returns:
        List of hits/popularity data with quality filters
    """
    if not uid:
        return [{"error": "Falta uid"}]

    limit = validate_limit(limit, default=50, max_limit=200)
    country = resolve_country_iso(country_input) if country_input else None
    resolved_definition = _resolve_definition(definition)
    resolved_license = _resolve_license(license_)

    scope = f"country={country}" if (
        scoped_by_country and country) else "global(hash_unique)"

    sql, params = _build_sql_hits_quality(
        country, uid, limit, resolved_definition, resolved_license)
    rows = db.execute_query(sql, params)
    logger.debug("SQL principal:\n%s\nparams=%s", sql, params)

    did_fallback = False
    if fallback_when_empty and not rows and resolved_definition:
        logger.info(
            "Sin resultados con definición; probando fallback sin definición")
        sql, params = _build_sql_hits_quality(
            country, uid, limit, None, resolved_license)
        rows = db.execute_query(sql, params)
        did_fallback = True
        logger.debug("SQL fallback:\n%s\nparams=%s", sql, params)

    fallback_info = " (fallback no-def)" if did_fallback else ""
    ident = (
        f"{scope} | uid={uid} | def={resolved_definition or 'any'}{fallback_info} "
        f"| lic={resolved_license or 'any'} | limit={limit}"
    )

    return handle_query_result(rows, "hits + quality", ident)

@dataclass
class PresenceWithPriceQuery:
    iso_alpha2: Optional[str] = None
    platform_name: Optional[str] = None
    platform_code: Optional[str] = None
    package_code: Optional[str] = None
    package_code2: Optional[str] = None
    plan_name: Optional[str] = None
    uid: Optional[str] = None
    hash_unique: Optional[str] = None
    type: Optional[str] = None
    title_like: Optional[str] = None
    duration_min: Optional[int] = None
    duration_max: Optional[int] = None

    price_type: Optional[List[str]] = None
    definition: Optional[List[str]] = None
    license_: Optional[List[str]] = None
    currency: Optional[List[str]] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None

    select: Optional[List[str]] = None
    order_by: Optional[str] = None
    limit: Optional[int] = 100
    offset: Optional[int] = 0

    count_only: bool = False
    today: Optional[date] = None

def build_presence_with_price_query(q: PresenceWithPriceQuery) -> Tuple[str, Dict[str, Any]]:
    """Genera SQL (LEFT JOIN LATERAL) para presencia con último precio."""
    params: Dict[str, Any] = {}
    where: List[str] = []

    if q.today:
        params["today_p"] = q.today
        where.append("(p.out_on IS NULL OR p.out_on >= %(today_p)s)")

    if q.uid:
        where.append("p.uid = %(uid)s")
        params["uid"] = q.uid
    if q.hash_unique:
        where.append("p.hash_unique = %(hash_unique)s")
        params["hash_unique"] = q.hash_unique
    if q.platform_code:
        where.append("p.platform_code ILIKE (%(platform_code)s)")
        params["platform_code"] = q.platform_code
    if q.platform_name:
        where.append("p.platform_name = %(platform_name)s")
        params["platform_name"] = q.platform_name
    if q.iso_alpha2:
        where.append("p.iso_alpha2 = %(iso_alpha2)s")
        params["iso_alpha2"] = q.iso_alpha2
    if q.title_like:
        where.append("p.clean_title ILIKE %(title_like)s")
        params["title_like"] = q.title_like
    if q.type:
        where.append("p.type = %(type)s")
        params["type"] = q.type
    if q.duration_min is not None:
        where.append("p.duration >= %(duration_min)s")
        params["duration_min"] = q.duration_min
    if q.duration_max is not None:
        where.append("p.duration <= %(duration_max)s")
        params["duration_max"] = q.duration_max

    price_where: List[str] = []
    if q.price_type:
        price_where.append("pp.price_type = ANY(%(ptype)s)")
        params["ptype"] = q.price_type
    if q.definition:
        price_where.append("pp.definition = ANY(%(def)s)")
        params["def"] = q.definition
    if q.license_:
        price_where.append("pp.license = ANY(%(lic)s)")
        params["lic"] = q.license_
    if q.currency:
        price_where.append("pp.currency = ANY(%(curr)s)")
        params["curr"] = [c.upper() for c in q.currency]
    if q.min_price is not None:
        price_where.append("pp.price >= %(minp)s")
        params["minp"] = q.min_price
    if q.max_price is not None:
        price_where.append("pp.price <= %(maxp)s")
        params["maxp"] = q.max_price
    price_where_sql = " AND ".join(price_where)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    if q.count_only:
        sql = f"""
            SELECT COUNT(*) AS cnt
            FROM {PRES_TBL} p
            LEFT JOIN LATERAL (
                SELECT
                    pp.price      AS price_amount,
                    pp.currency   AS price_currency,
                    pp.price_type AS price_type,
                    pp.definition AS price_definition,
                    pp.license    AS price_license,
                FROM {PRICES_TBL} pp
                WHERE pp.hash_unique = p.hash_unique AND ({price_where_sql})
                LIMIT 1
            ) price ON TRUE
            {where_sql};
        """
        return sql, params

    # SELECT principal
    select_cols = _validate_select(q.select)
    select_sql = ", ".join([
        f"p.{c}" if c in PRESENCE_ALLOWED_SELECT else f"price.{c}"
        for c in select_cols
    ])
    order_sql = "ORDER BY " + (q.order_by or "p.clean_title ASC")

    limit = validate_limit(q.limit, 100, 1000)
    offset = max(0, int(q.offset or 0))

    sql = f"""
        SELECT {select_sql}
        FROM {PRES_TBL} p
        LEFT JOIN LATERAL (
            SELECT
                pp.price      AS price_amount,
                pp.currency   AS price_currency,
                pp.price_type AS price_type,
                pp.definition AS price_definition,
                pp.license    AS price_license,
                pp.out_on     AS price_out_on
            FROM {PRICES_TBL} pp
            WHERE pp.hash_unique = p.hash_unique AND ({price_where_sql})
            LIMIT 1
        ) price ON TRUE
        {where_sql}
        {order_sql}
        LIMIT {limit} OFFSET {offset};
    """
    return sql, params

def query_presence_with_price(**kwargs) -> List[Dict[str, Any]]:
    """Ejecuta la query de presencia+precio y devuelve filas."""
    q = PresenceWithPriceQuery(**kwargs)
    sql, params = build_presence_with_price_query(q)
    rows = db.execute_query(sql, params) or []
    return rows

def tool_prices_latest(*args, **kwargs):
    """Últimos precios con filtros flexibles (hash/uid/país/plataforma, etc.)."""
    kwargs = normalize_args_kwargs(args, kwargs)
    arg1 = kwargs.get("__arg1")
    hash_unique = kwargs.get("hash_unique")
    uid = kwargs.get("uid")
    country = kwargs.get("country")
    platform_name = kwargs.get("platform_name")
    platform_code = kwargs.get("platform_code")
    price_type = kwargs.get("price_type")
    definition = _resolve_definition(kwargs.get("definition"))
    license_ = _resolve_license(kwargs.get("license_"))
    currency = kwargs.get("currency")
    min_price = kwargs.get("min_price")
    max_price = kwargs.get("max_price")
    limit = validate_limit(kwargs.get("limit", MAX_LIMIT),
                           DEFAULT_LIMIT, MAX_LIMIT)

    iso, plat_name, price_type, currency = _normalize_price_filters(
        country, platform_name, price_type, currency
    )

    if arg1 and not (hash_unique or uid or country):
        kind, _ = detect_id_kind(arg1, PRICES_TBL, PRES_TBL)
        if kind == "hash_unique":
            hash_unique = arg1
        elif kind in ("uid", "both"):
            uid = arg1
        else:
            country = arg1
            iso = resolve_country_iso(country)

    scopes, scope_params = [], []

    if hash_unique:
        scopes.append("pr.hash_unique = %s")
        scope_params.append(hash_unique)

    hashes_from_uid: List[str] = []
    if uid and not hash_unique:
        hashes_from_uid = get_hashes_by_uid(
            uid, PRES_TBL, iso=iso, platform_name=plat_name)
        if hashes_from_uid:
            scopes.append(
                f"pr.hash_unique IN ({', '.join(['%s']*len(hashes_from_uid))})")
            scope_params.extend(hashes_from_uid)

    need_presence = bool(
        (uid and not hashes_from_uid and not hash_unique)
        or (iso and not hashes_from_uid and not hash_unique)
        or (plat_name and not hashes_from_uid and not hash_unique)
    )
    join_pres = f"JOIN {PRES_TBL} p ON p.hash_unique = pr.hash_unique" if need_presence else ""

    if need_presence:
        if uid:
            scopes.append("p.uid = %s")
            scope_params.append(uid)
        if iso:
            scopes.append("p.iso_alpha2 = %s")
            scope_params.append(iso)
        if plat_name:
            scopes.append("p.platform_name = %s")
            scope_params.append(plat_name)

    if platform_code:
        scopes.append("pr.platform_code = %s")
        scope_params.append(platform_code)

    where_scopes = " AND ".join(scopes) if scopes else "TRUE"

    extra_filters, post_params = "TRUE", []

    pt_clause, pt_params = build_in_clause("price_type", price_type)
    if pt_clause:
        extra_filters += f" AND {pt_clause}"
        post_params.extend(pt_params)

    def_clause, def_params = build_in_clause("definition", definition)
    if def_clause:
        extra_filters += f" AND {def_clause}"
        post_params.extend(def_params)

    lic_clause, lic_params = build_in_clause("license", license_)
    if lic_clause:
        extra_filters += f" AND {lic_clause}"
        post_params.extend(lic_params)

    curr_clause, curr_params = build_in_clause("currency", currency)
    if curr_clause:
        extra_filters += f" AND {curr_clause}"
        post_params.extend(curr_params)

    if min_price is not None:
        extra_filters += " AND price >= %s"
        post_params.append(min_price)
    if max_price is not None:
        extra_filters += " AND price <= %s"
        post_params.append(max_price)

    sql = (
        SQL_LATEST_PRICE
        .replace("{JOIN_PRES}", join_pres)
        .replace("{WHERE_SCOPES}", where_scopes)
        .replace("{EXTRA_FILTERS}", extra_filters)
    )

    rows = db.execute_query(sql, tuple(
        scope_params + post_params + [limit])) or []
    return handle_query_result(
        rows,
        "presence_prices.latest",
        f"hash={hash_unique or '-'} uid={uid or '-'} iso={iso or '-'} plat_name={plat_name or '-'} plat_code={platform_code or '-'} limit={limit}",
    )

def tool_prices_history(*args, **kwargs):
    """Histórico de precios con filtros flexibles."""
    kwargs = normalize_args_kwargs(args, kwargs)
    arg1 = kwargs.get("__arg1")
    hash_unique = kwargs.get("hash_unique")
    uid = kwargs.get("uid")
    title_like = kwargs.get("title_like")
    platform_name = kwargs.get("platform_name")
    platform_code = kwargs.get("platform_code")
    price_type = kwargs.get("price_type")
    definition = _resolve_definition(kwargs.get("definition"))
    license_ = _resolve_license(kwargs.get("license_"))
    currency = kwargs.get("currency")
    min_price = kwargs.get("min_price")
    max_price = kwargs.get("max_price")
    limit = validate_limit(kwargs.get("limit", 500), 500, MAX_LIMIT)

    iso, plat_name, price_type, currency = _normalize_price_filters(
        country, platform_name, price_type, currency
    )

    if arg1 and not (hash_unique or uid):
        kind, _ = detect_id_kind(arg1, PRICES_TBL, PRES_TBL)
        if kind == "hash_unique":
            hash_unique = arg1
        elif kind in ("uid", "both"):
            uid = arg1
        else:
            title_like = title_like or arg1

    joins, where_parts = [], []
    params: List[Any] = []

    if hash_unique:
        where_parts.append("pr.hash_unique = %s")
        params.append(hash_unique)
    else:
        if uid and not (iso or plat_name or title_like):
            one = db.execute_query(
                f"SELECT p.hash_unique FROM {PRES_TBL} p WHERE p.uid = %s AND p.hash_unique IS NOT NULL LIMIT 1",
                (uid,),
            ) or []
            if one:
                where_parts.append("pr.hash_unique = %s")
                params.append(one[0]["hash_unique"])
        if not where_parts and (uid or iso or plat_name or title_like):
            joins.append(
                f"JOIN {PRES_TBL} p ON p.hash_unique = pr.hash_unique")
            if uid:
                where_parts.append("p.uid = %s")
                params.append(uid)
            if title_like:
                where_parts.append("p.clean_title ILIKE %s")
                params.append(f"%{title_like}%")
            if iso:
                where_parts.append("p.iso_alpha2 = %s")
                params.append(iso)
            if plat_name:
                where_parts.append("p.platform_name = %s")
                params.append(plat_name)

    if platform_code:
        where_parts.append("pr.platform_code = %s")
        params.append(platform_code)

    pt_clause, pt_params = build_in_clause("pr.price_type", price_type)
    if pt_clause:
        where_parts.append(pt_clause)
        params.extend(pt_params)

    def_clause, def_params = build_in_clause("pr.definition", definition)
    if def_clause:
        where_parts.append(def_clause)
        params.extend(def_params)

    lic_clause, lic_params = build_in_clause("pr.license", license_)
    if lic_clause:
        where_parts.append(lic_clause)
        params.extend(lic_params)

    curr_clause, curr_params = build_in_clause("pr.currency", currency)
    if curr_clause:
        where_parts.append(curr_clause)
        params.extend(curr_params)

    if min_price is not None:
        where_parts.append("pr.price >= %s")
        params.append(min_price)
    if max_price is not None:
        where_parts.append("pr.price <= %s")
        params.append(max_price)

    if not where_parts:
        raise ValueError(
            "Provide at least one filter: hash_unique, uid, title_like, country o platform_name"
        )

    sql = (
        SQL_PRICE_HISTORY
        .replace("{JOIN_CONDITIONS}", (" " + " ".join(joins) + " ") if joins else " ")
        .replace("{WHERE_CLAUSE}", " AND ".join(where_parts))
    )

    rows = db.execute_query(sql, tuple(params + [limit])) or []
    return handle_query_result(
        rows,
        "presence_prices.history",
        f"uid={uid or '-'} iso={iso or '-'} plat_name={plat_name or '-'} limit={limit}",
    )

def tool_prices_changes_last_n_days(*args, **kwargs):
    """Cambios de precio en los últimos N días (up/down/all)."""
    kwargs = normalize_args_kwargs(args, kwargs)
    arg1 = kwargs.get("__arg1")
    hash_unique = kwargs.get("hash_unique")
    uid = kwargs.get("uid")
    n_days = validate_days_back(kwargs.get("n_days", 7), DEFAULT_DAYS_BACK)
    country = kwargs.get("country")
    platform_code = kwargs.get("platform_code")
    price_type = kwargs.get("price_type")
    direction = kwargs.get("direction", "down")
    limit = validate_limit(kwargs.get("limit", MAX_LIMIT),
                           DEFAULT_LIMIT, MAX_LIMIT)

    iso = resolve_country_iso(country) if country else None
    if isinstance(price_type, str):
        price_type = [price_type]

    if arg1 and not (hash_unique or uid or country):
        kind, _ = detect_id_kind(arg1, PRICES_TBL, PRES_TBL)
        if kind == "hash_unique":
            hash_unique = arg1
        elif kind in ("uid", "both"):
            uid = arg1
        else:
            country = arg1
            iso = resolve_country_iso(country)

    scopes, scope_params = [], []
    join_pres = ""

    if hash_unique:
        scopes.append("pr.hash_unique = %s")
        scope_params.append(hash_unique)

    hashes_from_uid: List[str] = []
    if uid and not hash_unique:
        hashes_from_uid = get_hashes_by_uid(
            uid, PRES_TBL, iso=iso, platform_name=None)
        if hashes_from_uid:
            scopes.append(
                f"pr.hash_unique IN ({', '.join(['%s']*len(hashes_from_uid))})")
            scope_params.extend(hashes_from_uid)

    need_presence = bool((uid and not hashes_from_uid and not hash_unique) or (
        iso and not hashes_from_uid and not hash_unique))
    if need_presence:
        join_pres = f"JOIN {PRES_TBL} p ON p.hash_unique = pr.hash_unique"
        if uid:
            scopes.append("p.uid = %s")
            scope_params.append(uid)
        if iso:
            scopes.append("p.iso_alpha2 = %s")
            scope_params.append(iso)

    if platform_code:
        scopes.append("pr.platform_code = %s")
        scope_params.append(platform_code)

    pt_clause, pt_params = build_in_clause("pr.price_type", price_type)
    if pt_clause:
        scopes.append(pt_clause)
        scope_params.extend(pt_params)

    where_scopes = " AND ".join(scopes) if scopes else "TRUE"

    dir_sql = (
        "AND (price < prev_price)" if direction == "down"
        else "AND (price > prev_price)" if direction == "up"
        else ""
    )

    sql = (
        SQL_PRICE_CHANGES
        .replace("{JOIN_PRES}", join_pres)
        .replace("{WHERE_SCOPES}", where_scopes)
        .replace("{DIRECTION_FILTER}", f" {dir_sql} ")
    )

    interval_literal = f"'{int(max(1, n_days))} days'"
    rows = db.execute_query(sql, tuple(
        scope_params + [interval_literal, limit])) or []
    return handle_query_result(
        rows,
        "presence_prices.changes",
        f"last={n_days}d uid={uid or '-'} iso={iso or '-'} dir={direction} limit={limit}",
    )

def tool_prices_stats(*args, **kwargs):
    """Estadísticas de precio (min/max/avg/medianas/pXX) con filtros comunes."""
    kwargs = normalize_args_kwargs(args, kwargs)
    country = kwargs.get("country") or kwargs.get("__arg1")
    platform_code = kwargs.get("platform_code")
    platform_name = kwargs.get("platform_name")
    price_type = kwargs.get("price_type")
    definition = _resolve_definition(kwargs.get("definition"))
    license_ = _resolve_license(kwargs.get("license_"))
    currency = kwargs.get("currency")

    iso, plat_name, price_type, currency = _normalize_price_filters(
        country, platform_name, price_type, currency
    )

    join_pres = (
        f"JOIN {PRES_TBL} p ON p.hash_unique = pr.hash_unique" if (
            iso or plat_name) else ""
    )

    scopes, params = [], []
    if iso:
        scopes.append("p.iso_alpha2 = %s")
        params.append(iso)
    if plat_name:
        scopes.append("p.platform_name= %s")
        params.append(plat_name)
    if platform_code:
        scopes.append("pr.platform_code = %s")
        params.append(platform_code)

    pt_clause, pt_params = build_in_clause("pr.price_type", price_type)
    if pt_clause:
        scopes.append(pt_clause)
        params.extend(pt_params)

    def_clause, def_params = build_in_clause("pr.definition", definition)
    if def_clause:
        scopes.append(def_clause)
        params.extend(def_params)

    lic_clause, lic_params = build_in_clause("pr.license", license_)
    if lic_clause:
        scopes.append(lic_clause)
        params.extend(lic_params)

    curr_clause, curr_params = build_in_clause("pr.currency", currency)
    if curr_clause:
        scopes.append(curr_clause)
        params.extend(curr_params)

    where_scopes = " AND ".join(scopes) if scopes else "TRUE"
    sql = (
        SQL_PRICE_STATS
        .replace("{JOIN_PRES}", join_pres)
        .replace("{WHERE_SCOPES}", where_scopes)
    )

    rows = db.execute_query(sql, tuple(params)) or []
    return handle_query_result(
        rows,
        "presence_prices.stats",
        f"iso={iso or 'any'} plat_code={platform_code or 'any'} plat_name={plat_name or 'any'}",
    )