"""Router Configuration Helper

Simplifies router creation using configuration instead of wrapper functions.

Usage:
    router_fn = create_router(
        prompt=PRICING_ROUTER_PROMPT,
        valid_tools=PRICING_TOOLS
    )
"""

from typing import Set, Callable
from functools import partial
from app.strands.core.factories.router_helpers import route_with_llm
from app.strands.config.llm_models import MODEL_CLASSIFIER


def create_router(
    prompt: str,
    valid_tools: Set[str],
    model: str = None
) -> Callable:
    """Create a router function from parameters.
    
    Args:
        prompt: System prompt for the router
        valid_tools: Set of valid tool names
        model: Model to use (defaults to MODEL_CLASSIFIER)
        
    Returns:
        Async function that takes state and returns tool name
    """
    return partial(
        route_with_llm,
        model=model or MODEL_CLASSIFIER,
        prompt=prompt,
        valid_tools=valid_tools
    )
