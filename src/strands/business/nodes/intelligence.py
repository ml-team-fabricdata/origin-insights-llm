# src/strands/business/nodes/intelligence.py
"""Intelligence node - handles platform intelligence and catalog analysis queries."""

from src.strands.business.graph_core.state import State
from src.strands.business.nodes.prompt_business import INTELLIGENCE_PROMPT
from src.strands.business.nodes.routers import route_intelligence_tool
from src.strands.utils.config import MODEL_NODE_EXECUTOR
from src.strands.utils.base_node import BaseExecutorNode

from src.sql.modules.business.intelligence import (
    get_platform_exclusivity_by_country,
    catalog_similarity_for_platform,
    titles_in_A_not_in_B_sql
)


INTELLIGENCE_TOOLS_MAP = {
    "get_platform_exclusivity_by_country": get_platform_exclusivity_by_country,
    "catalog_similarity_for_platform": catalog_similarity_for_platform,
    "titles_in_A_not_in_B_sql": titles_in_A_not_in_B_sql,
}


# Configure executor
_intelligence_executor = BaseExecutorNode(
    node_name="intelligence",
    tools_map=INTELLIGENCE_TOOLS_MAP,
    router_fn=route_intelligence_tool,
    system_prompt=INTELLIGENCE_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def intelligence_node(state: State) -> State:
    """
    Execute intelligence tools dynamically.
    
    Handles:
    - Platform exclusivity analysis
    - Catalog similarity comparisons
    - Title differences between platforms
    
    Args:
        state: Current state with question and validated entities
        
    Returns:
        Updated state with results
    """
    return await _intelligence_executor.execute(state)
