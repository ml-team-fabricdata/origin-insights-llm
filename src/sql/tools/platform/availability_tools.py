from langchain_core.tools import StructuredTool, Tool
from typing import Optional, Dict, List, Any, Union
from src.sql.modules.platform.availability import *

# =============================================================================
# Availability
# =============================================================================

GET_AVAILABILITY_BY_UID_TOOL = StructuredTool.from_function(
    name="get_availability_by_uid",
    description=(
        "Get platform availability for a title by UID with optional price information. "
        "Parameters: uid (required), country (optional - accepts ISO-2 code like 'US' OR region name like 'LATAM', 'EU', 'latin_america'), with_prices (boolean, default False), limit (int, default 100 - max platforms to return). "
        "Supports regions: LATAM/latin_america, EU, north_america, south_america, europe, asia, africa, oceania, and more. "
        "When with_prices=True, includes comprehensive price summary: price range (min/max), available currencies, and platform counts with/without prices. "
        "Use limit=50 or less for faster responses. Returns detailed platform availability across countries and regions."
    ),
    func=get_availability_by_uid,
)


GET_PLATFORM_EXCLUSIVES_TOOL = Tool.from_function(
    name="get_platform_exclusives",
    description=(
        "Get exclusive titles available on a specific platform within a country or region. "
        "Requires platform_name and country (ISO-2 code OR region name like 'LATAM', 'EU', defaults to US). "
        "Supports regions: LATAM/latin_america, EU, north_america, south_america, europe, asia, africa, oceania. "
        "Returns list of exclusive content (uid, title, type) available only on that platform in the specified country/region. "
        "Useful for discovering platform-specific content across markets."
    ),
    func=get_platform_exclusives,
)


COMPARE_PLATFORMS_FOR_TITLE_TOOL = StructuredTool.from_function(
    name="compare_platforms_for_title",
    description="Compare which streaming platforms carry a specific title (exact title match). Returns distinct list of platform names and countries where the title is available. Useful for finding where to watch a specific movie or series across different platforms and regions.",
    func=compare_platforms_for_title,
)


GET_RECENT_PREMIERES_BY_COUNTRY_TOOL = Tool.from_function(
    name="get_recent_premieres_by_country",
    description=(
        "Get recent content premieres available in a specific country or region within the last 7 days. "
        "Requires country (ISO-2 code OR region name like 'LATAM', 'EU'). Parameter days_back is fixed at 7 days (policy restriction). "
        "Supports regions: LATAM/latin_america, EU, north_america, south_america, europe, asia, africa, oceania. "
        "Returns titles with release dates, aggregated platforms, and platform countries where available. "
        "Useful for discovering new releases across markets."
    ),
    func=get_recent_premieres_by_country,
)


ALL_AVAILABILITY_TOOLS = [
    GET_AVAILABILITY_BY_UID_TOOL,
    GET_PLATFORM_EXCLUSIVES_TOOL,
    COMPARE_PLATFORMS_FOR_TITLE_TOOL,
    GET_RECENT_PREMIERES_BY_COUNTRY_TOOL,
]
