from langchain_core.tools import Tool
from src.sql.modules.talent.actors import *


# =============================================================================
# Actor analysis tools
# =============================================================================
ACTOR_FILMOGRAPHY_BY_NAME_TOOL = Tool.from_function(
    name="get_actor_filmography_by_name",
    description=(
        "Get actor's filmography by name. Validates the actor name and returns their films/series from the database with title, type, year, and IMDb ID. "
        "Returns exactly what is in the database - no more, no less. Default limit is 10 films (most recent). "
        "If the name is ambiguous, returns options to choose from. If name not found, returns error message. Use this when you only have the actor's name."
    ),
    func=get_actor_filmography_by_name
)

ACTOR_COACTORS_BY_NAME_TOOL = Tool.from_function(
    name="answer_actor_coactors",
    description=(
        "Find co-actors (actors who have worked with a specific actor) by searching for the actor's name. "
        "Returns list of co-actors with their IDs, names, and number of films worked together. "
        "Validates the actor name first; if ambiguous, returns options. Useful for discovering professional collaborations."
    ),
    func=get_actor_coactors_by_name
)

ACTOR_FILMOGRAPHY_BY_ID_TOOL = Tool.from_function(
    name="get_actor_filmography",
    description=(
        "Get actor's filmography using their ID (efficient direct query). "
        "Single parameter: actor_id (cast_id). Returns default 10 films (most recent). "
        "Returns list of films/series the actor appeared in with title, type, year, and IMDb ID. "
        "Use this method when you already have the validated actor ID from a previous query."
    ),
    func=get_actor_filmography
)

ACTOR_COACTORS_BY_ID_TOOL = Tool.from_function(
    name="get_actor_coactors",
    description=(
        "Get co-actors using the actor's ID (efficient direct query). "
        "Single parameter: actor_id (cast_id). Returns default 20 co-actors (most frequent). "
        "Returns actors who have worked with this actor, showing number of shared films. "
        "Use this method when you already have the validated actor ID from a previous query."
    ),
    func=get_actor_coactors
)

ALL_ACTORS_TOOLS = [
    ACTOR_FILMOGRAPHY_BY_NAME_TOOL,
    ACTOR_COACTORS_BY_NAME_TOOL,
    ACTOR_FILMOGRAPHY_BY_ID_TOOL,
    ACTOR_COACTORS_BY_ID_TOOL,
]