from src.strands.content.graph_core.state import State
from src.strands.utils.router_helpers import route_with_llm
from src.strands.utils.config import MODEL_CLASSIFIER
from src.strands.content.nodes.prompt_content import (
    METADATA_ROUTER_PROMPT,
    DISCOVERY_ROUTER_PROMPT
)


METADATA_TOOLS = {
    "simple_all_count",
    "simple_all_list",
    "simple_all_stats",
    "simple_all_query"
}

DISCOVERY_TOOLS = {
    "filmography_by_uid",
    "title_rating",
    "multiple_titles_info"
}


async def route_metadata_tool(state: State) -> str:
    return await route_with_llm(
        state=state,
        model=MODEL_CLASSIFIER,
        prompt=METADATA_ROUTER_PROMPT,
        valid_tools=METADATA_TOOLS
    )


async def route_discovery_tool(state: State) -> str:
    return await route_with_llm(
        state=state,
        model=MODEL_CLASSIFIER,
        prompt=DISCOVERY_ROUTER_PROMPT,
        valid_tools=DISCOVERY_TOOLS
    )
