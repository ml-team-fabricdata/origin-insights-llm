# main_router/validation_preprocessor.py
"""
Nodo de validación que se ejecuta ANTES de los grafos específicos.
Valida títulos, actores y directores mencionados en la pregunta.
"""

from strands import Agent
from src.strands.utils.config import MODEL_NODE_EXECUTOR
from .state import MainRouterState

# Importar tools de validación
from src.sql.modules.common.validation import (
    validate_title,
    validate_actor,
    validate_director
)

from src.strands.main_router.prompts import VALIDATION_PREPROCESSOR_PROMPT


async def detect_entities_in_question(question: str) -> dict:
    """
    Detecta qué tipo de entidades están presentes en la pregunta.
    
    Returns:
        dict con keys: has_title, has_actor, has_director, entities
    """
    question_lower = question.lower()
    
    result = {
        "has_title": False,
        "has_actor": False,
        "has_director": False,
        "entities": []
    }
    
    # Patrones para detectar menciones
    title_keywords = ["película", "serie", "film", "movie", "show", "título"]
    actor_keywords = ["actor", "actriz", "protagonista", "actuó", "actúa"]
    director_keywords = ["director", "dirigió", "dirige", "dirigida por"]
    
    # Detectar si menciona título
    if any(kw in question_lower for kw in title_keywords):
        result["has_title"] = True
    
    # Detectar si menciona actor
    if any(kw in question_lower for kw in actor_keywords):
        result["has_actor"] = True
    
    # Detectar si menciona director
    if any(kw in question_lower for kw in director_keywords):
        result["has_director"] = True
    
    # Detectar nombres propios (capitalización)
    # Buscar palabras que empiecen con mayúscula (posibles nombres)
    words = question.split()
    potential_names = [w for w in words if w and w[0].isupper() and len(w) > 2]
    
    if potential_names:
        # Si hay nombres propios, probablemente hay entidades
        if not result["has_title"] and not result["has_actor"] and not result["has_director"]:
            # Asumir que podría ser título o persona
            result["has_title"] = True
        result["entities"] = potential_names
    
    return result


async def validation_preprocessor_node(state: MainRouterState) -> MainRouterState:
    """
    Nodo que valida entidades (títulos, actores, directores) antes de procesar.
    
    Se ejecuta después del main_router y antes de los grafos específicos.
    """
    
    print("\n" + "="*80)
    print("🔍 VALIDATION PREPROCESSOR")
    print("="*80)
    print(f"📝 Pregunta: {state['question']}")
    
    # Si ya se validó, saltar
    if state.get("validation_done", False):
        print("[VALIDATION] Ya validado, saltando...")
        return state
    
    # En lugar de detectar heurísticamente, SIEMPRE dar todas las tools al LLM
    # y dejar que el prompt decida si necesita validar o no
    print(f"[VALIDATION] 🤖 Ejecutando validación con LLM...")
    
    # Dar TODAS las tools de validación al agent
    validation_tools = [validate_title, validate_actor, validate_director]
    
    agent = Agent(
        model=MODEL_NODE_EXECUTOR,
        tools=validation_tools,
        system_prompt=VALIDATION_PREPROCESSOR_PROMPT
    )
    
    try:
        result = await agent.invoke_async(state['question'])
        
        # Extraer resultado correctamente
        if isinstance(result, dict):
            validation_result = str(result.get('message', result))
        else:
            validation_result = str(getattr(result, "message", result))
        
        print(f"[VALIDATION] 📦 Resultado de validación:")
        # Asegurar que validation_result es string antes de hacer slice
        validation_str = str(validation_result)
        print(f"   {validation_str[:300]}...")
        
        # Detectar si hay ambigüedad que requiere input del usuario
        needs_user_input = (
            "Multiple matches found" in validation_str or
            "Múltiples resultados" in validation_str or
            "múltiples resultados" in validation_str.lower() or
            "Please choose" in validation_str or
            "¿Cuál es?" in validation_str or
            "cual es?" in validation_str.lower() or
            '"status": "ambiguous"' in validation_str or
            "'status': 'ambiguous'" in validation_str
        )
        
        if needs_user_input:
            print(f"[VALIDATION] ⚠️ Ambigüedad detectada - requiere input del usuario")
            print("="*80 + "\n")
            
            # Retornar con flag especial para que el sistema pida clarificación
            return {
                **state,
                "validation_done": False,  # No completada, necesita clarificación
                "needs_user_input": True,
                "needs_validation": True,
                "validation_message": validation_str,
                "validated_entities": {
                    "status": "ambiguous",
                    "message": validation_str
                }
            }
        
        # Parsear resultado para extraer entidades validadas
        validated_entities = {
            "raw_validation": validation_str,
            "has_valid_entities": "NO_VALIDATION_NEEDED" not in validation_str.upper()
        }
        
        print(f"[VALIDATION] ✅ Validación completada")
        print("="*80 + "\n")
        
        return {
            **state,
            "validation_done": True,
            "needs_validation": True,
            "validated_entities": validated_entities
        }
        
    except Exception as e:
        print(f"[VALIDATION] ❌ Error en validación: {e}")
        import traceback
        traceback.print_exc()
        # Continuar sin validación en caso de error
        return {
            **state,
            "validation_done": True,
            "needs_validation": False,
            "validated_entities": {"error": str(e)}
        }


def should_validate(state: MainRouterState) -> str:
    """
    Decide si debe ejecutar validación o saltar directo al grafo.
    
    Returns:
        "validate" si necesita validación
        "END" si necesita input del usuario (ambigüedad)
        nombre del grafo si validación completada
    """
    # Si necesita input del usuario, terminar y retornar mensaje
    if state.get("needs_user_input", False):
        return "END"
    
    # Si ya se validó, ir directo al grafo
    if state.get("validation_done", False):
        selected = state.get("selected_graph", "common")
        routing_map = {
            "business": "business_graph",
            "talent": "talent_graph",
            "content": "content_graph",
            "platform": "platform_graph",
            "common": "common_graph"
        }
        return routing_map.get(selected, "common_graph")
    
    # Si no se ha validado, ir a validación
    return "validation_preprocessor"
