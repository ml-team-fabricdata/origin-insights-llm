from langchain_core.tools import Tool
from src.sql.modules.talent.directors import *


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

ALL_DIRECTORS_TOOLS = [
    DIRECTOR_FILMOGRAPHY_BY_NAME_TOOL,
    DIRECTOR_FILMOGRAPHY_BY_ID_TOOL,
    DIRECTOR_CODIRECTORS_BY_ID_TOOL,
]
