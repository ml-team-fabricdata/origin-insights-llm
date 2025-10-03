from src.sql.utils.db_utils_sql import *
from src.sql.utils.default_import import *
from src.sql.queries.platform.queries_availability import *
from src.sql.utils.validators_shared import *

def get_availability_by_uid(uid: str, country: Optional[str] = None, with_prices: bool = False) -> List[Dict]:
    """
    Get availability information for a specific UID
    {{ ... }}
    
    Args:
        uid: Unique identifier for the title (required)
        country: Country ISO-2 code or region name (e.g., 'US', 'LATAM', 'EU') (optional)
        with_prices: Include price information (default: False)
        
    Returns:
        List containing availability data or error message
    """
    uid, country = parse_uid_with_country(uid, country)
    
    if not uid:
        return [{"message": "UID parameter is required"}]
    
    country_isos = None
    if country:
        # Try to resolve as region first
        region_isos = get_region_iso_list(country)
        if region_isos:
            country_isos = region_isos
        else:
            # Try to resolve as individual country
            country_iso = resolve_country_iso(country)
            if country_iso:
                country_isos = [country_iso]
            else:
                return [{"message": f"Invalid country code or region: {country}"}]

    query_params = {"uid": uid}
    country_condition = ""

    if country_isos:
        if len(country_isos) == 1:
            country_condition = "AND p.iso_alpha2 = %(country_iso)s"
            query_params["country_iso"] = country_isos[0].lower()
        else:
            # Multiple countries (region) - need to use tuple for psycopg2
            placeholders = ", ".join([f"'{iso.lower()}'" for iso in country_isos])
            country_condition = f"AND p.iso_alpha2 IN ({placeholders})"

    if with_prices:
        sql = QUERY_AVAILABILITY_WITH_PRICES.format(country_condition=country_condition)
    else:
        sql = QUERY_AVAILABILITY_WITHOUT_PRICES.format(country_condition=country_condition)

    result = db.execute_query(sql, query_params)
    country_filter_display = country_isos[0] if country_isos and len(country_isos) == 1 else (f"region:{country}" if country_isos and len(country_isos) > 1 else None)
    logger.info(f"Availability queried for {uid} (country={country_filter_display}, with_prices={with_prices}), results: {len(result) if result else 0}")

    if not result:
        error_context = {"uid": uid, "message": "No availability found"}
        if country_isos:
            if len(country_isos) == 1:
                error_context["country"] = country_isos[0]
            else:
                error_context["region"] = country
                error_context["countries_searched"] = country_isos
        return [error_context]

    response_data = {
        "uid": uid,
        "country_filter": country_isos[0] if country_isos and len(country_isos) == 1 else None,
        "region_filter": country if country_isos and len(country_isos) > 1 else None,
        "countries_searched": country_isos if country_isos and len(country_isos) > 1 else None,
        "with_prices": with_prices,
        "total_platforms": len(result),
        "results": result
    }

    if with_prices:
        prices_found = [r for r in result if r.get('price') is not None]
        response_data.update({
            "platforms_with_prices": len(prices_found),
            "platforms_without_prices": len(result) - len(prices_found)
        })

        if prices_found:
            all_prices = [
                float(r['price']) for r in prices_found 
                if r.get('price') and str(r['price']).replace('.', '').isdigit()
            ]
            if all_prices:
                response_data.update({
                    "price_range": {
                        "min": min(all_prices),
                        "max": max(all_prices),
                        "currencies": list(set(
                            r['currency'] for r in prices_found 
                            if r.get('currency')
                        ))
                    }
                })

    return [response_data]

def query_platforms_for_title(uid: str, limit: int = 50) -> List[Dict]:
    """
    Get all platforms carrying a specific title.

    Args:
        uid: Unique identifier for the title
        limit: Maximum number of results

    Returns:
        List of platform information for the title
    """
    logger.info(f"query_platforms_for_title called with uid={uid}, limit={limit}")

    if not uid:
        return [{"message": "uid required"}]
    result = db.execute_query(QUERY_PLATFORMS_FOR_TITLE, (uid, limit))
    
    logger.info(f"Platforms queried for {uid}, results: {len(result) if result else 0}")
    return handle_query_result(result, "platforms for title (uid)", uid)

def query_platforms_for_uid_by_country(uid: str, country: str = None) -> List[Dict]:
    """
    Get platforms for a UID within a specific country or region.

    Args:
        uid: Unique identifier for the title
        country: Country ISO-2 code or region name (e.g., 'US', 'LATAM', 'EU') (optional)

    Returns:
        List of platform information filtered by country/region
    """
    logger.info(f"query_platforms_for_uid_by_country called with uid={uid}, country={country}")

    if not uid:
        return [{"message": "uid required"}]

    if not country:
        logger.info("No country provided, falling back to generic platforms query")
        return query_platforms_for_title(uid)

    # Try to resolve as region first
    region_isos = get_region_iso_list(country)
    if region_isos:
        # Handle region with multiple countries
        if len(region_isos) == 1:
            result = db.execute_query(QUERY_PLATFORMS_FOR_UID_BY_COUNTRY, (uid, region_isos[0]))
            return handle_query_result(result, "platforms for title by country", f"{uid} @ {region_isos[0]}")
        else:
            # Multiple countries - need different query approach
            placeholders = ", ".join([f"'{iso.lower()}'" for iso in region_isos])
            query = QUERY_PLATFORMS_FOR_UID_BY_COUNTRY.replace(
                "p.iso_alpha2 = %s",
                f"p.iso_alpha2 IN ({placeholders})"
            )
            result = db.execute_query(query, (uid,))
            return handle_query_result(result, "platforms for title by region", f"{uid} @ {country}")
    
    # Try as individual country
    resolved_country = resolve_country_iso(country)
    if not resolved_country:
        return [{"message": f"Invalid country code or region: {country}"}]
    
    result = db.execute_query(QUERY_PLATFORMS_FOR_UID_BY_COUNTRY, (uid, resolved_country))
    
    return handle_query_result(result, "platforms for title by country", f"{uid} @ {resolved_country}")

def get_platform_exclusives(platform_name: str, country: str = "US", limit: int = 30) -> List[Dict]:
    """
    Get titles exclusive to a platform within a country.

    Args:
        platform_name: Name of the platform
        country: Country ISO-2 code
        limit: Maximum number of results

    Returns:
        List of exclusive titles for the platform
    """
    logger.info(f"get_platform_exclusives called with platform_name={platform_name}, country={country}, limit={limit}")

    if not platform_name:
        return [{"message": "Platform name required"}]

    resolved_country = resolve_country_iso(country)
    resolved_platform = resolve_platform_name(platform_name)
    ident = f"exclusives {resolved_platform} @ {resolved_country}"

    result = db.execute_query(QUERY_PLATFORM_EXCLUSIVES, (resolved_platform, resolved_country, limit))
    
    return handle_query_result(result, "platform exclusives", ident)

def compare_platforms_for_title(title_: str) -> List[Dict]:
    """
    Compare which platforms carry a given title (exact match).

    Args:
        title_: Exact title to search for

    Returns:
        List of platforms carrying the title
    """
    logger.info(f"compare_platforms_for_title called with title_={title_}")

    if not title_:
        return [{"message": "Title required"}]

    result = db.execute_query(QUERY_COMPARE_PLATFORM_TITLE, (title_,))
    
    logger.info(f"Platforms queried for {title_}, results: {result}")
    return handle_query_result(result, "compare platforms for title", title_)

def get_recent_premieres_by_country(country: str, days_back: int = 7, limit: int = 30) -> List[Dict]:
    """
    Get recent premieres available in a country within the last N days.

    Sources: metadata_simple_all (release_date) + new_cp_presence (availability)
    Deduplicates by UID and aggregates platforms.

    Args:
        country: Country ISO-2 code
        days_back: Number of days to look back (fixed at 7)
        limit: Maximum number of results

    Returns:
        List of premiere information with platforms
    """
    if not country:
        return [{"message": "Valid country (ISO-2) required."}]

    if days_back != 7:
        return [{"message": "Only 7-day lookback allowed (days_back=7)."}]

    days_back = validate_days_back(days_back, default=7)
    date_from, date_to = get_date_range(days_back)
    resolved_country = resolve_country_iso(country)

    logger.debug(f"Date range: {date_from} → {date_to}")
    logger.debug(f"[recent_premieres] country={resolved_country}, days_back={days_back}, range=({date_from},{date_to}), limit={limit}")

    params = {
        "country": resolved_country,
        "date_from": date_from,
        "date_to": date_to,
        "limit": limit,
    }

    rows = db.execute_query(QUERY_RECENT_PREMIERES_BY_COUNTRY, params)
    ident = f"{resolved_country} last {days_back}d"
    
    return handle_query_result(rows, "recent premieres by country", ident)