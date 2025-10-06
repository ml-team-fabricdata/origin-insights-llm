from src.sql.queries.talent.queries_actors import *
from src.sql.utils.db_utils_sql import *
from src.sql.utils.constants_sql import *
from src.sql.utils.default_import import *
from src.sql.modules.common.validation import *

def get_actor_filmography(actor_id: str, limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
    """Get an actor's filmography - sync version.
    
    Args:
        actor_id: Actor ID
        limit: Maximum number of films to return (default 10, use 5 for faster response)
    """
    
    results = db.execute_query(
        FILMOGRAPHY_SQL_ACTOR, 
        (actor_id, limit),
        f"actor_filmography_{actor_id}"
    )
    return handle_query_result(results, "actor_filmography", actor_id)

def get_actor_coactors(actor_id: str, limit: int = MAX_LIMIT) -> Dict[str, Any]:
    """Get an actor's co-actors - sync version.
    
    Args:
        actor_id: Actor ID
        limit: Maximum number of co-actors to return (default 20, use 10 for faster response)
    """
    
    results = db.execute_query(
        COACTORS_SQL, 
        (actor_id, actor_id, limit),
        f"actor_coactors_{actor_id}"
    )
    return handle_query_result(results, "actor_coactors", actor_id)

def get_actor_filmography_by_name(
    actor_name: Union[str, List[str], Any], 
    limit: int = DEFAULT_LIMIT
) -> str:
    """Get actor filmography by name with validation - sync version."""
    validation = validate_actor(actor_name)
    
    if validation["status"] == "ok":
        filmography = get_actor_filmography(validation["id"], limit)
        return json.dumps(filmography, indent=2, ensure_ascii=False)
    
    query_text = normalize_input(actor_name)
    
    if validation["status"] == "ambiguous":
        options_text = format_validation_options(validation["options"], "actor")
        return f"Encontré varios posibles para '{query_text}'. Elige uno:\n{options_text}"
    
    return f"No encontré coincidencias para '{query_text}'."

def get_actor_coactors_by_name(
    actor_name: Union[str, List[str], Any], 
    limit: int = DEFAULT_LIMIT
) -> str:
    """Get actor co-actors by name with validation - sync version."""
    validation = validate_actor(actor_name)
    
    if validation["status"] == "ok":
        coactors = get_actor_coactors(validation["id"], limit)
        return json.dumps(coactors, indent=2, ensure_ascii=False)
    
    query_text = normalize_input(actor_name)
    
    if validation["status"] == "ambiguous":
        options_text = format_validation_options(validation["options"], "actor")
        return f"Encontré varios posibles para '{query_text}'. Elige uno:\n{options_text}"
    
    return f"No encontré coincidencias para '{query_text}'."