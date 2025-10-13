from langchain_core.tools import Tool
from src.sql.utils.constants_sql import *
from src.sql.modules.content.metadata import *

# =============================================================================
# Metadata query tools
# =============================================================================
METADATA_COUNT_TOOL = Tool.from_function(
    name="metadata_simple_all_count",
    description=(
        "Get SIMPLE COUNT of titles in metadata catalog (single number only). "
        "Filters: type (Movie/Series), country (ISO-2 OR region like 'LATAM', 'EU'), year_from, year_to. "
        "Supports regions: LATAM/latin_america, EU, north_america, south_america, europe, asia, africa, oceania. "
        "Returns only total count. Use for quick counts. For detailed statistics (year ranges, durations), use metadata_simple_all_stats instead."
    ),
    func=metadata_simple_all_count,
)

METADATA_LIST_TOOL = Tool.from_function(
    name="metadata_simple_all_list",
    description=(
        "Get distinct/unique values from specific metadata columns. Specify 'column' parameter to retrieve unique values from fields like: type, countries_iso, primary_genre, primary_language, year, etc. Supports aliases (genre→primary_genre, country→countries_iso, lang→primary_language). Useful for discovering available filter options."
    ),
    func=metadata_simple_all_list,
)


METADATA_STATS_TOOL = Tool.from_function(
    name="metadata_simple_all_stats",
    description=(
        "Get STATISTICAL SUMMARY of metadata catalog (5 metrics). "
        "Returns: total count, min_year, max_year, avg_duration, median_duration. "
        "Filters: type (Movie/Series), country (ISO-2 OR region like 'LATAM', 'EU'), year range. "
        "Supports regions: LATAM/latin_america, EU, north_america, south_america, europe, asia, africa, oceania. "
        "Use for catalog overview. For simple count only, use metadata_simple_all_count instead."
    ),
    func=metadata_simple_all_stats,
)

METADATA_QUERY_TOOL = Tool.from_function(
    name="metadata_simple_all_query",
    description=(
        "Advanced metadata search with comprehensive filtering and pagination. "
        "Filters: type (Movie/Series), countries_iso (ISO-2 OR region like 'LATAM', 'EU'), year_from/year_to, "
        "duration_min/duration_max, age rating, primary_genre, title_like/synopsis_like (text search), "
        "languages_any/countries_iso_any/directors_any/writers_any/cast_any (array searches). "
        "Supports regions: LATAM/latin_america, EU, north_america, south_america, europe, asia, africa, oceania. "
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
