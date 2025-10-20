import re
from strands import Agent
from src.strands.utils.config import MODEL_NODE_EXECUTOR
from .state import MainRouterState
from src.strands.common.common_modules.validation import validate_title, validate_actor, validate_director
from src.strands.main_router.prompts import VALIDATION_PREPROCESSOR_PROMPT

ROUTING_MAP = {
    "business": "business_graph",
    "talent": "talent_graph",
    "content": "content_graph",
    "platform": "platform_graph",
    "common": "common_graph"
}


def _extract_validation_result(result) -> str:
    if isinstance(result, dict):
        return str(result.get('message', result))
    return str(getattr(result, "message", result))


def _needs_user_input(validation_str: str) -> bool:
    ambiguity_indicators = [
        "Multiple matches found",
        "Múltiples resultados",
        "múltiples resultados",
        "Please choose",
        "¿Cuál es?",
        "cual es?",
        '"status": "ambiguous"',
        "'status': 'ambiguous'"
    ]
    
    validation_lower = validation_str.lower()
    return any(
        indicator.lower() in validation_lower if indicator.islower() else indicator in validation_str
        for indicator in ambiguity_indicators
    )


def _extract_entities(validation_str: str) -> dict:
    validated_entities = {
        "raw_validation": validation_str,
        "has_valid_entities": "NO_VALIDATION_NEEDED" not in validation_str.upper()
    }
    
    id_patterns = [
        (r'director.*?ID:\s*(\d+)', 'director_id'),
        (r'actor.*?ID:\s*(\d+)', 'actor_id'),
        (r'título.*?UID:\s*(\d+)', 'title_uid'),
        (r'title.*?UID:\s*(\d+)', 'title_uid'),
    ]
    
    for pattern, key in id_patterns:
        match = re.search(pattern, validation_str, re.IGNORECASE)
        if match:
            validated_entities[key] = int(match.group(1))
            print(f"[VALIDATION] Extraido {key}: {match.group(1)}")
    
    return validated_entities


async def validation_preprocessor_node(state: MainRouterState) -> MainRouterState:
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
    
    print("[VALIDATION] Ejecutando validacion con LLM...")
    
    validation_tools = [validate_title, validate_actor, validate_director]
    
    agent = Agent(
        model=MODEL_NODE_EXECUTOR,
        tools=validation_tools,
        system_prompt=VALIDATION_PREPROCESSOR_PROMPT
    )
    
    try:
        result = await agent.invoke_async(state['question'])
        validation_result = _extract_validation_result(result)
        
        print(f"[VALIDATION] Resultado de validacion:")
        print(f"   {validation_result[:300]}...")
        
        if _needs_user_input(validation_result):
            print("[VALIDATION] Ambiguedad detectada - requiere input del usuario")
            print("="*80 + "\n")
            
            return {
                **state,
                "validation_done": True,
                "validation_status": "ambiguous",
                "needs_user_input": True,
                "needs_validation": True,
                "validation_message": validation_result,
                "validated_entities": {
                    "status": "ambiguous",
                    "message": validation_result
                }
            }
        
        if "not_found" in validation_result.lower() or "no se encontró" in validation_result.lower():
            print("[VALIDATION] Entidad no encontrada")
            print("="*80 + "\n")
            
            return {
                **state,
                "validation_done": True,
                "validation_status": "not_found",
                "needs_user_input": True,
                "needs_validation": True,
                "validation_message": validation_result,
                "validated_entities": {
                    "status": "not_found",
                    "message": validation_result
                }
            }
        
        validated_entities = _extract_entities(validation_result)
        
        print("[VALIDATION] Validacion completada")
        print("="*80 + "\n")
        
        return {
            **state,
            "validation_done": True,
            "validation_status": "resolved",
            "needs_validation": True,
            "validated_entities": validated_entities
        }
        
    except Exception as e:
        print(f"[VALIDATION] Error en validacion: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            **state,
            "validation_done": True,
            "validation_status": "error",
            "needs_validation": False,
            "validated_entities": {"error": str(e)}
        }


def should_validate(state: MainRouterState) -> str:
    if state.get("needs_user_input", False):
        return "END"
    
    if state.get("validation_done", False):
        selected = state.get("selected_graph", "common")
        return ROUTING_MAP.get(selected, "common_graph")
    
    return "validation_preprocessor"