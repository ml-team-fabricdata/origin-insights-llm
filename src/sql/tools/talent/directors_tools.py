from langchain_core.tools import Tool
from src.sql.modules.talent.directors import *


# =============================================================================
# Director analysis tools
# =============================================================================

DIRECTOR_FILMOGRAPHY_BY_NAME_TOOL = Tool.from_function(
    name="get_director_filmography_by_name",
    description=(
        "Get complete filmography for a director by name. Validates the director name and returns their complete list of directed films/series with title, type, year, and IMDb ID. "
        "If the name is ambiguous, returns options to choose from. If name not found, returns error message. Use this when you only have the director's name."
    ),
    func=get_director_filmography_by_name
)

DIRECTOR_FILMOGRAPHY_BY_ID_TOOL = Tool.from_function(
    name="get_director_filmography",
    description=(
        "Get director's filmography using their ID (efficient direct query). "
        "Requires director_id. Returns complete list of films/series the director has directed. "
        "Use this method when you already have the validated director ID from a previous query."
    ),
    func=get_director_filmography
)

DIRECTOR_CODIRECTORS_BY_ID_TOOL = Tool.from_function(
    name="get_director_collaborators",
    description=(
        "Get co-directors (directors who have worked on the same films) using director's ID. "
        "Requires director_id. Returns list of co-directors with their IDs, names, and number of shared titles. "
        "Use this method when you already have the validated director ID from a previous query. Useful for discovering professional collaborations."
    ),
    func=get_director_collaborators
)

ALL_DIRECTORS_TOOLS = [
    DIRECTOR_FILMOGRAPHY_BY_NAME_TOOL,
    DIRECTOR_FILMOGRAPHY_BY_ID_TOOL,
    DIRECTOR_CODIRECTORS_BY_ID_TOOL,
]
