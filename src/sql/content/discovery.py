from typing import List, Dict, Any, Optional
from src.sql.utils.constants_sql import *
from src.sql.content.queries import *
from src.sql.utils.sql_db import db
from src.sql.utils.db_utils_sql import *
from src.sql.utils.validators_shared import *

def get_filmography_by_uid(uid: str) -> List[Dict[str, Any]]:
    """
    Obtiene la filmografía/ficha para un UID específico.
   
    Args:
        uid: Identificador único del título
       
    Returns:
        Lista con información del título, vacía si no se encuentra o UID inválido
        
    Raises:
        ValueError: Si el UID tiene formato inválido
    """
    # Validación de entrada mejorada
    if not uid or not isinstance(uid, str):
        logger.warning("Invalid or missing UID for filmography query")
        return []
        
    uid = uid.strip()
    if not uid:
        logger.warning("Empty UID provided for filmography query")
        return []
   
    logger.debug(f"Getting filmography for UID: {uid}")
    
    # Manejo de errores de base de datos
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
        country: Código de país opcional (ISO-2) para rating específico por país

    Returns:
        Lista de diccionarios con información de rating.
        Retorna lista vacía si no se encuentra el título.
        
    Raises:
        ValueError: Si el UID tiene formato inválido
    """
    # Validación de entrada consistente con get_filmography_by_uid
    if not uid or not isinstance(uid, str):
        logger.warning("Invalid or missing UID for rating query")
        return [{"error": "UID required and must be a valid string"}]
        
    uid = uid.strip()
    if not uid:
        logger.warning("Empty UID provided for rating query")
        return [{"error": "UID cannot be empty"}]

    logger.debug(f"Querying rating for UID: {uid}, country: {country or 'global'}")

    # Rating global (sin país específico)
    if not country:
        results = db.execute_query(RATING_QUERY_GLOBAL, (uid,))
        
        if results is None:
            logger.error(f"Database query failed for global rating UID: {uid}")
            return [{"error": "Database query failed"}]

        logger.info(f"Global rating queried for {uid}, results: {len(results)}")
        return handle_query_result(results, "title rating global", uid)
    
    # Rating específico por país
    country = country.strip() if isinstance(country, str) else str(country).strip()
    resolved_country_iso = resolve_country_iso(country)
    
    if not resolved_country_iso:
        logger.warning(f"Invalid country code provided: {country}")
        return [{"error": f"Invalid country code: {country}"}]
    
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
    
    # Filtrar UIDs válidos
    valid_uids = [uid.strip() for uid in uids if uid and isinstance(uid, str) and uid.strip()]
    
    if not valid_uids:
        logger.warning("No valid UIDs provided")
        return []
    
    logger.debug(f"Getting info for {len(valid_uids)} UIDs")
    
    # Construir query con placeholders para IN clause
    placeholders = ','.join(['%s'] * len(valid_uids))
    sql = f"""
        SELECT uid, title, type, year, duration, countries_iso
        FROM {META_TBL}
        WHERE uid IN ({placeholders})
        ORDER BY title
    """
    
    results = db.execute_query(sql, valid_uids)
    
    if results is None:
        logger.error("Database query failed for multiple UIDs")
        return []
    
    logger.info(f"Retrieved info for {len(results)} out of {len(valid_uids)} requested UIDs")
    return results