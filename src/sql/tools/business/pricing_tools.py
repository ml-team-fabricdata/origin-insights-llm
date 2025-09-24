from src.sql.utils.default_import import *
from src.sql.modules.business.pricing import *

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

ALL_PRICING_TOOLS = [
    # Pricing Tools
    PRESENCE_WITH_PRICE_TOOL,
    PRICES_LATEST_TOOL,
    PRICES_HISTORY_TOOL,
    PRICES_CHANGES_TOOL,
    PRICES_STATS_TOOL,
    HITS_WITH_QUALITY_TOOL,
]
