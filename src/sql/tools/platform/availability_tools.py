from langchain_core.tools import Tool
from src.sql.modules.platform.availability import *

# =============================================================================
# Availability
# =============================================================================

GET_AVAILABILITY_BY_UID_TOOL = Tool.from_function(
    name="get_availability_by_uid",
    description=(
        "Disponibilidad por UID; si se indica 'country' restringe por país. "
        "Con 'with_prices'=True agrega resumen de precios."
    ),
    func=get_availability_by_uid,
)


QUERY_PLATFORMS_FOR_TITLE_TOOL = Tool.from_function(
    name="query_platforms_for_title",
    description="Plataformas que llevan un UID (con límite configurable)",
    func=query_platforms_for_title,
)


# QUERY_PLATFORMS_FOR_UID_BY_COUNTRY_TOOL = Tool.from_function(
#     name="query_platforms_for_uid_by_country",
#     description="Plataformas para un UID dentro de un país (si no hay país, cae a consulta genérica)",
#     func=query_platforms_for_uid_by_country,
# )


GET_PLATFORM_EXCLUSIVES_TOOL = Tool.from_function(
    name="get_platform_exclusives",
    description="Títulos exclusivos de una plataforma dentro de un país (ISO-2)",
    func=get_platform_exclusives,
)


COMPARE_PLATFORMS_FOR_TITLE_TOOL = Tool.from_function(
    name="compare_platforms_for_title",
    description="Comparación: qué plataformas tienen un título (match exacto)",
    func=compare_platforms_for_title,
)


GET_RECENT_PREMIERES_BY_COUNTRY_TOOL = Tool.from_function(
    name="get_recent_premieres_by_country",
    description=(
        "Estrenos recientes disponibles en un país dentro de la ventana 'days_back' (policy: 7 días)."
    ),
    func=get_recent_premieres_by_country,
)


ALL_AVAILABILITY_TOOLS = [
    # Availability
    GET_AVAILABILITY_BY_UID_TOOL,
    QUERY_PLATFORMS_FOR_TITLE_TOOL,
    # QUERY_PLATFORMS_FOR_UID_BY_COUNTRY_TOOL,
    GET_PLATFORM_EXCLUSIVES_TOOL,
    COMPARE_PLATFORMS_FOR_TITLE_TOOL,
    GET_RECENT_PREMIERES_BY_COUNTRY_TOOL,
]
