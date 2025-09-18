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
    func=validate_title_sync,
    name="validate_title",
    description=(
        "MANDATORY: Validates movie/TV show titles and returns validation status. "
        "CRITICAL: If status='ambiguous', you MUST show the list of options to the user "
        "and STOP processing until the user selects one. Do NOT continue with queries "
        "until user disambiguation. If status='resolved', you can continue with the returned UID."
    )
)

VALIDATE_ACTOR_TOOL = Tool.from_function(
    func=validate_actor_sync,
    name="validate_actor", 
    description=(
        "MANDATORY: Validates ACTOR names and returns validation status. "
        "CRITICAL: If status='ambiguous', you MUST show the list of options to the user "
        "and STOP processing until the user selects one. Do NOT continue until user chooses. "
        "If status='resolved' or status='ok', you can continue with the returned ID."
    )
)

VALIDATE_DIRECTOR_TOOL = Tool.from_function(
    func=validate_director_sync,
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