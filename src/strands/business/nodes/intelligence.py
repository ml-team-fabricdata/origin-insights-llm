"""Intelligence node - handles platform intelligence and catalog analysis queries."""

from src.strands.business.graph_core.state import State
from src.strands.business.nodes.prompt_business import INTELLIGENCE_PROMPT
from src.strands.business.nodes.router_configs import (
    INTELLIGENCE_TOOLS,
    INTELLIGENCE_ROUTER_PROMPT
)
from src.strands.config.models import MODEL_NODE_EXECUTOR
from src.strands.core.nodes.base_node import BaseExecutorNode
from src.strands.core.factories.router_factory import create_router

from src.strands.business.business_modules.intelligence import (
    get_platform_exclusivity_by_country,
    catalog_similarity_for_platform,
    titles_in_A_not_in_B_sql
)


INTELLIGENCE_TOOLS_MAP = {
    "get_platform_exclusivity_by_country": get_platform_exclusivity_by_country,
    "catalog_similarity_for_platform": catalog_similarity_for_platform,
    "titles_in_A_not_in_B_sql": titles_in_A_not_in_B_sql,
}

_intelligence_executor = BaseExecutorNode(
    node_name="intelligence",
    tools_map=INTELLIGENCE_TOOLS_MAP,
    router_fn=create_router(
        prompt=INTELLIGENCE_ROUTER_PROMPT,
        valid_tools=INTELLIGENCE_TOOLS
    ),
    system_prompt=INTELLIGENCE_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def intelligence_node(state: State) -> State:
    return await _intelligence_executor.execute(state)
