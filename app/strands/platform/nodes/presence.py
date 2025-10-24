from app.strands.platform.graph_core.state import State
from app.strands.platform.nodes.prompt_platform import PRESENCE_PROMPT
from app.strands.platform.nodes.router_configs import (
    PRESENCE_TOOLS,
    PRESENCE_ROUTER_PROMPT
)
from app.strands.config.llm_models import MODEL_NODE_EXECUTOR
from app.strands.core.nodes.base_node import BaseExecutorNode
from app.strands.core.factories.router_factory import create_router

from app.strands.platform.platform_modules.presence import (
    presence_count, 
    presence_list, 
    presence_statistics, 
    platform_count_by_country, 
    country_platform_summary
)


PRESENCE_TOOLS_MAP = {
    "presence_count": presence_count,
    "presence_list": presence_list,
    "presence_statistics": presence_statistics,
    "platform_count_by_country": platform_count_by_country,
    "country_platform_summary": country_platform_summary
}


_presence_executor = BaseExecutorNode(
    node_name="presence",
    tools_map=PRESENCE_TOOLS_MAP,
    router_fn=create_router(
        prompt=PRESENCE_ROUTER_PROMPT,
        valid_tools=PRESENCE_TOOLS
    ),
    system_prompt=PRESENCE_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def presence_node(state: State) -> State:
    return await _presence_executor.execute(state)
