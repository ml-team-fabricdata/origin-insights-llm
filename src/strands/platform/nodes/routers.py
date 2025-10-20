# platform/nodes/routers.py - Routers usando helpers genéricos

from src.strands.platform.graph_core.state import State
from src.strands.utils.router_helpers import route_with_llm
from src.strands.utils.config import MODEL_CLASSIFIER
from src.strands.platform.nodes.prompt_platform import AVAILABILITY_ROUTER_PROMPT, PRESENCE_ROUTER_PROMPT


# Configuración de tools válidas
AVAILABILITY_TOOLS = {
    "availability_by_uid",
    "platform_exclusives",
    "compare_platforms",
    "recent_premieres"
}

PRESENCE_TOOLS = {
    "presence_count",
    "presence_list",
    "presence_statistics",
    "platform_count_by_country",
    "country_platform_summary"
}


async def route_availability_tool(state: State) -> str:
    """
    Router para herramientas de disponibilidad.
    Usa el helper genérico route_with_llm.
    """
    return await route_with_llm(
        state=state,
        model=MODEL_CLASSIFIER,
        prompt=AVAILABILITY_ROUTER_PROMPT,
        valid_tools=AVAILABILITY_TOOLS
    )


async def route_presence_tool(state: State) -> str:
    """
    Router para herramientas de presencia.
    Usa el helper genérico route_with_llm.
    """
    return await route_with_llm(
        state=state,
        model=MODEL_CLASSIFIER,
        prompt=PRESENCE_ROUTER_PROMPT,
        valid_tools=PRESENCE_TOOLS
    )
