"""Business Intelligence Module

Provides competitive intelligence tools for platform analysis:
- Platform exclusivity analysis by country
- Catalog similarity comparison between countries
- Content availability analysis (A vs B)
"""

from typing import Dict, List, Any, Optional, Tuple
from app.strands.core.shared_imports import *
from app.strands.infrastructure.database.utils import *
from app.strands.infrastructure.database.constants import *
from app.strands.infrastructure.validators.shared import *
from app.strands.infrastructure.cache.query_cache import intelligence_cache
from app.strands.business.business_queries.intelligence_queries import *
from strands import tool


@tool
def get_platform_exclusivity_by_country(
    platform_name: str,
    country: str,
    limit: int = 50,
) -> List[Dict]:
    """Analyze exclusive titles for a platform in a specific country.
    
    Returns titles that are exclusive to the specified platform in the given country,
    useful for market analysis and competitive intelligence.
    
    Args:
        platform_name: Platform name (e.g., 'netflix', 'prime', 'disney+')
        country: Country ISO-2 code (e.g., 'US', 'MX', 'BR')
        limit: Maximum results (default 100, max 1000)
    
    Returns:
        List of dicts with exclusive titles and metadata, or error dict
    """
    if not platform_name or not country:
        return [{"error": "platform_name and country (ISO-2) required."}]

    resolved_platform = resolve_platform_name(platform_name)
    if not resolved_platform:
        return [{"error": f"Invalid platform name: '{platform_name}'. Could not resolve to a valid platform."}]
    
    resolved_country = resolve_country_iso(country)
    if not resolved_country:
        return [{"error": f"Invalid country: '{country}'. Could not resolve to a valid ISO-2 code."}]
    
    limit_norm = validate_limit(limit, default=20, max_limit=50)
    
    cache_key = intelligence_cache.get_cache_key(
        'get_platform_exclusivity_by_country',
        resolved_platform, resolved_country, limit_norm
    )
    
    cached_result = intelligence_cache.get(cache_key)
    if cached_result is not None:
        ident = f"{resolved_platform} @ {resolved_country} limit={limit_norm}"
        logger.info(f"get_platform_exclusivity_by_country → {ident} ⇒ CACHE HIT")
        return cached_result

    sql = (SQL_PLATFORM_EXCLUSIVITY_BY_COUNTRY
           .replace("{PRES_TBL}", PRES_TBL)
           .replace("{META_TBL}", META_TBL))
    
    params = {
        'platform': resolved_platform,
        'country': resolved_country,
        'limit': limit_norm
    }
    rows = db.execute_query(sql, params)
    
    ident = f"{resolved_platform} @ {resolved_country} limit={limit_norm}"
    logger.info(f"get_platform_exclusivity_by_country → {ident} ⇒ {len(rows) if rows else 0} rows")
    
    result = handle_query_result(rows, "platform exclusivity (country)", ident)
    
    intelligence_cache.set(cache_key, result)
    
    return result


@tool
def catalog_similarity_for_platform(
    platform: str,
    iso_a: str,
    iso_b: str
) -> Dict[str, Any]:
    """Calculate catalog similarity between two countries for a platform.
    
    Uses Jaccard similarity index to compare content catalogs.
    Returns totals, shared/unique counts, and similarity percentage (0–100).
    Useful for understanding regional content strategies.
    
    Args:
        platform: Platform name (e.g., 'netflix', 'prime', 'disney+')
        iso_a: First country ISO-2 code (e.g., 'US', 'MX')
        iso_b: Second country ISO-2 code (e.g., 'JP', 'BR')
    
    Returns:
        Dict with keys: platform, country_a, country_b, total_titles_a,
        total_titles_b, shared_titles, similarity_percentage, unique_to_a, unique_to_b
    """
    resolved_platform = resolve_platform_name(platform)
    if not resolved_platform:
        return {"error": f"Invalid platform: '{platform}'. Could not resolve to a valid platform name."}

    resolved_iso_a = resolve_country_iso(iso_a)
    if not resolved_iso_a:
        return {"error": f"Invalid country A: '{iso_a}'. Could not resolve to a valid ISO-2 code."}

    resolved_iso_b = resolve_country_iso(iso_b)
    if not resolved_iso_b:
        return {"error": f"Invalid country B: '{iso_b}'. Could not resolve to a valid ISO-2 code."}
    
    cache_key = intelligence_cache.get_cache_key(
        'catalog_similarity_for_platform',
        resolved_platform, resolved_iso_a, resolved_iso_b
    )
    
    cached_result = intelligence_cache.get(cache_key)
    if cached_result is not None:
        logger.info(f"catalog_similarity_for_platform → {resolved_platform} @ {resolved_iso_a} vs {resolved_iso_b} ⇒ CACHE HIT")
        return cached_result

    sql = SQL_CATALOG_SIMILARITY_FOR_PLATFORM.replace("{PRES_TBL}", PRES_TBL)
    result = db.execute_query(
        sql, (resolved_iso_a, resolved_iso_b, resolved_platform, 
              resolved_iso_a, resolved_iso_b)) or []

    if not result:
        logger.warning(f"catalog_similarity_for_platform → No data for {resolved_platform} @ {resolved_iso_a} vs {resolved_iso_b}")
        return {"error": "No data found for the specified parameters"}

    row = result[0]
    total_a = int(row.get('total_a', 0) or 0)
    total_b = int(row.get('total_b', 0) or 0)
    shared = int(row.get('shared', 0) or 0)
    unique_a = int(row.get('unique_a', 0) or 0)
    unique_b = int(row.get('unique_b', 0) or 0)
    
    total_union = total_a + total_b - shared
    similarity_percentage = (
        shared * 100.0 / total_union) if total_union > 0 else 0.0

    logger.info(f"catalog_similarity_for_platform → {resolved_platform} @ {resolved_iso_a} vs {resolved_iso_b} ⇒ {round(similarity_percentage, 2)}% similarity")
    
    result_dict = {
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
    
    intelligence_cache.set(cache_key, result_dict)
    
    return result_dict

def _build_pin_pout_filters(platform: Optional[str]) -> Tuple[str, List[str], str, List[str]]:
    """Build platform filters for IN/OUT queries.
    
    Args:
        platform: Optional platform name to filter by
        
    Returns:
        Tuple of (in_filter, in_params, out_filter, out_params)
    """
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
    """Find titles available in location A but NOT in location B.
    
    Supports both individual countries (ISO-2 codes: 'US', 'JP', 'MX') and
    regions ('LATAM', 'EU', 'ASIA', 'OCEANIA', 'AFRICA', 'MENA').
    Optional platform filter applies to both locations.
    
    Examples:
        - US vs JP: titles_in_A_not_in_B_sql(country_in='US', country_not_in='JP')
        - LATAM vs EU: titles_in_A_not_in_B_sql(country_in='LATAM', country_not_in='EU')
        - Netflix specific: titles_in_A_not_in_B_sql(country_in='US', country_not_in='MX', platform='netflix')
    
    Args:
        country_in: Country/region where titles ARE available
        country_not_in: Country/region where titles are NOT available
        platform: Optional platform filter (e.g., 'netflix', 'prime', 'disney+')
        limit: Maximum results (default 50, max 200)
    
    Returns:
        List of dicts with title information, or error dict
    """

    isos_in = resolve_region_isos(country_in) or [
        resolve_country_iso(country_in)]
    isos_in = [iso for iso in isos_in if iso]
    
    if not isos_in:
        return [{"error": f"Invalid country/region IN: '{country_in}'. Could not resolve to valid ISO-2 code(s)."}]
    
    isos_out = resolve_region_isos(country_not_in) or [
        resolve_country_iso(country_not_in)]
    isos_out = [iso for iso in isos_out if iso]
    
    if not isos_out:
        return [{"error": f"Invalid country/region NOT IN: '{country_not_in}'. Could not resolve to valid ISO-2 code(s)."}]

    plat = None
    if platform:
        plat = resolve_platform_name(platform)
        if not plat:
            return [{"error": f"Invalid platform: '{platform}'. Could not resolve to a valid platform name."}]
    
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