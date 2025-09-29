from src.sql.utils.default_import import *
from src.sql.modules.business.rankings import *

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


ALL_RANKING_TOOLS = [
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
