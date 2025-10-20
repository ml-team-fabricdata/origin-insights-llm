from src.strands.utils.default_import import *
from src.sql.modules.business.rankings import *

# =============================================================================
# Rankings Tools
# =============================================================================


GENRE_MOMENTUM_TOOL = StructuredTool.from_function(
    name="genre_momentum",
    description=(
        "Ranking de géneros por crecimiento comparando un período actual vs. uno previo. "
        "Si se especifica país, usa presencia (ms.hits_presence); sin país usa global. "
        "Parámetros: country (ISO-2 opcional), content_type ('Movie'/'Series' opcional), "
        "limit (por defecto 20), days_back (días del período actual; el previo replica ese tamaño). "
        "Las ventanas se anclan a MAX(date_hits) de la tabla."
    ),
    func=get_genre_momentum,
)


TOP_BY_UID_TOOL = Tool.from_function(
    name="top_by_uid",
    description=(
        "Rating/top por UID (global). Requiere 'uid'. Devuelve el ranking agregado para el título."
    ),
    func=get_top_by_uid,
)


TOP_BY_COUNTRY_QUERY_TOOL = Tool.from_function(
    name="top_by_country_query",
    description=(
        "Top por país con año opcional. Internamente rutea a la query genérica con country+year. "
        "Parámetros: country (ISO-2 requerido), year (opcional), limit (por defecto 20)."
    ),
    func=new_top_by_country_tool,
)


TOP_GENERIC_QUERY_TOOL = Tool.from_function(
    name="top_generic_query",
    description=(
        "Top genérico con filtros flexibles; rutea automáticamente a presencia si hay país/región, "
        "sino a global. Filtros: country/region/countries_list, platform, genre, content_type, "
        "ventana temporal (days_back o date_from/date_to) o año (currentyear/year/year_from/year_to), "
        "más limit."
    ),
    func=get_top_generic_tool,
)


TOP_PRESENCE_TOOL = Tool.from_function(
    name="top_presence",
    description=(
        "Top en tabla de presencia (requiere ISO resuelto o iso_set). Acepta filtros por "
        "platform, genre, content_type y ventanas/años. Se ancla la ventana rolling a MAX(date_hits)."
    ),
    func=get_top_generic_tool,
)


TOP_GLOBAL_TOOL = Tool.from_function(
    name="top_global",
    description=(
        "Top global (sin país). Puede filtrar por genre y/o content_type (requiere metadata) "
        "y por platform (requiere join a presencia). Soporta days_back, date_from/date_to y años."
    ),
    func=get_top_generic_tool,
)


ALL_RANKING_TOOLS = [
    # Rankings Tools
    GENRE_MOMENTUM_TOOL,
    TOP_BY_UID_TOOL,
    TOP_BY_COUNTRY_QUERY_TOOL,
    TOP_GENERIC_QUERY_TOOL,
    TOP_PRESENCE_TOOL,
    TOP_GLOBAL_TOOL,
]
