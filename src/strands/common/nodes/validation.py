# src/strands/common/nodes/validation.py
"""Validation node - handles entity validation queries."""

from src.strands.common.graph_core.state import State
from src.strands.common.nodes.routers import route_validation_tool
from src.strands.utils.config import MODEL_NODE_EXECUTOR
from src.strands.common.nodes.prompt_common import VALIDATION_PROMPT
from src.strands.utils.base_node import BaseExecutorNode

from src.sql.modules.common.validation import (
    validate_title,
    validate_actor,
    validate_director
)


VALIDATION_TOOLS_MAP = {
    "validate_title": validate_title,
    "validate_actor": validate_actor,
    "validate_director": validate_director
}


# Configure executor
_validation_executor = BaseExecutorNode(
    node_name="validation",
    tools_map=VALIDATION_TOOLS_MAP,
    router_fn=route_validation_tool,
    system_prompt=VALIDATION_PROMPT,
    model=MODEL_NODE_EXECUTOR
)


async def validation_node(state: State) -> State:
    """
    Execute validation tools dynamically.
    
    Handles:
    - Title validation
    - Actor validation
    - Director validation
    
    Args:
        state: Current state with question and validated entities
        
    Returns:
        Updated state with results
    """
    return await _validation_executor.execute(state)
