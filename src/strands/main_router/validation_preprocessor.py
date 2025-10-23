import asyncio
from strands import Agent
from src.strands.config.llm_models import MODEL_NODE_EXECUTOR
from .state import MainRouterState
from src.strands.common.common_modules.validation import validate_title, validate_actor, validate_director
from src.strands.core.factories.router_factory import create_router
from src.strands.main_router.prompts import ENTITY_EXTRACTION_PROMPT, VALIDATION_ROUTER_PROMPT_STRICT

ROUTING_MAP = {
    "business": "business_graph",
    "talent": "talent_graph",
    "content": "content_graph",
    "platform": "platform_graph",
    "common": "common_graph"
}

VALIDATION_TOOLS_MAP = {
    "validate_title": validate_title,
    "validate_actor": validate_actor,
    "validate_director": validate_director
}

VALIDATION_TOOLS = list(VALIDATION_TOOLS_MAP.keys())


def _extract_text_from_result(result) -> str:
    if isinstance(result, dict):
        if 'content' in result and isinstance(result['content'], list):
            for content_item in result['content']:
                if isinstance(content_item, dict) and 'text' in content_item:
                    return content_item['text'].strip()
        if 'message' in result:
            return str(result['message']).strip()
    
    if hasattr(result, 'content'):
        content = result.content
        if isinstance(content, list) and len(content) > 0:
            first_content = content[0]
            if isinstance(first_content, dict) and 'text' in first_content:
                return first_content['text'].strip()
    
    if hasattr(result, 'message'):
        message = result.message
        if isinstance(message, dict):
            if 'content' in message and isinstance(message['content'], list):
                for content_item in message['content']:
                    if isinstance(content_item, dict) and 'text' in content_item:
                        return content_item['text'].strip()
        return str(message).strip()
    
    return str(result).strip()


async def _extract_entity_name(question: str) -> str:
    agent = Agent(model=MODEL_NODE_EXECUTOR, system_prompt=ENTITY_EXTRACTION_PROMPT)
    result = await agent.invoke_async(question)
    return _extract_text_from_result(result)


def _process_validation_result(validation_result: dict) -> tuple[str, bool, dict]:
    if not isinstance(validation_result, dict):
        return "error", False, {"status": "error", "error": "Invalid result type"}
    
    status = validation_result.get("status", "unknown")
    
    status_map = {
        "skipped": ("resolved", False, {"status": "skipped"}),
        "ambiguous": ("ambiguous", True, validation_result),
        "not_found": ("not_found", True, validation_result),
        "ok": ("resolved", False, validation_result),
        "resolved": ("resolved", False, validation_result)
    }
    
    return status_map.get(status, ("error", False, validation_result))


def _map_entity_ids(validated_entities: dict, tool_name: str) -> dict:
    if "id" not in validated_entities:
        return validated_entities
    
    entity_id = validated_entities["id"]
    
    if tool_name == "validate_actor":
        validated_entities["actor_id"] = entity_id
    elif tool_name == "validate_director":
        validated_entities["director_id"] = entity_id
    
    return validated_entities


def _validate_second_entity(validated_entities: dict, tool_name: str, entity_name: str) -> dict:
    tools_map = VALIDATION_TOOLS_MAP
    
    if tool_name == "validate_actor" and "actor_id" in validated_entities:
        director_result = tools_map["validate_director"](entity_name)
        if director_result.get("status") == "ok":
            validated_entities["director_id"] = director_result.get("id")
            validated_entities["director_name"] = director_result.get("name")
    
    elif tool_name == "validate_director" and "director_id" in validated_entities:
        actor_result = tools_map["validate_actor"](entity_name)
        if actor_result.get("status") == "ok":
            validated_entities["actor_id"] = actor_result.get("id")
            validated_entities["actor_name"] = actor_result.get("name")
    
    return validated_entities


def _process_multiple_entities(entity_names: list, tool_name: str, tool_fn) -> tuple[str, bool, dict]:
    print(f"[VALIDATION] Detectadas {len(entity_names)} entidades: {entity_names}")
    validated_entities = {"status": "ok"}
    
    for entity_name in entity_names:
        print(f"[VALIDATION] Validando: '{entity_name}'")
        validation_result = tool_fn(entity_name)
        print(f"[VALIDATION] Resultado: {validation_result}")
        
        if validation_result.get("status") == "ok":
            entity_id = validation_result.get("id")
            
            if tool_name == "validate_actor":
                if "actor_id" not in validated_entities:
                    validated_entities["actor_id"] = entity_id
                    validated_entities["actor_name"] = validation_result.get("name")
                else:
                    validated_entities = _validate_second_entity(validated_entities, tool_name, entity_name)
            
            elif tool_name == "validate_director":
                if "director_id" not in validated_entities:
                    validated_entities["director_id"] = entity_id
                    validated_entities["director_name"] = validation_result.get("name")
                else:
                    validated_entities = _validate_second_entity(validated_entities, tool_name, entity_name)
    
    return "resolved", False, validated_entities


def _handle_skip_validation(state: MainRouterState) -> MainRouterState:
    print("[VALIDATION] Validacion no requerida para este grafo, saltando...")
    return {
        **state,
        "validation_done": True,
        "validation_status": "resolved",
        "needs_validation": False,
        "validated_entities": {"status": "skipped"}
    }


def _handle_no_entity(state: MainRouterState) -> MainRouterState:
    print("[VALIDATION] Consulta general detectada, saltando validación")
    return {
        **state,
        "validation_done": True,
        "validation_status": "resolved",
        "needs_validation": False,
        "validated_entities": {"status": "skipped", "message": "General query, no specific entity"}
    }


def _handle_extraction_error(state: MainRouterState) -> MainRouterState:
    print("[VALIDATION] No se pudo extraer nombre de entidad")
    return {
        **state,
        "validation_done": True,
        "validation_status": "resolved",
        "needs_validation": False,
        "validated_entities": {"status": "skipped", "message": "No entity found"}
    }


def _handle_tool_not_found(state: MainRouterState, tool_name: str) -> MainRouterState:
    print(f"[VALIDATION] Tool no encontrado: {tool_name}")
    return {
        **state,
        "validation_done": True,
        "validation_status": "error",
        "needs_validation": False,
        "validated_entities": {"status": "error", "error": f"Tool not found: {tool_name}"}
    }


def _handle_user_input_required(state: MainRouterState, validation_status: str, validated_entities: dict) -> MainRouterState:
    print(f"[VALIDATION] Status: {validation_status} - requiere input del usuario")
    print("="*80 + "\n")
    
    return {
        **state,
        "validation_done": True,
        "validation_status": validation_status,
        "needs_user_input": True,
        "needs_validation": True,
        "validation_message": validated_entities.get("message", str(validated_entities)),
        "validated_entities": validated_entities
    }


def _handle_validation_error(state: MainRouterState, error: Exception) -> MainRouterState:
    print(f"[VALIDATION] Error: {error}")
    import traceback
    traceback.print_exc()
    
    return {
        **state,
        "validation_done": True,
        "validation_status": "error",
        "needs_validation": False,
        "validated_entities": {"status": "error", "error": str(error)}
    }


_validation_router = create_router(
    prompt=VALIDATION_ROUTER_PROMPT_STRICT,
    valid_tools=VALIDATION_TOOLS,
    model=MODEL_NODE_EXECUTOR
)


async def validation_preprocessor_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print("VALIDATION PREPROCESSOR")
    print("="*80)
    print(f"Pregunta: {state['question']}")
    
    if state.get("validation_done", False):
        print("[VALIDATION] Ya validado, saltando...")
        return state
    
    if state.get("skip_validation", False):
        return _handle_skip_validation(state)
    
    try:
        print("[VALIDATION] Ejecutando router y extractor en paralelo...")
        tool_name, entity_names_raw = await asyncio.gather(
            _validation_router(state),
            _extract_entity_name(state['question'])
        )
        print(f"[VALIDATION] Tool seleccionado: {tool_name}")
        
        tool_fn = VALIDATION_TOOLS_MAP.get(tool_name)
        if not tool_fn:
            return _handle_tool_not_found(state, tool_name)
        
        if not entity_names_raw:
            return _handle_extraction_error(state)
        
        print(f"[VALIDATION] Entidad(es) extraída(s): '{entity_names_raw}'")
        
        if "NO_ENTITY" in entity_names_raw.upper():
            return _handle_no_entity(state)
        
        entity_names = [name.strip() for name in entity_names_raw.split(" | ")]
        
        if len(entity_names) > 1:
            validation_status, needs_user_input, validated_entities = _process_multiple_entities(
                entity_names, tool_name, tool_fn
            )
        else:
            entity_name = entity_names[0]
            print(f"[VALIDATION] Ejecutando {tool_name}('{entity_name}')...")
            validation_result = tool_fn(entity_name)
            
            print(f"[VALIDATION] Resultado: {validation_result}")
            
            validation_status, needs_user_input, validated_entities = _process_validation_result(validation_result)
            validated_entities = _map_entity_ids(validated_entities, tool_name)
        
        if needs_user_input:
            return _handle_user_input_required(state, validation_status, validated_entities)
        
        print(f"[VALIDATION] Completada con status: {validation_status}")
        print(f"[VALIDATION] Entities: {validated_entities}")
        print("="*80 + "\n")
        
        return {
            **state,
            "validation_done": True,
            "validation_status": validation_status,
            "needs_validation": True,
            "validated_entities": validated_entities
        }
        
    except Exception as e:
        return _handle_validation_error(state, e)


def should_validate(state: MainRouterState) -> str:
    if state.get("needs_user_input", False):
        return "END"
    
    if state.get("validation_done", False):
        selected = state.get("selected_graph", "common")
        return ROUTING_MAP.get(selected, "common_graph")
    
    return "validation_preprocessor"