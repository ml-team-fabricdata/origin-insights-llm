"""Business Router Configurations

Tool sets and configurations for business domain routers.
"""

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
