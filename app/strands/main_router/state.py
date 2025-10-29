from typing import TypedDict, Literal, Optional, Dict, Any, List

class MainRouterState(TypedDict, total=False):
    question: str
    answer: str
    history: list[dict]
    selected_graph: Optional[Literal["business", "talent", "content", "common", "platform"]]
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
    routing_confidence: float
    routing_candidates: List[Dict[str, Any]]
    visited_graphs: List[str]
    max_hops: int
    parallel_execution: bool
    parallel_k: int
    parallel_results: List[Any]
    aggregated_result: Optional[Any]
    needs_clarification: bool
    clarification_message: Optional[str]
    domain_graph_status: Optional[str]
    schema_valid: bool
    schema_errors: List[str]
    schema_warnings: List[str]
    missing_params: List[str]
    telemetry_logger: Optional[Any]
    tool_execution_times: Optional[Dict[str, float]]
    pending_disambiguation: bool
    disambiguation_options: Optional[List[Dict[str, Any]]]
    original_question: Optional[str]