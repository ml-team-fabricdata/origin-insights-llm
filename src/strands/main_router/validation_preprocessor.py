import asyncio
from strands import Agent
from src.strands.config.models import MODEL_NODE_EXECUTOR
from .state import MainRouterState
from src.strands.common.common_modules.validation import validate_title, validate_actor, validate_director
from src.strands.common.nodes.prompt_common import VALIDATION_ROUTER_PROMPT
from src.strands.core.factories.router_factory import create_router

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


VALIDATION_ROUTER_PROMPT_STRICT = """Return ONLY ONE word: the tool name. NO explanations.

TOOLS:
- validate_title (for movies/series/shows)
- validate_actor (for actors/actresses)
- validate_director (for directors)

EXAMPLES:
Q: "filmography of Tom Hanks" → validate_actor
Q: "movies directed by Spielberg" → validate_director
Q: "information about Inception" → validate_title
Q: "¿Cuál es la filmografía de Tom Hanks?" → validate_actor

CRITICAL: Return ONLY the tool name. One word. Nothing else.
"""


ENTITY_EXTRACTION_PROMPT = """Extract entity name(s) from the question. 

RULES:
- If SPECIFIC entity: return the name
- If TWO entities (collaborations): return "ENTITY1 | ENTITY2" separated by " | "
- If NO specific entity (general query): return "NO_ENTITY"
- No explanations, no additional text

Examples with entities:
- "filmography of Tom Hanks" → Tom Hanks
- "movies directed by Steven Spielberg" → Steven Spielberg
- "information about Inception" → Inception
- "movies with Tom Hanks and Steven Spielberg" → Tom Hanks | Steven Spielberg
- "¿En qué películas han trabajado juntos Tom Hanks y Steven Spielberg?" → Tom Hanks | Steven Spielberg

Examples WITHOUT entities (general queries):
- "action movies" → NO_ENTITY
- "películas de acción" → NO_ENTITY
- "best movies of 2023" → NO_ENTITY
- "top rated series" → NO_ENTITY
- "busca películas de terror" → NO_ENTITY

Return ONLY the entity name(s), " | " separator for multiple, or "NO_ENTITY" for general queries.
"""


async def _extract_entity_name(question: str) -> str:
    """Extrae el nombre de la entidad usando LLM sin regex."""
    agent = Agent(model=MODEL_NODE_EXECUTOR, system_prompt=ENTITY_EXTRACTION_PROMPT)
    result = await agent.invoke_async(question)
    
    # Caso 1: Si result es un dict con estructura {'role': 'assistant', 'content': [...]}
    if isinstance(result, dict):
        if 'content' in result and isinstance(result['content'], list):
            for content_item in result['content']:
                if isinstance(content_item, dict) and 'text' in content_item:
                    return content_item['text'].strip()
        if 'message' in result:
            return str(result['message']).strip()
    
    # Caso 2: Si result tiene atributo 'content'
    if hasattr(result, 'content'):
        content = result.content
        if isinstance(content, list) and len(content) > 0:
            first_content = content[0]
            if isinstance(first_content, dict) and 'text' in first_content:
                return first_content['text'].strip()
    
    # Caso 3: Si result tiene atributo 'message'
    if hasattr(result, 'message'):
        message = result.message
        if isinstance(message, dict):
            if 'content' in message and isinstance(message['content'], list):
                for content_item in message['content']:
                    if isinstance(content_item, dict) and 'text' in content_item:
                        return content_item['text'].strip()
        return str(message).strip()
    
    # Fallback: convertir a string
    return str(result).strip()


def _process_validation_result(validation_result: dict) -> tuple[str, bool, dict]:
    """Procesa el resultado de validación y retorna (status, needs_user_input, entities).
    
    Returns:
        tuple: (validation_status, needs_user_input, validated_entities)
    """
    if not isinstance(validation_result, dict):
        return "error", False, {"status": "error", "error": "Invalid result type"}
    
    status = validation_result.get("status", "unknown")
    
    if status == "skipped":
        return "resolved", False, {"status": "skipped"}
    
    if status == "ambiguous":
        return "ambiguous", True, validation_result
    
    if status == "not_found":
        return "not_found", True, validation_result
    
    if status in ["ok", "resolved"]:
        return "resolved", False, validation_result
    
    return "error", False, validation_result


# Crear router de validación con prompt estricto
_validation_router = create_router(
    prompt=VALIDATION_ROUTER_PROMPT_STRICT,
    valid_tools=VALIDATION_TOOLS,
    model=MODEL_NODE_EXECUTOR
)


async def validation_preprocessor_node(state: MainRouterState) -> MainRouterState:
    """Nodo de validación de entidades usando patrón ROUTER.
    
    El router selecciona el tool correcto y lo ejecuta directamente,
    evitando que el LLM genere texto adicional.
    """
    print("\n" + "="*80)
    print("VALIDATION PREPROCESSOR")
    print("="*80)
    print(f"Pregunta: {state['question']}")
    
    if state.get("validation_done", False):
        print("[VALIDATION] Ya validado, saltando...")
        return state
    
    if state.get("skip_validation", False):
        print("[VALIDATION] Validacion no requerida para este grafo, saltando...")
        return {
            **state,
            "validation_done": True,
            "validation_status": "resolved",
            "needs_validation": False,
            "validated_entities": {"status": "skipped"}
        }
    
    try:
        # 1 & 2. PARALELIZAR: Router + Extractor (ejecutar en paralelo)
        print("[VALIDATION] Ejecutando router y extractor en paralelo...")
        tool_name, entity_names_raw = await asyncio.gather(
            _validation_router(state),
            _extract_entity_name(state['question'])
        )
        print(f"[VALIDATION] Tool seleccionado: {tool_name}")
        
        # 3. Obtener función del tool
        tool_fn = VALIDATION_TOOLS_MAP.get(tool_name)
        if not tool_fn:
            print(f"[VALIDATION] Tool no encontrado: {tool_name}")
            return {
                **state,
                "validation_done": True,
                "validation_status": "error",
                "needs_validation": False,
                "validated_entities": {"status": "error", "error": f"Tool not found: {tool_name}"}
            }
        # 4. Validar extracción
        if not entity_names_raw:
            print("[VALIDATION] No se pudo extraer nombre de entidad")
            return {
                **state,
                "validation_done": True,
                "validation_status": "resolved",
                "needs_validation": False,
                "validated_entities": {"status": "skipped", "message": "No entity found"}
            }
        
        print(f"[VALIDATION] Entidad(es) extraída(s): '{entity_names_raw}'")
        
        # 5. Detectar si es una consulta general (sin entidad específica)
        if "NO_ENTITY" in entity_names_raw.upper():
            print("[VALIDATION] Consulta general detectada, saltando validación")
            return {
                **state,
                "validation_done": True,
                "validation_status": "resolved",
                "needs_validation": False,
                "validated_entities": {"status": "skipped", "message": "General query, no specific entity"}
            }
        
        # 6. Detectar si hay múltiples entidades (colaboraciones)
        entity_names = [name.strip() for name in entity_names_raw.split(" | ")]
        
        if len(entity_names) > 1:
            # Caso: Múltiples entidades (colaboraciones)
            print(f"[VALIDATION] Detectadas {len(entity_names)} entidades: {entity_names}")
            validated_entities = {"status": "ok"}
            
            for entity_name in entity_names:
                print(f"[VALIDATION] Validando: '{entity_name}'")
                validation_result = tool_fn(entity_name)
                print(f"[VALIDATION] Resultado: {validation_result}")
                
                if validation_result.get("status") == "ok":
                    entity_id = validation_result.get("id")
                    # Determinar si es actor o director basado en el tool
                    if tool_name == "validate_actor":
                        # Si ya hay un actor_id, este es el segundo (para colaboraciones)
                        if "actor_id" not in validated_entities:
                            validated_entities["actor_id"] = entity_id
                            validated_entities["actor_name"] = validation_result.get("name")
                        else:
                            # Segundo actor - probablemente es un director
                            # Re-validar como director
                            director_result = VALIDATION_TOOLS_MAP["validate_director"](entity_name)
                            if director_result.get("status") == "ok":
                                validated_entities["director_id"] = director_result.get("id")
                                validated_entities["director_name"] = director_result.get("name")
                    elif tool_name == "validate_director":
                        if "director_id" not in validated_entities:
                            validated_entities["director_id"] = entity_id
                            validated_entities["director_name"] = validation_result.get("name")
                        else:
                            # Segundo director - probablemente es un actor
                            actor_result = VALIDATION_TOOLS_MAP["validate_actor"](entity_name)
                            if actor_result.get("status") == "ok":
                                validated_entities["actor_id"] = actor_result.get("id")
                                validated_entities["actor_name"] = actor_result.get("name")
            
            validation_status = "resolved"
            needs_user_input = False
        else:
            # Caso: Una sola entidad
            entity_name = entity_names[0]
            print(f"[VALIDATION] Ejecutando {tool_name}('{entity_name}')...")
            validation_result = tool_fn(entity_name)
            
            print(f"[VALIDATION] Resultado: {validation_result}")
            
            # 5. Procesar resultado
            validation_status, needs_user_input, validated_entities = _process_validation_result(validation_result)
            
            # 6. Mapear IDs a keys específicos para cada tipo de entidad
            if validation_status == "resolved" and "id" in validated_entities:
                entity_id = validated_entities["id"]
                if tool_name == "validate_actor":
                    validated_entities["actor_id"] = entity_id
                elif tool_name == "validate_director":
                    validated_entities["director_id"] = entity_id
                elif tool_name == "validate_title" and "uid" in validated_entities:
                    validated_entities["title_uid"] = validated_entities["uid"]
        
        if needs_user_input:
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
        print(f"[VALIDATION] Error: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            **state,
            "validation_done": True,
            "validation_status": "error",
            "needs_validation": False,
            "validated_entities": {"status": "error", "error": str(e)}
        }


def should_validate(state: MainRouterState) -> str:
    if state.get("needs_user_input", False):
        return "END"
    
    if state.get("validation_done", False):
        selected = state.get("selected_graph", "common")
        return ROUTING_MAP.get(selected, "common_graph")
    
    return "validation_preprocessor"