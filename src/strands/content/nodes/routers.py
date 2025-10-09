# nodes/routers.py - Routers de herramientas

from strands import Agent
from src.strands.platform.graph_core.state import State
from src.strands.platform.prompts import AVAILABILITY_ROUTER_PROMPT, PRESENCE_ROUTER_PROMPT
from src.strands.platform.config import MODEL_CLASSIFIER


def route_from_platform_classifier(state: State) -> str:
    """Router principal: availability vs presence."""
    task = (state.get("task") or "").lower()
    return "router_availability" if task == "availability" else "router_presence"


async def route_availability_tool(state: State) -> str:
    """
    Router para herramientas de disponibilidad.
    Confía completamente en el LLM con prompt estructurado.
    """
    agent = Agent(
        model=MODEL_CLASSIFIER,
        system_prompt=AVAILABILITY_ROUTER_PROMPT
    )

    result = await agent.invoke_async(state['question'])
    
    # Extraer mensaje correctamente
    if isinstance(result, dict):
        response = result.get('message', str(result))
    else:
        response = getattr(result, "message", str(result))
    
    # Asegurar que es string
    response = str(response).strip().lower()

    valid_tools = {
        "availability_by_uid",
        "platform_exclusives",
        "compare_platforms",
        "recent_premieres"
    }

    if response in valid_tools:
        return response

    return "availability_by_uid"


async def route_presence_tool(state: State) -> str:
    """
    Router para herramientas de presencia.
    Confía completamente en el LLM con prompt estructurado.
    """

    agent = Agent(
        model=MODEL_CLASSIFIER,
        system_prompt=PRESENCE_ROUTER_PROMPT
    )

    result = await agent.invoke_async(state['question'])
    
    # Extraer mensaje correctamente
    if isinstance(result, dict):
        response = result.get('message', str(result))
    else:
        response = getattr(result, "message", str(result))
    
    # Asegurar que es string
    response = str(response).strip().lower()

    valid_tools = {
        "presence_count",
        "presence_list",
        "presence_statistics",
        "platform_count_by_country",
        "country_platform_summary"
    }

    if response in valid_tools:
        return response

    return "presence_count"
