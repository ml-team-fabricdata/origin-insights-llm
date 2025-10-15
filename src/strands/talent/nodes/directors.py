from src.strands.talent.graph_core.state import State
from src.strands.talent.nodes.routers import route_directors_tool
from src.strands.talent.nodes.prompt_talent import DIRECTORS_PROMPT
from src.strands.utils.config import MODEL_NODE_EXECUTOR
from src.strands.utils.base_node import BaseExecutorNode

from src.sql.modules.talent.directors import (
    get_director_collaborators,
    get_director_filmography
)


DIRECTORS_TOOLS_MAP = {
    "get_director_collaborators": get_director_collaborators,
    "get_director_filmography": get_director_filmography,
}


_directors_executor = BaseExecutorNode(
    node_name="directors",
    tools_map=DIRECTORS_TOOLS_MAP,
    router_fn=route_directors_tool,
    system_prompt=DIRECTORS_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def directors_node(state: State) -> State:
    return await _directors_executor.execute(state)
