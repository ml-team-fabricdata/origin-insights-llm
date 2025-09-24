from langchain_core.tools import Tool
from src.sql.modules.talent.collaborations import *

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

ALL_COLLABORATIONS_TOOLS = [
    COMMON_PROJECTS_BY_IDS_TOOL
]