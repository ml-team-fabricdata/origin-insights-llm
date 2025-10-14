# src/strands/content/nodes/discovery.py
"""Discovery node - handles content discovery queries."""

from src.strands.content.graph_core.state import State
from src.strands.content.nodes.routers import route_discovery_tool
from src.strands.utils.config import MODEL_NODE_EXECUTOR
from src.strands.content.nodes.prompt_content import DISCOVERY_PROMPT
from src.strands.utils.base_node import BaseExecutorNode

from src.sql.modules.content.discovery import (
    get_filmography_by_uid, 
    get_title_rating, 
    get_multiple_titles_info
)


DISCOVERY_TOOLS_MAP = {
    "filmography_by_uid": get_filmography_by_uid,
    "title_rating": get_title_rating,
    "multiple_titles_info": get_multiple_titles_info
}


# Configure executor
_discovery_executor = BaseExecutorNode(
    node_name="discovery",
    tools_map=DISCOVERY_TOOLS_MAP,
    router_fn=route_discovery_tool,
    system_prompt=DISCOVERY_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def discovery_node(state: State) -> State:
    """
    Execute content discovery tools dynamically.
    
    Handles:
    - Filmography queries by UID
    - Title rating queries
    - Multiple titles information
    
    Args:
        state: Current state with question and validated entities
        
    Returns:
        Updated state with results
    """
    return await _discovery_executor.execute(state)
