# talent/nodes/routers.py - Routers usando helpers genéricos

from src.strands.common.graph_core.state import State
from src.strands.utils.router_helpers import route_with_llm
from src.strands.utils.config import MODEL_CLASSIFIER
from src.strands.talent.nodes.prompt_talent import (
    ACTORS_ROUTER_PROMPT,
    DIRECTORS_ROUTER_PROMPT,
    COLLABORATIONS_ROUTER_PROMPT
)


# Configuración de tools válidas por categoría
ACTORS_TOOLS = {
    "get_actor_filmography",
    "get_actor_coactors",
    "get_actor_coactors_by_name"
}

DIRECTORS_TOOLS = {
    "get_director_filmography",
    "get_director_collaborators",
}

COLLABORATIONS_TOOLS = {
    "find_common_titles_actor_director",
    "get_common_projects_actor_director_by_name"
}


async def route_actors_tool(state: State) -> str:
    """
    Router para herramientas de actores.
    Usa el helper genérico route_with_llm.
    """
    return await route_with_llm(
        state=state,
        model=MODEL_CLASSIFIER,
        prompt=ACTORS_ROUTER_PROMPT,
        valid_tools=ACTORS_TOOLS
    )


async def route_directors_tool(state: State) -> str:
    """
    Router para herramientas de directores.
    Usa el helper genérico route_with_llm.
    """
    return await route_with_llm(
        state=state,
        model=MODEL_CLASSIFIER,
        prompt=DIRECTORS_ROUTER_PROMPT,
        valid_tools=DIRECTORS_TOOLS
    )


async def route_collaborations_tool(state: State) -> str:
    """
    Router para herramientas de colaboraciones.
    Usa el helper genérico route_with_llm.
    """
    return await route_with_llm(
        state=state,
        model=MODEL_CLASSIFIER,
        prompt=COLLABORATIONS_ROUTER_PROMPT,
        valid_tools=COLLABORATIONS_TOOLS
    )
