from langgraph.graph import StateGraph, END
from .state import MainRouterState
from .advanced_router import advanced_router_node
from .clarifier import clarifier_node
from .parallel_executor import parallel_executor_node, aggregator_node
from .validation_preprocessor import validation_preprocessor_node
from .specialized_nodes import (
    disambiguation_node,
    not_found_responder_node,
    error_handler_node,
    responder_formatter_node
)
from .routing_gates import (
    route_from_router,
    route_from_validation,
    route_from_domain_graph,
    route_from_aggregator
)

from src.strands.business.graph_core.graph import process_question as business_process
from src.strands.talent.graph_core.graph import process_question as talent_process
from src.strands.content.graph_core.graph import process_question as content_process
from src.strands.platform.graph_core.graph import process_question as platform_process
from src.strands.common.graph_core.graph import process_question as common_process


GRAPH_PROCESSORS = {
    "business": business_process,
    "talent": talent_process,
    "content": content_process,
    "platform": platform_process,
    "common": common_process
}


async def domain_graph_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print("🎬 DOMAIN GRAPH EXECUTOR")
    print("="*80)
    
    selected_graph = state.get("selected_graph", "common")
    print(f"[DOMAIN] Ejecutando: {selected_graph}")
    
    processor = GRAPH_PROCESSORS.get(selected_graph)
    if not processor:
        print(f"[DOMAIN] ❌ Grafo no encontrado: {selected_graph}")
        return {
            **state,
            "error": f"Graph processor not found: {selected_graph}",
            "domain_graph_status": "error"
        }
    
    validated_entities = state.get('validated_entities', {})
    
    try:
        if selected_graph in ["talent", "content"]:
            result = await processor(
                state['question'],
                max_iterations=3,
                validated_entities=validated_entities
            )
        else:
            result = await processor(
                state['question'],
                max_iterations=3
            )
        
        supervisor_decision = result.get('supervisor_decision', '')
        
        if 'VOLVER_MAIN_ROUTER' in supervisor_decision or 'return_to_main_router' in supervisor_decision.lower():
            print(f"[DOMAIN] 🔄 {selected_graph} solicita re-routing")
            return {
                **state,
                "answer": result.get('accumulated_data', ''),
                "needs_rerouting": True,
                "domain_graph_status": "not_my_scope"
            }
        
        answer = result.get('answer', result.get('accumulated_data', ''))
        
        if not answer or len(answer) < 50:
            print(f"[DOMAIN] ⚠️ Respuesta insuficiente ({len(answer)} chars)")
            return {
                **state,
                "answer": answer,
                "needs_rerouting": True,
                "domain_graph_status": "not_my_scope"
            }
        
        print(f"[DOMAIN] ✅ Completado exitosamente ({len(answer)} chars)")
        print("="*80 + "\n")
        
        return {
            **state,
            "answer": answer,
            "domain_graph_status": "success"
        }
        
    except Exception as e:
        print(f"[DOMAIN] ❌ Error: {e}")
        print("="*80 + "\n")
        return {
            **state,
            "error": str(e),
            "domain_graph_status": "error"
        }


def create_advanced_graph():
    graph = StateGraph(MainRouterState)
    
    graph.add_node("advanced_router", advanced_router_node)
    graph.add_node("clarifier", clarifier_node)
    graph.add_node("parallel_executor", parallel_executor_node)
    graph.add_node("aggregator", aggregator_node)
    graph.add_node("validation_preprocessor", validation_preprocessor_node)
    graph.add_node("domain_graph", domain_graph_node)
    graph.add_node("disambiguation", disambiguation_node)
    graph.add_node("not_found_responder", not_found_responder_node)
    graph.add_node("error_handler", error_handler_node)
    graph.add_node("responder_formatter", responder_formatter_node)
    
    graph.set_entry_point("advanced_router")
    
    # Router → Clarifier o Validation
    graph.add_conditional_edges(
        "advanced_router",
        route_from_router,
        {
            "clarifier": "clarifier",
            "validation_preprocessor": "validation_preprocessor"
        }
    )
    
    graph.add_edge("clarifier", END)
    
    # Validation → Parallel/Domain/Disambiguation/NotFound
    graph.add_conditional_edges(
        "validation_preprocessor",
        route_from_validation,
        {
            "parallel_executor": "parallel_executor",
            "domain_graph": "domain_graph",
            "disambiguation": "disambiguation",
            "not_found_responder": "not_found_responder"
        }
    )
    
    # Parallel → Aggregator → Domain
    graph.add_edge("parallel_executor", "aggregator")
    
    graph.add_conditional_edges(
        "aggregator",
        route_from_aggregator,
        {
            "domain_graph": "domain_graph",
            "error_handler": "error_handler"
        }
    )
    
    graph.add_edge("disambiguation", END)
    graph.add_edge("not_found_responder", END)
    
    graph.add_conditional_edges(
        "domain_graph",
        route_from_domain_graph,
        {
            "responder_formatter": "responder_formatter",
            "advanced_router": "advanced_router",
            "clarifier": "clarifier",
            "error_handler": "error_handler"
        }
    )
    
    graph.add_edge("responder_formatter", END)
    graph.add_edge("error_handler", END)
    
    return graph.compile()


async def process_question_advanced(
    question: str,
    max_iterations: int = 3,
    max_hops: int = 2
) -> MainRouterState:
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
        "validation_message": None,
        "validation_status": None,
        "skip_validation": False,
        "routing_confidence": 0.0,
        "routing_candidates": [],
        "visited_graphs": [],
        "max_hops": max_hops,
        "parallel_execution": False,
        "parallel_results": [],
        "aggregated_result": None,
        "needs_clarification": False,
        "clarification_message": None,
        "domain_graph_status": None
    }
    
    graph = create_advanced_graph()
    result = await graph.ainvoke(initial_state)
    
    return result


async def process_question_advanced_streaming(
    question: str,
    max_iterations: int = 3,
    max_hops: int = 2
):
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
        "validation_message": None,
        "validation_status": None,
        "skip_validation": False,
        "routing_confidence": 0.0,
        "routing_candidates": [],
        "visited_graphs": [],
        "max_hops": max_hops,
        "parallel_execution": False,
        "parallel_results": [],
        "aggregated_result": None,
        "needs_clarification": False,
        "clarification_message": None,
        "domain_graph_status": None
    }
    
    graph = create_advanced_graph()
    
    async for event in graph.astream(initial_state):
        node_name = list(event.keys())[0]
        state_output = event[node_name]
        
        print(f"\n🔹 Node: {node_name}")
        if node_name == "advanced_router":
            print(f"   Selected: {state_output.get('selected_graph', 'N/A')}")
            print(f"   Confidence: {state_output.get('routing_confidence', 0.0):.2f}")
        elif node_name == "domain_graph":
            print(f"   Status: {state_output.get('domain_graph_status', 'N/A')}")
        print("---")
    
    return state_output
