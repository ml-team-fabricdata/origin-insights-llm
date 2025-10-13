# main_router/state.py
from typing import TypedDict, Literal, Optional, Dict, Any

class MainRouterState(TypedDict, total=False):
    """Estado del router principal que decide entre grafos"""
    question: str
    answer: str
    selected_graph: Literal["business", "talent", "content", "common", "platform"]
    routing_done: bool
    error: Optional[str]
    needs_rerouting: bool  # Indica si un sub-grafo no completó y necesita rerouting
    previous_graph: Optional[str]  # Grafo anterior que no completó
    rerouting_count: int  # Contador de re-routings para evitar loops infinitos
    
    # Validación de entidades
    validation_done: bool  # Indica si ya se validaron las entidades
    validated_entities: Optional[Dict[str, Any]]  # Entidades validadas (título, actor, director)
    needs_validation: bool  # Indica si la pregunta requiere validación
    needs_user_input: bool  # Indica si hay ambigüedad y se necesita input del usuario
    validation_message: Optional[str]  # Mensaje de validación con opciones para el usuario
