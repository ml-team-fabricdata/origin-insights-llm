from src.strands.common.graph_core.state import State
from src.strands.common.nodes.prompt_common import VALIDATION_PROMPT
from src.strands.common.nodes.router_configs import (
    VALIDATION_TOOLS,
    VALIDATION_ROUTER_PROMPT
)
from src.strands.config.llm_models import MODEL_NODE_EXECUTOR
from src.strands.core.nodes.base_node import BaseExecutorNode
from src.strands.core.factories.router_factory import create_router

from src.strands.common.common_modules.validation import (
    validate_title,
    validate_actor,
    validate_director
)


VALIDATION_TOOLS_MAP = {
    "validate_title": validate_title,
    "validate_actor": validate_actor,
    "validate_director": validate_director
}


_validation_executor = BaseExecutorNode(
    node_name="validation",
    tools_map=VALIDATION_TOOLS_MAP,
    router_fn=create_router(
        prompt=VALIDATION_ROUTER_PROMPT,
        valid_tools=VALIDATION_TOOLS
    ),
    system_prompt=VALIDATION_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def validation_node(state: State) -> State:
    return await _validation_executor.execute(state)
