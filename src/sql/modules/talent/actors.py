from src.sql.queries.talent.queries_actors import *
from src.sql.utils.db_utils_sql import *
from src.sql.utils.constants_sql import *
from src.sql.utils.default_import import *
from src.sql.modules.common.validation import *
from strands import tool

@tool
def get_actor_filmography(actor_id: str, limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
    """Get actor's filmography using their ID (efficient direct query).
    
    Single parameter: actor_id (cast_id). Returns default 10 films (most recent).
    Returns list of films/series the actor appeared in with title, type, year, and IMDb ID.
    Use this method when you already have the validated actor ID from a previous query.
    
    Args:
        actor_id: Actor ID (cast_id)
        limit: Maximum number of films to return (default 10)
    
    Returns:
        Dict with filmography data or error message
    """
    
    results = db.execute_query(
        FILMOGRAPHY_SQL_ACTOR, 
        (actor_id, limit),
        f"actor_filmography_{actor_id}"
    )
    return handle_query_result(results, "actor_filmography", actor_id)

@tool
def get_actor_coactors(actor_id: str, limit: int = MAX_LIMIT) -> Dict[str, Any]:
    """Get co-actors using the actor's ID (efficient direct query).
    
    Single parameter: actor_id (cast_id). Returns default 20 co-actors (most frequent).
    Returns actors who have worked with this actor, showing number of shared films.
    Use this method when you already have the validated actor ID from a previous query.
    
    Args:
        actor_id: Actor ID (cast_id)
        limit: Maximum number of co-actors to return (default 20)
    
    Returns:
        Dict with co-actors data or error message
    """
    
    results = db.execute_query(
        COACTORS_SQL, 
        (actor_id, actor_id, limit),
        f"actor_coactors_{actor_id}"
    )
    return handle_query_result(results, "actor_coactors", actor_id)

@tool
def get_actor_filmography_by_name(
    actor_name: Union[str, List[str], Any], 
    limit: int = DEFAULT_LIMIT
    ) -> str:
    """Get actor's filmography by name.
    
    Validates the actor name and returns their films/series from the database with title, type, year, and IMDb ID.
    Returns exactly what is in the database - no more, no less. Default limit is 10 films (most recent).
    If the name is ambiguous, returns options to choose from. If name not found, returns error message.
    Use this when you only have the actor's name.
    
    Args:
        actor_name: Actor name to search for
        limit: Maximum number of films to return (default 10)
    
    Returns:
        JSON string with filmography data, options, or error message
    """
    validation = validate_actor(actor_name)
    
    if validation["status"] == "ok":
        filmography = get_actor_filmography(validation["id"], limit)
        return json.dumps(filmography, indent=2, ensure_ascii=False)
    
    query_text = normalize_input(actor_name)
    
    if validation["status"] == "ambiguous":
        options_text = format_validation_options(validation["options"], "actor")
        return f"Encontré varios posibles para '{query_text}'. Elige uno:\n{options_text}"
    
    return f"No encontré coincidencias para '{query_text}'."

@tool
def get_actor_coactors_by_name(
    actor_name: Union[str, List[str], Any], 
    limit: int = DEFAULT_LIMIT
    ) -> str:
    """Find co-actors (actors who have worked with a specific actor) by searching for the actor's name.
    
    Returns list of co-actors with their IDs, names, and number of films worked together.
    Validates the actor name first; if ambiguous, returns options. Useful for discovering professional collaborations.
    
    Args:
        actor_name: Actor name to search for
        limit: Maximum number of co-actors to return (default 10)
    
    Returns:
        JSON string with co-actors data, options, or error message
    """
    validation = validate_actor(actor_name)
    
    if validation["status"] == "ok":
        coactors = get_actor_coactors(validation["id"], limit)
        return json.dumps(coactors, indent=2, ensure_ascii=False)
    
    query_text = normalize_input(actor_name)
    
    if validation["status"] == "ambiguous":
        options_text = format_validation_options(validation["options"], "actor")
        return f"Encontré varios posibles para '{query_text}'. Elige uno:\n{options_text}"
    
    return f"No encontré coincidencias para '{query_text}'."