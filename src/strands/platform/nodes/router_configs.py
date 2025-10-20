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
    "recent_premieres"
}

PRESENCE_TOOLS = {
    "presence_count",
    "presence_list",
    "presence_statistics",
    "platform_count_by_country",
    "country_platform_summary"
}
