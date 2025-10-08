# children_presence.py
from .state import State
from src.strands.platform.prompt_platform import PRESENCE_PROMPT
from src.sql.modules.platform.presence import (
    presence_count, presence_list, presence_statistics,
    platform_count_by_country, country_platform_summary,
)


async def node_presence_count(state: State) -> State:
    return await _execute_tool(
        state,
        presence_count,
        "presence_count",
        PRESENCE_PROMPT,
        "presence"
    )


async def node_presence_list(state: State) -> State:
    return await _execute_tool(
        state,
        presence_list,
        "presence_list",
        PRESENCE_PROMPT,
        "presence"
    )


async def node_presence_statistics(state: State) -> State:
    return await _execute_tool(
        state,
        presence_statistics,
        "presence_statistics",
        PRESENCE_PROMPT,
        "presence"
    )


async def node_platform_count_by_country(state: State) -> State:
    return await _execute_tool(
        state,
        platform_count_by_country,
        "platform_count_by_country",
        PRESENCE_PROMPT,
        "presence"
    )


async def node_country_platform_summary(state: State) -> State:
    return await _execute_tool(
        state,
        country_platform_summary,
        "country_platform_summary",
        PRESENCE_PROMPT,
        "presence"
    )
