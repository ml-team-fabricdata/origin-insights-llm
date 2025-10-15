from src.strands.talent.graph_core.state import State
from src.strands.talent.nodes.prompt_talent import ACTORS_PROMPT
from src.strands.talent.nodes.routers import route_actors_tool
from src.strands.utils.config import MODEL_NODE_EXECUTOR
from src.strands.utils.base_node import BaseExecutorNode

from src.sql.modules.talent.actors import (
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
    router_fn=route_actors_tool,
    system_prompt=ACTORS_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def actors_node(state: State) -> State:
    return await _actors_executor.execute(state)
