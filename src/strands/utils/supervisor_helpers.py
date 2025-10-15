from strands import Agent
from src.prompt import RESPONSE_PROMPT, get_supervisor_prompt
from src.strands.utils.config import MODEL_SUPERVISOR, MODEL_FORMATTER
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
        print("[SUPERVISOR] ⚠️ No se completó, volviendo al main router")
        return {**state, "supervisor_decision": "VOLVER_MAIN_ROUTER"}
    accumulated = state.get('accumulated_data', '')
    if not accumulated or len(accumulated.strip()) < 50:
        print("[SUPERVISOR] No hay datos suficientes, volviendo al main router")
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
        print("[SUPERVISOR] ✓ Pregunta respondida, ir a format")
        supervisor_decision = "COMPLETO"
    else:
        print("[SUPERVISOR] ✗ Necesita mas informacion, volviendo al main router")
        supervisor_decision = "VOLVER_MAIN_ROUTER"
    return {**state, "supervisor_decision": supervisor_decision}


def create_route_from_supervisor(classifier_node_name: str):
    def route_from_main_supervisor(state: TypedDict) -> Literal[str, str, str]:
        decision = state.get("supervisor_decision", "COMPLETO").upper()
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
    formatter = Agent(model=MODEL_FORMATTER, tools=[], system_prompt=RESPONSE_PROMPT)
    accumulated = state.get('accumulated_data', state.get('answer', ''))
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
