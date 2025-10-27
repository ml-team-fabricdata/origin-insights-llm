"""Pricing node - handles pricing and quality queries."""

from app.strands.business.graph_core.state import State
from app.strands.business.nodes.prompt_business import PRICING_PROMPT
from app.strands.business.nodes.router_configs import (
    PRICING_TOOLS,
    PRICING_ROUTER_PROMPT
)
from app.strands.config.llm_models import MODEL_NODE_EXECUTOR
from app.strands.core.nodes.base_node import BaseExecutorNode
from app.strands.core.factories.router_factory import create_router

from app.strands.business.business_modules.pricing import (
    query_presence_with_price,
    tool_hits_with_quality,
    tool_prices_latest,
    tool_prices_history,
    tool_prices_history_light,
    tool_prices_changes_last_n_days,
    tool_prices_stats,
    tool_prices_stats_fast
)


PRICING_TOOLS_MAP = {
    "tool_prices_latest": tool_prices_latest,
    "tool_prices_history": tool_prices_history,
    "tool_prices_history_light": tool_prices_history_light,
    "tool_prices_changes_last_n_days": tool_prices_changes_last_n_days,
    "tool_prices_stats": tool_prices_stats,
    "tool_prices_stats_fast": tool_prices_stats_fast,
    "tool_hits_with_quality": tool_hits_with_quality
}

_pricing_executor = BaseExecutorNode(
    node_name="pricing",
    tools_map=PRICING_TOOLS_MAP,
    router_fn=create_router(
        prompt=PRICING_ROUTER_PROMPT,
        valid_tools=PRICING_TOOLS
    ),
    system_prompt=PRICING_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def pricing_node(state: State) -> State:
    return await _pricing_executor.execute(state)
