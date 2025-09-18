from src.sql.core.queries import *
from src.sql.core.validation import *

async def get_filmography_by_uid(uid: str) -> List[Dict[str, Any]]:
    """
    Obtiene la filmografía/ficha para un UID específico.
   
    Args:
        uid: Identificador único del título
       
    Returns:
        Lista con información del título
    """
    if not uid:
        return []
   
    logger.debug(f"Getting filmography for UID: {uid}")
    results = await db.execute_query(FILMOGRAPHY_SQL, (uid,))
    return handle_query_result(results, "filmography", uid)