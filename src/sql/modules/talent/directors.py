from src.sql.queries.talent.queries_directors import *
from src.sql.utils.db_utils_sql import *
from src.sql.utils.constants_sql import *
from src.sql.utils.default_import import *
from src.sql.modules.common.validation import *

@tool
def get_director_filmography(director_id: str, limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
    """Get director's filmography using their ID (efficient direct query).
    
    Single parameter: director_id. Returns default 10 films (most recent).
    Returns list of films/series the director has directed with title, type, year, and IMDb ID.
    Use this method when you already have the validated director ID from a previous query.
    
    Args:
        director_id: Director ID
        limit: Maximum number of films to return (default 10)
    
    Returns:
        Dict with filmography data or error message
    """
   
    results = db.execute_query(
        FILMOGRAPHY_SQL_DIRECTOR,
        (director_id, limit),
        f"director_filmography_{director_id}"
    )
    return handle_query_result(results, "director_filmography", director_id)

@tool
def get_director_collaborators(director_id: str, limit: int = MAX_LIMIT) -> Dict[str, Any]:
    """Get co-directors (directors who have worked on the same films) using director's ID.
    
    Single parameter: director_id. Returns default 20 collaborators (most frequent).
    Returns list of co-directors with their IDs, names, and number of shared titles.
    Use this method when you already have the validated director ID from a previous query. Useful for discovering professional collaborations.
    
    Args:
        director_id: Director ID
        limit: Maximum number of collaborators to return (default 20)
    
    Returns:
        Dict with collaborators data or error message
    """
   
    results = db.execute_query(
        CODIRECTORS_SQL,
        (director_id, director_id, limit),
        f"director_collaborators_{director_id}"
    )
    return handle_query_result(results, "director_collaborators", director_id)

@tool
def get_director_filmography_by_name(
    director_name: Union[str, List[str], Any],
    limit: int = DEFAULT_LIMIT
    ) -> str:
    """Get complete filmography for a director by name.
    
    Validates the director name and returns their complete list of directed films/series with title, type, year, and IMDb ID.
    If the name is ambiguous, returns options to choose from. If name not found, returns error message.
    Use this when you only have the director's name.
    
    Args:
        director_name: Director name to search for
        limit: Maximum number of films to return (default 10)
    
    Returns:
        JSON string with filmography data, options, or error message
    """
    validation = validate_director(director_name)
   
    if validation["status"] == "ok":
        filmography = get_director_filmography(validation["id"], limit)
        return json.dumps(filmography, indent=2, ensure_ascii=False)
   
    query_text = normalize_input(director_name)
   
    if validation["status"] == "ambiguous":
        options_text = format_validation_options(validation["options"], "director")
        return f"Encontré varios posibles para '{query_text}'. Elige uno:\n{options_text}"
   
    return f"No encontré coincidencias para '{query_text}'."