from langchain_core.tools import Tool

from src.sql.constants_sql import *
from src.sql.content.metadata import *
from src.sql.content.discovery import *

FILMOGRAPHY_UID_TOOL = Tool(
    name="answer_filmography_by_uid",
    func=get_filmography_by_uid,
    description="ONLY use after having UID confirmed by user. Returns filmography/profile information.",
)

TITLE_RATING_TOOL = Tool.from_function(
    name="get_title_rating",
    description=f"Rating/score for a title by UID optional country iso. {POLICY_TITLE}",
    func=get_title_rating,
)


# =============================================================================
# Metadata query tools
# =============================================================================
METADATA_COUNT_TOOL = Tool.from_function(
    name="metadata_simple_all_count",
    description="Count of titles in metadata content.",
    func=tool_metadata_count,
)

METADATA_LIST_TOOL = Tool.from_function(
    name="metadata_simple_all_list",
    description=(
        "Basic listing of metadata content (search, order)."
    ),
    func=tool_metadata_list,
)

METADATA_DISTINCT_TOOL = Tool.from_function(
    name="metadata_simple_all_distinct",
    description=(
        "Unique values of safe metadata columns like type, country, title."
    ),
    func=tool_metadata_distinct,
)

METADATA_STATS_TOOL = Tool.from_function(
    name="metadata_simple_all_stats",
    description=(
        "Stats (count/min/max year, avg/median duration) metadata content."
    ),
    func=tool_metadata_stats,
)

METADATA_QUERY_TOOL = Tool.from_function(
    name="metadata_simple_all_query",
    description=(
        "Query metadata information with filters (type, year range, duration, "
        "genre/languages/country/directors/writers/cast) and search by title/"
        "synopsis. Safe parameters, ordering, limit and pagination. Use "
        "'count_only=True' to get only the count."
    ),
    func=query_metadata_simple_all_tool,
)



ALL_DISCOVERY_TOOLS = [
    FILMOGRAPHY_UID_TOOL,
    TITLE_RATING_TOOL,
    # Metadata query tools
    METADATA_COUNT_TOOL,
    METADATA_LIST_TOOL,
    METADATA_DISTINCT_TOOL,
    METADATA_QUERY_TOOL,
    METADATA_STATS_TOOL
]