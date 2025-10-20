from src.strands.talent.talent_queries.queries_directors import *
from src.strands.utils.db_utils_sql import *
from src.strands.utils.constants_sql import *
from src.strands.utils.default_import import *
from src.strands.common.common_modules.validation import *
from strands import tool

@tool
def get_director_filmography(director_id: str, limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
    """Get director's filmography using their numeric ID (efficient direct query).
    
    IMPORTANT: director_id must be a NUMERIC ID (e.g., 615683), NOT an IMDB ID (e.g., nm0634240).
    
    Single parameter: director_id. Returns default 10 films (most recent).
    Returns list of films/series the director has directed with title, type, year, and IMDb ID.
    Use this method when you already have the validated director ID from a previous query.
    
    Args:
        director_id: Director numeric ID (e.g., "615683")
        limit: Maximum number of films to return (default 10)
    
    Returns:
        Dict with filmography data or error message
    """
    
    # Convert director_id to integer (remove any non-numeric characters)
    try:
        # Extract only numeric characters
        numeric_id = ''.join(filter(str.isdigit, str(director_id)))
        if not numeric_id:
            return {"error": f"Invalid director_id: {director_id}. Must be numeric (e.g., 615683)"}
        director_id_int = int(numeric_id)
    except (ValueError, TypeError) as e:
        return {"error": f"Invalid director_id: {director_id}. Must be numeric. Error: {str(e)}"}
   
    results = db.execute_query(
        FILMOGRAPHY_SQL_DIRECTOR,
        (director_id_int, limit),
        f"director_filmography_{director_id_int}"
    )
    return handle_query_result(results, "director_filmography", director_id_int)

@tool
def get_director_collaborators(director_id: str, limit: int = MAX_LIMIT) -> Dict[str, Any]:
    """Get co-directors (directors who have worked on the same films) using director's numeric ID.
    
    IMPORTANT: director_id must be a NUMERIC ID (e.g., 615683), NOT an IMDB ID (e.g., nm0634240).
    
    Single parameter: director_id. Returns default 20 collaborators (most frequent).
    Returns list of co-directors with their IDs, names, and number of shared titles.
    Use this method when you already have the validated director ID from a previous query. Useful for discovering professional collaborations.
    
    Args:
        director_id: Director numeric ID (e.g., "615683")
        limit: Maximum number of collaborators to return (default 20)
    
    Returns:
        Dict with collaborators data or error message
    """
    
    # Convert director_id to integer (remove any non-numeric characters)
    try:
        # Extract only numeric characters
        numeric_id = ''.join(filter(str.isdigit, str(director_id)))
        if not numeric_id:
            return {"error": f"Invalid director_id: {director_id}. Must be numeric (e.g., 615683)"}
        director_id_int = int(numeric_id)
    except (ValueError, TypeError) as e:
        return {"error": f"Invalid director_id: {director_id}. Must be numeric. Error: {str(e)}"}
   
    results = db.execute_query(
        CODIRECTORS_SQL,
        (director_id_int, director_id_int, limit),
        f"director_collaborators_{director_id_int}"
    )
    return handle_query_result(results, "director_collaborators", director_id_int)
