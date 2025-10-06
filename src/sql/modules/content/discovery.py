from src.sql.utils.default_import import *
from src.sql.utils.constants_sql import *
from src.sql.queries.content.queries_discovery import *
from src.sql.utils.sql_db import db
from src.sql.utils.validators_shared import *

def get_filmography_by_uid(uid: str) -> List[Dict[str, Any]]:
    """
    Obtiene la filmografía/ficha para un UID específico.
    Args:
        uid (str): Identificador único del título
       
    Returns:
        Lista con información del título, vacía si no se encuentra o UID inválido
        
    Raises:
        ValueError: Si el UID tiene formato inválido
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

def get_title_rating(uid: str, country: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Obtiene información de rating para un título por UID.

    Args:
        uid: Identificador único del título
        country: Código de país opcional (ISO-2) o región (e.g., 'US', 'LATAM', 'EU') para rating específico

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