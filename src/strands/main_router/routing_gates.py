from typing import Literal
from .state import MainRouterState
from .config import MIN_CONFIDENCE_NO_CLARIFICATION


def route_from_router(state: MainRouterState) -> Literal["clarifier", "validation_preprocessor", "domain_graph"]:
    """Router → Clarifier, Validation (solo si necesario), o Domain Graph directo"""
    if state.get("needs_clarification", False):
        return "clarifier"
    
    confidence = state.get("routing_confidence", 1.0)
    
    if confidence < MIN_CONFIDENCE_NO_CLARIFICATION:
        return "clarifier"
    
    # Solo validar para dominios TALENT y CONTENT
    selected_graph = state.get("selected_graph", "").lower()
    if selected_graph in ["talent", "content", "business", "platform", "common"]:
        return "validation_preprocessor"
    
    # Para otros dominios (BUSINESS, PLATFORM, COMMON), ir directo a domain graph
    return "domain_graph"


def route_from_validation(state: MainRouterState) -> Literal["parallel_executor", "domain_graph", "disambiguation", "not_found_responder"]:
    """Validation → Parallel/Domain/Disambiguation/NotFound"""
    validation_status = state.get("validation_status")
    
    # Si validación falla, terminar temprano
    if validation_status == "ambiguous":
        return "disambiguation"
    
    if validation_status == "not_found":
        return "not_found_responder"
    
    # Validación OK → decidir si paralelizar basado en state
    # El router ya decidió si usar parallel_execution basado en τ
    use_parallel = state.get("parallel_execution", False)
    
    if use_parallel:
        return "parallel_executor"
    
    return "domain_graph"


def route_from_domain_graph(state: MainRouterState) -> Literal["format_response", "advanced_router", "clarifier", "error_handler"]:
    """Domain Graph → Format Response (si success) o Re-routing/Error"""
    domain_status = state.get("domain_graph_status")
    visited_graphs = state.get("visited_graphs", [])
    current_hop = len(visited_graphs)
    max_hops = state.get("max_hops", 3)
    
    # CRITICAL: Prevenir loops infinitos
    if current_hop >= max_hops:
        print(f"[ROUTING] Max hops reached ({current_hop}/{max_hops}). Forcing format_response.")
        return "format_response"
    
    if domain_status == "success":
        return "format_response"
    
    if domain_status == "not_my_scope":
        print(f"[ROUTING] Re-routing requested. Hop: {current_hop + 1}/{max_hops}")
        return "advanced_router"
    
    if domain_status == "needs_clarification":
        return "clarifier"
    
    if domain_status == "error":
        return "error_handler"
    
    return "format_response"  # Default: formatear respuesta


def route_from_aggregator(state: MainRouterState) -> Literal["domain_graph", "error_handler"]:
    """Aggregator → Domain Graph (ya validado) o Error"""
    selected_graph = state.get("selected_graph")
    
    if not selected_graph:
        return "error_handler"
    
    return "domain_graph"


