from dataclasses import dataclass
from datetime import date
from typing import Any, List, Literal, Optional, Tuple, Dict
from common.sql_db import db
from .validators_shared import *
from .constants_sql import *
from .db_utils_sql import handle_query_result
from .constants_sql import *
import logging

logger = logging.getLogger(__name__)

def _norm(s: str) -> str:
    return (s or "").strip().lower()

def _resolve_definition(values: Optional[List[str]]) -> Optional[List[str]]:
    logger.info(f"_resolve_definition called with values={values}")
    if not values:
        return None
    out = []
    for v in values:
        key = _norm(v)
        canon = DEF_ALIASES.get(key) or v.strip().upper().replace(" ", "")
        if canon == "SDHD":
            canon = "SD/HD"
        if canon in VALID_DEFINITIONS:
            out.append(canon)
    return out or None

def _resolve_license(values: Optional[List[str]]) -> Optional[List[str]]:
    logger.info(f"_resolve_license called with values={values}")
    if not values:
        return None
    out = []
    for v in values:
        key = _norm(v)
        canon = LIC_ALIASES.get(key, v.strip().upper())
        if canon in VALID_LICENSES:
            out.append(canon)
    return out or None

def validate_limit(limit: Optional[int], default: int = DEFAULT_LIMIT, max_limit: int = MAX_LIMIT) -> int:
    """Validates and normalizes limit parameter."""
    if not isinstance(limit, int) or limit <= 0:
        return default
    return min(limit, max_limit)

def validate_days_back(days: Optional[int], default: int = DEFAULT_DAYS_BACK) -> int:
    """Validates and normalizes days_back parameter."""
    if not isinstance(days, int) or days <= 0:
        return default
    return max(1, days)

# --------------------------------------------------------------------
# ÃšLTIMO PRECIO por hash_unique (scoped por país/plataforma)
# --------------------------------------------------------------------
SQL_LATEST_PRICE = f"""
WITH prices_scoped AS (
  SELECT pr.*
  FROM {PRICES_TBL} pr
  {{JOIN_PRES}}
  {{WHERE_SCOPES}}
),
ranked AS (
  SELECT ps.*,
         ROW_NUMBER() OVER (
           PARTITION BY ps.hash_unique
           ORDER BY COALESCE(ps.created_at) DESC
         ) AS rn
  FROM prices_scoped ps
)
SELECT
  r.hash_unique, r.platform_code, r.price_type, r.price, r.currency,
  r.definition, r.license, r.out_on, r.created_at
FROM ranked r
WHERE r.rn = 1
{{EXTRA_FILTERS}}
ORDER BY r.created_at DESC NULLS LAST
LIMIT %s;
""".strip()

IdKind = Literal["hash_unique", "uid", "none", "both"]

def _normalize_tool_call(args, kwargs):
    """
    Tolerancia a llamadas posicionales del orquestador:
    - (dict)           → merge con kwargs
    - (str/int/...)    → mapea a '__arg1'
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

def detect_id_kind(value: str) -> Tuple[IdKind, Optional[str]]:
    """
    Consulta la DB para ver si 'value' existe como hash_unique (prices) o uid (presence).
    """
    if not value:
        return "none", None

    q_hash = f"SELECT 1 FROM {PRICES_TBL} WHERE hash_unique = %s LIMIT 1"
    exists_hash = bool(db.execute_query(q_hash, (value,)))

    q_uid = f"SELECT 1 FROM {PRES_TBL} WHERE uid = %s LIMIT 1"
    exists_uid = bool(db.execute_query(q_uid, (value,)))

    if exists_hash and exists_uid:
        return "both", value
    if exists_hash:
        return "hash_unique", value
    if exists_uid:
        return "uid", value
    return "none", None

def get_hashes_by_uid(uid: str, *, iso: Optional[str] = None, platform_name: Optional[str] = None) -> List[str]:
    """
    Devuelve DISTINCT hash_unique desde presence para un uid, con filtros opcionales por país/plataforma.
    """
    if not uid:
        return []
    where, params = ["p.uid = %s"], [uid]
    if iso:
        where.append("LOWER(p.iso_alpha2) = %s")
        params.append(iso.lower())
    if platform_name:
        where.append("LOWER(p.platform_name) = %s")
        params.append(platform_name)
    sql = f"""
        SELECT DISTINCT p.hash_unique
        FROM {PRES_TBL} p
        WHERE {" AND ".join(where)}
    """
    rows = db.execute_query(sql, tuple(params)) or []
    return [r["hash_unique"] for r in rows if r.get("hash_unique")]

def get_hash_by_uid(uid: str, *, iso: Optional[str] = None, platform_name: Optional[str] = None) -> Optional[str]:
    """
    Variante que devuelve un solo hash (primero disponible).
    """
    lst = get_hashes_by_uid(uid, iso=iso, platform_name=platform_name)
    return lst[0] if lst else None

# =========================
# Tools
# =========================

def tool_prices_latest(*args, **kwargs):
    """
    Devuelve el ÚLTIMO registro de precios por hash_unique (incluye price y currency).

    Soporta:
      - hash_unique (fast-path sin JOIN)
      - uid (resuelve lista de hashes; evita JOIN si puede)
      - country (ISO/nombre via presence), platform_name (presence), platform_code (prices)
      - price_type, definition, license_, currency, min_price, max_price, limit
      - __arg1 tolerante: se desambigua (uid/hash_unique); si no existe, puede ser country
    """
    # --- normalizar llamada ---
    kwargs = _normalize_tool_call(args, kwargs)

    # --- args ---
    arg1 = kwargs.get("__arg1")
    hash_unique = kwargs.get("hash_unique")
    uid = kwargs.get("uid")
    country = kwargs.get("country")
    platform_name = kwargs.get("platform_name")
    platform_code = kwargs.get("platform_code")
    price_type = kwargs.get("price_type")
    definition = kwargs.get("definition")
    license_ = kwargs.get("license_")
    currency = kwargs.get("currency")
    min_price = kwargs.get("min_price")
    max_price = kwargs.get("max_price")
    limit = validate_limit(kwargs.get("limit", MAX_LIMIT))

    # --- normalizaciones ---
    iso = resolve_country_iso(country) if country else None
    plat_name = resolve_platform_name(platform_name) if platform_name else None

    if isinstance(price_type, str):
        price_type = [price_type]
    definition = _resolve_definition(definition)
    license_ = _resolve_license(license_)
    if isinstance(currency, str):
        currency = [currency]
    currency = [c.upper() for c in (currency or [])]

    # --- desambiguar __arg1 ---
    if arg1 and not (hash_unique or uid or country):
        kind, _ = detect_id_kind(arg1)
        if kind == "hash_unique":
            hash_unique = arg1
        elif kind in ("uid", "both"):
            uid = arg1
        else:
            country = arg1
            iso = resolve_country_iso(country)

    logger.info(
        "tool_prices_latest called with hash_unique=%s, uid=%s, iso=%s, platform_name=%s, platform_code=%s, "
        "price_type=%s, definition=%s, license_=%s, currency=%s, min_price=%s, max_price=%s, limit=%s",
        hash_unique, uid, iso, plat_name, platform_code, price_type, definition,
        license_, currency, min_price, max_price, limit
    )

    # ------------------------------
    # PRE-ranking (scopes para prices_scoped)
    # ------------------------------
    scopes, scope_params = [], []

    # Fast-path por hash_unique
    if hash_unique:
        scopes.append("pr.hash_unique = %s")
        scope_params.append(hash_unique)

    # Fast-path por uid → usar SIEMPRE lista de hashes (mejor recall)
    hashes_from_uid: List[str] = []
    if uid and not hash_unique:
        hashes_from_uid = get_hashes_by_uid(
            uid, iso=iso, platform_name=plat_name)
        if hashes_from_uid:
            MAX_HASHES = 200  # defensivo
            subset = hashes_from_uid[:MAX_HASHES]
            scopes.append(
                f"pr.hash_unique IN ({', '.join(['%s']*len(subset))})")
            scope_params.extend(subset)

    # ¿Necesitamos JOIN con presence?
    need_presence = bool(
        (uid and not hashes_from_uid and not hash_unique) or
        (iso and not hashes_from_uid and not hash_unique) or
        (plat_name and not hashes_from_uid and not hash_unique)
    )
    join_pres = f"JOIN {PRES_TBL} p ON p.hash_unique = pr.hash_unique" if need_presence else ""

    if need_presence:
        if uid:
            scopes.append("p.uid = %s")
            scope_params.append(uid)
        if iso:
            scopes.append("LOWER(p.iso_alpha2) = %s")
            scope_params.append(iso.lower())
        if plat_name:
            scopes.append("LOWER(p.platform_name) = %s")
            scope_params.append(plat_name)

    # Filtros que NO requieren presence
    if platform_code:
        scopes.append("LOWER(pr.platform_code) = %s")
        scope_params.append(platform_code.lower())

    where_scopes = "WHERE " + " AND ".join(scopes) if scopes else ""

    # ------------------------------
    # POST-ranking (EXTRA_FILTERS sobre r.*)
    # ------------------------------
    extra_filters, params_post = "", []
    if price_type:
        extra_filters += f" AND r.price_type IN ({', '.join(['%s']*len(price_type))})"
        params_post.extend(price_type)
    if definition:
        extra_filters += f" AND r.definition IN ({', '.join(['%s']*len(definition))})"
        params_post.extend(definition)
    if license_:
        extra_filters += f" AND r.license IN ({', '.join(['%s']*len(license_))})"
        params_post.extend(license_)
    if currency:
        extra_filters += f" AND r.currency IN ({', '.join(['%s']*len(currency))})"
        params_post.extend(currency)
    if min_price is not None:
        extra_filters += " AND r.price >= %s"
        params_post.append(min_price)
    if max_price is not None:
        extra_filters += " AND r.price <= %s"
        params_post.append(max_price)

    sql = (
        SQL_LATEST_PRICE
        .replace("{JOIN_PRES}", join_pres)
        .replace("{WHERE_SCOPES}", where_scopes)
        .replace("{EXTRA_FILTERS}", extra_filters)
    )

    rows = db.execute_query(sql, tuple(
        scope_params + params_post + [limit])) or []
    return handle_query_result(
        rows,
        "presence_prices.latest",
        (
            f"hash={hash_unique or '-'} uid={uid or '-'} iso={iso or '-'} "
            f"plat_name={plat_name or '-'} plat_code={platform_code or '-'} "
            f"ptype={price_type or '-'} def={definition or '-'} lic={license_ or '-'} "
            f"curr={currency or '-'} minP={min_price or '-'} maxP={max_price or '-'} "
            f"limit={limit}"
        ),
    )

SQL_PRICE_HISTORY = f"""
{{HEAD_CTE}}
SELECT
  pr.hash_unique, pr.platform_code, pr.price_type, pr.price, pr.currency,
  pr.definition, pr.license, pr.out_on, pr.created_at
FROM {PRICES_TBL} pr
{{FROM_JOIN}}
{{WHERE_CLAUSE}}
ORDER BY COALESCE(pr.created_at) DESC
LIMIT %s;
""".strip()

def tool_prices_history(*args, **kwargs):
    """
    Histórico de precios (desc por fecha) con patrón UID/hash_unique:
      - __arg1 se desambigua (hash_unique vs uid vs title_like).
      - Si tengo hash(es) -> filtro directo en PRICES (sin JOIN).
      - Si no, uso CTE (presence) para resolverlos.
    """
    kwargs = _normalize_tool_call(args, kwargs)

    # ---- args ----
    arg1 = kwargs.get("__arg1")
    hash_unique = kwargs.get("hash_unique")
    uid = kwargs.get("uid")
    title_like = kwargs.get("title_like")
    country = kwargs.get("country")
    platform_name = kwargs.get("platform_name")
    platform_code = kwargs.get("platform_code")
    price_type = kwargs.get("price_type")
    definition = kwargs.get("definition")
    license_ = kwargs.get("license_")
    currency = kwargs.get("currency")
    min_price = kwargs.get("min_price")
    max_price = kwargs.get("max_price")
    limit = validate_limit(kwargs.get("limit", 500))

    # normalizaciones
    iso = resolve_country_iso(country) if country else None
    plat_name = resolve_platform_name(platform_name) if platform_name else None
    if isinstance(price_type, str):
        price_type = [price_type]
    definition = _resolve_definition(definition)
    license_ = _resolve_license(license_)
    if isinstance(currency, str):
        currency = [currency]
    currency = [c.upper() for c in (currency or [])]

    # desambiguar arg1
    if arg1 and not (hash_unique or uid):
        kind, _ = detect_id_kind(arg1)
        if kind == "hash_unique":
            hash_unique = arg1
        elif kind in ("uid", "both"):
            uid = arg1
        else:
            title_like = title_like or arg1

    logger.info(
        "tool_prices_history called with hash_unique=%s uid=%s title_like=%s iso=%s plat_name=%s plat_code=%s "
        "ptype=%s def=%s lic=%s curr=%s minP=%s maxP=%s limit=%s",
        hash_unique, uid, title_like, iso, plat_name, platform_code,
        price_type, definition, license_, currency, min_price, max_price, limit
    )

    head_cte, from_join = "", ""
    where_pr: List[str] = []
    params_cte: List = []    # params del CTE (presence)
    params_where: List = []  # params del WHERE (prices)

    # Fast-path: hash_unique directo
    if hash_unique:
        where_pr.append("pr.hash_unique = %s")
        params_where.append(hash_unique)

    # Fast-path por uid → resolver hashes y evitar JOIN
    hashes_from_uid: List[str] = []
    if uid and not hash_unique:
        if not (iso or plat_name or title_like):
            one = get_hash_by_uid(uid)
            if one:
                hashes_from_uid = [one]
        else:
            hashes_from_uid = get_hashes_by_uid(
                uid, iso=iso, platform_name=plat_name)
        if hashes_from_uid:
            where_pr.append(
                f"pr.hash_unique IN ({', '.join(['%s']*len(hashes_from_uid))})")
            params_where.extend(hashes_from_uid)

    # ¿Necesitamos presence (CTE)?
    need_presence = bool(
        (uid and not hashes_from_uid and not hash_unique) or
        (title_like and not hashes_from_uid and not hash_unique) or
        (iso and not hashes_from_uid and not hash_unique) or
        (plat_name and not hashes_from_uid and not hash_unique)
    )
    if need_presence:
        hashes_where, hashes_params = [], []
        if uid:
            hashes_where.append("p.uid = %s")
            hashes_params.append(uid)
        if title_like:
            hashes_where.append("p.clean_title ILIKE %s")
            hashes_params.append(f"%{title_like}%")
        if iso:
            hashes_where.append("LOWER(p.iso_alpha2) = %s")
            hashes_params.append(iso.lower())
        if plat_name:
            hashes_where.append("LOWER(p.platform_name) = %s")
            hashes_params.append(plat_name)

        if hashes_where:
            head_cte = f"""
WITH hashes AS (
  SELECT DISTINCT p.hash_unique
  FROM {PRES_TBL} p
  WHERE {" AND ".join(hashes_where)}
)
""".strip()
            from_join = "JOIN hashes h ON h.hash_unique = pr.hash_unique"
            params_cte.extend(hashes_params)  # ¡primero params del CTE!

    # Filtros en PRICES (no requieren presence)
    if platform_code:
        where_pr.append("LOWER(pr.platform_code) = %s")
        params_where.append(platform_code.lower())
    if price_type:
        where_pr.append(
            f"pr.price_type IN ({', '.join(['%s']*len(price_type))})")
        params_where.extend(price_type)
    if definition:
        where_pr.append(
            f"pr.definition IN ({', '.join(['%s']*len(definition))})")
        params_where.extend(definition)
    if license_:
        where_pr.append(f"pr.license IN ({', '.join(['%s']*len(license_))})")
        params_where.extend(license_)
    if currency:
        where_pr.append(f"pr.currency IN ({', '.join(['%s']*len(currency))})")
        params_where.extend(currency)
    if min_price is not None:
        where_pr.append("pr.price >= %s")
        params_where.append(min_price)
    if max_price is not None:
        where_pr.append("pr.price <= %s")
        params_where.append(max_price)

    if not where_pr and not head_cte:
        raise ValueError(
            "Provide at least one filter: hash_unique, uid, title_like, country o platform_name")

    where_clause = "WHERE " + " AND ".join(where_pr) if where_pr else ""

    sql = (
        SQL_PRICE_HISTORY
        .replace("{HEAD_CTE}", head_cte)
        .replace("{FROM_JOIN}", f" {from_join} ")
        .replace("{WHERE_CLAUSE}", where_clause)
    )
    # Orden correcto: CTE → WHERE → LIMIT
    rows = db.execute_query(sql, tuple(
        params_cte + params_where + [limit])) or []
    return handle_query_result(
        rows,
        "presence_prices.history",
        (
            f"hash={hash_unique or '-'} uid={uid or '-'} title_like={title_like or '-'} "
            f"iso={iso or '-'} plat_name={plat_name or '-'} plat_code={platform_code or '-'} "
            f"ptype={price_type or '-'} def={definition or '-'} lic={license_ or '-'} "
            f"curr={currency or '-'} minP={min_price or '-'} maxP={max_price or '-'} limit={limit}"
        ),
    )

SQL_PRICE_CHANGES = f"""
WITH scoped AS (
  SELECT pr.*
  FROM {PRICES_TBL} pr
  {{JOIN_PRES}}
  {{WHERE_SCOPES}}
),
ordered AS (
  SELECT
    s.*,
    COALESCE(s.created_at) AS ts,
    LAG(s.price) OVER (
      PARTITION BY s.hash_unique, s.platform_code, s.price_type, s.definition, s.license, s.currency
      ORDER BY COALESCE(s.created_at)
    ) AS prev_price,
    LAG(COALESCE(s.created_at)) OVER (
      PARTITION BY s.hash_unique, s.platform_code, s.price_type, s.definition, s.license, s.currency
      ORDER BY COALESCE(s.created_at)
    ) AS prev_ts
  FROM scoped s
),
since AS (
  SELECT *
  FROM ordered
  WHERE ts >= CURRENT_DATE - %s::interval
)
SELECT
  s.hash_unique,
  s.platform_code,
  s.price_type,
  s.definition,
  s.license,
  s.currency,
  s.prev_price,
  s.price,
  (s.price - s.prev_price) AS delta,
  s.created_at,
  s.ts       AS current_ts,
  s.prev_ts  AS previous_ts
FROM since s
WHERE s.prev_price IS NOT NULL
{{DIRECTION}}
ORDER BY (s.price - s.prev_price) {{DELTA_ORDER}}, s.ts DESC
LIMIT %s;
""".strip()

def tool_prices_changes_last_n_days(*args, **kwargs):
    """
    Cambios de precio en los últimos N días (patrón UID/hash_unique):
      - __arg1 se desambigua (hash_unique vs uid vs country).
      - Si tengo hash(es) -> filtro directo (sin JOIN).
      - Si no, uso JOIN con presence para acotar por uid/país.
    """
    kwargs = _normalize_tool_call(args, kwargs)

    # args
    arg1 = kwargs.get("__arg1")
    hash_unique = kwargs.get("hash_unique")
    uid = kwargs.get("uid")
    n_days = validate_days_back(kwargs.get("n_days", 7))
    country = kwargs.get("country")
    platform_code = kwargs.get("platform_code")
    price_type = kwargs.get("price_type")
    direction = kwargs.get("direction", "down")
    limit = validate_limit(kwargs.get("limit", MAX_LIMIT))

    # normalizaciones
    iso = resolve_country_iso(country) if country else None
    if isinstance(price_type, str):
        price_type = [price_type]

    # desambiguar arg1
    if arg1 and not (hash_unique or uid or country):
        kind, _ = detect_id_kind(arg1)
        if kind == "hash_unique":
            hash_unique = arg1
        elif kind in ("uid", "both"):
            uid = arg1
        else:
            country = arg1
            iso = resolve_country_iso(country)

    logger.info(
        "tool_prices_changes_last_n_days called with n_days=%s hash_unique=%s uid=%s iso=%s "
        "platform_code=%s price_type=%s direction=%s limit=%s",
        n_days, hash_unique, uid, iso, platform_code, price_type, direction, limit
    )

    # dirección
    if direction == "down":
        direction_sql, delta_order = "AND (s.price < s.prev_price)", "ASC"
    elif direction == "up":
        direction_sql, delta_order = "AND (s.price > s.prev_price)", "DESC"
    else:
        direction_sql, delta_order = "", "DESC"

    interval_literal = f"'{int(max(1, n_days))} days'"

    # Scopes
    join_pres, scopes, scope_params = "", [], []

    # Fast-path por hash_unique
    if hash_unique:
        scopes.append("pr.hash_unique = %s")
        scope_params.append(hash_unique)

    # Fast-path por uid → resolver hashes
    hashes_from_uid: List[str] = []
    if uid and not hash_unique:
        hashes_from_uid = get_hashes_by_uid(uid, iso=iso, platform_name=None)
        if hashes_from_uid:
            MAX_HASHES = 200
            subset = hashes_from_uid[:MAX_HASHES]
            scopes.append(
                f"pr.hash_unique IN ({', '.join(['%s']*len(subset))})")
            scope_params.extend(subset)

    # ¿Necesitamos JOIN?
    need_presence = bool(
        (uid and not hashes_from_uid and not hash_unique) or
        (iso and not hashes_from_uid and not hash_unique)
    )
    if need_presence:
        join_pres = f"JOIN {PRES_TBL} p ON p.hash_unique = pr.hash_unique"
        if uid:
            scopes.append("p.uid = %s")
            scope_params.append(uid)
        if iso:
            scopes.append("LOWER(p.iso_alpha2) = %s")
            scope_params.append(iso.lower())

    # Filtros que no requieren presence
    if platform_code:
        scopes.append("LOWER(pr.platform_code) = %s")
        scope_params.append(platform_code.lower())
    if price_type:
        scopes.append(
            f"pr.price_type IN ({', '.join(['%s']*len(price_type))})")
        scope_params.extend(price_type)

    where_scopes = "WHERE " + " AND ".join(scopes) if scopes else ""

    sql = (
        SQL_PRICE_CHANGES
        .replace("{JOIN_PRES}", join_pres)
        .replace("{WHERE_SCOPES}", where_scopes)
        .replace("{DIRECTION}", f" {direction_sql} ")
        .replace("{DELTA_ORDER}", delta_order)
    )

    rows = db.execute_query(sql, tuple(
        scope_params + [interval_literal, limit])) or []
    return handle_query_result(
        rows,
        "presence_prices.changes",
        f"last={n_days}d hash={hash_unique or '-'} uid={uid or '-'} iso={iso or '-'} "
        f"plat_code={platform_code or '-'} ptype={price_type or '-'} dir={direction} limit={limit}",
    )

# ---------------------------------------------------------
# 4) RESUMEN / ESTADÍSTICAS por país/plataforma
# ---------------------------------------------------------
SQL_PRICE_STATS = f"""
SELECT
  pr.platform_code,
  pr.price_type,
  pr.currency,
  pr.definition,
  pr.license,
  COUNT(*)                                        AS samples,
  MIN(pr.price)                                   AS min_price,
  MAX(pr.price)                                   AS max_price,
  AVG(pr.price)::numeric(18,2)                    AS avg_price,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pr.price)::numeric(18,2) AS median_price
FROM {PRICES_TBL} pr
{{JOIN_PRES}}
{{WHERE_SCOPES}}
GROUP BY pr.platform_code, pr.price_type, pr.currency, pr.definition, pr.license
ORDER BY pr.platform_code, pr.price_type, pr.definition, pr.license;
""".strip()

def tool_prices_stats(*args, **kwargs):
    """
    Resumen estadístico (count/min/max/avg/median) con tolerancia a llamadas posicionales (__arg1).
    Params (opcionales):
      - country, platform_code, platform_name
      - price_type[List[str]], definition[List[str]], license_[List[str]], currency[List[str]]
    """
    # ---- tolerancia a __arg1 / posicional ----
    # ---- normalizar llamada ----
    kwargs = _normalize_tool_call(args, kwargs)

    # ---- args ----
    country = kwargs.get("country") or kwargs.get("__arg1")
    platform_code = kwargs.get("platform_code")
    platform_name = kwargs.get("platform_name")
    price_type = kwargs.get("price_type")
    definition = kwargs.get("definition")
    license_ = kwargs.get("license_")
    currency = kwargs.get("currency")

    logger.info(
        "tool_prices_stats called with country=%s, platform_code=%s, platform_name=%s, "
        "price_type=%s, definition=%s, license_=%s, currency=%s",
        country, platform_code, platform_name, price_type, definition, license_, currency
    )

    # ---- normalizaciones ----
    iso = resolve_country_iso(country) if country else None
    plat_name = resolve_platform_name(platform_name) if platform_name else None

    definition = _resolve_definition(definition)
    license_ = _resolve_license(license_)
    # Aceptar str o lista y normalizar currency a upper
    if isinstance(currency, str):
        currency = [currency]
    currency = [c.upper() for c in (currency or [])]

    # Aceptar str o lista para price_type
    if isinstance(price_type, str):
        price_type = [price_type]

    join_pres, scopes, params = "", [], []

    # JOIN presence solo si hace falta (country o platform_name)
    if iso or plat_name:
        join_pres = f"JOIN {PRES_TBL} p ON p.hash_unique = pr.hash_unique"

    if iso:
        scopes.append("LOWER(p.iso_alpha2) = %s")
        params.append(iso.lower())

    if plat_name:
        scopes.append("LOWER(p.platform_name) = %s")
        params.append(plat_name)

    if platform_code:
        scopes.append("LOWER(pr.platform_code) = %s")
        params.append(platform_code.lower())

    if price_type:
        scopes.append(
            f"pr.price_type IN ({', '.join(['%s']*len(price_type))})")
        params.extend(price_type)

    if definition:
        scopes.append(
            f"pr.definition IN ({', '.join(['%s']*len(definition))})")
        params.extend(definition)

    if license_:
        scopes.append(f"pr.license IN ({', '.join(['%s']*len(license_))})")
        params.extend(license_)

    if currency:
        scopes.append(f"pr.currency IN ({', '.join(['%s']*len(currency))})")
        params.extend(currency)

    where_scopes = "WHERE " + " AND ".join(scopes) if scopes else ""

    sql = (
        SQL_PRICE_STATS
        .replace("{JOIN_PRES}", join_pres)
        .replace("{WHERE_SCOPES}", where_scopes)
    )

    rows = db.execute_query(sql, tuple(params))
    return handle_query_result(
        rows,
        "presence_prices.stats",
        (
            f"iso={iso or 'any'} plat_code={platform_code or 'any'} plat_name={plat_name or 'any'} "
            f"ptype={price_type or 'any'} def={definition or 'any'} lic={license_ or 'any'} "
            f"curr={currency or 'any'}"
        ),
    )

# ------------------------------------------------------------
# Allowed columns and validation functions
# ------------------------------------------------------------
PRICES_ALLOWED_SELECT = {
    "id","hash_unique","platform_code","price_type",
    "price","currency","definition","license",
    "out_on","created_at"
}

PRICES_ALLOWED_ORDER = {
    "out_on","created_at","price","currency","platform_code"
}

def _like(v: str) -> str:
    return f"%{(v or '').strip()}%"


def _validate_select(select: Optional[List[str]]) -> List[str]:
    if not select:
        return ["hash_unique","platform_code","price","currency","out_on"]
    safe = [c for c in select if c in PRICES_ALLOWED_SELECT]
    return safe or ["hash_unique","platform_code","price","currency"]

# ------------------------------------------------------------
# Query model
# ------------------------------------------------------------
@dataclass
class PresencePricesQuery:
    hash_unique: Optional[str] = None
    platform_code: Optional[str] = None
    currency: Optional[str] = None
    price_type: Optional[str] = None
    license: Optional[str] = None
    definition: Optional[str] = None

    active_only: bool = True
    today: Optional[date] = None

    select: Optional[List[str]] = None
    order_by: Optional[str] = None
    order_dir: str = "DESC"
    limit: Optional[int] = DEFAULT_LIMIT
    offset: Optional[int] = 0
    count_only: bool = False

# ------------------------------------------------------------
# Builder
# ------------------------------------------------------------
def build_presence_prices_query(q: PresencePricesQuery) -> Tuple[str, Dict[str, Any]]:
    params: Dict[str, Any] = {}
    where: List[str] = []

    # Estado vigente
    if q.active_only:
        today = q.today or date.today()
        params["today"] = today
        where.append("(out_on IS NULL)")

    if q.hash_unique:
        where.append("hash_unique = %(hu)s"); params["hu"] = q.hash_unique
    if q.platform_code:
        where.append("platform_code ILIKE %(pc)s"); params["pc"] = _like(q.platform_code)
    if q.currency:
        where.append("currency ILIKE %(cur)s"); params["cur"] = _like(q.currency)
    if q.price_type:
        where.append("price_type ILIKE %(pt)s"); params["pt"] = _like(q.price_type)
    if q.license:
        where.append("license ILIKE %(lic)s"); params["lic"] = _like(q.license)
    if q.definition:
        where.append("definition ILIKE %(defn)s"); params["defn"] = _like(q.definition)

    where_sql = " WHERE " + " AND ".join(where) if where else ""

    if q.count_only:
        sql = f"SELECT COUNT(*) AS cnt FROM {PRICES_TBL}{where_sql};"
        return sql, params

    select_cols = _validate_select(q.select)
    order_dir = "DESC" if str(q.order_dir).upper() == "DESC" else "ASC"
    limit = validate_limit(q.limit)
    offset = int(q.offset or 0)

    sql = f"""
        SELECT {", ".join(select_cols)}
        FROM {PRICES_TBL}
        {where_sql}
        LIMIT {limit} OFFSET {offset};
    """.strip()

    return sql, params

def query_presence_prices(**kwargs) -> List[Dict[str, Any]]:
    q = PresencePricesQuery(**kwargs)
    sql, params = build_presence_prices_query(q)
    return db.execute_query(sql, params) or []

# ------------------------------------------------------------
# Prices by UID tool
# ------------------------------------------------------------
# Columnas que puede devolver la tool (presencia + precios)
PRICES_BY_UID_ALLOWED_SELECT = {
    # presencia
    "uid","hash_unique","platform_name","platform_code","iso_alpha2",
    # precios
    "price","currency","price_type","definition","license",
    "out_on","created_at",
}

PRICES_BY_UID_DEFAULT_SELECT = [
    "uid","hash_unique","platform_name","platform_code","iso_alpha2",
    "price","currency"
]

def _validate_prices_by_uid_select(select: Optional[List[str]]) -> List[str]:
    if not select:
        return PRICES_BY_UID_DEFAULT_SELECT
    safe = [c for c in select if c in PRICES_BY_UID_ALLOWED_SELECT]
    return safe or PRICES_BY_UID_DEFAULT_SELECT

@dataclass
class PricesByUidQuery:
    uid: str

    # filtros para el paso 1 (presencias)
    active_only_presence: bool = True
    iso_alpha2: Optional[str] = None
    platform_name: Optional[str] = None
    platform_code: Optional[str] = None
    registry_status: Optional[str] = None  # override (si querés algo distinto de 'active')

    # filtros para el paso 2 (precios)
    latest_only: bool = True
    active_only_price: bool = True
    currency: Optional[str] = None
    price_type: Optional[str] = None
    license: Optional[str] = None
    definition: Optional[str] = None

    # salida
    select: Optional[List[str]] = None
    limit: int = MAX_LIMIT
    offset: int = 0
    today: Optional[date] = None

def query_prices_by_uid(
    uid: str,
    *,
    active_only_presence: bool = True,
    iso_alpha2: Optional[str] = None,
    platform_name: Optional[str] = None,
    platform_code: Optional[str] = None,
    registry_status: Optional[str] = None,
    latest_only: bool = True,
    active_only_price: bool = True,
    currency: Optional[str] = None,
    price_type: Optional[str] = None,
    license: Optional[str] = None,
    definition: Optional[str] = None,
    select: Optional[List[str]] = None,
    limit: int = MAX_LIMIT,
    offset: int = 0,
    today: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """
    Paso 1: obtiene hash_unique (y datos de plataforma) desde ms.new_cp_presence por uid.
    Paso 2: usa esos hash_unique para consultar precios en ms.new_cp_presence_prices.
    """
    if not uid:
        return []

    # -------------------- PASO 1: presencias por uid --------------------
    p_params: Dict[str, Any] = {"uid": uid}
    p_where = ["p.uid = %(uid)s"]

    if active_only_presence:
        p_params["today"] = today or date.today()
        p_where += ["(p.out_on IS NULL)"]
    if registry_status:
        p_where.append("p.registry_status ILIKE %(rstat)s"); p_params["rstat"] = _like(registry_status)
    if iso_alpha2:
        iso_alpha2 = resolve_country_iso(iso_alpha2)
        p_where.append("p.iso_alpha2 ILIKE %(iso)s"); p_params["iso"] = _like(iso_alpha2)
    if platform_name:
        platform_name = resolve_platform_name(platform_name)
        p_where.append("p.platform_name ILIKE %(pname)s"); p_params["pname"] = _like(platform_name)
    if platform_code:
        p_where.append("p.platform_code ILIKE %(pcode)s"); p_params["pcode"] = _like(platform_code)

    pres_sql = f"""
        SELECT p.hash_unique, p.platform_name, p.platform_code, p.iso_alpha2, p.uid
        FROM {PRES_TBL} p
        WHERE {" AND ".join(p_where)}
        ORDER BY p.platform_name ASC, p.platform_code ASC
    """.strip()

    pres = db.execute_query(pres_sql, p_params) or []
    if not pres:
        return []

    hashes = [r["hash_unique"] for r in pres if r.get("hash_unique")]
    if not hashes:
        return []

    # Para enriquecer salida sin re-joinear presencia: map local hash -> datos plataforma
    pres_map: Dict[str, Dict[str, Any]] = {
        r["hash_unique"]: {
            "uid": r.get("uid"),
            "platform_name": r.get("platform_name"),
            "platform_code": r.get("platform_code"),
            "iso_alpha2": r.get("iso_alpha2"),
        } for r in pres if r.get("hash_unique")
    }

    # -------------------- PASO 2: precios por hash_unique --------------------
    filters: List[str] = ["pp.hash_unique = ANY(%(hashes)s)"]
    params: Dict[str, Any] = {"hashes": hashes}

    if active_only_price:
        params["todayp"] = today or date.today()
        filters += ["pp.out_on IS NULL"]
    if currency:
        filters.append("pp.currency ILIKE %(cur)s"); params["cur"] = _like(currency)
    if price_type:
        filters.append("pp.price_type ILIKE %(pt)s"); params["pt"] = _like(price_type)
    if license:
        filters.append("pp.license ILIKE %(lic)s"); params["lic"] = _like(license)
    if definition:
        filters.append("pp.definition ILIKE %(defn)s"); params["defn"] = _like(definition)

    cols = _validate_prices_by_uid_select(select)

    # armamos la proyección con las columnas solicitadas
    # (las columnas de presencia se rellenan luego desde pres_map)
    price_cols = []
    for c in cols:
        if c in {"price","currency","price_type","definition","license","out_on","created_at","hash_unique"}:
            price_cols.append(f"pp.{c} AS {c}")
        # uid/platform_name/platform_code/iso_alpha2 se completan del map

    if latest_only:
        # último precio por hash_unique (DISTINCT ON + ORDER)
        sql = f"""
            SELECT DISTINCT ON (pp.hash_unique)
                   pp.hash_unique,
                   {", ".join([pc for pc in price_cols if not pc.startswith("pp.hash_unique")])}
            FROM {PRICES_TBL} pp
            WHERE {" AND ".join(filters)}
        """.strip()
    else:
        # histórico completo
        sql = f"""
            SELECT pp.hash_unique,
                   {", ".join([pc for pc in price_cols if not pc.startswith("pp.hash_unique")])}
            FROM {PRICES_TBL} pp
            WHERE {" AND ".join(filters)}
        """.strip()

    rows = db.execute_query(sql, params) or []

    # Enriquecer con datos de presencia y filtrar columnas finales
    out: List[Dict[str, Any]] = []
    for r in rows:
        hu = r.get("hash_unique")
        base = pres_map.get(hu, {})
        merged = {**base, **r}

        # filtrar por SELECT final respetando orden
        final_row = {}
        for c in cols:
            if c in merged:
                final_row[c] = merged[c]
        out.append(final_row)

    return out