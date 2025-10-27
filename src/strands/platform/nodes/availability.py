from src.strands.platform.graph_core.state import State
from src.strands.platform.nodes.prompt_platform import AVAILABILITY_PROMPT
from src.strands.platform.nodes.router_configs import (
    AVAILABILITY_TOOLS,
    AVAILABILITY_ROUTER_PROMPT
)
from src.strands.config.llm_models import MODEL_NODE_EXECUTOR
from src.strands.core.nodes.base_node import BaseExecutorNode
from src.strands.core.factories.router_factory import create_router

from src.strands.platform.platform_modules.availability import (
    get_availability_by_uid, 
    get_platform_exclusives, 
    compare_platforms_for_title, 
    get_recent_premieres_by_country,
    query_platforms_for_title,
    query_platforms_for_uid_by_country
)


AVAILABILITY_TOOLS_MAP = {
    "availability_by_uid": get_availability_by_uid,
    "get_platform_exclusives": get_platform_exclusives,
    "compare_platforms_for_title": compare_platforms_for_title,
    "get_recent_premieres_by_country": get_recent_premieres_by_country,
    "query_platforms_for_title": query_platforms_for_title,
    "query_platforms_for_uid_by_country": query_platforms_for_uid_by_country
}


_availability_executor = BaseExecutorNode(
    node_name="availability",
    tools_map=AVAILABILITY_TOOLS_MAP,
    router_fn=create_router(
        prompt=AVAILABILITY_ROUTER_PROMPT,
        valid_tools=AVAILABILITY_TOOLS
    ),
    system_prompt=AVAILABILITY_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def availability_node(state: State) -> State:
    return await _availability_executor.execute(state)
