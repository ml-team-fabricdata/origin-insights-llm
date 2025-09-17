from langchain_core.tools import Tool
from src.sql.core.validation import *
from typing import Optional, Dict, Any

def sync_validate_title(title: str, threshold: Optional[float] = None) -> Dict[str, Any]:
    return run_async_in_sync(validate_title(title, threshold))


def sync_validate_actor(name: str) -> Dict[str, Any]:
    return run_async_in_sync(validate_actor(name))


def sync_validate_director(name: str) -> Dict[str, Any]:
    return run_async_in_sync(validate_director(name))


VALIDATE_TITLE_TOOL = Tool.from_function(
    func=sync_validate_title,
    name="validate_title",
    description=(
        "MANDATORY: Validates titles and returns status. If status='ambiguous': "
        "SHOW list of options to user and STOP. Do NOT continue until user "
        "chooses. If status='resolved': can continue with returned UID."
    ),
)

VALIDATE_ACTOR_TOOL = Tool.from_function(
    func=sync_validate_actor,
    name="validate_actor",
    description=(
        "MANDATORY: Validates ACTORS by name and returns status. If "
        "status='ambiguous': SHOW list of options to user and STOP. Do NOT "
        "continue until user chooses. If status='resolved': can continue with "
        "returned UID."
    ),
)

VALIDATE_DIRECTOR_TOOL = Tool.from_function(
    func=sync_validate_director,
    name="validate_director",
    description=(
        "MANDATORY: Validates DIRECTORS by name and returns status. If "
        "status='ambiguous': SHOW list of options to user and STOP. Do NOT "
        "continue until user chooses. If status='resolved': can continue with "
        "returned UID."
    ),
)

ALL_CORE = [
    VALIDATE_TITLE_TOOL,
    VALIDATE_ACTOR_TOOL,
    VALIDATE_DIRECTOR_TOOL
]