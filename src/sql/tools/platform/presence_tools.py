from langchain_core.tools import Tool
from src.sql.modules.platform.presence import *

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


GET_AVAILABILITY_BY_UID_PRICE_TOOL = StructuredTool.from_function(
    name="get_availability_by_uid_price",
    description=(
        "Disponibilidad por UID (opcionalmente scoping por país) con precios, si 'with_prices' es True, "
        "incluye resumen de precios (rango, monedas, conteos)."
    ),
    func=get_availability_by_uid_price,
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
