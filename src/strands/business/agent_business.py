
from src.sql.modules.business.pricing import *
from src.sql.modules.business.rankings import *
from src.sql.modules.business.intelligence import *
from src.strands.business.prompt import INTELLIGENCE_PROMPT, PRICING_PROMPT, RANKING_PROMPT


MODEL_TOOL = "us.anthropic.claude-3-5-haiku-20241022-v1:0"

PRICING_AGENT = Agent(
    model=MODEL_TOOL,
    tools=[tool_prices_latest, tool_prices_history,
           tool_prices_changes_last_n_days, tool_prices_stats, tool_hits_with_quality],
    system_prompt= PRICING_PROMPT
)

INTELLIGENCE_AGENT = Agent(
    model=MODEL_TOOL,
    tools=[get_platform_exclusivity_by_country,
           catalog_similarity_for_platform, titles_in_A_not_in_B_sql],
    system_prompt = INTELLIGENCE_PROMPT
)

RANKING_AGENT = Agent(
    model=MODEL_TOOL,
    tools=[get_genre_momentum, get_top_by_uid, new_top_by_country_tool, get_top_generic_tool],
    system_prompt= RANKING_PROMPT
)