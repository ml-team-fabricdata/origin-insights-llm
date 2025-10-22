from src.strands.common.graph_core.state import State
from src.strands.core.factories.router_helpers import route_with_llm
from src.strands.config.llm_models import MODEL_CLASSIFIER
from src.strands.common.nodes.prompt_common import (
    ADMIN_ROUTER_PROMPT,
    VALIDATION_ROUTER_PROMPT
)


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
    return await route_with_llm(
        state=state,
        model=MODEL_CLASSIFIER,
        prompt=VALIDATION_ROUTER_PROMPT,
        valid_tools=VALIDATION_TOOLS
    )


async def route_admin_tool(state: State) -> str:
    return await route_with_llm(
        state=state,
        model=MODEL_CLASSIFIER,
        prompt=ADMIN_ROUTER_PROMPT,
        valid_tools=ADMIN_TOOLS
    )
