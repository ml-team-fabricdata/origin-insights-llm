"""Common Router Configurations

Tool sets and configurations for common/governance domain routers.
"""

from app.strands.common.nodes.prompt_common import (
    ADMIN_ROUTER_PROMPT,
    VALIDATION_ROUTER_PROMPT
)


VALIDATION_TOOLS = {
    "validate_title",
    "validate_actor",
    "validate_director"
}

ADMIN_TOOLS = {
    "build_sql",
    "run_sql_adapter",
    "validate_intent"
}
