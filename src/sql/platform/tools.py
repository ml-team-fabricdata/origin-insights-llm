from langchain_core.tools import Tool
from src.sql.platform.presence import *
from src.sql.platform.availability import *

# =============================================================================
# Presence
# =============================================================================

PRESENCE_COUNT_TOOL = Tool.from_function(
    name="presence_count",
    description="Conteo de registros de presencia con filtros opcionales (country, platform, uid, type, title_like).",
    func=presence_count,
)


PRESENCE_LIST_TOOL = Tool.from_function(
    name="presence_list",
    description=(
        "Listado de presencia con paginación/orden. 'order_by' debe estar en PRESENCE_ALLOWED_ORDER; "
        "'order_dir' ∈ {ASC, DESC}."
    ),
    func=presence_list,
)


PRESENCE_DISTINCT_TOOL = Tool.from_function(
    name="presence_distinct",
    description=(
        "Valores distintos para columnas permitidas (iso_alpha2, plan_name, platform_code, platform_name, type, content_type)."
    ),
    func=presence_distinct,
)


PRESENCE_STATISTICS_TOOL = Tool.from_function(
    name="presence_statistics",
    description="Resumen estadístico de presencia (por país/plataforma/tipo).",
    func=presence_statistics,
)


GET_AVAILABILITY_BY_UID_TOOL = Tool.from_function(
    name="get_availability_by_uid",
    description=(
        "Disponibilidad por UID (opcionalmente scoping por país) y, si 'with_prices' es True, "
        "incluye resumen de precios (rango, monedas, conteos)."
    ),
    func=get_availability_by_uid,
)


PLATFORM_COUNT_BY_COUNTRY_TOOL = Tool.from_function(
    name="platform_count_by_country",
    description="Conteo de plataformas por país o global si no se especifica.",
    func=platform_count_by_country,
)


COUNTRY_PLATFORM_SUMMARY_TOOL = Tool.from_function(
    name="country_platform_summary",
    description="Resumen de plataformas y contenido por país (si se indica) o global.",
    func=country_platform_summary,
)


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


QUERY_PLATFORMS_FOR_UID_BY_COUNTRY_TOOL = Tool.from_function(
    name="query_platforms_for_uid_by_country",
    description="Plataformas para un UID dentro de un país (si no hay país, cae a consulta genérica)",
    func=query_platforms_for_uid_by_country,
)


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


ALL_PLATFORM_TOOLS = [
    # Presence
    PRESENCE_COUNT_TOOL,
    PRESENCE_LIST_TOOL,
    PRESENCE_DISTINCT_TOOL,
    PRESENCE_STATISTICS_TOOL,
    GET_AVAILABILITY_BY_UID_TOOL,
    PLATFORM_COUNT_BY_COUNTRY_TOOL,
    COUNTRY_PLATFORM_SUMMARY_TOOL,

    # Availability
    GET_AVAILABILITY_BY_UID_TOOL,
    QUERY_PLATFORMS_FOR_TITLE_TOOL,
    QUERY_PLATFORMS_FOR_UID_BY_COUNTRY_TOOL,
    GET_PLATFORM_EXCLUSIVES_TOOL,
    COMPARE_PLATFORMS_FOR_TITLE_TOOL,
    GET_RECENT_PREMIERES_BY_COUNTRY_TOOL,

]
