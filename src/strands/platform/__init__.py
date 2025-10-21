# platform/__init__.py - Módulo Platform

from .graph_core.graph import create_streaming_graph, process_question, process_question_streaming
from .graph_core.state import State, create_initial_state
from src.strands.config.models import (
    MODEL_CLASSIFIER,
    MODEL_SUPERVISOR,
    MODEL_NODE_EXECUTOR,
    MODEL_FORMATTER,
    DEFAULT_MAX_ITERATIONS
)

__all__ = [
    "create_streaming_graph",
    "process_question",
    "process_question_streaming",
    "State",
    "create_initial_state",
    "MODEL_CLASSIFIER",
    "MODEL_SUPERVISOR",
    "MODEL_NODE_EXECUTOR",
    "MODEL_FORMATTER",
    "DEFAULT_MAX_ITERATIONS"
]
