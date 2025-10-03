from langchain_core.tools import Tool
from src.sql.modules.platform.presence import *

# =============================================================================
# Presence
# =============================================================================

PRESENCE_COUNT_TOOL = Tool.from_function(
    name="presence_count",
    description=(
        "Get SIMPLE COUNT of content presence records (single number only). "
        "Filters: country (ISO-2), platform_name, uid, type (Movie/Series), title_like. "
        "Returns only total count of matching records. "
        "Use for quick counts. For detailed statistics (platforms, countries, durations, etc.), use presence_statistics instead."
    ),
    func=presence_count,
)


PRESENCE_LIST_TOOL = Tool.from_function(
    name="presence_list",
    description=(
        "List content presence records with pagination and ordering. Filters: country (ISO-2), platform_name, type (Movie/Series), title_like. "
        "Supports pagination (limit, offset) and ordering (order_by with allowed fields, order_dir: ASC/DESC). "
        "Returns detailed presence information including title, uid, platform details, country, duration, and availability status."
    ),
    func=presence_list,
)


PRESENCE_DISTINCT_TOOL = Tool.from_function(
    name="presence_distinct",
    description=(
        "Get distinct/unique values from presence table columns. Specify column parameter from allowed list: iso_alpha2, plan_name, platform_code, platform_name, type, content_type. "
        "Supports optional filters: country, platform_name, type. Returns unique values for the specified column, useful for discovering available options and filter values."
    ),
    func=presence_distinct,
)


PRESENCE_STATISTICS_TOOL = Tool.from_function(
    name="presence_statistics",
    description=(
        "Get COMPREHENSIVE STATISTICAL summary of content presence (10+ metrics). "
        "Returns: total_records, unique_platforms, unique_countries, unique_content, avg/median duration, "
        "exclusive_count, kids_count, movies_count, series_count. Filters: country, platform_name, type. "
        "Use for detailed analysis. For simple count only, use presence_count instead."
    ),
    func=presence_statistics,
)


PLATFORM_COUNT_BY_COUNTRY_TOOL = Tool.from_function(
    name="platform_count_by_country",
    description=(
        "Get QUICK COUNT of streaming platforms by country (lightweight query). "
        "If country (ISO-2) specified: returns platform_count + platforms array for that country. "
        "If no country: returns platform_count for ALL countries sorted by count. "
        "Use this for simple platform counting. For detailed statistics including content counts, use country_platform_summary instead."
    ),
    func=platform_count_by_country,
)


COUNTRY_PLATFORM_SUMMARY_TOOL = Tool.from_function(
    name="country_platform_summary",
    description=(
        "Get COMPREHENSIVE DETAILED summary of platforms and content by country/region (complete analysis). "
        "Returns per country: unique_platforms (count), unique_content (count), total_records, movies count, series count, "
        "exclusive_content count, and platforms array. Supports country/region filtering or global summary. "
        "Use this for detailed market analysis. For simple platform counting only, use platform_count_by_country instead."
    ),
    func=country_platform_summary,
)



ALL_PRESENCE_TOOLS = [
    PRESENCE_COUNT_TOOL,
    PRESENCE_LIST_TOOL,
    PRESENCE_DISTINCT_TOOL,
    PRESENCE_STATISTICS_TOOL,
    PLATFORM_COUNT_BY_COUNTRY_TOOL,
    COUNTRY_PLATFORM_SUMMARY_TOOL,
]
