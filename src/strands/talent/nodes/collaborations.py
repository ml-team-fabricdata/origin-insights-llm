from src.strands.talent.graph_core.state import State
from src.strands.talent.nodes.prompt_talent import COLLABORATIONS_PROMPT
from src.strands.talent.nodes.router_configs import (
    COLLABORATIONS_TOOLS,
    COLLABORATIONS_ROUTER_PROMPT
)
from src.strands.config.models import MODEL_NODE_EXECUTOR
from src.strands.core.nodes.base_node import BaseExecutorNode
from src.strands.core.factories.router_factory import create_router

from src.strands.talent.talent_modules.collaborations import (
    find_common_titles_actor_director,
    get_common_projects_actor_director_by_name,
)


COLLABORATIONS_TOOLS_MAP = {
    "find_common_titles_actor_director": find_common_titles_actor_director,
    "get_common_projects_actor_director_by_name": get_common_projects_actor_director_by_name,
}


_collaborations_executor = BaseExecutorNode(
    node_name="collaborations",
    tools_map=COLLABORATIONS_TOOLS_MAP,
    router_fn=create_router(
        prompt=COLLABORATIONS_ROUTER_PROMPT,
        valid_tools=COLLABORATIONS_TOOLS
    ),
    system_prompt=COLLABORATIONS_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def collaborations_node(state: State) -> State:
    """
    Collaborations node - MUST execute after actor or director validation.
    
    This node requires validated entities (actor and/or director) to function.
    If no validated entities are found, it will return an error.
    """
    # Check if we have validated entities
    validated_entities = state.get("validated_entities") or {}
    # Check for truthy values (not None, not empty string, not False)
    has_actor = bool(validated_entities.get("actor"))
    has_director = bool(validated_entities.get("director"))
    
    # If no validated entities, return error
    if not has_actor and not has_director:
        error_msg = (
            "ERROR: Collaborations node requires validated actor or director entities. "
            "Please validate actor/director first before requesting collaborations."
        )
        print(f"\n[COLLABORATIONS] {error_msg}\n")
        
        return {
            **state,
            "accumulated_data": state.get("accumulated_data", "") + f"\n{error_msg}",
            "supervisor_decision": "VOLVER_MAIN_ROUTER",
            "last_node": "collaborations_node"
        }
    
    # If we have validated entities, proceed normally
    return await _collaborations_executor.execute(state)
