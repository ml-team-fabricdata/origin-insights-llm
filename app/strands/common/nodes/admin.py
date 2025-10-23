from app.strands.common.graph_core.state import State
from app.strands.common.nodes.prompt_common import ADMIN_PROMPT
from app.strands.common.nodes.router_configs import (
    ADMIN_TOOLS,
    ADMIN_ROUTER_PROMPT
)
from app.strands.config.llm_models import MODEL_NODE_EXECUTOR
from app.strands.core.nodes.base_node import BaseExecutorNode
from app.strands.core.factories.router_factory import create_router

from app.strands.common.common_modules.admin import (
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
