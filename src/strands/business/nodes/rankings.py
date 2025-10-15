from src.strands.business.graph_core.state import State
from src.strands.business.nodes.routers import route_rankings_tool
from src.strands.business.nodes.prompt_business import RANKINGS_PROMPT
from src.strands.utils.config import MODEL_NODE_EXECUTOR
from src.strands.utils.base_node import BaseExecutorNode

from src.sql.modules.business.rankings import (
    get_genre_momentum,
    get_top_generic,
    get_top_presence,
    get_top_global,
    get_top_by_uid,
    get_top_generic_tool,
    new_top_by_country_tool
)


RANKINGS_TOOLS_MAP = {
    "get_genre_momentum": get_genre_momentum,
    "get_top_generic": get_top_generic,
    "get_top_presence": get_top_presence,
    "get_top_global": get_top_global,
    "get_top_by_uid": get_top_by_uid,
    "get_top_generic_tool": get_top_generic_tool,
    "new_top_by_country_tool": new_top_by_country_tool
}


_rankings_executor = BaseExecutorNode(
    node_name="rankings",
    tools_map=RANKINGS_TOOLS_MAP,
    router_fn=route_rankings_tool,
    system_prompt=RANKINGS_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def rankings_node(state: State) -> State:
    return await _rankings_executor.execute(state)
