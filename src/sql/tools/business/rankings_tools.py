from src.sql.utils.default_import import *
from src.sql.modules.business.rankings import *

# =============================================================================
# Rankings Tools
# =============================================================================
# GENRE_MOMENTUM_TOOL = Tool.from_function(
#     name="genre_momentum",
#     description="[advanced] Ranking de géneros por crecimiento (ventana actual vs ventana previa).",
#     func=get_genre_momentum,
# )

# class GenreMomentumArgs(BaseModel):
#     country: str | None = Field(None, description="ISO-2 o 'global'")
#     days: int = Field(30, ge=1)
#     prev_days: int | None = Field(None, ge=1)
#     content_type: str | None = Field(None, description="'movie' o 'series'")
#     preset: str | None = Field(None, description="last_30d|last_60d|last_90d|last_year|last_12m|last_5_years|global")
#     limit: int = Field(20, ge=1, le=200)

GENRE_MOMENTUM_TOOL = StructuredTool.from_function(
    name="genre_momentum",
    description=(
        "Ranking de géneros por crecimiento. "
        "Con país → ms.hits_presence; sin país/global → ms.hits_global. "
        "Admite 'preset' (last_30d/60d/90d/last_year/last_12m/last_5_years/global). "
        "Ancla ventanas a MAX(date_hits)."
    ),
    func=get_genre_momentum,
)

# PLATFORMS_FOR_TITLE_QUERY_TOOL = Tool.from_function(
#     name="platforms_for_title_query",
#     description="[advanced] Plataformas por UID (consulta directa, no wrapper).",
#     func=query_platforms_for_title,
# )


# PLATFORMS_FOR_UID_BY_COUNTRY_QUERY_TOOL = Tool.from_function(
#     name="platforms_for_uid_by_country_query",
#     description="[advanced] Plataformas por UID y país (consulta directa).",
#     func=query_platforms_for_uid_by_country,
# )


PLATFORM_EXCLUSIVES_QUERY_TOOL = Tool.from_function(
    name="platform_exclusives_query",
    description="[advanced] Exclusivos por plataforma y país (consulta directa).",
    func=get_platform_exclusives,
)


# COMPARE_PLATFORMS_FOR_TITLE_TOOL = Tool.from_function(
#     name="compare_platforms_for_title",
#     description="Comparar plataformas que tienen un título (match exacto).",
#     func=compare_platforms_for_title,
# )


TOP_BY_UID_TOOL = Tool.from_function(
    name="top_by_uid",
    description="Rating/top por UID (global).",
    func=get_top_by_uid,
)


TOP_BY_COUNTRY_QUERY_TOOL = Tool.from_function(
    name="top_by_country_query",
    description="Top por país (consulta directa) con año opcional.",
    func=new_top_by_country_tool,
)


TOP_GENERIC_QUERY_TOOL = Tool.from_function(
    name="top_generic_query",
    description="Top genérico (consulta directa); rutea a presence/global según país/región.",
    func=get_top_generic_tool,
)


TOP_PRESENCE_TOOL = Tool.from_function(
    name="top_presence",
    description="[advanced] Top en tabla de presencia (requiere ISO resuelto o iso_set).",
    func=get_top_generic_tool,
)


TOP_GLOBAL_TOOL = Tool.from_function(
    name="top_global",
    description="[advanced] Top en tabla global de hits (con filtros por tipo, plataforma y género).",
    func=get_top_generic_tool,
)


# TOP_BY_GENRE_TOOL = Tool.from_function(
#     name="top_by_genre",
#     description="[SIMPLE] Solo por género, SIN otros filtros. Si necesitas género+tipo, usa top_generic_query.",
#     func=get_top_by_genre_tool,
# )

TOP_BY_TYPE_TOOL = Tool.from_function(
    name="top_by_type",
    description="[SIMPLE] Solo por tipo (movie/series), SIN otros filtros. Si necesitas tipo+género, usa top_generic_query.",
    func=get_top_by_type_tool,
)

TOP_BY_GENRE_IN_PLATFORM_COUNTRY_TOOL = Tool.from_function(
    name="top_by_genre_in_platform_country",
    description="Convenience: top por género dentro de una plataforma y país.",
    func=get_top_by_genre_in_platform_country,
)

ALL_RANKING_TOOLS = [
    # Rankings Tools
    GENRE_MOMENTUM_TOOL,
    # PLATFORMS_FOR_TITLE_QUERY_TOOL,
    # PLATFORMS_FOR_UID_BY_COUNTRY_QUERY_TOOL,
    # COMPARE_PLATFORMS_FOR_TITLE_TOOL,
    PLATFORM_EXCLUSIVES_QUERY_TOOL,
    TOP_BY_UID_TOOL,
    TOP_BY_COUNTRY_QUERY_TOOL,
    TOP_GENERIC_QUERY_TOOL,
    TOP_PRESENCE_TOOL,
    TOP_GLOBAL_TOOL,
    # TOP_BY_GENRE_TOOL,
    TOP_BY_TYPE_TOOL,
    TOP_BY_GENRE_IN_PLATFORM_COUNTRY_TOOL,
]
