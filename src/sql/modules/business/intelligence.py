from src.sql.utils.default_import import *
from src.sql.utils.db_utils_sql import *
from src.sql.utils.constants_sql import *
from src.sql.utils.validators_shared import *
from src.sql.queries.business.intelligence_queries import *
from strands import tool


@tool
def get_platform_exclusivity_by_country(
    platform_name: str,
    country: str,
    limit: int = 100,
) -> List[Dict]:
    """Count of exclusive titles for a platform in a given country (ISO-2).
    
    Returns a JSON-serializable list of rows showing titles that are exclusive to the specified platform
    in the given country. Useful for market analysis and competitive intelligence.
    
    Args:
        platform_name: Name of the platform
        country: Country ISO-2 code
        limit: Maximum number of results (default 100, max 1000)
    
    Returns:
        List of exclusive titles with metadata
    """
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


@tool
def catalog_similarity_for_platform(
    platform: Any,
    iso_a: Any = None,
    iso_b: Any = None,
    arg1: Any = None
) -> Dict[str, Any]:
    """Similarity of a platform's catalog between two countries (ISO-2).
    
    Returns totals, shared/unique counts, and similarity_percentage (0–100).
    Compares the content catalog of a platform across two different countries to identify
    overlap and differences. Useful for understanding regional content strategies.
    
    Args:
        platform: Platform name
        iso_a: First country ISO-2 code
        iso_b: Second country ISO-2 code
        arg1: Alternative combined format (optional)
    
    Returns:
        Dict with similarity metrics and counts
    """
    if not all([platform, iso_a, iso_b]) and arg1:
        s = str(arg1).strip()
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

def _build_pin_pout_filters(platform: Optional[str]) -> Tuple[str, List[str], str, List[str]]:
    """Construye filtros de plataforma para queries IN/OUT."""
    if not platform:
        return "", [], "", []
    return (
        "AND p_in.platform_name ILIKE %s", [platform],
        "AND p_out.platform_name ILIKE %s", [platform]
    )

@tool
def titles_in_A_not_in_B_sql(
    *,
    country_in: str,
    country_not_in: str,
    platform: Optional[str] = None,
    limit: int = 50,
) -> List[Dict]:
    """Find titles available on a platform in location A but NOT in location B.
    
    Both parameters accept either individual countries (ISO-2 codes like 'US', 'JP', 'MX')
    or regions ('LATAM', 'EU', 'ASIA', 'OCEANIA', 'AFRICA', 'MENA').
    Optional platform filter (e.g., 'netflix', 'prime', 'disney+') applies to both locations.
    Examples: US vs JP, US vs ASIA, LATAM vs EU, MX vs LATAM.
    Returns up to 'limit' titles (default 50, max 200).
    
    Args:
        country_in: Country/region where titles ARE available
        country_not_in: Country/region where titles are NOT available
        platform: Optional platform filter (applies to both locations)
        limit: Maximum results (default 50, max 200)
    
    Returns:
        List of titles available in A but not in B
    """

    isos_in = resolve_region_isos(country_in) or [
        resolve_country_iso(country_in)]
    isos_out = resolve_region_isos(country_not_in) or [
        resolve_country_iso(country_not_in)]

    isos_in = [iso for iso in isos_in if iso]
    isos_out = [iso for iso in isos_out if iso]

    if not isos_in:
        return [{"error": f"Could not resolve country/region: {country_in}"}]
    if not isos_out:
        return [{"error": f"Could not resolve country/region: {country_not_in}"}]

    plat = resolve_platform_name(platform) if platform else None
    limit_norm = validate_limit(limit, default=50, max_limit=200)

    pin_filter, pin_params, pout_filter, pout_params = _build_pin_pout_filters(
        plat)

    in_condition, _ = build_in_clause("p_in.iso_alpha2", isos_in)
    out_condition, _ = build_in_clause("p_out.iso_alpha2", isos_out)

    sql = (SQL_TITLES_IN_A_NOT_IN_B
           .replace("{in_condition}", in_condition)
           .replace("{out_condition}", out_condition)
           .replace("{pin_filter}", pin_filter if pin_filter else "")
           .replace("{pout_filter}", pout_filter if pout_filter else "")
           .replace("{limit_placeholder}", "%s"))

    params = list(isos_in) + pin_params + list(isos_out) + \
        pout_params + [limit_norm]

    rows = db.execute_query(sql, tuple(params))

    region_in = f"{country_in}({len(isos_in)})" if len(
        isos_in) > 1 else isos_in[0]
    region_out = f"{country_not_in}({len(isos_out)})" if len(
        isos_out) > 1 else isos_out[0]
    ident = f"A={region_in} !B={region_out} platform={plat or 'any'} limit={limit_norm}"
    logger.info(
        f"titles_in_A_not_in_B → {ident} ⇒ {len(rows) if rows else 0} rows")

    return handle_query_result(rows, "titles in A not in B", ident)