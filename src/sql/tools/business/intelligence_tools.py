from src.sql.utils.default_import import *
from src.sql.modules.business.intelligence import *

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


TITLES_DIFFERENCE_TOOL = StructuredTool.from_function(
    name="titles_in_A_not_in_B",
    description=(
        "Find titles available on a platform in location A but NOT in location B. "
        "Both parameters accept either individual countries (ISO-2 codes like 'US', 'JP', 'MX') "
        "or regions ('LATAM', 'EU', 'ASIA', 'OCEANIA', 'AFRICA', 'MENA'). "
        "Optional platform filter (e.g., 'netflix', 'prime', 'disney+') applies to both locations. "
        "Examples: US vs JP, US vs ASIA, LATAM vs EU, MX vs LATAM. "
        "Returns up to 'limit' titles (default 50, max 200)."
    ),
    func=titles_in_A_not_in_B_sql,
)

ALL_INTELLIGENCE_TOOLS = [
    # Intelligence Tools
    PLATFORM_EXCLUSIVITY_COUNTRY_TOOL,
    CATALOG_SIMILARITY_TOOL,
    TITLES_DIFFERENCE_TOOL,
]
