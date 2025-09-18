from typing import Union
from src.sql_db import db
from src.sql.talent.queries import *
from src.sql.db_utils_sql import *
from src.sql.constants_sql import *
from src.sql.core.validation import *

def find_common_titles_actor_director(
    actor_name: Union[str, List[str], Any], 
    director_name: Union[str, List[str], Any], 
    limit: int = DEFAULT_LIMIT
) -> Dict[str, Any]:
    """
    Encuentra títulos en común entre un actor y un director por nombre - sync version.
   
    Args:
        actor_name: Nombre del actor
        director_name: Nombre del director
        limit: Límite de resultados
       
    Returns:
        Dict con títulos en común o mensaje de error
    """
  

    actor_validation = validate_actor(actor_name)
    if actor_validation.get("status") != "ok":
        query_text = normalize_input(actor_name)
        return {"message": f"No se pudo resolver actor {query_text}. Estado: {actor_validation.get('status')}"}
   
    # Validar director
    director_validation = validate_director(director_name)
    if director_validation.get("status") != "ok":
        query_text = normalize_input(director_name)
        return {"message": f"No se pudo resolver director {query_text}. Estado: {director_validation.get('status')}"}
   
    logger.debug(f"Finding common titles for actor ID {actor_validation['id']} and director ID {director_validation['id']}")
   
    results = db.execute_query(
        COMMON_TITLES_ACTOR_DIRECTOR_SQL,
        (actor_validation["id"], director_validation["id"], limit),
        f"common_titles_actor_{actor_validation['id']}_director_{director_validation['id']}"
    )
    
    ident = f"{actor_validation['name']} × {director_validation['name']}"
    return handle_query_result(results, "actor+director common titles", ident)


def get_common_projects_actor_director_by_name(
    actor_name: Union[str, List[str], Any],
    director_name: Union[str, List[str], Any],
    limit: int = DEFAULT_LIMIT
) -> str:
    """
    Get common projects between actor and director by name with validation - sync version.
    Returns JSON string for consistency with other modules.
    """
    result = find_common_titles_actor_director(actor_name, director_name, limit)
    return json.dumps(result, indent=2, ensure_ascii=False)
