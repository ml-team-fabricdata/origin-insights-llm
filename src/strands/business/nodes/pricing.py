# src/strands/business/nodes/pricing.py
"""Pricing node - handles pricing and quality queries."""

from src.strands.business.graph_core.state import State
from src.strands.business.nodes.routers import route_pricing_tool
from src.strands.business.nodes.prompt_business import PRICING_PROMPT
from src.strands.utils.config import MODEL_NODE_EXECUTOR
from src.strands.utils.base_node import BaseExecutorNode

from src.sql.modules.business.pricing import (
    query_presence_with_price,
    tool_hits_with_quality,
    tool_prices_latest,
    tool_prices_history,
    tool_prices_changes_last_n_days,
    tool_prices_stats
)


PRICING_TOOLS_MAP = {
    "query_presence_with_price": query_presence_with_price,
    "tool_prices_latest": tool_prices_latest,
    "tool_prices_history": tool_prices_history,
    "tool_prices_changes_last_n_days": tool_prices_changes_last_n_days,
    "tool_prices_stats": tool_prices_stats,
    "tool_hits_with_quality": tool_hits_with_quality
}


# Configure executor
_pricing_executor = BaseExecutorNode(
    node_name="pricing",
    tools_map=PRICING_TOOLS_MAP,
    router_fn=route_pricing_tool,
    system_prompt=PRICING_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def pricing_node(state: State) -> State:
    """
    Execute pricing tools dynamically.
    
    Handles:
    - Presence with price queries
    - Latest prices
    - Price history
    - Price changes
    - Price statistics
    - Quality hits
    
    Args:
        state: Current state with question and validated entities
        
    Returns:
        Updated state with results
    """
    return await _pricing_executor.execute(state)
