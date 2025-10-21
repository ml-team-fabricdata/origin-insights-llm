from src.strands.content.graph_core.state import State
from src.strands.content.nodes.prompt_content import METADATA_PROMPT
from src.strands.content.nodes.router_configs import (
    METADATA_TOOLS,
    METADATA_ROUTER_PROMPT
)
from src.strands.config.models import MODEL_NODE_EXECUTOR
from src.strands.core.nodes.base_node import BaseExecutorNode
from src.strands.core.factories.router_factory import create_router

from src.strands.content.content_modules.metadata import (
    metadata_simple_all_count,
    metadata_simple_all_list,
    metadata_simple_all_stats,
    metadata_simple_all_query
)


METADATA_TOOLS_MAP = {
    "simple_all_count": metadata_simple_all_count,
    "simple_all_list": metadata_simple_all_list,
    "simple_all_stats": metadata_simple_all_stats,
    "simple_all_query": metadata_simple_all_query
}


_metadata_executor = BaseExecutorNode(
    node_name="metadata",
    tools_map=METADATA_TOOLS_MAP,
    router_fn=create_router(
        prompt=METADATA_ROUTER_PROMPT,
        valid_tools=METADATA_TOOLS
    ),
    system_prompt=METADATA_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def metadata_node(state: State) -> State:
    return await _metadata_executor.execute(state)
