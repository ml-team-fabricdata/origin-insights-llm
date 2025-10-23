from strands import Agent
from app.prompt.brand_guard import build_prompt
from app.strands.config.llm_models import (
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
        return {**state, "supervisor_decision": "NECESITA_CLASIFICACION"}

    if tool_calls >= max_iter:
        print(f"[SUPERVISOR] Maximo de iteraciones alcanzado ({tool_calls}/{max_iter})")
        return {**state, "supervisor_decision": "VOLVER_MAIN_ROUTER"}

    accumulated = state.get('accumulated_data', '')
    if not accumulated or len(accumulated.strip()) < 50:
        print("[SUPERVISOR] No hay datos suficientes, volviendo al main router")
        return {**state, "supervisor_decision": "VOLVER_MAIN_ROUTER"}

    accumulated_lower = accumulated.lower()
    generic_phrases = [
        "lo siento, no tengo", "i'm sorry, i don't have", "no tengo información",
        "don't have access", "no puedo proporcionar", "cannot provide",
        "lamentablemente, no tengo", "unfortunately, i don't", "no tengo acceso"
    ]

    if any(phrase in accumulated_lower for phrase in generic_phrases):
        print("[SUPERVISOR] Respuesta genérica detectada, reencaminando")
        return {**state, "supervisor_decision": "VOLVER_MAIN_ROUTER"}

    # Brand Guard (nuevo prompt framework)
    prompt_parts = build_prompt(
        user_text="Evalúa si los datos acumulados responden correctamente la pregunta del usuario.",
        ctx_uid=None,
        ctx_country=None,
        ctx_year=None,
        ctx_type=None,
    )

    supervisor_agent = Agent(model=MODEL_SUPERVISOR, system_prompt=prompt_parts.system)
    response = await supervisor_agent.invoke_async(state["question"])

    if isinstance(response, dict):
        decision = str(response.get('message', response)).strip().upper()
    else:
        decision = str(getattr(response, "message", response)).strip().upper()

    print(f"[SUPERVISOR] Decision del LLM: {decision}")

    if "COMPLETO" in decision or "COMPLETE" in decision:
        supervisor_decision = "COMPLETO"
    else:
        supervisor_decision = "VOLVER_MAIN_ROUTER"

    return {**state, "supervisor_decision": supervisor_decision}


def create_route_from_supervisor(classifier_node_name: str):
    def route_from_main_supervisor(state: TypedDict) -> Literal[str, str, str]:
        decision = state.get("supervisor_decision", "COMPLETO").upper()
        print(f"\n[ROUTING] route_from_main_supervisor called")
        print(f"[ROUTING] supervisor_decision: '{decision}'")
        print(f"[ROUTING] classifier_node_name: '{classifier_node_name}'")

        if decision == "COMPLETO":
            return "format_response"
        if "VOLVER_MAIN_ROUTER" in decision:
            return "return_to_main_router"
        if "CLASIFICACION" in decision:
            return classifier_node_name
        return "return_to_main_router"

    route_from_main_supervisor.__name__ = f"route_from_main_supervisor_to_{classifier_node_name}"
    return route_from_main_supervisor


async def format_response(state: TypedDict) -> TypedDict:
    accumulated = state.get('accumulated_data', state.get('answer', ''))

    if not accumulated or len(accumulated.strip()) < 20:
        return {
            "question": state["question"],
            "answer": "Lo siento, no pude obtener información suficiente para responder tu pregunta.",
            "task": state.get("task"),
            "tool_calls_count": state.get("tool_calls_count", 0),
            "status": "insufficient_data"
        }

    # Detectar estructuras ya formateadas
    is_structured = (
        accumulated.strip().startswith('[')
        or accumulated.strip().startswith('{')
        or '\n- ' in accumulated
        or '\n* ' in accumulated
    )

    if is_structured:
        print("[FORMAT] Datos ya estructurados, no se requiere formato adicional")
        return {
            "question": state["question"],
            "answer": accumulated,
            "task": state.get("task"),
            "tool_calls_count": state.get("tool_calls_count", 0),
            "status": "success"
        }

    print("[FORMAT] Aplicando formato con modelo FORMATTER (Brand Guard)")
    prompt_parts = build_prompt("Formatea una respuesta clara, natural y breve para el usuario.")
    formatter = Agent(model=MODEL_FORMATTER, system_prompt=prompt_parts.system)

    payload = f"""Question: {state['question']}

Raw data:
{accumulated}

Format a clear, concise, user-friendly response."""
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