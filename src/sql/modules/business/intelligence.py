from src.sql.utils.default_import import *
from src.sql.utils.db_utils_sql import *
from src.sql.utils.constants_sql import *
from src.sql.utils.validators_shared import *
from src.sql.queries.talent.queries_talent import *


# ------------------------------------------------------------------
# Platform exclusivity by country
# ------------------------------------------------------------------

def get_platform_exclusivity_by_country(
    platform_name: str,
    country: str,
    limit: int = 100,
) -> List[Dict]:
    if not platform_name or not country:
        return [{"message": "platform_name and country (ISO-2) required."}]

    resolved_country = resolve_country_iso(country)
    resolved_platform = resolve_platform_name(platform_name)
    limit_norm = validate_limit(limit, default=100, max_limit=1000)

    sql = (SQL_PLATFORM_EXCLUSIVITY_BY_COUNTRY
           .replace("{PRES_TBL}", PRES_TBL)
           .replace("{META_TBL}", META_TBL))
    params = (resolved_country, resolved_platform,
              resolved_platform, limit_norm)
    rows = db.execute_query(sql, params)
    ident = f"{resolved_platform} @ {resolved_country} limit={limit_norm}"
    return handle_query_result(rows, "platform exclusivity (country)", ident)

# ------------------------------------------------------------------
# Catalog similarity (platform, country A vs B)
# ------------------------------------------------------------------


def catalog_similarity_for_platform(
    platform: Any,
    iso_a: Any = None,
    iso_b: Any = None,
    __arg1: Any = None
) -> Dict[str, Any]:
    if not all([platform, iso_a, iso_b]) and __arg1:
        s = str(__arg1).strip()
        parts = [p.strip() for p in s.replace(
            '|', ':').replace(',', ':').split(':') if p.strip()]
        if len(parts) == 3:
            if len(str(platform or "")) == 0:
                platform = parts[0]
                iso_a, iso_b = parts[1], parts[2]
            else:
                iso_a, iso_b = parts[0], parts[1]

    resolved_platform = resolve_platform_name(platform)
    if not resolved_platform:
        return {"error": "Could not resolve platform name"}

    resolved_iso_a = resolve_country_iso(iso_a)
    if not resolved_iso_a:
        return {"error": "Could not resolve first country ISO"}

    resolved_iso_b = resolve_country_iso(iso_b)
    if not resolved_iso_b:
        return {"error": "Could not resolve second country ISO"}

    sql = SQL_CATALOG_SIMILARITY_FOR_PLATFORM.replace("{PRES_TBL}", PRES_TBL)
    result = db.execute_query(
        sql, (resolved_platform, resolved_iso_a, resolved_platform, resolved_iso_b)) or []

    if not result:
        return {"error": "No data found for the specified parameters"}

    row = result[0]
    total_a = int(row.get('total_a', 0) or 0)
    total_b = int(row.get('total_b', 0) or 0)
    shared = int(row.get('shared', 0) or 0)
    unique_a = int(row.get('unique_a', 0) or 0)
    unique_b = int(row.get('unique_b', 0) or 0)
    total_unique = total_a + total_b

    similarity_percentage = (
        shared * 200.0 / total_unique) if total_unique > 0 else 0.0

    return {
        'platform': resolved_platform,
        'country_a': resolved_iso_a,
        'country_b': resolved_iso_b,
        'total_titles_a': total_a,
        'total_titles_b': total_b,
        'shared_titles': shared,
        'similarity_percentage': round(similarity_percentage, 2),
        'unique_to_a': unique_a,
        'unique_to_b': unique_b
    }

# ------------------------------------------------------------------
# Titles in A not in B
# ------------------------------------------------------------------


def _build_pin_pout_filters(platform: Optional[str]) -> Tuple[str, List[str], str, List[str]]:
    pin = ""
    pout = ""
    pin_params: List[str] = []
    pout_params: List[str] = []
    if platform:
        pin = "AND p_in.platform_name = %s"
        pout = "AND p_out.platform_name = %s"
        pin_params.append(platform)
        pout_params.append(platform)
    return pin, pin_params, pout, pout_params


def titles_in_A_not_in_B_sql(
    *,
    country_in: str,
    country_not_in: str,
    platform: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    c_in = resolve_country_iso(country_in)
    c_out = resolve_country_iso(country_not_in)
    plat = resolve_platform_name(platform) if platform else None
    limit_norm = validate_limit(limit, default=50, max_limit=200)

    pin_filter, pin_params, pout_filter, pout_params = _build_pin_pout_filters(
        plat)

    sql = (SQL_TITLES_IN_A_NOT_IN_B
           .replace("{PRES_TBL}", PRES_TBL)
           .replace("{META_TBL}", META_TBL)
           .replace("{PIN_FILTER}", f" {pin_filter} " if pin_filter else "")
           .replace("{POUT_FILTER}", f" {pout_filter} " if pout_filter else ""))

    params: List[Any] = [c_in] + pin_params + \
        [c_out] + pout_params + [limit_norm]
    rows = db.execute_query(sql, tuple(params))
    ident = f"A={c_in} !B={c_out} platform={plat or 'any'} limit={limit_norm}"
    logger.info(
        f"titles_in_A_not_in_B → {ident} ⇒ {len(rows) if rows else 0} rows")
    return handle_query_result(rows, "titles in A not in B", ident)
