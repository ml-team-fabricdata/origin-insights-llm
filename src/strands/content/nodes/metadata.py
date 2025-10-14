# src/strands/content/nodes/metadata.py
"""Metadata node - handles content metadata queries."""

from src.strands.content.graph_core.state import State
from src.strands.content.nodes.routers import route_metadata_tool
from src.strands.utils.config import MODEL_NODE_EXECUTOR
from src.strands.content.nodes.prompt_content import METADATA_PROMPT
from src.strands.utils.base_node import BaseExecutorNode

from src.sql.modules.content.metadata import (
    metadata_simple_all_count, 
    metadata_simple_all_list, 
    metadata_simple_all_stats, 
    metadata_simple_all_query
)


METADATA_TOOLS_MAP = {
    "simple_all_count": metadata_simple_all_count,
    "simple_all_list": metadata_simple_all_list,
    "simple_all_stats": metadata_simple_all_stats,
    "simple_all_query": metadata_simple_all_query
}


# Configure executor
_metadata_executor = BaseExecutorNode(
    node_name="metadata",
    tools_map=METADATA_TOOLS_MAP,
    router_fn=route_metadata_tool,
    system_prompt=METADATA_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def metadata_node(state: State) -> State:
    """
    Execute content metadata tools dynamically.
    
    Handles:
    - Count queries
    - List queries
    - Statistics queries
    - General metadata queries
    
    Args:
        state: Current state with question and validated entities
        
    Returns:
        Updated state with results
    """
    return await _metadata_executor.execute(state)
