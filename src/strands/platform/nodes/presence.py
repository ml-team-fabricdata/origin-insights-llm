from src.strands.platform.graph_core.state import State
from src.strands.platform.nodes.routers import route_presence_tool
from src.strands.platform.prompt_platform import PRESENCE_PROMPT
from src.strands.utils.config import MODEL_NODE_EXECUTOR
from src.strands.utils.base_node import BaseExecutorNode

from src.sql.modules.platform.presence import (
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
    router_fn=route_presence_tool,
    system_prompt=PRESENCE_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def presence_node(state: State) -> State:
    return await _presence_executor.execute(state)
