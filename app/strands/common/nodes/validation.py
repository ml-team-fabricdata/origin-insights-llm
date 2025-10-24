from app.strands.common.graph_core.state import State
from app.strands.common.nodes.prompt_common import VALIDATION_PROMPT
from app.strands.common.nodes.router_configs import (
    VALIDATION_TOOLS,
    VALIDATION_ROUTER_PROMPT
)
from app.strands.config.llm_models import MODEL_NODE_EXECUTOR
from app.strands.core.nodes.base_node import BaseExecutorNode
from app.strands.core.factories.router_factory import create_router

from app.strands.common.common_modules.validation import (
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
