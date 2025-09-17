# Standard library imports
import time
import re

from langchain_core.messages import AIMessage, ToolMessage


def get_events_last_message(agent, state, thread_id="default", verbose=True):
    regex_exp = re.compile(
        r'(te recomiendo|te sugiero|recomendaciones|sugerencias?|consejos?|tips?|curiosidades?|datos curiosos?|características|propiedades?|observaciones?|notas?|bonus|extra) ?:.*', re.I | re.DOTALL)

    print("ENTRA A GET EVENTS LAST MESSAGE")
    start_time = time.time()
    last_message = None

    config = {"configurable": {"thread_id": thread_id}}
    events = agent.stream(state, config=config, stream_mode="values")

    for event in events:
        msg = event["messages"][-1]  # último mensaje del paso
        last_message = msg.content

        # 🔎 imprime herramientas llamadas o respondidas
        tool_info = None
        if isinstance(msg, AIMessage):
            # Llamadas a tools (cuando el modelo pide usar una herramienta)
            tcalls = msg.additional_kwargs.get(
                "tool_calls") or getattr(msg, "tool_calls", None)
            if tcalls:
                tool_info = " | ".join(
                    f"CALL → {tc['name']}({tc.get('id', '')})"
                    for tc in tcalls
                    if isinstance(tc, dict) and "name" in tc
                )
        elif isinstance(msg, ToolMessage):
            # Respuesta de la tool (cuando la herramienta devuelve algo)
            tool_info = f"RETURN ← {msg.name}"

        event["messages"] = msg  # tu línea original
        step_time = round(time.time() - start_time, 2)

        if verbose:
            base = f"({agent.name:16}) Time: {step_time:5}s | {event}"
            print(base if not tool_info else base + f"  [{tool_info}]")

    st = agent.get_state(config)
    print(
        f"[DEBUG] Memoria thread_id={thread_id} tiene {len(st.values.get('messages', []))} mensajes")

    print("LAST_MESSAGE", last_message)
    last_message = regex_exp.sub('', last_message)
    print("NOW", last_message)

    return last_message or "No response generated"
