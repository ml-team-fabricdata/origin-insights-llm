# content/graph_core/state.py
from typing import TypedDict, Literal, Optional, List, Dict, Any

class State(TypedDict, total=False):
    # Campos originales
    question: str
    answer: str
    task: Literal["actors", "directors", "collaborations"]
    tool_calls_count: int
    max_iterations: int
    accumulated_data: str
    supervisor_decision: str
    needs_more: bool
    
    # Campos adicionales para mejor control
    classification_done: bool  # Evita reclasificación
    status: Literal["success", "insufficient_data", "format_error", "max_iterations"]
    
    # Tracking de errores
    classification_error: Optional[str]
    supervisor_error: Optional[str]
    node_errors: Optional[List[str]]
    
    # Metadata útil para debugging
    iteration_history: Optional[List[Dict[str, Any]]]  # Historial de decisiones
    last_node: Optional[Literal["actors_node", "directors_node", "collaborations_node"]]
    
    # Control de flujo
    should_continue: bool  # Flag explícito para continuar o no
    
    # Entidades validadas del Main Router
    validated_entities: Optional[Dict[str, Any]]  # Entidades validadas (título, actor, director)


def create_initial_state(question: str, max_iterations: int = 3) -> State:
    """Factory function para crear estado inicial consistente"""
    return {
        "question": question,
        "answer": "",
        "task": None,
        "tool_calls_count": 0,
        "max_iterations": max_iterations,
        "accumulated_data": "",
        "supervisor_decision": "",
        "needs_more": True,
        "classification_done": False,
        "status": None,
        "iteration_history": [],
        "worker_errors": [],
        "should_continue": True
    }


def append_to_accumulated_data(state: State, new_data: str, source: str = "") -> State:
    """Helper para agregar datos de forma consistente"""
    current = state.get("accumulated_data", "")
    separator = "\n\n---\n\n" if current else ""
    source_label = f"[{source}]\n" if source else ""
    
    return {
        **state,
        "accumulated_data": f"{current}{separator}{source_label}{new_data}"
    }


def increment_tool_calls(state: State, worker_name: str = "") -> State:
    """Helper para incrementar contador de forma segura"""
    count = state.get("tool_calls_count", 0) + 1
    history = state.get("iteration_history", [])
    
    history.append({
        "iteration": count,
        "node": worker_name,
        "data_length": len(state.get("accumulated_data", ""))
    })
    
    return {
        **state,
        "tool_calls_count": count,
        "last_node": worker_name,
        "iteration_history": history
    }

def add_error(state: State, error: str, error_type: str = "node") -> State:
    """Helper para registrar errores"""
    errors = state.get("node_errors", [])
    if errors is None:
        errors = []
    errors.append(f"[{error_type}] {error}")
    
    return {
        **state,
        "node_errors": errors
    }