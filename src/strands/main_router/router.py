# main_router/router.py
import asyncio
from strands import Agent
from src.strands.utils.config import MODEL_CLASSIFIER
from .state import MainRouterState
from .prompts import MAIN_ROUTER_PROMPT
from typing import Literal, Tuple

async def main_graph_router(state: MainRouterState) -> MainRouterState:
    """
    Router principal que decide a qué grafo enviar la pregunta.
    
    Este nodo se ejecuta ANTES de cualquier otro grafo y decide si la pregunta
    debe ir a: business, talent, content, platform o common.
    
    Si un grafo no completó (needs_rerouting=True), reclasifica la pregunta.
    """
    
    print("\n" + "="*80)
    print("🎯 MAIN GRAPH ROUTER")
    print("="*80)
    print(f"📝 Pregunta: {state['question']}")
    
    # Si es un rerouting, incrementar contador y resetear flags
    if state.get("needs_rerouting", False):
        rerouting_count = state.get("rerouting_count", 0) + 1
        previous_graph = state.get("previous_graph", "unknown")
        print(f"🔄 REROUTING #{rerouting_count} desde {previous_graph}")
        state = {
            **state,
            "needs_rerouting": False,
            "routing_done": False,
            "rerouting_count": rerouting_count
        }
    
    if state.get("routing_done") and not state.get("needs_rerouting", False):
        print("[ROUTER] Ya clasificado, saltando...")
        return state
    
    # Crear agent clasificador
    agent = Agent(
        model=MODEL_CLASSIFIER,
        system_prompt=MAIN_ROUTER_PROMPT
    )
    
    # Clasificar la pregunta
    response = await agent.invoke_async(state['question'])
    
    # Extraer decisión
    if isinstance(response, dict):
        decision = str(response.get('message', response)).strip().upper()
    else:
        decision = str(getattr(response, "message", response)).strip().upper()
    
    print(f"[ROUTER] Decisión raw: {decision}")
    
    # Validar y normalizar
    valid_graphs = ["BUSINESS", "TALENT", "CONTENT", "PLATFORM", "COMMON"]
    
    if decision not in valid_graphs:
        # Intentar extraer la palabra clave
        for graph in valid_graphs:
            if graph in decision:
                decision = graph
                break
        else:
            # Fallback: analizar keywords en la pregunta
            question_lower = state['question'].lower()
            if any(word in question_lower for word in ["precio", "cuesta", "cost", "ranking", "popular", "exclusiv"]):
                decision = "BUSINESS"
            elif any(word in question_lower for word in ["actor", "actriz", "director", "dirigid", "filmograf"]):
                decision = "TALENT"
            elif any(word in question_lower for word in ["donde", "ver", "disponible", "plataforma", "netflix", "disney", "hbo"]):
                decision = "PLATFORM"
            elif any(word in question_lower for word in ["año", "duraci", "rating", "género", "imdb"]):
                decision = "CONTENT"
            else:
                decision = "COMMON"  # Fallback final
    
    selected_graph = decision.lower()
    print(f"[ROUTER] ✅ Grafo seleccionado: {selected_graph}")
    print("="*80 + "\n")
    
    return {
        **state,
        "selected_graph": selected_graph,
        "routing_done": True
    }


async def parallel_routing_and_validation_node(state: MainRouterState) -> MainRouterState:
    """
    Nodo que ejecuta routing y validación en paralelo para mejorar performance.
    
    Este nodo reemplaza la ejecución secuencial de:
    1. main_graph_router
    2. validation_preprocessor_node
    
    Ejecutándolos en paralelo con asyncio.gather().
    """
    print("\n" + "="*80)
    print("⚡ PARALLEL ROUTING & VALIDATION")
    print("="*80)
    print(f"📝 Pregunta: {state['question']}")
    
    # Si ya se ejecutó, saltar
    if state.get("routing_done") and state.get("validation_done"):
        print("[PARALLEL] Ya ejecutado, saltando...")
        return state
    
    # Importar aquí para evitar circular imports
    from .validation_preprocessor import validation_preprocessor_node
    
    # Crear tasks para ejecutar en paralelo
    print("🚀 Iniciando routing y validación en paralelo...")
    routing_task = asyncio.create_task(main_graph_router(state))
    validation_task = asyncio.create_task(validation_preprocessor_node(state))
    
    # Esperar ambos en paralelo
    routing_result, validation_result = await asyncio.gather(
        routing_task,
        validation_task,
        return_exceptions=True
    )
    
    # Manejar errores
    if isinstance(routing_result, Exception):
        print(f"❌ Error en routing: {routing_result}")
        routing_result = {**state, "selected_graph": "common", "routing_done": True}
    
    if isinstance(validation_result, Exception):
        print(f"❌ Error en validación: {validation_result}")
        validation_result = {**state, "validation_done": True, "needs_validation": False}
    
    # Combinar resultados de ambos nodos
    # IMPORTANTE: routing_result debe ir DESPUÉS de validation_result
    # para que selected_graph no sea sobrescrito
    combined_state = {
        **state,
        **validation_result,  # Primero validación
        **routing_result      # Luego routing (para que selected_graph prevalezca)
    }
    
    # Debug: verificar que selected_graph esté presente
    selected = combined_state.get('selected_graph', 'N/A')
    if selected == 'N/A' or selected is None:
        print(f"⚠️  WARNING: selected_graph es {selected}, usando fallback")
        print(f"   routing_result keys: {routing_result.keys() if isinstance(routing_result, dict) else 'NOT A DICT'}")
        print(f"   validation_result keys: {validation_result.keys() if isinstance(validation_result, dict) else 'NOT A DICT'}")
        # Fallback: extraer directamente de routing_result
        if isinstance(routing_result, dict) and 'selected_graph' in routing_result:
            combined_state['selected_graph'] = routing_result['selected_graph']
            selected = routing_result['selected_graph']
    
    print(f"✅ Routing completado: {selected}")
    print(f"✅ Validación completada: {combined_state.get('validation_done', False)}")
    print("="*80 + "\n")
    
    return combined_state


def route_to_graph(state: MainRouterState) -> Literal["business_graph", "talent_graph", "content_graph", "platform_graph", "common_graph", "END"]:
    """
    Función de routing condicional para LangGraph.
    Retorna el nombre del nodo del grafo seleccionado o END si necesita input del usuario.
    """
    # Si necesita input del usuario (ambigüedad), terminar
    if state.get("needs_user_input", False):
        return "END"
    
    selected = state.get("selected_graph", "common")
    
    routing_map = {
        "business": "business_graph",
        "talent": "talent_graph",
        "content": "content_graph",
        "platform": "platform_graph",
        "common": "common_graph"
    }
    
    return routing_map.get(selected, "common_graph")
