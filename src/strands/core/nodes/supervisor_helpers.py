from strands import Agent
from src.prompt import RESPONSE_PROMPT, get_supervisor_prompt
from src.strands.config.llm_models import (
    MODEL_SUPERVISOR,
    MODEL_FORMATTER,
)
from typing import Literal, TypedDict


async def main_supervisor(state: TypedDict) -> TypedDict:
    print(f"[SUPERVISOR] Evaluando estado... tools={state.get('tool_calls_count', 0)}, task={state.get('task')}")
    tool_calls = state.get('tool_calls_count', 0)
    max_iter = state.get('max_iterations', 3)
    if tool_calls == 0:
        print("[SUPERVISOR] Primera iteracion, necesita clasificacion")
        print("[SUPERVISOR] Retornando: supervisor_decision='NECESITA_CLASIFICACION'")
        return {**state, "supervisor_decision": "NECESITA_CLASIFICACION"}
    if tool_calls >= max_iter:
        print(f"[SUPERVISOR] Maximo de iteraciones alcanzado ({tool_calls}/{max_iter})")
        print("[SUPERVISOR] No se completo, volviendo al main router")
        return {**state, "supervisor_decision": "VOLVER_MAIN_ROUTER"}
    accumulated = state.get('accumulated_data', '')
    if not accumulated or len(accumulated.strip()) < 50:
        print("[SUPERVISOR] No hay datos suficientes, volviendo al main router")
        return {**state, "supervisor_decision": "VOLVER_MAIN_ROUTER"}
    
    accumulated_lower = accumulated.lower()
    generic_phrases = [
        "lo siento, no tengo",
        "i'm sorry, i don't have",
        "no tengo información",
        "don't have access",
        "no puedo proporcionar",
        "cannot provide",
        "lamentablemente, no tengo",
        "unfortunately, i don't",
        "no tengo acceso"
    ]
    
    if any(phrase in accumulated_lower for phrase in generic_phrases):
        print("[SUPERVISOR]   Respuesta genérica detectada (frases de disculpa)")
        print("[SUPERVISOR] Esto indica que las herramientas no se usaron correctamente")
        print("[SUPERVISOR] Volviendo al main router para intentar otro enfoque")
        return {**state, "supervisor_decision": "VOLVER_MAIN_ROUTER"}
    supervisor_prompt = get_supervisor_prompt(
        question=state['question'],
        tool_calls=tool_calls,
        max_iter=max_iter,
        accumulated=accumulated
    )
    supervisor_agent = Agent(model=MODEL_SUPERVISOR, system_prompt=supervisor_prompt)
    response = await supervisor_agent.invoke_async("¿Los datos responden la pregunta?")
    if isinstance(response, dict):
        decision = str(response.get('message', response)).strip().upper()
    else:
        decision = str(getattr(response, "message", response)).strip().upper()
    print(f"[SUPERVISOR] Decision del LLM: {decision}")
    if "COMPLETO" in decision or "COMPLETE" in decision:
        print("[SUPERVISOR] Pregunta respondida, ir a format")
        supervisor_decision = "COMPLETO"
        # Copiar accumulated_data a answer para que el main router pueda acceder
        answer = state.get('answer', '') or accumulated
        return {**state, "supervisor_decision": supervisor_decision, "answer": answer}
    else:
        print("[SUPERVISOR] Necesita mas informacion, volviendo al main router")
        supervisor_decision = "VOLVER_MAIN_ROUTER"
    return {**state, "supervisor_decision": supervisor_decision}


def create_route_from_supervisor(classifier_node_name: str):
    def route_from_main_supervisor(state: TypedDict) -> Literal[str, str, str]:
        decision = state.get("supervisor_decision", "COMPLETO").upper()
        print(f"\n[ROUTING] route_from_main_supervisor called")
        print(f"[ROUTING] supervisor_decision: '{decision}'")
        print(f"[ROUTING] classifier_node_name: '{classifier_node_name}'")
        
        if decision == "COMPLETO":
            print(f"[ROUTING] → COMPLETO (END)")
            return "COMPLETO"
        if "VOLVER_MAIN_ROUTER" in decision:
            print(f"[ROUTING] → return_to_main_router")
            return "return_to_main_router"
        if "CLASIFICACION" in decision:
            print(f"[ROUTING] → {classifier_node_name}")
            return classifier_node_name
        
        print(f"[ROUTING] → return_to_main_router (default)")
        return "return_to_main_router"
    route_from_main_supervisor.__name__ = f"route_from_main_supervisor_to_{classifier_node_name}"
    return route_from_main_supervisor


async def format_response(state: TypedDict) -> TypedDict:
    """
    Optimized format_response: Only uses LLM for complex responses.
    Simple/structured data is returned directly without LLM formatting.
    """
    accumulated = state.get('accumulated_data', state.get('answer', ''))
    
    if not accumulated or len(accumulated.strip()) < 20:
        return {
            "question": state["question"],
            "answer": "Lo siento, no pude obtener informacion suficiente para responder tu pregunta.",
            "task": state.get("task"),
            "tool_calls_count": state.get("tool_calls_count", 0),
            "status": "insufficient_data"
        }
    
    # Use LLM to check if response contains real data or is a "no data" response
    check_prompt = """Evaluate if the response contains REAL DATA or is a "no data" response.

REAL DATA = specific information, numbers, lists, titles, names, facts from database
NO DATA = "no results", "not found", "not available", "0 rows", generic apologies

Response to evaluate:
{response}

Answer ONLY with ONE WORD: DATA or NO_DATA
"""
    
    checker = Agent(model=MODEL_SUPERVISOR, system_prompt=check_prompt.format(response=accumulated[:500]))
    check_result = await checker.invoke_async("Evaluate:")
    
    decision = ""
    if isinstance(check_result, dict):
        decision = str(check_result.get('message', check_result)).strip().upper()
    else:
        decision = str(getattr(check_result, "message", check_result)).strip().upper()
    
    if "NO_DATA" in decision or "NO DATA" in decision:
        print("[FORMAT] LLM detected 'NO DATA' response, returning as-is without formatting")
        return {
            "question": state["question"],
            "answer": accumulated,
            "task": state.get("task"),
            "tool_calls_count": state.get("tool_calls_count", 0),
            "status": "no_data"
        }
    
    is_json_list = accumulated.strip().startswith('[') and accumulated.strip().endswith(']')
    is_json_object = accumulated.strip().startswith('{') and accumulated.strip().endswith('}')
    has_markdown_lists = '\n- ' in accumulated or '\n* ' in accumulated
    
    if is_json_list or is_json_object or has_markdown_lists:
        print("[FORMAT] Data already structured (JSON/Markdown), skipping LLM formatting")
        return {
            "question": state["question"],
            "answer": accumulated,
            "task": state.get("task"),
            "tool_calls_count": state.get("tool_calls_count", 0),
            "status": "success"
        }
    
    print("[FORMAT] Complex data detected, using LLM formatting")
    formatter = Agent(model=MODEL_FORMATTER, tools=[], system_prompt=RESPONSE_PROMPT)
    payload = f"""Question: {state['question']}

        Raw data:
        {accumulated}

        Format a clear, concise response for the user."""
    out = await formatter.invoke_async(payload)
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