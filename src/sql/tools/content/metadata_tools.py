from langchain_core.tools import Tool
from src.sql.utils.constants_sql import *
from src.sql.modules.content.metadata import *

# =============================================================================
# Metadata query tools
# =============================================================================
METADATA_COUNT_TOOL = Tool.from_function(
    name="metadata_simple_all_count",
    description="Get total count of titles in the metadata catalog. Supports optional filters by content type (Movie/Series), country (ISO-2 code), and year range (year_from, year_to). Returns the total number of titles matching the criteria.",
    func=tool_metadata_count,
)

METADATA_LIST_TOOL = Tool.from_function(
    name="metadata_simple_all_list",
    description=(
        "Get distinct/unique values from specific metadata columns. Specify 'column' parameter to retrieve unique values from fields like: type, countries_iso, primary_genre, primary_language, year, etc. Supports aliases (genre→primary_genre, country→countries_iso, lang→primary_language). Useful for discovering available filter options."
    ),
    func=tool_metadata_list,
)


METADATA_STATS_TOOL = Tool.from_function(
    name="metadata_simple_all_stats",
    description=(
        "Get statistical summary of metadata catalog including: total count, min/max year range, average and median duration. Supports optional filters by content type (Movie/Series), country (ISO-2), and year range. Provides quick overview of catalog composition."
    ),
    func=tool_metadata_stats,
)

METADATA_QUERY_TOOL = Tool.from_function(
    name="metadata_simple_all_query",
    description=(
        "Advanced metadata search with comprehensive filtering and pagination. "
        "Filters: type (Movie/Series), countries_iso (ISO-2), year_from/year_to, "
        "duration_min/duration_max, age rating, primary_genre, title_like/synopsis_like (text search), "
        "languages_any/countries_iso_any/directors_any/writers_any/cast_any (array searches). "
        "Supports: custom field selection (select=[]), ordering (order_by, order_dir), "
        "pagination (limit, offset), and count_only=True for totals. Returns complete title metadata."
    ),
    func=query_metadata_simple_all_tool,
)


ALL_METADATA_TOOLS = [
    # Metadata query tools
    METADATA_COUNT_TOOL,
    METADATA_LIST_TOOL,
    METADATA_QUERY_TOOL,
    METADATA_STATS_TOOL
]
