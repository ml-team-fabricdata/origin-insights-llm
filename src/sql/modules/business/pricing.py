
from src.sql.utils.db_utils_sql import *
from src.sql.utils.default_import import *
from src.sql.queries.business.queries_business import *
from src.sql.utils.validators_shared import *

# ================================================================
# Helpers de normalización y validación
# ================================================================


def _normalize_string(s: Optional[str]) -> str:
    """Normaliza para matching de alias (strip + lower)."""
    return (s or "").strip().lower()


def _resolve_definition(values: Optional[List[str]]) -> Optional[List[str]]:
    """Normaliza/valida definiciones (e.g., "sd hd" -> "SD/HD")."""
    if not values:
        return None
    resolved: List[str] = []
    for value in values:
        key = _normalize_string(value)
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
        key = _normalize_string(value)
        canonical = LIC_ALIASES.get(key, value.strip().upper())
        if canonical in VALID_LICENSES:
            resolved.append(canonical)
        else:
            logger.warning(f"Licencia no válida ignorada: {value}")
    return resolved or None


def _normalize_tool_call(args, kwargs) -> Dict[str, Any]:
    """Permite llamadas flexibles (posicional, dict único o kwargs puros)."""
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


def _validate_select(select: Optional[List[str]]) -> List[str]:
    """Valida columnas de salida para presencia+precio."""
    if not select:
        return PRESENCE_DEFAULT_SELECT
    safe = [
        c for c in select
        if c in PRESENCE_ALLOWED_SELECT or c in PRESENCE_PRICE_DERIVED_SELECT
    ]
    return safe or PRESENCE_DEFAULT_SELECT


# ================================================================
# Bloque: HITS con calidad (definition/license)
# ================================================================

def _build_filters_and_params(
    definition: Optional[List[str]],
    license_: Optional[List[str]],
) -> Tuple[str, str, List[str]]:
    """Construye filtros SQL y parámetros para las columnas derivadas (x.*)."""
    def_filter = ""
    lic_filter = ""
    params: List[str] = []

    if definition:
        placeholders = ", ".join(["%s"] * len(definition))
        def_filter = f"AND COALESCE(x.definition,'') IN ({placeholders})"
        params.extend(definition)

    if license_:
        placeholders = ", ".join(["%s"] * len(license_))
        lic_filter = f"AND COALESCE(x.license,'') IN ({placeholders})"
        params.extend(license_)

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
) -> str:
    """Devuelve hits con filtros de calidad (definition/license)."""
    if not uid:
        return as_tool_payload([{"error": "Falta uid"}], ident="hits + quality | missing-uid")

    limit = max(1, min(int(limit) if isinstance(limit, int) else 50, 200))
    country = resolve_country_iso(country_input) if country_input else None
    resolved_definition = _resolve_definition(definition)
    resolved_license = _resolve_license(license_)

    scope = f"country={country}" if (
        scoped_by_country and country) else "global(hash_unique)"

    # Consulta principal
    sql, params = _build_sql_hits_quality(
        country, uid, limit, resolved_definition, resolved_license)
    rows = db.execute_query(sql, params)
    logger.debug("SQL principal:\n%s\nparams=%s", sql, params)

    # Fallback: si no hay resultados y se pidió definición, reintentar sin definition
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

    payload = handle_query_result(rows, "hits + quality", ident)
    return as_tool_payload(payload, ident=f"hits_with_quality | {ident}")


# ================================================================
# Presencia + precio (query model + builder)
# ================================================================

@dataclass
class PresenceWithPriceQuery:
    # Filtros de presencia
    active_only_presence: bool = True
    registry_status: Optional[str] = None
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

    # Filtros de precio
    active_only_price: bool = True
    price_type: Optional[List[str]] = None
    definition: Optional[List[str]] = None
    license_: Optional[List[str]] = None
    currency: Optional[List[str]] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None

    # Salida, orden y paginación
    select: Optional[List[str]] = None
    order_by: Optional[str] = None
    limit: Optional[int] = 100
    offset: Optional[int] = 0

    # Especiales
    count_only: bool = False
    today: Optional[date] = None


def build_presence_with_price_query(q: PresenceWithPriceQuery) -> Tuple[str, Dict[str, Any]]:
    """Genera SQL (LEFT JOIN LATERAL) para presencia con último precio."""
    params: Dict[str, Any] = {}
    where: List[str] = []

    # Presencia activa
    if q.active_only_presence:
        today = q.today or date.today()
        params["today_p"] = today
        where.append("(p.out_on IS NULL)")

    # Filtros de presencia
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
    if q.registry_status:
        where.append("p.registry_status = %(registry_status)s")
        params["registry_status"] = q.registry_status

    # Filtros de precio
    price_where: List[str] = []
    if q.active_only_price:
        price_where.append(
            "(pp.active_only_price IS NULL OR pp.active_only_price = TRUE)")
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
    if not price_where:
        price_where.append("TRUE")
    price_where_sql = " AND ".join(price_where)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    # COUNT ONLY
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
                    pp.created_at AS price_created_at
                FROM {PRICES_TBL} pp
                WHERE pp.hash_unique = p.hash_unique AND ({price_where_sql})
                ORDER BY pp.created_at DESC
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
                pp.out_on     AS price_out_on,
                pp.created_at AS price_created_at
            FROM {PRICES_TBL} pp
            WHERE pp.hash_unique = p.hash_unique AND ({price_where_sql})
            ORDER BY pp.created_at DESC
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


# ================================================================
# Herramientas de precios (latest, history, changes, stats)
# ================================================================

def tool_prices_latest(*args, **kwargs):
    """Últimos precios con filtros flexibles (hash/uid/país/plataforma, etc.)."""
    kwargs = _normalize_tool_call(args, kwargs)
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

    iso = resolve_country_iso(country) if country else None
    plat_name = resolve_platform_name(platform_name) if platform_name else None

    if isinstance(price_type, str):
        price_type = [price_type]
    if isinstance(currency, str):
        currency = [currency]
    currency = [c.upper() for c in (currency or [])]

    # Desambiguación de __arg1
    if arg1 and not (hash_unique or uid or country):
        kind, _ = detect_id_kind(arg1, PRICES_TBL, PRES_TBL)
        if kind == "hash_unique":
            hash_unique = arg1
        elif kind in ("uid", "both"):
            uid = arg1
        else:
            country = arg1
            iso = resolve_country_iso(country)

    # Scopes para WHERE_SCOPES (solo condiciones)
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

    # Filtros post (EXTRA_FILTERS)
    extra_filters, post_params = "TRUE", []
    if price_type:
        extra_filters += f" AND price_type IN ({', '.join(['%s']*len(price_type))})"
        post_params += price_type
    if definition:
        extra_filters += f" AND definition IN ({', '.join(['%s']*len(definition))})"
        post_params += definition
    if license_:
        extra_filters += f" AND license IN ({', '.join(['%s']*len(license_))})"
        post_params += license_
    if currency:
        extra_filters += f" AND currency IN ({', '.join(['%s']*len(currency))})"
        post_params += currency
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
    kwargs = _normalize_tool_call(args, kwargs)
    arg1 = kwargs.get("__arg1")
    hash_unique = kwargs.get("hash_unique")
    uid = kwargs.get("uid")
    title_like = kwargs.get("title_like")
    country = kwargs.get("country")
    platform_name = kwargs.get("platform_name")
    platform_code = kwargs.get("platform_code")
    price_type = kwargs.get("price_type")
    definition = _resolve_definition(kwargs.get("definition"))
    license_ = _resolve_license(kwargs.get("license_"))
    currency = kwargs.get("currency")
    min_price = kwargs.get("min_price")
    max_price = kwargs.get("max_price")
    limit = validate_limit(kwargs.get("limit", 500), 500, MAX_LIMIT)

    iso = resolve_country_iso(country) if country else None
    plat_name = resolve_platform_name(platform_name) if platform_name else None

    if isinstance(price_type, str):
        price_type = [price_type]
    if isinstance(currency, str):
        currency = [currency]
    currency = [c.upper() for c in (currency or [])]

    # __arg1 heurístico
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

    # JOIN/WHERE principal
    if hash_unique:
        where_parts.append("pr.hash_unique = %s")
        params.append(hash_unique)
    else:
        # Fast-path: si sólo dan uid, intentar un hash
        if uid and not (iso or plat_name or title_like):
            one = db.execute_query(
                f"SELECT p.hash_unique FROM {PRES_TBL} p WHERE p.uid = %s AND p.hash_unique IS NOT NULL LIMIT 1",
                (uid,),
            ) or []
            if one:
                where_parts.append("pr.hash_unique = %s")
                params.append(one[0]["hash_unique"])
        # Si no hay fast-path válido, usar JOIN con presencia
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
    if price_type:
        where_parts.append(
            f"pr.price_type IN ({', '.join(['%s']*len(price_type))})")
        params += price_type
    if definition:
        where_parts.append(
            f"pr.definition IN ({', '.join(['%s']*len(definition))})")
        params += definition
    if license_:
        where_parts.append(
            f"pr.license IN ({', '.join(['%s']*len(license_))})")
        params += license_
    if currency:
        where_parts.append(
            f"pr.currency IN ({', '.join(['%s']*len(currency))})")
        params += currency
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
    kwargs = _normalize_tool_call(args, kwargs)
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
    if price_type:
        scopes.append(
            f"pr.price_type IN ({', '.join(['%s']*len(price_type))})")
        scope_params += price_type

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
    kwargs = _normalize_tool_call(args, kwargs)
    country = kwargs.get("country") or kwargs.get("__arg1")
    platform_code = kwargs.get("platform_code")
    platform_name = kwargs.get("platform_name")
    price_type = kwargs.get("price_type")
    definition = _resolve_definition(kwargs.get("definition"))
    license_ = _resolve_license(kwargs.get("license_"))
    currency = kwargs.get("currency")

    iso = resolve_country_iso(country) if country else None
    plat_name = resolve_platform_name(platform_name) if platform_name else None

    if isinstance(currency, str):
        currency = [currency]
    currency = [c.upper() for c in (currency or [])]
    if isinstance(price_type, str):
        price_type = [price_type]

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
    if price_type:
        scopes.append(
            f"pr.price_type IN ({', '.join(['%s']*len(price_type))})")
        params += price_type
    if definition:
        scopes.append(
            f"pr.definition IN ({', '.join(['%s']*len(definition))})")
        params += definition
    if license_:
        scopes.append(f"pr.license IN ({', '.join(['%s']*len(license_))})")
        params += license_
    if currency:
        scopes.append(f"pr.currency IN ({', '.join(['%s']*len(currency))})")
        params += currency

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
