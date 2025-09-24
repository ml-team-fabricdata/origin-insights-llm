from src.sql.utils.default_import import *
from src.sql.business.pricing import *
from src.sql.business.rankings import *
from src.sql.business.intelligence import *

# =============================================================================
# Intelligence Tools
# =============================================================================
PLATFORM_EXCLUSIVITY_COUNTRY_TOOL = Tool.from_function(
    name="get_platform_exclusivity_by_country",
    description=(
        "Count of exclusive titles for a platform in a given country (ISO-2). "
        "Returns a JSON-serializable list of rows."
    ),
    func=get_platform_exclusivity_by_country,
)

CATALOG_SIMILARITY_TOOL = Tool.from_function(
    name="catalog_similarity_for_platform",
    description=(
        "Similarity of a platform's catalog between two countries (ISO-2). "
        "Returns totals, shared/unique counts, and similarity_percentage (0–100)."
    ),
    func=catalog_similarity_for_platform,
)

TITLES_DIFFERENCE_TOOL = Tool.from_function(
    name="titles_in_A_not_in_B",
    description=(
        "Titles present in country_in and NOT in country_not_in (ISO-2). "
        "Optional platform filter applies the same platform to both countries."
    ),
    func=titles_in_A_not_in_B_sql,
)
# =============================================================================
# Pricing Tools
# =============================================================================
PRESENCE_WITH_PRICE_TOOL = Tool.from_function(
    name="query_presence_prices",
    description=(
        "Returns availability from ms.new_cp_presence along with LATEST valid "
        "price from ms.new_cp_presence_prices (JOIN by hash_unique using LEFT "
        "JOIN LATERAL). By default: active_only_presence=True and "
        "active_only_price=True."
    ),
    func=query_presence_with_price,
)

PRICES_LATEST_TOOL = Tool.from_function(
    name="prices_latest",
    description=(
        "Últimos precios por hash/uid y/o filtros de país/plataforma. "
        "Soporta price_type, definition, license, currency, min/max y limit. "
        "Devuelve filas JSON-serializables ordenadas por created_at DESC."
    ),
    func=tool_prices_latest,
)

PRICES_HISTORY_TOOL = Tool.from_function(
    name="prices_history",
    description=(
        "Histórico de precios con joins opcionales a presencia (uid/country/plataforma). "
        "Permite title_like y filtros por tipo/definición/licencia/moneda/rango de precio."
    ),
    func=tool_prices_history,
)

PRICES_CHANGES_TOOL = Tool.from_function(
    name="prices_changes_last_n_days",
    description=(
        "Cambios de precio en los últimos N días (direction: down|up|all). "
        "Scope por hash/uid/país; filtros por platform_code y price_type."
    ),
    func=tool_prices_changes_last_n_days,
)


PRICES_STATS_TOOL = Tool.from_function(
    name="prices_stats",
    description=(
        "Estadísticas de precios (min, max, avg, median, pXX, stddev, count) con filtros por "
        "país, plataforma (name/code), price_type, definición, licencia y moneda."
    ),
    func=tool_prices_stats,
)


HITS_WITH_QUALITY_TOOL = Tool.from_function(
    name="hits_with_quality",
    description=(
        "Hits (popularidad) con filtros de calidad. Scope global o por país ISO-2. "
        "Si 'fallback_when_empty' está activo, reintenta sin 'definition' cuando no hay resultados."
    ),
    func=tool_hits_with_quality,
)

# =============================================================================
# Rankings Tools
# =============================================================================
GENRE_MOMENTUM_TOOL = Tool.from_function(
name="genre_momentum",
description="[advanced] Ranking de géneros por crecimiento (ventana actual vs ventana previa).",
func=get_genre_momentum,
)


PLATFORMS_FOR_TITLE_QUERY_TOOL = Tool.from_function(
name="platforms_for_title_query",
description="[advanced] Plataformas por UID (consulta directa, no wrapper).",
func=query_platforms_for_title,
)


PLATFORMS_FOR_UID_BY_COUNTRY_QUERY_TOOL = Tool.from_function(
name="platforms_for_uid_by_country_query",
description="[advanced] Plataformas por UID+país (consulta directa).",
func=query_platforms_for_uid_by_country,
)


PLATFORM_EXCLUSIVES_QUERY_TOOL = Tool.from_function(
name="platform_exclusives_query",
description="[advanced] Exclusivos por plataforma y país (consulta directa).",
func=get_platform_exclusives,
)


COMPARE_PLATFORMS_FOR_TITLE_TOOL = Tool.from_function(
name="compare_platforms_for_title",
description="Comparar plataformas que tienen un título (match exacto).",
func=compare_platforms_for_title,
)


TOP_BY_UID_TOOL = Tool.from_function(
name="top_by_uid",
description="Rating/top por UID (global).",
func=get_top_by_uid,
)


TOP_BY_COUNTRY_QUERY_TOOL = Tool.from_function(
name="top_by_country_query",
description="Top por país (consulta directa) con año opcional.",
func=get_top_by_country,
)


TOP_GENERIC_QUERY_TOOL = Tool.from_function(
name="top_generic_query",
description="Top genérico (consulta directa); rutea a presence/global según país/región.",
func=get_top_generic,
)


TOP_PRESENCE_TOOL = Tool.from_function(
name="top_presence",
description="[advanced] Top en tabla de presencia (requiere ISO resuelto o iso_set).",
func=get_top_presence,
)


TOP_GLOBAL_TOOL = Tool.from_function(
name="top_global",
description="[advanced] Top en tabla global de hits (con filtros por tipo, plataforma y género).",
func=get_top_global,
)


TOP_BY_GENRE_TOOL = Tool.from_function(
name="top_by_genre",
description="Convenience: top por género (usa top_generic).",
func=get_top_by_genre,
)


TOP_BY_TYPE_TOOL = Tool.from_function(
name="top_by_type",
description="Convenience: top por tipo (movie/series).",
func=get_top_by_type,
)


TOP_BY_GENRE_IN_PLATFORM_COUNTRY_TOOL = Tool.from_function(
name="top_by_genre_in_platform_country",
description="Convenience: top por género dentro de una plataforma y país.",
func=get_top_by_genre_in_platform_country,
)


ALL_BUSINESS_TOOLS = [
    # Intelligence Tools
    PLATFORM_EXCLUSIVITY_COUNTRY_TOOL,
    CATALOG_SIMILARITY_TOOL,
    TITLES_DIFFERENCE_TOOL,
    # Pricing Tools
    PRESENCE_WITH_PRICE_TOOL,
    PRICES_LATEST_TOOL,
    PRICES_HISTORY_TOOL,
    PRICES_CHANGES_TOOL,
    PRICES_STATS_TOOL,
    HITS_WITH_QUALITY_TOOL,
    # Rankings Tools
    GENRE_MOMENTUM_TOOL,
    PLATFORMS_FOR_TITLE_QUERY_TOOL,
    PLATFORMS_FOR_UID_BY_COUNTRY_QUERY_TOOL,
    PLATFORM_EXCLUSIVES_QUERY_TOOL,
    COMPARE_PLATFORMS_FOR_TITLE_TOOL,
    TOP_BY_UID_TOOL,
    TOP_BY_COUNTRY_QUERY_TOOL,
    TOP_GENERIC_QUERY_TOOL,
    TOP_PRESENCE_TOOL,
    TOP_GLOBAL_TOOL,
    TOP_BY_GENRE_TOOL,
    TOP_BY_TYPE_TOOL,
    TOP_BY_GENRE_IN_PLATFORM_COUNTRY_TOOL,
]
