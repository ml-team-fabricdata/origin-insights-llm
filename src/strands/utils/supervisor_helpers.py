# utils/supervisor_helpers.py - Funciones compartidas de supervisión

from strands import Agent
from src.prompt import RESPONSE_PROMPT, get_supervisor_prompt
from src.strands.utils.config import MODEL_SUPERVISOR, MODEL_FORMATTER
from typing import Literal, TypedDict, Any


async def main_supervisor(state: TypedDict) -> TypedDict:
    """
    Decide si continuar buscando datos, finalizar, o volver al main router.
    
    Esta función es GENÉRICA y funciona para cualquier grafo que siga
    el patrón de supervisión con loop.
    
    Decisiones posibles:
    - NECESITA_CLASIFICACION: Continuar en el grafo actual
    - COMPLETO: Finalizar y formatear respuesta
    - VOLVER_MAIN_ROUTER: Volver al main router para reclasificar
    """
    
    print(f"[SUPERVISOR] Evaluando estado... tools={state.get('tool_calls_count', 0)}, task={state.get('task')}")
    
    tool_calls = state.get('tool_calls_count', 0)
    max_iter = state.get('max_iterations', 3)
    
    # Caso 1: Primera iteración - necesita clasificación
    if tool_calls == 0:
        print("[SUPERVISOR] Primera iteracion, necesita clasificacion")
        return {
            **state,
            "supervisor_decision": "NECESITA_CLASIFICACION"
        }
    
    # Caso 2: Alcanzó máximo de iteraciones - VOLVER AL MAIN ROUTER
    if tool_calls >= max_iter:
        print(f"[SUPERVISOR] Maximo de iteraciones alcanzado ({tool_calls}/{max_iter})")
        print("[SUPERVISOR] ⚠️ No se completó, volviendo al main router")
        return {
            **state,
            "supervisor_decision": "VOLVER_MAIN_ROUTER"
        }
    
    # Caso 3: Evaluar si los datos son suficientes
    accumulated = state.get('accumulated_data', '')
    
    # Si no hay datos acumulados, volver al main router
    if not accumulated or len(accumulated.strip()) < 50:
        print("[SUPERVISOR] No hay datos suficientes, volviendo al main router")
        return {
            **state,
            "supervisor_decision": "VOLVER_MAIN_ROUTER"
        }
    
    # Evaluar con LLM si los datos son suficientes
    supervisor_prompt = get_supervisor_prompt(
        question=state['question'],
        tool_calls=tool_calls,
        max_iter=max_iter,
        accumulated=accumulated
    )
    
    supervisor_agent = Agent(
        model=MODEL_SUPERVISOR,
        system_prompt=supervisor_prompt
    )
    
    response = await supervisor_agent.invoke_async("¿Los datos responden la pregunta?")
    
    # Extraer mensaje correctamente (puede ser dict u objeto)
    if isinstance(response, dict):
        decision = str(response.get('message', response)).strip().upper()
    else:
        decision = str(getattr(response, "message", response)).strip().upper()
    
    print(f"[SUPERVISOR] Decision del LLM: {decision}")
    
    if "COMPLETO" in decision or "COMPLETE" in decision:
        print("[SUPERVISOR] ✓ Pregunta respondida, ir a format")
        supervisor_decision = "COMPLETO"
    else:
        print("[SUPERVISOR] ✗ Necesita mas informacion, volviendo al main router")
        supervisor_decision = "VOLVER_MAIN_ROUTER"
    
    return {
        **state,
        "supervisor_decision": supervisor_decision
    }


def create_route_from_supervisor(classifier_node_name: str):
    """
    Factory que crea una función de routing personalizada.
    
    Args:
        classifier_node_name: Nombre del nodo classifier ("platform_node", "content_node", etc.)
        
    Returns:
        Función de routing
        
    Example:
        >>> route_from_main_supervisor = create_route_from_supervisor("platform_node")
    """
    def route_from_main_supervisor(state: TypedDict) -> Literal[str, str, str]:
        """Enruta basado en la decisión del supervisor"""
        
        decision = state.get("supervisor_decision", "COMPLETO").upper()
        tool_calls = state.get("tool_calls_count", 0)
        max_iter = state.get("max_iterations", 1)
        
        # Si está completo, formatear respuesta
        if decision == "COMPLETO":
            return "format_response"
        
        # Si necesita volver al main router
        if "VOLVER_MAIN_ROUTER" in decision:
            return "return_to_main_router"
        
        # Si necesita clasificación, ir al classifier_node
        if "CLASIFICACION" in decision:
            return classifier_node_name
        
        # Fallback: volver al main router
        return "return_to_main_router"
    
    # Actualizar metadata para debugging
    route_from_main_supervisor.__name__ = f"route_from_main_supervisor_to_{classifier_node_name}"
    
    return route_from_main_supervisor


async def format_response(state: TypedDict) -> TypedDict:
    """
    Formatea la respuesta final al usuario.
    
    Esta función es GENÉRICA y funciona para cualquier grafo.
    """
    
    formatter = Agent(
        model=MODEL_FORMATTER,
        tools=[],
        system_prompt=RESPONSE_PROMPT
    )
    
    accumulated = state.get('accumulated_data', state.get('answer', ''))
    
    # Si no hay datos, indicarlo en la respuesta
    if not accumulated or len(accumulated.strip()) < 20:
        return {
            "question": state["question"],
            "answer": "Lo siento, no pude obtener información suficiente para responder tu pregunta.",
            "task": state.get("task"),
            "tool_calls_count": state.get("tool_calls_count", 0),
            "status": "insufficient_data"
        }
    
    payload = f"""Question: {state['question']}

        Raw data:
        {accumulated}

        Format a clear, concise response for the user."""
    
    out = await formatter.invoke_async(payload)
    
    # Extraer mensaje correctamente (puede ser dict u objeto)
    if isinstance(out, dict):
        answer = str(out.get('message', out))
    else:
        answer = str(getattr(out, "message", out))
    
    return {
        "question": state["question"],
        "answer": answer,
        "task": state.get("task"),
        "tool_calls_count": state.get("tool_calls_count", 0),
        "status": "success"
    }
