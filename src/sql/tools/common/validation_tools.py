from langchain_core.tools import StructuredTool
from typing import Optional, Union, List, Any
from src.sql.modules.common.validation import *

# =============================================================================
# Validation Tools
# =============================================================================
VALIDATE_TITLE_TOOL = StructuredTool.from_function(
    func=validate_title,
    name="validate_title",
    description="Valida y resuelve títulos para asegurar una identificación única. "
               "Requiere el título a validar como parámetro.",
)

VALIDATE_ACTOR_TOOL = StructuredTool.from_function(
    func=validate_actor,
    name="validate_actor",
    description="Valida y resuelve nombres de actores para identificación única. "
               "Requiere el nombre del actor a validar como parámetro.",
)

VALIDATE_DIRECTOR_TOOL = StructuredTool.from_function(
    func=validate_director,
    name="validate_director",
    description="Valida y resuelve nombres de directores para identificación única. "
               "Requiere el nombre del director a validar como parámetro.",
)

ALL_VALIDATION_TOOLS = [
    VALIDATE_TITLE_TOOL,
    VALIDATE_ACTOR_TOOL,
    VALIDATE_DIRECTOR_TOOL
]
