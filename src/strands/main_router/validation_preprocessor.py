# main_router/validation_preprocessor.py
"""
Nodo de validación que se ejecuta ANTES de los grafos específicos.
Valida títulos, actores y directores mencionados en la pregunta.
"""

import asyncio
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
    
    # Si el grafo no requiere validación, saltar
    if state.get("skip_validation", False):
        print("[VALIDATION] ⏭️  Validación no requerida para este grafo, saltando...")
        return {
            **state,
            "validation_done": True,
            "needs_validation": False,
            "validation_status": "resolved"
        }
    
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
                "validation_done": True,
                "needs_user_input": True,
                "needs_validation": True,
                "validation_status": "ambiguous",
                "validation_message": validation_str,
                "answer": f"🔍 Disambiguation Required:\n\n{validation_str}",
                "validated_entities": {
                    "status": "ambiguous",
                    "message": validation_str
                }
            }
        
        # Detectar si no se encontró la entidad
        if "not_found" in validation_str.lower() or "no se encontró" in validation_str.lower() or "no se encontro" in validation_str.lower():
            print(f"[VALIDATION] ❌ Entidad no encontrada")
            print("="*80 + "\n")
            
            return {
                **state,
                "validation_done": True,
                "needs_user_input": True,
                "needs_validation": True,
                "validation_status": "not_found",
                "validation_message": validation_str,
                "answer": f"❌ Entity Not Found:\n\n{validation_str}",
                "validated_entities": {
                    "status": "not_found",
                    "message": validation_str
                }
            }
        
        # Parsear resultado para extraer entidades validadas
        import re
        
        validated_entities = {
            "raw_validation": validation_str,
            "has_valid_entities": "NO_VALIDATION_NEEDED" not in validation_str.upper()
        }
        
        # Extraer IDs estructurados usando regex
        # Formato esperado: "validado (ID: 123456)" o "ID: 123456"
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
                print(f"[VALIDATION] 📌 Extraído {key}: {match.group(1)}")
        
        print(f"[VALIDATION] ✅ Validación completada")
        print("="*80 + "\n")
        
        return {
            **state,
            "validation_done": True,
            "needs_validation": True,
            "validation_status": "resolved",
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
