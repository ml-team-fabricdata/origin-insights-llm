from langchain_core.tools import Tool
from src.sql.modules.talent.actors import *


# =============================================================================
# Actor analysis tools
# =============================================================================
ACTOR_FILMOGRAPHY_BY_NAME_TOOL = Tool.from_function(
    name="get_actor_filmography_by_name",
    description=(
        "Obtiene la filmografía completa de un actor buscando por nombre.\n"
    ),
    func=get_actor_filmography_by_name
)

ACTOR_COACTORS_BY_NAME_TOOL = Tool.from_function(
    name="answer_actor_coactors",
    description=(
        "Encuentra actores que han trabajado con un actor específico buscando por nombre.\n"
    ),
    func=get_actor_coactors_by_name
)

ACTOR_FILMOGRAPHY_BY_ID_TOOL = Tool.from_function(
    name="get_actor_filmography",
    description=(
        "Obtiene la filmografía de un actor usando su ID (método eficiente).\n"
    ),
    func=get_actor_filmography
)

ACTOR_COACTORS_BY_ID_TOOL = Tool.from_function(
    name="get_actor_coactors",
    description=(
        "Encuentra co-actores usando el ID del actor (método eficiente).\n"
    ),
    func=get_actor_coactors
)



ALL_ACTORS_TOOLS = [
    ACTOR_FILMOGRAPHY_BY_NAME_TOOL,
    ACTOR_COACTORS_BY_NAME_TOOL,
    ACTOR_FILMOGRAPHY_BY_ID_TOOL,
    ACTOR_COACTORS_BY_ID_TOOL,
]