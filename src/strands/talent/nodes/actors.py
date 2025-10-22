from src.strands.talent.graph_core.state import State
from src.strands.talent.nodes.prompt_talent import ACTORS_PROMPT
from src.strands.talent.nodes.router_configs import (
    ACTORS_TOOLS,
    ACTORS_ROUTER_PROMPT
)
from src.strands.config.llm_models import MODEL_NODE_EXECUTOR
from src.strands.core.nodes.base_node import BaseExecutorNode
from src.strands.core.factories.router_factory import create_router

from src.strands.talent.talent_modules.actors import (
    get_actor_filmography,
    get_actor_coactors,
    get_actor_coactors_by_name
)


ACTORS_TOOLS_MAP = {
    "get_actor_filmography": get_actor_filmography,
    "get_actor_coactors": get_actor_coactors,
    "get_actor_coactors_by_name": get_actor_coactors_by_name,
}


_actors_executor = BaseExecutorNode(
    node_name="actors",
    tools_map=ACTORS_TOOLS_MAP,
    router_fn=create_router(
        prompt=ACTORS_ROUTER_PROMPT,
        valid_tools=ACTORS_TOOLS
    ),
    system_prompt=ACTORS_PROMPT,
    model=MODEL_NODE_EXECUTOR,
    entity_key="actor_id"
)


async def actors_node(state: State) -> State:
    return await _actors_executor.execute(state)
