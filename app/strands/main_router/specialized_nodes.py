from .state import MainRouterState
from app.strands.main_router.session_state import session_memory
import re


def _extract_selection_number(question: str) -> int:
    match = re.search(r'\b(\d+)\b', question)
    return int(match.group(1)) if match else None


def _create_validated_entities_for_title(selected_option: dict) -> dict:
    return {
        "status": "resolved",
        "uid": selected_option.get("uid"),
        "name": selected_option.get("title"),
        "year": selected_option.get("year"),
        "type": selected_option.get("type")
    }


def _create_validated_entities_for_person(selected_option: dict, original_question: str) -> dict:
    entity_id = selected_option.get("id")
    entity_name = selected_option.get("name")
    
    is_actor = "actor" in original_question.lower()
    key_prefix = "actor" if is_actor else "director"
    
    return {
        "status": "resolved",
        f"{key_prefix}_id": entity_id,
        f"{key_prefix}_name": entity_name,
        "id": entity_id,
        "name": entity_name
    }


def _create_validated_entities(selected_option: dict, original_question: str) -> dict:
    if "uid" in selected_option:
        return _create_validated_entities_for_title(selected_option)
    elif "id" in selected_option:
        return _create_validated_entities_for_person(selected_option, original_question)
    return {}


async def user_selection_resolver_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print("USER SELECTION RESOLVER")
    print("="*80)
    
    question = state.get("question", "")
    options = state.get("disambiguation_options", [])
    original_question = state.get("original_question", "")
    
    selection = _extract_selection_number(question)
    
    if not selection:
        print("[SELECTION] No se pudo extraer número de selección")
        error_msg = "Por favor, selecciona una de las opciones enviando el número correspondiente (1, 2, 3, etc.)."
        return {
            **state,
            "answer": error_msg,
            "needs_user_input": False,  # Cambiar a False para terminar el flujo
            "pending_disambiguation": True,  # Mantener pending para que el frontend sepa
            "domain_graph_status": "error"  # Marcar como error para evitar re-routing
        }
    
    if selection < 1 or selection > len(options):
        print(f"[SELECTION] Selección fuera de rango: {selection} (opciones: 1-{len(options)})")
        error_msg = f"Selección inválida. Por favor, elige un número entre 1 y {len(options)}."
        return {
            **state,
            "answer": error_msg,
            "needs_user_input": False,  # Cambiar a False para terminar el flujo
            "pending_disambiguation": True,  # Mantener pending para que el frontend sepa
            "domain_graph_status": "error"  # Marcar como error para evitar re-routing
        }
    
    # ------------------------------
    # Obtener y validar selección
    # ------------------------------
    selected_option = options[selection - 1]
    print(f"[SELECTION] Usuario seleccionó opción {selection}")
    print(f"[SELECTION] Opción: {selected_option}")
    
    validated_entities = _create_validated_entities(selected_option, original_question)

    # ------------------------------
    # Persistir el UID en memoria
    # ------------------------------
    thread_id = state.get("thread_id") or state.get("session_id")
    if "uid" in selected_option and thread_id:
        session_memory.update(thread_id, last_uid=selected_option["uid"])
        print(f"[SESSION] UID guardado en memoria: {selected_option['uid']} (thread {thread_id})")
    elif "id" in selected_option and thread_id:
        session_memory.update(thread_id, last_uid=selected_option["id"])
        print(f"[SESSION] ID guardado en memoria: {selected_option['id']} (thread {thread_id})")

    print("="*80 + "\n")
    
    # ------------------------------
    # Devolver nuevo estado limpio
    # ------------------------------
    return {
        **state,
        "question": original_question,
        "validated_entities": validated_entities,
        "validation_status": "resolved",
        "validation_done": True,
        "needs_user_input": False,
        "pending_disambiguation": False,
        "disambiguation_options": None,
        "routing_done": False,
        "visited_graphs": [],
        "needs_rerouting": False,
        "domain_graph_status": None  # Limpiar status para que routing funcione
    }


def _format_title_option(i: int, option: dict) -> str:
    return f"{i}. {option.get('title', 'Unknown')} ({option.get('year', 'N/A')}) - {option.get('type', 'N/A')} [UID: {option.get('uid', 'N/A')}]"


def _format_person_option(i: int, option: dict) -> str:
    n_titles = option.get('n_titles', 'N/A')
    return f"{i}. {option.get('name', 'Unknown')} ({n_titles} titles) [ID: {option.get('id', 'N/A')}]"


def _format_disambiguation_options(options: list) -> list:
    formatted_options = []
    for i, option in enumerate(options, 1):
        if "uid" in option:
            formatted_options.append(_format_title_option(i, option))
        elif "id" in option:
            formatted_options.append(_format_person_option(i, option))
        else:
            formatted_options.append(f"{i}. {option}")
    return formatted_options


async def disambiguation_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print("DISAMBIGUATION NODE")
    print("="*80)
    
    validated_entities = state.get("validated_entities", {})
    options = validated_entities.get("options", [])
    question = state.get("question", "")
    
    formatted_options = _format_disambiguation_options(options)
    options_text = "\n".join(formatted_options)
    
    formatted_message = f"""Multiple matches found for your query.

Your question: {question}

Please specify which one you meant:

{options_text}

Reply with the number of your choice (e.g., "1" or "option 2")."""
    
    # Agregar option_number a cada opción para el frontend
    options_with_numbers = []
    for i, option in enumerate(options, 1):
        option_copy = option.copy()
        option_copy["option_number"] = i
        # Agregar campo 'count' si es persona (n_titles)
        if "n_titles" in option:
            option_copy["count"] = option["n_titles"]
        options_with_numbers.append(option_copy)
    
    print("[DISAMBIGUATION] Opciones formateadas:")
    print(options_text)
    print("[DISAMBIGUATION]   Setting pending_disambiguation=True")
    print("[DISAMBIGUATION]   Saving original_question:", question)
    print("[DISAMBIGUATION]   Saving", len(options), "options")
    print("="*80 + "\n")
    
    result = {
        **state,
        "answer": formatted_message,
        "needs_user_input": True,
        "pending_disambiguation": True,
        "disambiguation_options": options_with_numbers,
        "original_question": question
    }
    
    print(f"[DISAMBIGUATION]  Returning state with pending_disambiguation={result.get('pending_disambiguation')}")
    
    return result


async def not_found_responder_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print("NOT FOUND RESPONDER")
    print("="*80)
    
    validation_msg = state.get("validation_message", "")
    question = state.get("question", "")
    
    formatted_message = f"""Entity Not Found

I couldn't find the entity you're looking for in our database.

Your question: {question}

Details: {validation_msg}

Please check the spelling or try a different search term."""
    
    print("[NOT_FOUND] Mensaje formateado")
    print("="*80 + "\n")
    
    return {
        **state,
        "answer": formatted_message,
        "needs_user_input": False
    }


async def error_handler_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print("ERROR HANDLER")
    print("="*80)
    
    error = state.get("error", "Unknown error")
    question = state.get("question", "")
    
    formatted_message = f"""System Error

I encountered an error while processing your question.

Your question: {question}

Error: {error}

Please try rephrasing your question or contact support if the issue persists."""
    
    print(f"[ERROR_HANDLER] Error: {error}")
    print("="*80 + "\n")
    
    return {
        **state,
        "answer": formatted_message,
        "needs_user_input": False
    }


async def responder_formatter_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print("RESPONDER/FORMATTER")
    print("="*80)
    
    answer = state.get("answer", "")
    
    if not answer:
        answer = "I couldn't generate a response. Please try rephrasing your question."
    
    print("\n RESULTADO:")
    print("="*80)
    print(answer)
    print("="*80 + "\n")
    
    result = {**state, "answer": answer}
    
    print(f"[RESPONDER] pending_disambiguation={result.get('pending_disambiguation')}")
    
    return result