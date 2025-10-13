# content/graph_core/supervisor.py
from strands import Agent
from src.strands.talent.nodes.prompt_talent import TALENT_PROMPT
from src.strands.utils.config import MODEL_CLASSIFIER
from src.strands.utils.supervisor_helpers import (
    main_supervisor,
    create_route_from_supervisor,
    format_response
)
from .state import State
from typing import Literal

async def talent_classifier(state: State) -> State:
    """Clasifica la pregunta UNA SOLA VEZ al inicio del flujo"""
    
    print(f"[TALENT CLASSIFIER] Clasificando pregunta: {state['question']}")
    
    if state.get("classification_done"):
        print("[TALENT CLASSIFIER] Ya clasificado, saltando...")
        return state
    
    agent = Agent(
        model=MODEL_CLASSIFIER,
        system_prompt=TALENT_PROMPT
    )

    # Pasar la pregunta del usuario al agent
    response = await agent.invoke_async(state['question'])
    
    # Extraer mensaje correctamente (puede ser dict u objeto)
    if isinstance(response, dict):
        decision = str(response.get('message', response)).strip().upper()
    else:
        decision = str(getattr(response, "message", response)).strip().upper()
    
    print(f"[TALENT CLASSIFIER] Decision: {decision}")
    
    # Validación estricta
    if decision not in ["ACTORS", "DIRECTORS", "COLLABORATIONS"]:
        # Intenta extraer la palabra clave
        if "ACTORS" in decision:
            decision = "ACTORS"
        elif "DIRECTORS" in decision:
            decision = "DIRECTORS"
        else:
            decision = "COLLABORATIONS"  # Fallback por defecto
    
    task = decision.lower()
    print(f"[TALENT CLASSIFIER] Task final: {task}")
    
    return {
        **state,
        "task": task,
        "classification_done": True
    }


# Crear router específico para talent usando el factory
route_from_main_supervisor = create_route_from_supervisor("talent_classifier")