import time
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from .state import MainRouterState
from .advanced_router import advanced_router_node
from .clarifier import clarifier_node
from .parallel_executor import parallel_executor_node, aggregator_node
from .validation_preprocessor import validation_preprocessor_node
from .specialized_nodes import (
    user_selection_resolver_node,
    disambiguation_node,
    not_found_responder_node,
    error_handler_node,
    responder_formatter_node
)
from app.strands.core.nodes.supervisor_helpers import format_response
from .routing_gates import (
    route_from_router,
    route_from_validation,
    route_from_domain_graph,
    route_from_aggregator
)
from .telemetry import TelemetryLogger, print_telemetry_summary

from app.strands.business.graph_core.graph import process_question as business_process_question
from app.strands.talent.graph_core.graph import process_question as talent_process_question
from app.strands.content.graph_core.graph import process_question as content_process_question
from app.strands.platform.graph_core.graph import process_question as platform_process_question
from app.strands.common.graph_core.graph import process_question as common_process_question

checkpointer = MemorySaver()

GRAPH_PROCESSORS = {
    "business": business_process_question,
    "talent": talent_process_question,
    "content": content_process_question,
    "platform": platform_process_question,
    "common": common_process_question
}


def _print_tool_execution_times(tool_times: dict):
    if not tool_times:
        return
    
    print(f"\n[DOMAIN] Tool Execution Times:")
    for tool_name, tool_time in tool_times.items():
        print(f"  - {tool_name}: {tool_time:.2f}s")


def _handle_rerouting_request(state: MainRouterState, result: dict, tool_times: dict) -> MainRouterState:
    print(f"[DOMAIN] {state.get('selected_graph')} solicita re-routing")
    return {
        **state,
        "answer": result.get('accumulated_data', ''),
        "needs_rerouting": True,
        "domain_graph_status": "not_my_scope",
        "tool_execution_times": tool_times
    }


def _handle_insufficient_answer(state: MainRouterState, answer: str, tool_times: dict) -> MainRouterState:
    print(f"[DOMAIN] Respuesta insuficiente ({len(answer)} chars)")
    return {
        **state,
        "answer": answer,
        "needs_rerouting": True,
        "domain_graph_status": "not_my_scope",
        "tool_execution_times": tool_times
    }


def _handle_success(state: MainRouterState, answer: str, tool_times: dict) -> MainRouterState:
    print(f"[DOMAIN] Completado exitosamente ({len(answer)} chars)")
    print("="*80 + "\n")
    return {
        **state,
        "answer": answer,
        "domain_graph_status": "success",
        "tool_execution_times": tool_times
    }


def _handle_error(state: MainRouterState, error: Exception) -> MainRouterState:
    print(f"[DOMAIN] Error: {error}")
    print("="*80 + "\n")
    return {
        **state,
        "error": str(error),
        "domain_graph_status": "error"
    }


def _should_reroute(supervisor_decision: str) -> bool:
    return 'VOLVER_MAIN_ROUTER' in supervisor_decision or 'return_to_main_router' in supervisor_decision.lower()


async def domain_graph_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print("DOMAIN GRAPH EXECUTOR")
    print("="*80)
    
    selected_graph = state.get("selected_graph", "common")
    visited_graphs = state.get("visited_graphs", [])
    current_hop = len(visited_graphs)
    max_hops = state.get("max_hops", 3)
    
    print(f"[DOMAIN] Ejecutando: {selected_graph} (hop {current_hop}/{max_hops})")
    print(f"[DOMAIN] Visited: {visited_graphs}")
    
    # SAFETY: Si ya visitamos este grafo 2+ veces, forzar success
    graph_visit_count = visited_graphs.count(selected_graph)
    if graph_visit_count >= 2:
        print(f"[DOMAIN] ⚠️ SAFETY: {selected_graph} visitado {graph_visit_count} veces. Forzando success.")
        return {
            **state,
            "answer": state.get("answer", "No pude obtener una respuesta completa después de múltiples intentos."),
            "domain_graph_status": "success",
            "tool_execution_times": {}
        }
    
    processor = GRAPH_PROCESSORS.get(selected_graph)
    if not processor:
        print(f"[DOMAIN] Grafo no encontrado: {selected_graph}")
        return {
            **state,
            "error": f"Graph processor not found: {selected_graph}",
            "domain_graph_status": "error"
        }
    
    validated_entities = state.get('validated_entities', {})
    
    start_time = time.time()
    
    kwargs = {"max_iterations": 3}
    if selected_graph in ["talent", "content", "platform", "business"]:
        kwargs["validated_entities"] = validated_entities
    
    result = await processor(state['question'], **kwargs)
    execution_time = time.time() - start_time
    
    tool_times = result.get('tool_execution_times', {})
    _print_tool_execution_times(tool_times)
    
    print(f"[DOMAIN] Tiempo total de ejecución: {execution_time:.2f}s")
    
    supervisor_decision = result.get('supervisor_decision', '')
    print(f"[DOMAIN] Supervisor decision: {supervisor_decision}")
    
    if _should_reroute(supervisor_decision):
        return _handle_rerouting_request(state, result, tool_times)
    
    answer = result.get('answer', result.get('accumulated_data', ''))
    
    # Si el supervisor decidió COMPLETO, respetar esa decisión incluso si la respuesta es corta
    # Una respuesta de "no hay datos" es válida y completa
    if supervisor_decision.upper() == "COMPLETO":
        print(f"[DOMAIN] Supervisor aprobó respuesta (COMPLETO), aceptando resultado")
        return _handle_success(state, answer, tool_times)
    
    # Solo verificar longitud si el supervisor NO aprobó explícitamente
    if not answer or len(answer) < 50:
        return _handle_insufficient_answer(state, answer, tool_times)
    
    return _handle_success(state, answer, tool_times)


async def format_response_node(state: MainRouterState) -> MainRouterState:
    result = await format_response(state)
    return {
        **state,
        "answer": result.get("answer", state.get("answer", ""))
    }


def _add_nodes(graph: StateGraph):
    nodes = {
        "user_selection_resolver": user_selection_resolver_node,
        "advanced_router": advanced_router_node,
        "clarifier": clarifier_node,
        "parallel_executor": parallel_executor_node,
        "aggregator": aggregator_node,
        "validation_preprocessor": validation_preprocessor_node,
        "domain_graph": domain_graph_node,
        "format_response": format_response_node,
        "disambiguation": disambiguation_node,
        "not_found_responder": not_found_responder_node,
        "error_handler": error_handler_node,
        "responder_formatter": responder_formatter_node
    }
    
    for name, node_func in nodes.items():
        graph.add_node(name, node_func)


def _route_from_router_with_disambiguation(state: MainRouterState) -> str:
    # Solo ir a resolver selección si:
    # 1. Hay disambiguación pendiente
    # 2. HAY opciones guardadas (no es la primera pregunta)
    pending = state.get("pending_disambiguation", False)
    options = state.get("disambiguation_options", [])
    
    if pending and options and len(options) > 0:
        print("[ROUTER] Pending disambiguation detected, going to resolver...")
        return "user_selection_resolver"
    
    if pending and not options:
        print("[ROUTER] Pending disambiguation but no options, skipping resolver...")
    
    return route_from_router(state)


def _add_edges(graph: StateGraph):
    graph.set_entry_point("advanced_router")
    
    graph.add_conditional_edges(
        "advanced_router",
        _route_from_router_with_disambiguation,
        {
            "user_selection_resolver": "user_selection_resolver",
            "clarifier": "clarifier",
            "validation_preprocessor": "validation_preprocessor",
            "domain_graph": "domain_graph"
        }
    )
    
    # Routing condicional desde user_selection_resolver
    def route_from_selection_resolver(state: MainRouterState) -> str:
        # Si hay error (no se pudo extraer número), terminar
        if state.get("domain_graph_status") == "error":
            print("[ROUTING] Selection failed, going to responder")
            return "responder_formatter"
        # Si la selección fue exitosa, continuar con routing
        print("[ROUTING] Selection successful, going to router")
        return "advanced_router"
    
    graph.add_conditional_edges(
        "user_selection_resolver",
        route_from_selection_resolver,
        {
            "advanced_router": "advanced_router",
            "responder_formatter": "responder_formatter"
        }
    )
    
    graph.add_edge("clarifier", "responder_formatter")
    
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
    
    graph.add_edge("parallel_executor", "aggregator")
    
    graph.add_conditional_edges(
        "aggregator",
        route_from_aggregator,
        {
            "domain_graph": "domain_graph",
            "error_handler": "error_handler"
        }
    )
    
    graph.add_edge("disambiguation", "responder_formatter")
    graph.add_edge("not_found_responder", "responder_formatter")
    
    graph.add_conditional_edges(
        "domain_graph",
        route_from_domain_graph,
        {
            "format_response": "format_response",
            "advanced_router": "advanced_router",
            "clarifier": "clarifier",
            "error_handler": "error_handler"
        }
    )
    
    graph.add_edge("format_response", "responder_formatter")
    graph.add_edge("responder_formatter", END)
    graph.add_edge("error_handler", "responder_formatter")


def create_advanced_graph(use_checkpointer: bool = True):
    graph = StateGraph(MainRouterState)
    _add_nodes(graph)
    _add_edges(graph)
    
    return graph.compile(checkpointer=checkpointer if use_checkpointer else None)


def _create_initial_state(question: str, max_hops: int) -> MainRouterState:
    return {
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
        "parallel_k": 1,
        "parallel_results": [],
        "aggregated_result": None,
        "needs_clarification": False,
        "clarification_message": None,
        "domain_graph_status": None,
        "schema_valid": False,
        "schema_errors": [],
        "schema_warnings": [],
        "missing_params": []
    }


def _load_existing_state(graph, config: dict):
    state_snapshot = graph.get_state(config)
    if state_snapshot and hasattr(state_snapshot, 'values'):
        existing_state = state_snapshot.values
        print(f"[PROCESS] Loaded checkpoint state: pending_disambiguation={existing_state.get('pending_disambiguation', False)}")
        return existing_state
    
    return None


def _print_execution_summary(total_time: float, tool_times: dict):
    print(f"\n{'='*80}")
    print("EXECUTION SUMMARY")
    print(f"{'='*80}")
    print(f"Total time: {total_time:.2f}s")
    print(f"{'='*80}\n")
    
    if tool_times:
        print("\n" + "="*80)
        print("TOOL EXECUTION TIMES")
        print("="*80)
        for tool_name, tool_time in sorted(tool_times.items(), key=lambda x: x[1], reverse=True):
            print(f"  {tool_name}: {tool_time:.2f}s")
        print("="*80 + "\n")


def _verify_checkpoint(graph, config: dict):
    final_snapshot = graph.get_state(config)
    if final_snapshot and hasattr(final_snapshot, 'values'):
        final_state = final_snapshot.values
        print(f"\n[PROCESS] ✅ Checkpoint saved: pending_disambiguation={final_state.get('pending_disambiguation', False)}")
        if final_state.get('pending_disambiguation'):
            print(f"[PROCESS] ✅ Options saved: {len(final_state.get('disambiguation_options', []))}")


async def process_question_advanced(
    question: str,
    max_iterations: int = 3,
    max_hops: int = 3,
    enable_telemetry: bool = True,
    thread_id: str = "default",
    context: dict = None
) -> MainRouterState:
    telemetry_logger = TelemetryLogger(log_to_file=enable_telemetry) if enable_telemetry else None
    start_time = time.time()
    
    graph = create_advanced_graph(use_checkpointer=True)
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 50  # Aumentar límite para queries complejas
    }
    
    existing_state = _load_existing_state(graph, config)
    
    if existing_state and existing_state.get("pending_disambiguation", False):
        print("[PROCESS] ✅ Continuing disambiguation flow...")
        print(f"[PROCESS] Original question: {existing_state.get('original_question')}")
        print(f"[PROCESS] Options available: {len(existing_state.get('disambiguation_options', []))}")
        initial_state = {**existing_state, "question": question}
    else:
        initial_state = _create_initial_state(question, max_hops)
    
    result = await graph.ainvoke(initial_state, config=config)
    
    _verify_checkpoint(graph, config)
    
    total_time = time.time() - start_time
    tool_times = result.get("tool_execution_times", {})
    
    _print_execution_summary(total_time, tool_times)
    
    if telemetry_logger:
        print_telemetry_summary(telemetry_logger, result)
        telemetry_logger.save_to_file(result)
    
    return result


async def process_question_advanced_streaming(
    question: str,
    max_iterations: int = 3,
    max_hops: int = 2,
    thread_id: str = "default"
):
    initial_state = _create_initial_state(question, max_hops)
    graph = create_advanced_graph()
    config = {"configurable": {"thread_id": thread_id}}
    
    async for event in graph.astream(initial_state, config=config):
        node_name = list(event.keys())[0]
        state_output = event[node_name]
        
        print(f"\nNode: {node_name}")
        if node_name == "advanced_router":
            print(f"   Selected: {state_output.get('selected_graph', 'N/A')}")
            print(f"   Confidence: {state_output.get('routing_confidence', 0.0):.2f}")
        elif node_name == "domain_graph":
            print(f"   Status: {state_output.get('domain_graph_status', 'N/A')}")
        print("---")
    
    return state_output


def get_graph():
    return create_advanced_graph()


graph = create_advanced_graph(use_checkpointer=False)