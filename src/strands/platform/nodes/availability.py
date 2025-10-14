# src/strands/platform/nodes/availability.py
"""Availability node - handles content availability queries."""

from src.strands.platform.graph_core.state import State
from src.strands.platform.nodes.routers import route_availability_tool
from src.strands.utils.config import MODEL_NODE_EXECUTOR
from src.strands.utils.base_node import BaseExecutorNode

from src.sql.modules.platform.availability import (
    get_availability_by_uid, 
    get_platform_exclusives, 
    compare_platforms_for_title, 
    get_recent_premieres_by_country
)

from src.strands.platform.prompt_platform import AVAILABILITY_PROMPT


AVAILABILITY_TOOLS_MAP = {
    "availability_by_uid": get_availability_by_uid,
    "platform_exclusives": get_platform_exclusives,
    "compare_platforms": compare_platforms_for_title,
    "recent_premieres": get_recent_premieres_by_country
}


# Configure executor
_availability_executor = BaseExecutorNode(
    node_name="availability",
    tools_map=AVAILABILITY_TOOLS_MAP,
    router_fn=route_availability_tool,
    system_prompt=AVAILABILITY_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def availability_node(state: State) -> State:
    """
    Execute availability tools dynamically.
    
    Handles:
    - Availability by UID
    - Platform exclusives
    - Platform comparisons
    - Recent premieres
    
    Args:
        state: Current state with question and validated entities
        
    Returns:
        Updated state with results
    """
    return await _availability_executor.execute(state)
