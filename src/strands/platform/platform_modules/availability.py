from src.strands.infrastructure.database.utils import *
from src.strands.config.default_import import *
from src.strands.platform.platform_queries.queries_availability import *
from src.strands.infrastructure.validators.legacy import *
from strands import tool


@tool
def get_availability_by_uid(uid: str, country: Optional[str] = None, with_prices: bool = False, limit: int = 100) -> List[Dict]:
    """Get platform availability for a title by UID with optional price information.

    NOTE: Country validation is handled by validation_node in the graph.
    This function expects country to already be normalized to ISO-2 or None.

    Parameters: uid (required), country (optional - ISO-2 code or None if already validated),
    with_prices (boolean, default False), limit (int, default 100 - max platforms to return).
    Returns platform availability data including platform names, countries, and optionally pricing information.

    Args:
        uid: Unique identifier for the title
        country: Country ISO-2 code (already validated) or None
        with_prices: Include price information (default False)
        limit: Maximum number of platforms to return (default 100)

    Returns:
        List containing availability data or error message
    """
    uid, country = parse_uid_with_country(uid, country)

    if not uid:
        return [{"message": "UID parameter is required"}]

    # Country is already validated by validation_node
    # Just check if we have a country_list (region expansion)
    country_isos = None
    if country:
        # Assume country is already ISO-2 or a list was provided
        country_isos = [country] if isinstance(country, str) else country

    query_params = {"uid": uid}
    country_condition = ""

    if country_isos:
        if len(country_isos) == 1:
            country_condition = "AND p.iso_alpha2 = %(country_iso)s"
            query_params["country_iso"] = country_isos[0]
        else:
            # Multiple countries (region expansion from validation_node)
            placeholders = ", ".join([f"'{iso}'" for iso in country_isos])
            country_condition = f"AND p.iso_alpha2 IN ({placeholders})"

    if with_prices:
        sql = QUERY_AVAILABILITY_WITH_PRICES.format(
            country_condition=country_condition)
    else:
        sql = QUERY_AVAILABILITY_WITHOUT_PRICES.format(
            country_condition=country_condition)

    result = db.execute_query(sql, query_params)
    country_filter_display = country_isos[0] if country_isos and len(country_isos) == 1 else (
        f"region:{country}" if country_isos and len(country_isos) > 1 else None)
    logger.info(
        f"Availability queried for {uid} (country={country_filter_display}, with_prices={with_prices}), results: {len(result) if result else 0}")

    if not result:
        error_context = {"uid": uid, "message": "No availability found"}
        if country_isos:
            if len(country_isos) == 1:
                error_context["country"] = country_isos[0]
            else:
                error_context["region"] = country
                error_context["countries_searched"] = country_isos
        return [error_context]

    # Limit results if needed
    total_platforms = len(result)
    if limit and len(result) > limit:
        result = result[:limit]

    response_data = {
        "uid": uid,
        "country_filter": country_isos[0] if country_isos and len(country_isos) == 1 else None,
        "region_filter": country if country_isos and len(country_isos) > 1 else None,
        "countries_searched": country_isos if country_isos and len(country_isos) > 1 else None,
        "with_prices": with_prices,
        "total_platforms": total_platforms,
        "results_returned": len(result),
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


@tool
def query_platforms_for_title(uid: str, limit: int = 50) -> List[Dict]:
    """
    Get all platforms carrying a specific title.

    Args:
        uid: Unique identifier for the title
        limit: Maximum number of results

    Returns:
        List of platform information for the title
    """
    logger.info(
        f"query_platforms_for_title called with uid={uid}, limit={limit}")

    if not uid:
        return [{"message": "uid required"}]
    result = db.execute_query(QUERY_PLATFORMS_FOR_TITLE, (uid, limit))

    logger.info(
        f"Platforms queried for {uid}, results: {len(result) if result else 0}")
    return handle_query_result(result, "platforms for title (uid)", uid)


@tool
def query_platforms_for_uid_by_country(uid: str, country: str = None) -> List[Dict]:
    """
    Get platforms for a UID within a specific country or region.

    NOTE: Country validation is handled by validation_node in the graph.
    This function expects country to already be normalized to ISO-2 or None.

    Args:
        uid: Unique identifier for the title
        country: Country ISO-2 code (already validated) or None

    Returns:
        List of platform information filtered by country/region
    """
    logger.info(
        f"query_platforms_for_uid_by_country called with uid={uid}, country={country}")

    if not uid:
        return [{"message": "uid required"}]

    if not country:
        logger.info(
            "No country provided, falling back to generic platforms query")
        return query_platforms_for_title(uid)

    # Country is already validated by validation_node
    # Just handle single vs multiple countries
    country_isos = [country] if isinstance(country, str) else country
    
    if len(country_isos) == 1:
        result = db.execute_query(
            QUERY_PLATFORMS_FOR_UID_BY_COUNTRY, (uid, country_isos[0]))
        return handle_query_result(result, "platforms for title by country", f"{uid} @ {country_isos[0]}")
    else:
        # Multiple countries (region expansion from validation_node)
        placeholders = ", ".join([f"'{iso}'" for iso in country_isos])
        query = QUERY_PLATFORMS_FOR_UID_BY_COUNTRY.replace(
            "p.iso_alpha2 = %s",
            f"p.iso_alpha2 IN ({placeholders})"
        )
        result = db.execute_query(query, (uid,))
        return handle_query_result(result, "platforms for title by region", f"{uid} @ {country}")


@tool
def get_platform_exclusives(platform_name: str, country: str = "US", limit: int = 50) -> List[Dict]:
    """Get exclusive titles available on a specific platform within a country or region.

    NOTE: Platform and country validation handled by validation_node.
    Expects platform_name and country to already be normalized.

    Args:
        platform_name: Platform name (already normalized)
        country: Country ISO-2 code (already validated, defaults to US)
        limit: Maximum number of results

    Returns:
        List of exclusive titles for the platform
    """
    logger.info(
        f"get_platform_exclusives called with platform_name={platform_name}, country={country}, limit={limit}")

    if not platform_name:
        return [{"message": "Platform name required"}]

    # Platform and country already validated by validation_node
    country_isos = [country] if isinstance(country, str) else country
    
    if len(country_isos) == 1:
        result = db.execute_query(
            QUERY_PLATFORM_EXCLUSIVES, (platform_name, country_isos[0], limit))
        return handle_query_result(result, "platform exclusives", f"exclusives {platform_name} @ {country_isos[0]}")
    else:
        # Multiple countries (region expansion from validation_node)
        all_results = []
        for iso in country_isos:
            result = db.execute_query(
                QUERY_PLATFORM_EXCLUSIVES, (platform_name, iso, limit))
            if result:
                all_results.extend(result)
        
        # Remove duplicates by uid and limit
        seen_uids = set()
        unique_results = []
        for r in all_results:
            if r.get('uid') not in seen_uids:
                seen_uids.add(r.get('uid'))
                unique_results.append(r)
                if len(unique_results) >= limit:
                    break
        return handle_query_result(unique_results, "platform exclusives", f"exclusives {platform_name} @ region")


@tool
def compare_platforms_for_title(title_: str) -> List[Dict]:
    """Compare which streaming platforms carry a specific title (exact title match).

    Returns distinct list of platform names and countries where the title is available.
    Useful for finding where to watch a specific movie or series across different platforms and regions.

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


@tool
def get_recent_premieres_by_country(country: str, days_back: int = 7, limit: int = 30) -> List[Dict]:
    """
    Get recent premieres available in a country or region within the last N days.

    Sources: metadata_simple_all (release_date) + new_cp_presence (availability)
    Deduplicates by UID and aggregates platforms.

    Args:
        country: Country ISO-2 code or region name (e.g., 'US', 'LATAM', 'EU')
        days_back: Number of days to look back (fixed at 7)
        limit: Maximum number of results

    Returns:
        List of premiere information with platforms
    """
    if not country:
        return [{"message": "Valid country (ISO-2) or region required."}]

    if days_back != 7:
        return [{"message": "Only 7-day lookback allowed (days_back=7)."}]

    days_back = validate_days_back(days_back, default=7)
    date_from, date_to = get_date_range(days_back)

    logger.debug(f"Date range: {date_from} → {date_to}")

    # Try to resolve as region first
    region_isos = get_region_iso_list(country)
    if region_isos:
        # Handle region with multiple countries
        if len(region_isos) == 1:
            params = {
                "country": region_isos[0],
                "date_from": date_from,
                "date_to": date_to,
                "limit": limit,
            }
            logger.debug(
                f"[recent_premieres] country={region_isos[0]}, days_back={days_back}, range=({date_from},{date_to}), limit={limit}")
            rows = db.execute_query(QUERY_RECENT_PREMIERES_BY_COUNTRY, params)
            return handle_query_result(rows, "recent premieres by country", f"{region_isos[0]} last {days_back}d")
        else:
            # Multiple countries - aggregate results
            all_results = []
            for iso in region_isos:
                params = {
                    "country": iso,
                    "date_from": date_from,
                    "date_to": date_to,
                    "limit": limit,
                }
                rows = db.execute_query(
                    QUERY_RECENT_PREMIERES_BY_COUNTRY, params)
                if rows:
                    all_results.extend(rows)
            # Remove duplicates by uid and limit
            seen_uids = set()
            unique_results = []
            for r in all_results:
                if r.get('uid') not in seen_uids:
                    seen_uids.add(r.get('uid'))
                    unique_results.append(r)
                    if len(unique_results) >= limit:
                        break
            logger.debug(
                f"[recent_premieres] region={country}, days_back={days_back}, range=({date_from},{date_to}), total_results={len(unique_results)}")
            return handle_query_result(unique_results, "recent premieres by region", f"{country} last {days_back}d")

    # Try as individual country
    resolved_country = resolve_country_iso(country)
    if not resolved_country:
        return [{"message": f"Invalid country code or region: {country}"}]

    params = {
        "country": resolved_country,
        "date_from": date_from,
        "date_to": date_to,
        "limit": limit,
    }

    logger.debug(
        f"[recent_premieres] country={resolved_country}, days_back={days_back}, range=({date_from},{date_to}), limit={limit}")
    rows = db.execute_query(QUERY_RECENT_PREMIERES_BY_COUNTRY, params)

    return handle_query_result(rows, "recent premieres by country", f"{resolved_country} last {days_back}d")
