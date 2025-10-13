# content/graph_core/supervisor.py
from strands import Agent
from src.strands.business.nodes.prompt_business import BUSINESS
from src.strands.utils.config import MODEL_CLASSIFIER
from src.strands.utils.supervisor_helpers import (
    main_supervisor,
    create_route_from_supervisor,
    format_response
)
from .state import State
from typing import Literal

async def business_classifier(state: State) -> State:
    """Clasifica la pregunta UNA SOLA VEZ al inicio del flujo"""
    
    print(f"[BUSINESS CLASSIFIER] Clasificando pregunta: {state['question']}")
    
    if state.get("classification_done"):
        print("[CLASSIFIER] Ya clasificado, saltando...")
        return state
    
    agent = Agent(
        model=MODEL_CLASSIFIER,
        system_prompt=BUSINESS
    )

    # Pasar la pregunta del usuario al agent
    response = await agent.invoke_async(state['question'])
    
    # Extraer mensaje correctamente (puede ser dict u objeto)
    if isinstance(response, dict):
        decision = str(response.get('message', response)).strip().upper()
    else:
        decision = str(getattr(response, "message", response)).strip().upper()
    
    print(f"[BUSINESS CLASSIFIER] Decision: {decision}")
    
    # Validación estricta
    if decision not in ["PRICING", "RANKINGS", "INTELLIGENCE"]:
        # Intenta extraer la palabra clave
        if "PRICING" in decision:
            decision = "PRICING"
        elif "RANKINGS" in decision:
            decision = "RANKINGS"
        else:
            decision = "INTELLIGENCE"  # Fallback por defecto
    
    task = decision.lower()
    print(f"[BUSINESS CLASSIFIER] Task final: {task}")
    
    return {
        **state,
        "task": task,
        "classification_done": True
    }


# Crear router específico para business usando el factory
route_from_main_supervisor = create_route_from_supervisor("business_classifier")