from langchain_core.tools import Tool
from src.sql.modules.common.validation import *

# =============================================================================
# Validation Tools
# =============================================================================
VALIDATE_TITLE_TOOL = Tool.from_function(
    func=validate_title,
    name="validate_title",
    description="Validates titles. Status='ambiguous': show options and STOP. Status='resolved': continue with UID."
)
VALIDATE_ACTOR_TOOL = Tool.from_function(
    func=validate_actor,
    name="validate_actor",
    description="Validates actors. Status='ambiguous': show options and STOP."
)

VALIDATE_DIRECTOR_TOOL = Tool.from_function(
    func=validate_director,
    name="validate_director",
    description="Validates directors. Status='ambiguous': show options and STOP."
)


ALL_VALIDATION_TOOLS = [
    # VALIDATE
    VALIDATE_TITLE_TOOL,
    VALIDATE_ACTOR_TOOL,
    VALIDATE_DIRECTOR_TOOL
]
