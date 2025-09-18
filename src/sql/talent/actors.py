from typing import Union
from src.sql_db import db
from src.sql.talent.queries import *
from src.sql.db_utils_sql import *
from src.sql.constants_sql import *
from src.sql.core.validation import *

def get_actor_filmography(actor_id: str, limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
    """Get an actor's filmography - sync version."""
    
    results = db.execute_query(
        FILMOGRAPHY_SQL_ACTOR, 
        (actor_id, limit),
        f"actor_filmography_{actor_id}"
    )
    return handle_query_result(results, "actor_filmography", actor_id)


def get_actor_coactors(actor_id: str, limit: int = MAX_LIMIT) -> Dict[str, Any]:
    """Get an actor's co-actors - sync version."""
    
    results = db.execute_query(
        COACTORS_SQL, 
        (actor_id, actor_id, limit),
        f"actor_coactors_{actor_id}"
    )
    return handle_query_result(results, "actor_coactors", actor_id)


def _format_actor_options(options: List[Dict[str, Any]]) -> str:
    """Format actor validation options for display."""
    return "\n".join(
        f"- {opt['name']} (id: {opt['id']}" +
        (f", score: {opt['score']:.2f}" if opt.get("score") else "") + ")"
        for opt in options
    )


def _get_query_text(actor_name: Union[str, List[str], Any]) -> str:
    """Extract normalized query text from actor name input."""
    return normalize_input(actor_name)


def get_actor_filmography_by_name(
    actor_name: Union[str, List[str], Any], 
    limit: int = DEFAULT_LIMIT
) -> str:
    """Get actor filmography by name with validation - sync version."""
    validation = validate_actor(actor_name)
    
    if validation["status"] == "ok":
        filmography = get_actor_filmography(validation["id"], limit)
        return json.dumps(filmography, indent=2, ensure_ascii=False)
    
    query_text = _get_query_text(actor_name)
    
    if validation["status"] == "ambiguous":
        options_text = _format_actor_options(validation["options"])
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
    
    query_text = _get_query_text(actor_name)
    
    if validation["status"] == "ambiguous":
        options_text = _format_actor_options(validation["options"])
        return f"Encontré varios posibles para '{query_text}'. Elige uno:\n{options_text}"
    
    return f"No encontré coincidencias para '{query_text}'."