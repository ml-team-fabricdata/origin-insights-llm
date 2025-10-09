# graph_core/supervisor.py
from strands import Agent
from src.strands.platform.prompts import PLATFORM_PROMPT, RESPONSE_PROMPT, get_supervisor_prompt
from src.strands.platform.config import MODEL_CLASSIFIER, MODEL_SUPERVISOR, MODEL_FORMATTER
from .state import State
from typing import Literal, Optional

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
        

async def main_supervisor(state: State) -> State:
    """Decide si continuar buscando datos o finalizar"""
    
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
    
    # Caso 2: Alcanzó máximo de iteraciones - COMPLETO
    if tool_calls >= max_iter:
        print(f"[SUPERVISOR] Maximo de iteraciones alcanzado ({tool_calls}/{max_iter})")
        return {
            **state,
            "supervisor_decision": "COMPLETO"
        }
    
    # Caso 3: Evaluar si los datos son suficientes
    accumulated = state.get('accumulated_data', '')
    
    # Si no hay datos acumulados, está mal
    if not accumulated or len(accumulated.strip()) < 50:
        print("[SUPERVISOR] No hay datos suficientes, marcando como COMPLETO")
        return {
            **state,
            "supervisor_decision": "COMPLETO"
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
        print("[SUPERVISOR] ✗ Necesita mas informacion, continuar loop")
        supervisor_decision = "NECESITA_CLASIFICACION"
    
    return {
        **state,
        "supervisor_decision": supervisor_decision
    }


def route_from_main_supervisor(state: State) -> Literal["platform_node", "format_response"]:
    """Enruta basado en la decisión del supervisor"""
    
    decision = state.get("supervisor_decision", "COMPLETO").upper()
    tool_calls = state.get("tool_calls_count", 0)
    max_iter = state.get("max_iterations", 1)
    
    # Seguridad: si excede iteraciones, siempre terminar
    if tool_calls >= max_iter:
        return "format_response"
    
    # Si está completo, formatear respuesta
    if decision == "COMPLETO":
        return "format_response"
    
    # Si necesita clasificación, ir al platform_node
    if "CLASIFICACION" in decision:
        return "platform_node"
    
    # Fallback: formatear con lo que hay
    return "format_response"


async def format_response(state: State) -> State:
    """Formatea la respuesta final al usuario"""
    
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