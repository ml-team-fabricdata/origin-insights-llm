# main_router/router.py
from strands import Agent
from src.strands.utils.config import MODEL_CLASSIFIER
from .state import MainRouterState
from .prompts import MAIN_ROUTER_PROMPT
from typing import Literal

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
