# platform/graph_core/supervisor.py
from strands import Agent
from src.strands.platform.prompt_platform import PLATFORM_PROMPT
from src.strands.utils.config import MODEL_CLASSIFIER
from src.strands.utils.supervisor_helpers import (
    main_supervisor,
    create_route_from_supervisor,
    format_response
)
from .state import State
from typing import Literal

async def platform_classifier(state: State) -> State:
    """Clasifica la pregunta UNA SOLA VEZ al inicio del flujo"""
    
    print(f"[CLASSIFIER] Clasificando pregunta: {state['question']}")
    
    if state.get("classification_done"):
        print("[CLASSIFIER] Ya clasificado, saltando...")
        return state
    
    agent = Agent(
        model=MODEL_CLASSIFIER,
        system_prompt=PLATFORM_PROMPT
    )

    # Pasar la pregunta del usuario al agent
    response = await agent.invoke_async(state['question'])
    
    # Extraer mensaje correctamente (puede ser dict u objeto)
    if isinstance(response, dict):
        decision = str(response.get('message', response)).strip().upper()
    else:
        decision = str(getattr(response, "message", response)).strip().upper()
    
    print(f"[CLASSIFIER] Decision: {decision}")
    
    # Validación estricta
    if decision not in ["AVAILABILITY", "PRESENCE"]:
        # Intenta extraer la palabra clave
        if "AVAILABILITY" in decision:
            decision = "AVAILABILITY"
        elif "PRESENCE" in decision:
            decision = "PRESENCE"
        else:
            decision = "PRESENCE"  # Fallback (mayoría de preguntas son presence)
    
    task = decision.lower()
    print(f"[CLASSIFIER] Task final: {task}")
    
    return {
        **state,
        "task": task,
        "classification_done": True
    }


# Crear router específico para platform usando el factory
route_from_main_supervisor = create_route_from_supervisor("platform_node")