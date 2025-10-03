from langchain_core.tools import StructuredTool
from typing import Optional, Dict, List, Any, Union
from src.sql.modules.platform.availability import *

# =============================================================================
# Availability
# =============================================================================

# GET_AVAILABILITY_BY_UID_TOOL = StructuredTool.from_function(
#     name="get_availability_by_uid",
#     description=(
#         "Disponibilidad por UID; si se indica 'country' restringe por país. "
#         "Con 'with_prices'=True agrega resumen de precios."
#     ),
#     func=get_availability_by_uid,
# )


# QUERY_PLATFORMS_FOR_TITLE_TOOL = Tool.from_function(
#     name="query_platforms_for_title",
#     description="Plataformas que llevan un UID (con límite configurable)",
#     func=query_platforms_for_title,
# )


# QUERY_PLATFORMS_FOR_UID_BY_COUNTRY_TOOL = Tool.from_function(
#     name="query_platforms_for_uid_by_country",
#     description="Plataformas para un UID dentro de un país (si no hay país, cae a consulta genérica)",
#     func=query_platforms_for_uid_by_country,
# )


GET_PLATFORM_EXCLUSIVES_TOOL = Tool.from_function(
    name="get_platform_exclusives",
    description="Get exclusive titles available on a specific platform within a country. Requires platform_name and country (ISO-2 code, defaults to US). Returns list of exclusive content (uid, title, type) available only on that platform in the specified country. Useful for discovering platform-specific content.",
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
        "Get recent content premieres available in a specific country within the last 7 days. "
        "Requires country (ISO-2 code). Parameter days_back is fixed at 7 days (policy restriction). "
        "Returns titles with release dates, aggregated platforms, and platform countries where available. "
        "Useful for discovering new releases in a specific market."
    ),
    func=get_recent_premieres_by_country,
)


ALL_AVAILABILITY_TOOLS = [
    # Availability
    # GET_AVAILABILITY_BY_UID_TOOL,
    # QUERY_PLATFORMS_FOR_TITLE_TOOL,
    # QUERY_PLATFORMS_FOR_UID_BY_COUNTRY_TOOL,
    GET_PLATFORM_EXCLUSIVES_TOOL,
    COMPARE_PLATFORMS_FOR_TITLE_TOOL,
    GET_RECENT_PREMIERES_BY_COUNTRY_TOOL,
]
