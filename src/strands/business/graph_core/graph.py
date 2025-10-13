# content/graph_core/graph.py
from langgraph.graph import StateGraph, END
from .state import State, create_initial_state
from .supervisor import (
    business_classifier,
    main_supervisor,
    route_from_main_supervisor,
    format_response
)
from src.strands.business.nodes.intelligence import intelligence_node
from src.strands.business.nodes.rankings import rankings_node
from src.strands.business.nodes.pricing import pricing_node

def create_streaming_graph():
    """Crea el grafo de procesamiento con supervisión para CONTENT"""
    
    # Inicializar grafo
    graph = StateGraph(State)
    
    # Agregar nodos
    graph.add_node("main_supervisor", main_supervisor)
    graph.add_node("business_classifier", business_classifier)
    graph.add_node("intelligence_node", intelligence_node)
    graph.add_node("rankings_node", rankings_node)
    graph.add_node("pricing_node", pricing_node)
    graph.add_node("format_response", format_response)
    
    # Flujo: START → main_supervisor → business_classifier → nodes → format → END
    graph.set_entry_point("main_supervisor")
    
    # Supervisor decide si necesita clasificar, formatear, o volver al main router
    graph.add_conditional_edges(
        "main_supervisor",
        route_from_main_supervisor,
        {
            "business_classifier": "business_classifier",
            "format_response": "format_response",
            "return_to_main_router": END  # Termina para volver al main router
        }
    )
    
    def route_from_classifier(state: State) -> str:
        """Ruta desde classifier a rankings, pricing o intelligence"""
        task = state.get("task", "").lower()
        if task == "rankings":
            return "rankings_node"
        elif task == "pricing":
            return "pricing_node"
        else:  # intelligence fallback
            return "intelligence_node"
    
    graph.add_conditional_edges(
        "business_classifier",
        route_from_classifier,
        {
            "rankings_node": "rankings_node",
            "pricing_node": "pricing_node",
            "intelligence_node": "intelligence_node"
        }
    )
    
    # Después de cada node, VOLVER al supervisor para evaluar
    graph.add_edge("rankings_node", "main_supervisor")
    graph.add_edge("pricing_node", "main_supervisor")
    graph.add_edge("intelligence_node", "main_supervisor")
    
    # Formatear respuesta es el paso final
    graph.add_edge("format_response", END)
    
    return graph.compile()


# Uso del grafo
async def process_question(question: str, max_iterations: int = 3) -> State:
    """Procesa una pregunta a través del grafo"""
    
    # Crear estado inicial
    initial_state = create_initial_state(question, max_iterations)
    
    # Crear y ejecutar grafo
    graph = create_streaming_graph()
    
    # Ejecutar
    result = await graph.ainvoke(initial_state)
    
    return result


# Ejemplo de uso con streaming
async def process_question_streaming(question: str, max_iterations: int = 3):
    """Procesa una pregunta con streaming de eventos"""
    
    initial_state = create_initial_state(question, max_iterations)
    graph = create_streaming_graph()
    
    async for event in graph.astream(initial_state):
        # event es un dict con formato: {node_name: state_output}
        node_name = list(event.keys())[0]
        state_output = event[node_name]
        
        # Puedes emitir eventos aquí para UI
        print(f"Node: {node_name}")
        print(f"Tool calls: {state_output.get('tool_calls_count', 0)}")
        print(f"Decision: {state_output.get('supervisor_decision', 'N/A')}")
        print("---")
    
    return state_output

