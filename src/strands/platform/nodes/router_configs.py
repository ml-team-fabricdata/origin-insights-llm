"""Platform Router Configurations

Tool sets and configurations for platform domain routers.
"""

from src.strands.platform.nodes.prompt_platform import (
    AVAILABILITY_ROUTER_PROMPT,
    PRESENCE_ROUTER_PROMPT
)


AVAILABILITY_TOOLS = {
    "availability_by_uid",
    "platform_exclusives",
    "compare_platforms",
    "recent_premieres",
    "get_platform_exclusives",
    "compare_platforms_for_title",
    "get_recent_premieres_by_country",
    "query_platforms_for_title",
    "query_platforms_for_uid_by_country"
}
PRESENCE_TOOLS = {
    "presence_count",
    "presence_list",
    "presence_statistics",
    "platform_count_by_country",
    "country_platform_summary"
}
