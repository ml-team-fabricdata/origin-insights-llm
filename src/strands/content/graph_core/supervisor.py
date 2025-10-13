# content/graph_core/supervisor.py
from strands import Agent
from src.strands.content.nodes.prompt_content import CONTENT_PROMPT
from src.strands.utils.config import MODEL_CLASSIFIER
from src.strands.utils.supervisor_helpers import (
    main_supervisor,
    create_route_from_supervisor,
    format_response
)
from .state import State
from typing import Literal

async def content_classifier(state: State) -> State:
    """Clasifica la pregunta UNA SOLA VEZ al inicio del flujo"""
    
    print(f"[CONTENT CLASSIFIER] Clasificando pregunta: {state['question']}")
    
    if state.get("classification_done"):
        print("[CLASSIFIER] Ya clasificado, saltando...")
        return state
    
    agent = Agent(
        model=MODEL_CLASSIFIER,
        system_prompt=CONTENT_PROMPT
    )

    # Pasar la pregunta del usuario al agent
    response = await agent.invoke_async(state['question'])
    
    # Extraer mensaje correctamente (puede ser dict u objeto)
    if isinstance(response, dict):
        decision = str(response.get('message', response)).strip().upper()
    else:
        decision = str(getattr(response, "message", response)).strip().upper()
    
    print(f"[CONTENT CLASSIFIER] Decision: {decision}")
    
    # Validación estricta
    if decision not in ["METADATA", "DISCOVERY"]:
        # Intenta extraer la palabra clave
        if "METADATA" in decision:
            decision = "METADATA"
        elif "DISCOVERY" in decision:
            decision = "DISCOVERY"
        else:
            decision = "METADATA"  # Fallback
    
    task = decision.lower()
    print(f"[CLASSIFIER] Task final: {task}")
    
    return {
        **state,
        "task": task,
        "classification_done": True
    }


# Crear router específico para content usando el factory
route_from_main_supervisor = create_route_from_supervisor("content_classifier")