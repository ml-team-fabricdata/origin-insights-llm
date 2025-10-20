from src.strands.content.graph_core.state import State
from src.strands.content.nodes.prompt_content import DISCOVERY_PROMPT
from src.strands.content.nodes.router_configs import (
    DISCOVERY_TOOLS,
    DISCOVERY_ROUTER_PROMPT
)
from src.strands.utils.config import MODEL_NODE_EXECUTOR
from src.strands.utils.base_node import BaseExecutorNode
from src.strands.utils.router_config import create_router

from src.strands.content.content_modules.discovery import (
    get_filmography_by_uid, 
    get_title_rating, 
    get_multiple_titles_info
)


DISCOVERY_TOOLS_MAP = {
    "filmography_by_uid": get_filmography_by_uid,
    "title_rating": get_title_rating,
    "multiple_titles_info": get_multiple_titles_info
}


_discovery_executor = BaseExecutorNode(
    node_name="discovery",
    tools_map=DISCOVERY_TOOLS_MAP,
    router_fn=create_router(
        prompt=DISCOVERY_ROUTER_PROMPT,
        valid_tools=DISCOVERY_TOOLS
    ),
    system_prompt=DISCOVERY_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def discovery_node(state: State) -> State:
    return await _discovery_executor.execute(state)
