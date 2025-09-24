from src.sql.default_import import *
from src.sql.business.pricing import *
from src.sql.business.rankings import *
from src.sql.business.intelligence import *

# =============================================================================
# Intelligence Tools
# =============================================================================
PLATFORM_EXCLUSIVITY_COUNTRY_TOOL = StructuredTool.from_function(
    name="get_platform_exclusivity_by_country",
    description=(
        "Count of exclusive titles per platform in a given country (ISO-2). "
        "Params: platform_name:str, country:str, limit:int."
    ),
    func=get_platform_exclusivity_by_country,
)

CATALOG_SIMILARITY_TOOL = Tool.from_function(
    name="catalog_similarity_for_platform",
    description=(
        "Calculates similarity (Jaccard) of a platform catalog between two "
        "countries (ISO-2)."
    ),
    func=catalog_similarity_for_platform,
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

# =============================================================================
# Rankings Tools
# =============================================================================
TOP_GENERIC_TOOL = StructuredTool.from_function(
    name="get_top_generic_tool",
    description=(
        "Top, popular, rating or ranking by hits with filters for content "
        "type, genre, country(ISO-2)|region|countries_list, platform, time "
        "range and year."
    ),
    func=get_top_generic,
)

TOP_BY_UID_TOOL = Tool.from_function(
    name="get_top_by_uid",
    description=(
        "Top records for a given UID (hits-based). Params: uid:str."
    ),
    func=get_top_by_uid,
)

PLATFORMS_FOR_UID_BY_COUNTRY_TOOL = Tool.from_function(
    name="query_platforms_for_uid_by_country",
    description=(
        "List platforms for a specific UID, optionally filtered by ISO-2 "
        "country. Preferred over title-based comparison due to precision."
    ),
    func=query_platforms_for_uid_by_country,
)

PLATFORM_EXCLUSIVES_TOOL = Tool.from_function(
    name="get_platform_exclusives",
    description=(
        "Exclusive, active titles for a platform within a country (ISO-2). "
        "Params: platform_name:str, country:str, limit:int."
    ),
    func=get_platform_exclusives,
)

RECENT_PREMIERES_BY_COUNTRY_TOOL = Tool.from_function(
    name="get_recent_premieres_by_country",
    description=(
        "Recent premieres/out_on within a day-window for a country (ISO-2). "
        "Params: country:str, days_back:int=7, limit:int."
    ),
    func=get_recent_premieres_by_country,
)

ALL_BUSINESS_TOOLS = [
    PLATFORM_EXCLUSIVITY_COUNTRY_TOOL,
    CATALOG_SIMILARITY_TOOL,
    PRESENCE_WITH_PRICE_TOOL,
    TOP_GENERIC_TOOL,
    TOP_BY_UID_TOOL,
    PLATFORMS_FOR_UID_BY_COUNTRY_TOOL,
    PLATFORM_EXCLUSIVES_TOOL,
    RECENT_PREMIERES_BY_COUNTRY_TOOL,
]