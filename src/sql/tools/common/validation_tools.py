from langchain_core.tools import Tool
from src.sql.modules.common.validation import *

# =============================================================================
# Validation Tools
# =============================================================================
VALIDATE_TITLE_TOOL = Tool.from_function(
    func=validate_title,
    name="validate_title",
    description=(
        "Valida y resuelve títulos para asegurar una identificación única.\n"
    )
)

VALIDATE_ACTOR_TOOL = Tool.from_function(
    func=validate_actor,
    name="validate_actor",
    description=(
        "Valida y resuelve nombres de actores para identificación única.\n"
    )
)

VALIDATE_DIRECTOR_TOOL = Tool.from_function(
    func=validate_director,
    name="validate_director",
    description=(
        "Valida y resuelve nombres de directores para identificación única.\n"
    )
)


ALL_VALIDATION_TOOLS = [
    # VALIDATE
    VALIDATE_TITLE_TOOL,
    VALIDATE_ACTOR_TOOL,
    VALIDATE_DIRECTOR_TOOL
]
