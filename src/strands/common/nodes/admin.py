from src.strands.common.graph_core.state import State
from src.strands.common.nodes.prompt_common import ADMIN_PROMPT
from src.strands.common.nodes.router_configs import (
    ADMIN_TOOLS,
    ADMIN_ROUTER_PROMPT
)
from src.strands.utils.config import MODEL_NODE_EXECUTOR
from src.strands.utils.base_node import BaseExecutorNode
from src.strands.utils.router_config import create_router

from src.strands.common.common_modules.admin import (
    build_sql,
    validate_intent,
    run_sql_adapter
)


ADMIN_TOOLS_MAP = {
    "build_sql": build_sql,
    "validate_intent": validate_intent,
    "run_sql_adapter": run_sql_adapter
}


_admin_executor = BaseExecutorNode(
    node_name="admin",
    tools_map=ADMIN_TOOLS_MAP,
    router_fn=create_router(
        prompt=ADMIN_ROUTER_PROMPT,
        valid_tools=ADMIN_TOOLS
    ),
    system_prompt=ADMIN_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def admin_node(state: State) -> State:
    return await _admin_executor.execute(state)
