"""Content Router Configurations

Tool sets and configurations for content domain routers.
"""

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
