from langchain_core.tools import Tool
from src.sql.modules.platform.presence import *

# =============================================================================
# Presence
# =============================================================================

PRESENCE_COUNT_TOOL = Tool.from_function(
    name="presence_count",
    description="Get total count of content presence records with optional filters. Supports filtering by country (ISO-2), platform_name, uid, type (Movie/Series), and title_like (text search). Returns total count of active content availability records matching the criteria. Useful for measuring catalog size.",
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
    description="Get comprehensive statistical summary of content presence data. Returns: total records, unique platforms count, unique countries count, unique content count, average/median duration, exclusive content count, kids content count, movies vs series breakdown. Supports optional filters by country, platform_name, and type.",
    func=presence_statistics,
)


GET_AVAILABILITY_BY_UID_PRICE_TOOL = StructuredTool.from_function(
    name="get_availability_by_uid_price",
    description=(
        "Get platform availability for a title by UID with optional price information. Parameters: uid (required), country (optional ISO-2 for filtering), with_prices (boolean). "
        "When with_prices=True, includes comprehensive price data: individual platform prices with currency/type/definition/license, price range (min/max), currencies available, and platform counts with/without prices. "
        "Returns detailed availability across platforms and countries."
    ),
    func=get_availability_by_uid_price,
)


PLATFORM_COUNT_BY_COUNTRY_TOOL = Tool.from_function(
    name="platform_count_by_country",
    description="Get count of streaming platforms available by country. If country (ISO-2) is specified, returns platform count and list of platforms for that specific country. If no country specified, returns platform counts for all countries sorted by count. Useful for comparing platform availability across markets.",
    func=platform_count_by_country,
)


COUNTRY_PLATFORM_SUMMARY_TOOL = Tool.from_function(
    name="country_platform_summary",
    description="Get comprehensive summary of platforms and content availability by country or region. Returns detailed statistics per country: unique platforms count, unique content count, total records, movies/series breakdown, exclusive content count, and list of available platforms. Supports country/region filtering or returns global summary for all countries.",
    func=country_platform_summary,
)



ALL_PRESENCE_TOOLS = [
    # Presence
    PRESENCE_COUNT_TOOL,
    PRESENCE_LIST_TOOL,
    PRESENCE_DISTINCT_TOOL,
    PRESENCE_STATISTICS_TOOL,
    GET_AVAILABILITY_BY_UID_PRICE_TOOL,
    PLATFORM_COUNT_BY_COUNTRY_TOOL,
    COUNTRY_PLATFORM_SUMMARY_TOOL,
]
