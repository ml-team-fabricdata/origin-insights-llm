from sql.queries.talent.queries_talent import *
from src.sql.utils.db_utils_sql import *
from src.sql.utils.constants_sql import *
from src.sql.utils.default_import import *
from src.sql.modules.common.validation import *

def get_director_filmography(director_id: str, limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
    """Get a director's filmography - sync version."""
   
    results = db.execute_query(
        FILMOGRAPHY_SQL_DIRECTOR,
        (director_id, limit),
        f"director_filmography_{director_id}"
    )
    return handle_query_result(results, "director_filmography", director_id)


def get_director_collaborators(director_id: str, limit: int = MAX_LIMIT) -> Dict[str, Any]:
    """Get a director's collaborators (actors they've worked with) - sync version."""
   
    results = db.execute_query(
        CODIRECTORS_SQL,
        (director_id, director_id, limit),
        f"director_collaborators_{director_id}"
    )
    return handle_query_result(results, "director_collaborators", director_id)


def format_director_options(options: List[Dict[str, Any]]) -> str:
    """Format director validation options for display."""
    return "\n".join(
        f"- {opt['name']} (id: {opt['id']}" +
        (f", score: {opt['score']:.2f}" if opt.get("score") else "") + ")"
        for opt in options
    )


def get_query_text(director_name: Union[str, List[str], Any]) -> str:
    """Extract normalized query text from director name input."""
    return normalize_input(director_name)


def get_director_filmography_by_name(
    director_name: Union[str, List[str], Any],
    limit: int = DEFAULT_LIMIT
) -> str:
    """Get director filmography by name with validation - sync version."""
    validation = validate_director(director_name)
   
    if validation["status"] == "ok":
        filmography = get_director_filmography(validation["id"], limit)
        return json.dumps(filmography, indent=2, ensure_ascii=False)
   
    query_text = get_query_text(director_name)
   
    if validation["status"] == "ambiguous":
        options_text = format_director_options(validation["options"])
        return f"Encontré varios posibles para '{query_text}'. Elige uno:\n{options_text}"
   
    return f"No encontré coincidencias para '{query_text}'."
