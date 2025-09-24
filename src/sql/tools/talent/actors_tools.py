from langchain_core.tools import Tool
from src.sql.modules.talent.actors import *


# =============================================================================
# Actor analysis tools
# =============================================================================
ACTOR_FILMOGRAPHY_BY_NAME_TOOL = Tool.from_function(
    name="get_actor_filmography_by_name",
    description=(
        "Filmography of an ACTOR (by name). Validates the name; if ambiguous, returns options instead of guessing."
    ),
    func=get_actor_filmography_by_name
)

ACTOR_COACTORS_BY_NAME_TOOL = Tool.from_function(
    name="answer_actor_coactors",
    description=(
        "List of CO-ACTORS who worked with an ACTOR (by name). Validates the name; if ambiguous, returns options."
    ),
    func=get_actor_coactors_by_name
)

ACTOR_FILMOGRAPHY_BY_ID_TOOL = Tool.from_function(
    name="get_actor_filmography",
    description=(
        "Filmography of an ACTOR by ID (efficient path, no hits). Use if you "
        "already resolved the actor_id."
    ),
    func=get_actor_filmography
)

ACTOR_COACTORS_BY_ID_TOOL = Tool.from_function(
    name="get_actor_coactors",
    description=(
        "Co-actors of an ACTOR by ID. Use if you already resolved the "
        "actor_id."
    ),
    func=get_actor_coactors
)



ALL_ACTORS_TOOLS = [
    ACTOR_FILMOGRAPHY_BY_NAME_TOOL,
    ACTOR_COACTORS_BY_NAME_TOOL,
    ACTOR_FILMOGRAPHY_BY_ID_TOOL,
    ACTOR_COACTORS_BY_ID_TOOL,
]