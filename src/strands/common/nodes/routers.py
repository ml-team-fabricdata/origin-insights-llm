# content/nodes/routers.py - Routers usando helpers genéricos

from src.strands.common.graph_core.state import State
from src.strands.utils.router_helpers import route_with_llm
from src.strands.utils.config import MODEL_CLASSIFIER
from src.strands.common.nodes.prompt_common import (
    ADMIN_ROUTER_PROMPT,
    VALIDATION_ROUTER_PROMPT
)


# Configuración de tools válidas por categoría

VALIDATION_TOOLS = {
    "validate_title",
    "validate_actor",
    "validate_director"
}

ADMIN_TOOLS = {
    "build_sql",
    "run_sql_adapter",
    "validate_intent"
}


async def route_validation_tool(state: State) -> str:
    """
    Router para herramientas de validation.
    Usa el helper genérico route_with_llm.
    """
    return await route_with_llm(
        state=state,
        model=MODEL_CLASSIFIER,
        prompt=VALIDATION_ROUTER_PROMPT,
        valid_tools=VALIDATION_TOOLS
    )


async def route_admin_tool(state: State) -> str:
    """
    Router para herramientas de admin.
    Usa el helper genérico route_with_llm.
    """
    return await route_with_llm(
        state=state,
        model=MODEL_CLASSIFIER,
        prompt=ADMIN_ROUTER_PROMPT,
        valid_tools=ADMIN_TOOLS
    )
