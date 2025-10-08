from src.sql.utils.default_import import *
from src.sql.utils.constants_sql import *
from src.sql.queries.content.queries_discovery import *
from src.sql.utils.sql_db import db
from src.sql.utils.validators_shared import *

@tool
def get_filmography_by_uid(uid: str) -> List[Dict[str, Any]]:
    """Get complete filmography and profile information for a specific title using its UID.
    
    Returns detailed metadata including title, type, year, duration, and countries.
    ONLY use after UID has been confirmed or validated.
    
    Args:
        uid: Unique identifier for the title
       
    Returns:
        List with title information, empty if not found or invalid UID
        
    Raises:
        ValueError: If UID has invalid format
    """
    uid = validate_uid(uid)
    if not uid:
        logger.warning("Invalid or empty UID for filmography query")
        return []
   
    logger.debug(f"Getting filmography for UID: {uid}")
    
    results = db.execute_query(FILMOGRAPHY_SQL, (uid,))
    
    if results is None:
        logger.error(f"Database query failed for filmography UID: {uid}")
        return []
    
    return handle_query_result(results, "filmography", uid)

@tool
def get_title_rating(uid: str, country: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get rating and popularity metrics for a title by UID.
    
    Supports global ratings or country/region-specific ratings (provide ISO-2 country code OR region name like 'LATAM', 'EU').
    Supports regions: LATAM/latin_america, EU, north_america, south_america, europe, asia, africa, oceania.
    Returns total hits, average hits, and hit count from popularity data.

    Args:
        uid: Unique identifier for the title
        country: Optional country code (ISO-2) or region (e.g., 'US', 'LATAM', 'EU') for specific rating

    Returns:
        Lista de diccionarios con información de rating.
        Retorna lista vacía si no se encuentra el título.
        
    Raises:
        ValueError: Si el UID tiene formato inválido
    """
    uid = validate_uid(uid)
    if not uid:
        logger.warning("Invalid or empty UID for rating query")
        return [{"error": "UID required and must be a valid string"}]

    logger.debug(f"Querying rating for UID: {uid}, country: {country or 'global'}")

    if not country:
        results = db.execute_query(RATING_QUERY_GLOBAL, (uid,))
        
        if results is None:
            logger.error(f"Database query failed for global rating UID: {uid}")
            return [{"error": "Database query failed"}]

        logger.info(f"Global rating queried for {uid}, results: {len(results)}")
        return handle_query_result(results, "title rating global", uid)
    
    country = country.strip() if isinstance(country, str) else str(country).strip()
    
    # Try to resolve as region first
    region_isos = get_region_iso_list(country)
    if region_isos:
        # Handle region with multiple countries
        if len(region_isos) == 1:
            results = db.execute_query(RATING_QUERY_COUNTRY, (uid, region_isos[0]))
            if results is None:
                logger.error(f"Database query failed for country rating UID: {uid}, country: {region_isos[0]}")
                return [{"error": "Database query failed"}]
            logger.info(f"Country rating queried for {uid}:{region_isos[0]}, results: {len(results)}")
            return handle_query_result(results, "title rating by country", uid)
        else:
            # Multiple countries - aggregate results
            all_results = []
            for iso in region_isos:
                results = db.execute_query(RATING_QUERY_COUNTRY, (uid, iso))
                if results:
                    # Add country info to each result
                    for r in results:
                        r['queried_country'] = iso
                    all_results.extend(results)
            
            if not all_results:
                logger.info(f"No rating found for {uid} in region {country}")
                return [{"message": f"No rating found for UID {uid} in region {country}"}]
            
            logger.info(f"Region rating queried for {uid}:{country}, results: {len(all_results)}")
            return all_results
    
    # Try as individual country
    resolved_country_iso = resolve_country_iso(country)
    
    if not resolved_country_iso:
        logger.warning(f"Invalid country code or region provided: {country}")
        return [{"error": f"Invalid country code or region: {country}"}]
    
    results = db.execute_query(RATING_QUERY_COUNTRY, (uid, resolved_country_iso))
    
    if results is None:
        logger.error(f"Database query failed for country rating UID: {uid}, country: {resolved_country_iso}")
        return [{"error": "Database query failed"}]

    logger.info(f"Country rating queried for {uid}:{resolved_country_iso}, results: {len(results)}")
    return handle_query_result(results, "title rating by country", uid)

@tool
def get_multiple_titles_info(uids: List[str]) -> List[Dict[str, Any]]:
    """
    Obtiene información básica para múltiples UIDs de una vez.
    
    Args:
        uids: Lista de identificadores únicos
        
    Returns:
        Lista con información de los títulos encontrados
    """
    if not uids or not isinstance(uids, list):
        logger.warning("Invalid or missing UIDs list")
        return []
    
    valid_uids = [validated for uid in uids if (validated := validate_uid(uid))]
    
    if not valid_uids:
        logger.warning("No valid UIDs provided")
        return []
    
    logger.debug(f"Getting info for {len(valid_uids)} UIDs")
    
    in_clause, params = build_in_clause("uid", valid_uids)
    sql = f"""
        SELECT uid, title, type, year, duration, countries_iso
        FROM {META_TBL}
        WHERE {in_clause}
        ORDER BY title
    """
    
    results = db.execute_query(sql, params)
    
    if results is None:
        logger.error("Database query failed for multiple UIDs")
        return []
    
    logger.info(f"Retrieved info for {len(results)} out of {len(valid_uids)} requested UIDs")
    return results