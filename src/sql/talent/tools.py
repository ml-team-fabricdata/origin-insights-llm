from langchain_core.tools import Tool
from src.sql.talent.actors import *
from src.sql.talent.directors import *
from src.sql.talent.collaborations import *


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


# =============================================================================
# Director analysis tools
# =============================================================================

DIRECTOR_FILMOGRAPHY_BY_NAME_TOOL = Tool.from_function(
    name="get_director_filmography_by_name",
    description=(
        "Filmography of a DIRECTOR (by name). Validates the name; if ambiguous, returns options."
    ),
    func=get_director_filmography_by_name
)

DIRECTOR_FILMOGRAPHY_BY_ID_TOOL = Tool.from_function(
    name="get_director_filmography",
    description=(
        "Filmography of a DIRECTOR by ID (efficient path, no hits). Use if you already resolved the director_id."
    ),
    func=get_director_filmography
)

DIRECTOR_CODIRECTORS_BY_ID_TOOL = Tool.from_function(
    name="get_director_collaborators",
    description=(
        "Co-directors of a DIRECTOR by ID. Use if you already resolved the "
        "director_id."
    ),
    func=get_director_collaborators
)

# =============================================================================
# COLLABORATIONS
# =============================================================================

COMMON_PROJECTS_BY_IDS_TOOL = Tool.from_function(
    name="get_common_projects_actor_director_by_name",
    description=(
        "Common projects between an ACTOR and DIRECTOR using combined ID format. "
        "Expected input: 'actor_id_director_id' (e.g., '1302077_239033')."
    ),
    func=get_common_projects_actor_director_by_name
)

ALL_TALENT_TOOLS = [
    ACTOR_FILMOGRAPHY_BY_NAME_TOOL,
    ACTOR_COACTORS_BY_NAME_TOOL,
    ACTOR_FILMOGRAPHY_BY_ID_TOOL,
    ACTOR_COACTORS_BY_ID_TOOL,

    DIRECTOR_FILMOGRAPHY_BY_NAME_TOOL,
    DIRECTOR_FILMOGRAPHY_BY_ID_TOOL,
    DIRECTOR_CODIRECTORS_BY_ID_TOOL,

    COMMON_PROJECTS_BY_IDS_TOOL
]