from langchain_core.tools import Tool
from src.sql.modules.talent.collaborations import *

# =============================================================================
# COLLABORATIONS
# =============================================================================

COMMON_PROJECTS_BY_IDS_TOOL = Tool.from_function(
    name="get_common_projects_actor_director_by_name",
    description=(
        "Find common projects/collaborations between an actor and a director by their names. "
        "Automatically validates both actor and director names. Returns list of films/series where the actor performed and the director directed. "
        "Shows title, type (Movie/Series), and year for each collaboration. Useful for discovering actor-director partnerships and their shared filmography."
    ),
    func=get_common_projects_actor_director_by_name
)

ALL_COLLABORATIONS_TOOLS = [
    COMMON_PROJECTS_BY_IDS_TOOL
]