from typing import TypedDict, Literal, Optional, Dict, Any, List, Tuple

class MainRouterState(TypedDict, total=False):
    question: str
    answer: str
    selected_graph: Literal["business", "talent", "content", "common", "platform"]
    routing_done: bool
    error: Optional[str]
    needs_rerouting: bool
    previous_graph: Optional[str]
    rerouting_count: int
    validation_done: bool
    validated_entities: Optional[Dict[str, Any]]
    needs_validation: bool
    needs_user_input: bool
    validation_message: Optional[str]
    validation_status: Optional[Literal["resolved", "ambiguous", "not_found", "error"]]
    skip_validation: bool
    
    # New fields for advanced routing
    routing_confidence: float
    routing_candidates: List[Tuple[str, float]]
    visited_graphs: List[str]
    max_hops: int
    parallel_execution: bool
    parallel_results: List[Dict[str, Any]]
    aggregated_result: Optional[Dict[str, Any]]
    needs_clarification: bool
    clarification_message: Optional[str]
    domain_graph_status: Optional[Literal["success", "not_my_scope", "needs_clarification", "error"]]