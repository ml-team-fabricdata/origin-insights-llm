# main_router/graph.py
"""
Grafo principal que orquesta todos los sub-grafos.

Flujo:
1. Usuario hace pregunta
2. Main Router clasifica → business/talent/content/platform/common
3. Se ejecuta el sub-grafo correspondiente
4. Se retorna la respuesta al usuario
"""

from langgraph.graph import StateGraph, END
from .state import MainRouterState
from .router import main_graph_router, route_to_graph
from .validation_preprocessor import validation_preprocessor_node, should_validate

# Importar los process_question de cada grafo
from src.strands.business.graph_core.graph import process_question as business_process
from src.strands.talent.graph_core.graph import process_question as talent_process
from src.strands.content.graph_core.graph import process_question as content_process
from src.strands.platform.graph_core.graph import process_question as platform_process
from src.strands.common.graph_core.graph import process_question as common_process


async def business_graph_node(state: MainRouterState) -> MainRouterState:
    """Ejecuta el grafo de business"""
    print("\n🏢 Ejecutando BUSINESS GRAPH...")
    result = await business_process(state['question'], max_iterations=3)
    
    # Verificar si necesita volver al main router
    if result.get('supervisor_decision') == 'VOLVER_MAIN_ROUTER':
        print("⚠️ Business graph no completó, volviendo al main router...")
        return {
            **state,
            "answer": result.get('accumulated_data', ''),
            "needs_rerouting": True,
            "previous_graph": "business_graph"
        }
    
    return {
        **state,
        "answer": result.get('answer', 'No se pudo obtener respuesta')
    }


async def talent_graph_node(state: MainRouterState) -> MainRouterState:
    """Ejecuta el grafo de talent"""
    print("\n🎬 Ejecutando TALENT GRAPH...")
    
    # Pasar entidades validadas al grafo de talent
    validated_entities = state.get('validated_entities', {})
    result = await talent_process(
        state['question'], 
        max_iterations=3,
        validated_entities=validated_entities
    )
    
    # Verificar si necesita volver al main router
    if result.get('supervisor_decision') == 'VOLVER_MAIN_ROUTER':
        print("⚠️ Talent graph no completó, volviendo al main router...")
        return {
            **state,
            "answer": result.get('accumulated_data', ''),
            "needs_rerouting": True,
            "previous_graph": "talent_graph"
        }
    
    return {
        **state,
        "answer": result.get('answer', 'No se pudo obtener respuesta')
    }


async def content_graph_node(state: MainRouterState) -> MainRouterState:
    """Ejecuta el grafo de content"""
    print("\n📺 Ejecutando CONTENT GRAPH...")
    result = await content_process(state['question'], max_iterations=3)
    
    # Verificar si necesita volver al main router
    if result.get('supervisor_decision') == 'VOLVER_MAIN_ROUTER':
        print("⚠️ Content graph no completó, volviendo al main router...")
        return {
            **state,
            "answer": result.get('accumulated_data', ''),
            "needs_rerouting": True,
            "previous_graph": "content_graph"
        }
    
    return {
        **state,
        "answer": result.get('answer', 'No se pudo obtener respuesta')
    }


async def platform_graph_node(state: MainRouterState) -> MainRouterState:
    """Ejecuta el grafo de platform"""
    print("\n🌐 Ejecutando PLATFORM GRAPH...")
    result = await platform_process(state['question'], max_iterations=3)
    
    # Verificar si necesita volver al main router
    if result.get('supervisor_decision') == 'VOLVER_MAIN_ROUTER':
        print("⚠️ Platform graph no completó, volviendo al main router...")
        return {
            **state,
            "answer": result.get('accumulated_data', ''),
            "needs_rerouting": True,
            "previous_graph": "platform_graph"
        }
    
    return {
        **state,
        "answer": result.get('answer', 'No se pudo obtener respuesta')
    }


async def common_graph_node(state: MainRouterState) -> MainRouterState:
    """Ejecuta el grafo de common"""
    print("\n⚙️ Ejecutando COMMON GRAPH...")
    result = await common_process(state['question'], max_iterations=3)
    
    # Verificar si necesita volver al main router
    if result.get('supervisor_decision') == 'VOLVER_MAIN_ROUTER':
        print("⚠️ Common graph no completó, volviendo al main router...")
        return {
            **state,
            "answer": result.get('accumulated_data', ''),
            "needs_rerouting": True,
            "previous_graph": "common_graph"
        }
    
    return {
        **state,
        "answer": result.get('answer', 'No se pudo obtener respuesta')
    }


def create_main_graph():
    """
    Crea el grafo principal que orquesta todos los sub-grafos.
    
    Estructura:
    START → main_router → validation_preprocessor → [business|talent|content|platform|common]_graph → END o main_router
    
    El validation_preprocessor valida entidades (títulos, actores, directores) antes de ejecutar los grafos.
    Si un sub-grafo no completa, vuelve al main_router para reclasificar.
    """
    
    graph = StateGraph(MainRouterState)
    
    # Agregar nodos
    graph.add_node("main_router", main_graph_router)
    graph.add_node("validation_preprocessor", validation_preprocessor_node)
    graph.add_node("business_graph", business_graph_node)
    graph.add_node("talent_graph", talent_graph_node)
    graph.add_node("content_graph", content_graph_node)
    graph.add_node("platform_graph", platform_graph_node)
    graph.add_node("common_graph", common_graph_node)
    
    # Punto de entrada
    graph.set_entry_point("main_router")
    
    # Router condicional desde main_router → puede ir a validación o directo al grafo
    graph.add_conditional_edges(
        "main_router",
        should_validate,
        {
            "validation_preprocessor": "validation_preprocessor",
            "business_graph": "business_graph",
            "talent_graph": "talent_graph",
            "content_graph": "content_graph",
            "platform_graph": "platform_graph",
            "common_graph": "common_graph"
        }
    )
    
    # Desde validation_preprocessor → ir al grafo correspondiente o END si hay ambigüedad
    graph.add_conditional_edges(
        "validation_preprocessor",
        route_to_graph,
        {
            "business_graph": "business_graph",
            "talent_graph": "talent_graph",
            "content_graph": "content_graph",
            "platform_graph": "platform_graph",
            "common_graph": "common_graph",
            "END": END  # Si necesita input del usuario
        }
    )
    
    # Función para decidir si volver al main_router o terminar
    def should_reroute(state: MainRouterState) -> str:
        """Decide si el sub-grafo debe volver al main_router o terminar"""
        if state.get("needs_rerouting", False):
            # Verificar límite de re-routings para evitar loops infinitos
            rerouting_count = state.get("rerouting_count", 0)
            if rerouting_count >= 2:  # Máximo 2 re-routings
                print("⚠️ Límite de re-routings alcanzado, terminando...")
                return "END"
            print(f"🔄 Re-routing #{rerouting_count + 1} al main_router...")
            return "main_router"
        return "END"
    
    # Los sub-grafos pueden volver al main_router o terminar
    graph.add_conditional_edges(
        "business_graph",
        should_reroute,
        {
            "main_router": "main_router",
            "END": END
        }
    )
    
    graph.add_conditional_edges(
        "talent_graph",
        should_reroute,
        {
            "main_router": "main_router",
            "END": END
        }
    )
    
    graph.add_conditional_edges(
        "content_graph",
        should_reroute,
        {
            "main_router": "main_router",
            "END": END
        }
    )
    
    graph.add_conditional_edges(
        "platform_graph",
        should_reroute,
        {
            "main_router": "main_router",
            "END": END
        }
    )
    
    graph.add_conditional_edges(
        "common_graph",
        should_reroute,
        {
            "main_router": "main_router",
            "END": END
        }
    )
    
    return graph.compile()


async def process_question_main(
    question: str, 
    max_iterations: int = 3,
    resolved_entity: dict = None
) -> MainRouterState:
    """
    Función principal para procesar preguntas.
    
    Esta es la función que debes usar desde el exterior.
    
    Args:
        question: Pregunta del usuario
        max_iterations: Máximo de iteraciones para cada sub-grafo
        resolved_entity: Entidad resuelta por el usuario (cuando hubo ambigüedad)
                        Formato: {"type": "title/actor/director", "id": "...", "name": "..."}
        
    Returns:
        MainRouterState con la respuesta final
        
    Example:
        >>> # Primera llamada
        >>> result = await process_question_main("¿De qué año es The Matrix?")
        >>> if result.get('needs_user_input'):
        >>>     # Usuario elige opción 1
        >>>     result = await process_question_main(
        >>>         "¿De qué año es The Matrix?",
        >>>         resolved_entity={"type": "title", "uid": "123", "title": "The Matrix (1999)"}
        >>>     )
    """
    
    initial_state: MainRouterState = {
        "question": question,
        "answer": "",
        "selected_graph": None,
        "routing_done": False,
        "error": None,
        "needs_rerouting": False,
        "previous_graph": None,
        "rerouting_count": 0,
        "validation_done": False,
        "validated_entities": None,
        "needs_validation": False,
        "needs_user_input": False,
        "validation_message": None
    }
    
    # Si el usuario ya resolvió la ambigüedad, marcar como validado
    if resolved_entity:
        initial_state["validation_done"] = True
        initial_state["needs_validation"] = True
        initial_state["validated_entities"] = {
            "status": "resolved",
            "result": resolved_entity
        }
    
    graph = create_main_graph()
    result = await graph.ainvoke(initial_state)
    
    # Si necesita input del usuario (ambigüedad), retornar el mensaje de validación
    if result.get("needs_user_input"):
        result["answer"] = result.get("validation_message", "Multiple options found. Please clarify.")
    
    return result


async def process_question_main_streaming(question: str, max_iterations: int = 3):
    """
    Versión con streaming de eventos.
    
    Útil para ver el progreso en tiempo real.
    """
    
    initial_state: MainRouterState = {
        "question": question,
        "answer": "",
        "selected_graph": None,
        "routing_done": False,
        "error": None,
        "needs_rerouting": False,
        "previous_graph": None,
        "rerouting_count": 0,
        "validation_done": False,
        "validated_entities": None,
        "needs_validation": False
    }
    
    graph = create_main_graph()
    
    async for event in graph.astream(initial_state):
        node_name = list(event.keys())[0]
        state_output = event[node_name]
        
        print(f"\n📍 Node: {node_name}")
        if node_name == "main_router":
            print(f"   Selected: {state_output.get('selected_graph', 'N/A')}")
        elif "graph" in node_name:
            print(f"   Answer preview: {state_output.get('answer', 'N/A')[:100]}...")
        print("---")
    
    return state_output
