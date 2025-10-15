from src.strands.platform.graph_core.state import State
from src.strands.platform.nodes.routers import route_availability_tool
from src.strands.platform.prompt_platform import AVAILABILITY_PROMPT
from src.strands.utils.config import MODEL_NODE_EXECUTOR
from src.strands.utils.base_node import BaseExecutorNode

from src.sql.modules.platform.availability import (
    get_availability_by_uid, 
    get_platform_exclusives, 
    compare_platforms_for_title, 
    get_recent_premieres_by_country
)


AVAILABILITY_TOOLS_MAP = {
    "availability_by_uid": get_availability_by_uid,
    "platform_exclusives": get_platform_exclusives,
    "compare_platforms": compare_platforms_for_title,
    "recent_premieres": get_recent_premieres_by_country
}


_availability_executor = BaseExecutorNode(
    node_name="availability",
    tools_map=AVAILABILITY_TOOLS_MAP,
    router_fn=route_availability_tool,
    system_prompt=AVAILABILITY_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def availability_node(state: State) -> State:
    return await _availability_executor.execute(state)
