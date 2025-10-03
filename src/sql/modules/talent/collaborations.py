from src.sql.queries.talent.queries_collaborations import *
from src.sql.utils.db_utils_sql import *
from src.sql.utils.constants_sql import *
from src.sql.utils.default_import import *
from src.sql.modules.common.validation import *

def parse_combined_ids(
    combined_input: str,
    separator: str = '_',
    expected_parts: int = 2,
    part_names: Optional[Tuple[str, ...]] = None
) -> Tuple[bool, Dict[str, str]]:
    """
    Parse combined ID or name strings.
    
    Returns:
        Tuple of (success: bool, result: dict with parsed values or error)
    """
    if not combined_input or not isinstance(combined_input, str):
        return False, {"error": "Invalid input: empty or not a string"}
    
    parts = combined_input.split(separator)
    
    if len(parts) != expected_parts:
        for alt_sep in ['_', ', ', ' and ', ' & ', '|']:
            if alt_sep != separator:
                parts = combined_input.split(alt_sep)
                if len(parts) == expected_parts:
                    break
    
    if len(parts) != expected_parts:
        return False, {
            "error": f"Expected {expected_parts} parts separated by '{separator}', got {len(parts)}"
        }
    
    parts = [part.strip() for part in parts]
    
    result = {}
    if part_names:
        for name, value in zip(part_names, parts):
            result[name] = value
    else:
        result = {"parts": parts}
    
    return True, result

def find_common_titles_actor_director(
    actor_name: Union[str, List[str], Any],
    director_name: Union[str, List[str], Any],
    limit: int = DEFAULT_LIMIT
) -> Dict[str, Any]:
    """
    Find common titles between an actor and director by name.
    
    Args:
        actor_name: Actor name or ID
        director_name: Director name or ID  
        limit: Maximum results
        
    Returns:
        Dict with common titles or error message
    """
    actor_input = normalize_input(actor_name)
    director_input = normalize_input(director_name)
    
    actor_validation = validate_actor(actor_input)
    if actor_validation.get("status") != "ok":
        return {
            "error": f"Actor not found: {actor_input}",
            "details": actor_validation
        }
    
    director_validation = validate_director(director_input)
    if director_validation.get("status") != "ok":
        return {
            "error": f"Director not found: {director_input}",
            "details": director_validation
        }
    
    logger.debug(
        f"Finding common titles for actor '{actor_validation['name']}' (ID: {actor_validation['id']}) "
        f"and director '{director_validation['name']}' (ID: {director_validation['id']})"
    )
    
    limit = validate_limit(limit, default=DEFAULT_LIMIT, max_limit=100)
    
    results = db.execute_query(
        COMMON_TITLES_ACTOR_DIRECTOR_SQL,
        (actor_validation["id"], director_validation["id"], limit),
        f"common_titles_actor_{actor_validation['id']}_director_{director_validation['id']}"
    )
    
    if not results:
        return {
            "message": f"No common projects found between {actor_validation['name']} and {director_validation['name']}",
            "actor": {
                "id": actor_validation["id"],
                "name": actor_validation["name"]
            },
            "director": {
                "id": director_validation["id"],
                "name": director_validation["name"]
            },
            "projects": []
        }
    
    return {
        "actor": {
            "id": actor_validation["id"],
            "name": actor_validation["name"]
        },
        "director": {
            "id": director_validation["id"],
            "name": director_validation["name"]
        },
        "count": len(results),
        "projects": results
    }

def get_common_projects_actor_director_by_name(
    actor_director: Optional[str] = None,
    actor_name: Optional[str] = None,
    director_name: Optional[str] = None,
    limit: int = DEFAULT_LIMIT
) -> str:
    """
    Get common projects between actor and director.
    
    This function handles multiple input formats:
    1. Combined string: actor_director="Brad Pitt_David Fincher" 
    2. Combined IDs: actor_director="1302077_239033"
    3. Separate args: actor_name="Brad Pitt", director_name="David Fincher"
    
    Args:
        actor_director: Combined actor and director (name or ID)
        actor_name: Actor name (if using separate args)
        director_name: Director name (if using separate args)
        limit: Maximum results
        
    Returns:
        JSON string with common projects
    """
    if actor_director:
        if '_' in actor_director:
            parts = actor_director.split('_')
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                actor_id = parts[0]
                director_id = parts[1]
                
                limit = validate_limit(limit, default=DEFAULT_LIMIT, max_limit=100)
                
                results = db.execute_query(
                    COMMON_TITLES_ACTOR_DIRECTOR_SQL,
                    (actor_id, director_id, limit),
                    f"common_titles_{actor_id}_{director_id}"
                )
                
                if not results:
                    return json.dumps({
                        "message": "No common projects found",
                        "actor_id": actor_id,
                        "director_id": director_id,
                        "projects": []
                    }, ensure_ascii=False)
                
                return json.dumps({
                    "actor_id": actor_id,
                    "director_id": director_id,
                    "count": len(results),
                    "projects": results
                }, indent=2, ensure_ascii=False)
        
        success, parsed = parse_combined_ids(
            actor_director,
            separator='_',
            expected_parts=2,
            part_names=('actor', 'director')
        )
        
        if not success:
            return json.dumps(parsed, ensure_ascii=False)
        
        actor_name = parsed['actor']
        director_name = parsed['director']

    else:
        return json.dumps({
            "error": "Must provide either 'actor_director' combined string or both 'actor_name' and 'director_name'"
        }, ensure_ascii=False)
    
    result = find_common_titles_actor_director(actor_name, director_name, limit)
    return json.dumps(result, indent=2, ensure_ascii=False)