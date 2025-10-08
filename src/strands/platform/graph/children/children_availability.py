from .state import State
from src.strands.platform.prompt_platform import AVAILABILITY_PROMPT
from src.sql.modules.platform.availability import (
    get_availability_by_uid, get_platform_exclusives,
    compare_platforms_for_title, get_recent_premieres_by_country,
)
from src.strands.utils import _execute_tool


async def node_availability_by_uid(state: State) -> State:
    return await _execute_tool(
        state,
        get_availability_by_uid,
        "availability_by_uid",
        AVAILABILITY_PROMPT,
        "availability"
    )


async def node_platform_exclusives(state: State) -> State:
    return await _execute_tool(
        state,
        get_platform_exclusives,
        "platform_exclusives",
        AVAILABILITY_PROMPT,
        "availability"
    )


async def node_compare_platforms(state: State) -> State:
    return await _execute_tool(
        state,
        compare_platforms_for_title,
        "compare_platforms",
        AVAILABILITY_PROMPT,
        "availability"
    )

async def node_recent_premieres(state: State) -> State:
    return await _execute_tool(
        state,
        get_recent_premieres_by_country,
        "recent_premieres",
        AVAILABILITY_PROMPT,
        "availability"
    )