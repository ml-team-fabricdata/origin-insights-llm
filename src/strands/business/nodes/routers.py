from src.strands.business.graph_core.state import State
from src.strands.core.factories.router_helpers import route_with_llm
from src.strands.config.models import MODEL_CLASSIFIER
from src.strands.business.nodes.prompt_business import (
    INTELLIGENCE_ROUTER_PROMPT,
    PRICING_ROUTER_PROMPT,
    RANKINGS_ROUTER_PROMPT
)

PRICING_TOOLS = {
    "tool_prices_latest",
    "tool_prices_history",
    "tool_prices_changes_last_n_days",
    "tool_prices_stats",
    "query_presence_with_price",
    "build_presence_with_price_query",
    "tool_hits_with_quality"
}

RANKINGS_TOOLS = {
    "get_genre_momentum",
    "get_top_generic",
    "get_top_presence",
    "get_top_global",
    "get_top_by_uid",
    "get_top_generic_tool",
    "new_top_by_country_tool"
}

INTELLIGENCE_TOOLS = {
    "get_platform_exclusivity_by_country",
    "catalog_similarity_for_platform",
    "titles_in_A_not_in_B_sql"
}


async def route_pricing_tool(state: State) -> str:
    return await route_with_llm(
        state=state,
        model=MODEL_CLASSIFIER,
        prompt=PRICING_ROUTER_PROMPT,
        valid_tools=PRICING_TOOLS
    )


async def route_rankings_tool(state: State) -> str:
    return await route_with_llm(
        state=state,
        model=MODEL_CLASSIFIER,
        prompt=RANKINGS_ROUTER_PROMPT,
        valid_tools=RANKINGS_TOOLS
    )


async def route_intelligence_tool(state: State) -> str:
    return await route_with_llm(
        state=state,
        model=MODEL_CLASSIFIER,
        prompt=INTELLIGENCE_ROUTER_PROMPT,
        valid_tools=INTELLIGENCE_TOOLS
    )
