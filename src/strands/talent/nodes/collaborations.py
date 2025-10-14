# src/strands/talent/nodes/collaborations.py
"""Collaborations node - handles actor-director collaboration queries."""

from src.strands.talent.graph_core.state import State
from src.strands.talent.nodes.routers import route_collaborations_tool
from src.strands.talent.nodes.prompt_talent import COLLABORATIONS_PROMPT
from src.strands.utils.config import MODEL_NODE_EXECUTOR
from src.strands.utils.base_node import BaseExecutorNode

from src.sql.modules.talent.collaborations import (
    find_common_titles_actor_director,
    get_common_projects_actor_director_by_name,
)


COLLABORATIONS_TOOLS_MAP = {
    "find_common_titles_actor_director": find_common_titles_actor_director,
    "get_common_projects_actor_director_by_name": get_common_projects_actor_director_by_name,
}


# Configure executor
_collaborations_executor = BaseExecutorNode(
    node_name="collaborations",
    tools_map=COLLABORATIONS_TOOLS_MAP,
    router_fn=route_collaborations_tool,
    system_prompt=COLLABORATIONS_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def collaborations_node(state: State) -> State:
    """
    Execute actor-director collaboration tools dynamically.
    
    Handles:
    - Finding common titles between actors and directors
    - Getting common projects by name
    
    Args:
        state: Current state with question and validated entities
        
    Returns:
        Updated state with results
    """
    return await _collaborations_executor.execute(state)
