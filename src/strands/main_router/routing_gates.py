from typing import Literal
from .state import MainRouterState


def route_from_router(state: MainRouterState) -> Literal["clarifier", "validation_preprocessor"]:
    """Router → Clarifier o Validation (siempre valida primero)"""
    if state.get("needs_clarification", False):
        return "clarifier"
    
    confidence = state.get("routing_confidence", 1.0)
    
    if confidence < 0.5:
        return "clarifier"
    
    return "validation_preprocessor"


def route_from_validation(state: MainRouterState) -> Literal["parallel_executor", "domain_graph", "disambiguation", "not_found_responder"]:
    """Validation → Parallel/Domain/Disambiguation/NotFound"""
    validation_status = state.get("validation_status")
    
    # Si validación falla, terminar temprano
    if validation_status == "ambiguous":
        return "disambiguation"
    
    if validation_status == "not_found":
        return "not_found_responder"
    
    # Validación OK → decidir si paralelizar
    candidates = state.get("routing_candidates", [])
    
    if len(candidates) >= 2 and len(candidates) > 1 and candidates[1][1] > 0.6:
        return "parallel_executor"
    
    return "domain_graph"


def route_from_domain_graph(state: MainRouterState) -> Literal["responder_formatter", "advanced_router", "clarifier", "error_handler"]:
    domain_status = state.get("domain_graph_status")
    
    if domain_status == "success":
        return "responder_formatter"
    
    if domain_status == "not_my_scope":
        return "advanced_router"
    
    if domain_status == "needs_clarification":
        return "clarifier"
    
    if domain_status == "error":
        return "error_handler"
    
    return "responder_formatter"


def route_from_aggregator(state: MainRouterState) -> Literal["domain_graph", "error_handler"]:
    """Aggregator → Domain Graph (ya validado) o Error"""
    selected_graph = state.get("selected_graph")
    
    if not selected_graph:
        return "error_handler"
    
    return "domain_graph"
