"""LangChain Tools for Multimedia Database Operations.

This module exposes a registry of LangChain tools for querying and
analyzing multimedia content data (titles, actors, directors, platforms,
pricing, and availability). It keeps a strict policy around input
validation (e.g., title/actor/director disambiguation and ISO-2 country
codes) and provides safe wrappers over database access.
"""
from __future__ import annotations

from typing import Any, Optional
import json

from langchain_core.tools import StructuredTool, Tool

# Database connection (imported for side-effects/compat)
from common.sql_db import db  # noqa: F401

# ---------------------------------------------------------------------------
# Business logic imports (explicit to avoid star-imports and aid static tooling)
# ---------------------------------------------------------------------------
# akas
from .akas import *

# platform queries
from .platform_queries import *
# top / ranking tools
from .top_tools import *
# cast / director
from .cast_director import *
# hits with quality / prices
from .hits_with_quality import *

# presence + prices
from .presence_with_price_tools import *
from .presence_prices_tools import *
from .presence_simple_tools import *

# metadata
from .metadata_simple_tools import *

# misc analytics
from .sql_builder import run_sql_adapter
from .constants_sql import ALLOWED_TABLES
from .platform_queries import *
from .top_tools import *

# =============================================================================
# Policy constants
# =============================================================================
POLICY_STOP_ON_AMBIGUITY = (
    "Policy: NEVER proceed if the resolver returns status in {\"ambiguous\",\n"
    "\"not_found\"}. If ambiguous: show the provided options and ask the\n"
    "user to choose ONE. If not_found: explain what you tried (e.g., country\n"
    "ISO or platform names) and suggest a correction."
)

POLICY_COUNTRY = (
    "Country input MUST be ISO-2 (e.g., 'US','AR','ES'). The tool internally\n"
    "resolves user text to platform_name_iso."
)

POLICY_TITLE = (
    "Titles MUST be validated first with 'validate_title'. Do not call\n"
    "platform/detail tools without a resolved UID."
)

POLICY_PARAMS = (
    "Validate and sanitize numeric params (limit, days_back) with built-in\n"
    "caps. Never pass raw user strings to SQL."
)

# =============================================================================
# Raw SQL tool (admin/backoffice)
# =============================================================================
RAW_SQL_TOOL = Tool(
    name="run_sql",
    func=run_sql_adapter,
    description=(
        "Executes raw parameterized SQL queries against the `ms` multimedia "
        "database schema. Allowed tables: "
        + ", ".join(ALLOWED_TABLES)
        + ". \n\u26a0\ufe0f Use ONLY for admin/backoffice tasks when no higher-level "
        "wrapper exists. Expected params: query:str, params:Sequence[Any]."
    ),
)

# =============================================================================
# Content validation tools
# =============================================================================
VALIDATE_TITLE_TOOL = Tool(
    name="validate_title",
    func=validate_title,
    description=(
        "MANDATORY: Validates titles and returns status. If status='ambiguous': "
        "SHOW list of options to user and STOP. Do NOT continue until user "
        "chooses. If status='resolved': can continue with returned UID."
    ),
)

VALIDATE_ACTOR_TOOL = Tool.from_function(
    name="validate_actor",
    description=(
        "MANDATORY: Validates ACTORS by name and returns status. If "
        "status='ambiguous': SHOW list of options to user and STOP. Do NOT "
        "continue until user chooses. If status='resolved': can continue with "
        "returned UID."
    ),
    func=validate_actor,
)

VALIDATE_DIRECTOR_TOOL = Tool.from_function(
    name="validate_director",
    description=(
        "MANDATORY: Validates DIRECTORS by name and returns status. If "
        "status='ambiguous': SHOW list of options to user and STOP. Do NOT "
        "continue until user chooses. If status='resolved': can continue with "
        "returned UID."
    ),
    func=validate_director,
)

# =============================================================================
# Content information tools
# =============================================================================
# FILMOGRAPHY_BY_UID_TOOL = Tool(
#     name="answer_filmography_by_uid",
#     func=lambda *a, **k: _deprecated_alias(*a, **k),  # preserved; see alias below
#     description=(
#         "ONLY use after having UID confirmed by user. Returns filmography/"
#         "profile information. (Alias maintained for backward compatibility.)"
#     ),
# )

ANSWER_FILMOGRAPHY_BY_UID = Tool(
    name="answer_filmography_by_uid",
    func=get_filmography_by_uid,
    description="ONLY use after having UID confirmed by user. Returns filmography/profile information.",
)

TITLE_RATING_TOOL = Tool.from_function(
    name="get_title_rating",
    description=f"Rating/score for a title by UID. {POLICY_TITLE}",
    func=get_title_rating,
)

# =============================================================================
# Actor analysis tools
# =============================================================================
ACTOR_FILMOGRAPHY_BY_NAME_TOOL = Tool.from_function(
    name="answer_actor_filmography",
    description=(
        "Filmography of an ACTOR (by name). Validates the name; if ambiguous, "
        "returns options instead of guessing."
    ),
    func=answer_actor_filmography,
)

ACTOR_COACTORS_BY_NAME_TOOL = Tool.from_function(
    name="answer_actor_coactors",
    description=(
        "List of CO-ACTORS who worked with an ACTOR (by name). Validates the "
        "name; if ambiguous, returns options."
    ),
    func=answer_actor_coactors,
)

ACTOR_FILMOGRAPHY_BY_ID_TOOL = Tool.from_function(
    name="get_actor_filmography",
    description=(
        "Filmography of an ACTOR by ID (efficient path, no hits). Use if you "
        "already resolved the actor_id."
    ),
    func=get_actor_filmography,
)

ACTOR_COACTORS_BY_ID_TOOL = Tool.from_function(
    name="get_actor_coactors",
    description=(
        "Co-actors of an ACTOR by ID. Use if you already resolved the "
        "actor_id."
    ),
    func=get_actor_coactors,
)

# =============================================================================
# Director analysis tools
# =============================================================================
DIRECTOR_FILMOGRAPHY_BY_NAME_TOOL = StructuredTool.from_function(
    name="answer_director_filmography",
    description=(
        "Filmography of a DIRECTOR (by name). Validates the name; if "
        "ambiguous, returns options."
    ),
    func=answer_director_filmography,
)

DIRECTOR_CODIRECTORS_BY_NAME_TOOL = Tool.from_function(
    name="answer_director_codirectors",
    description=(
        "Co-directors of a DIRECTOR (by name). Validates the name; if "
        "ambiguous, returns options."
    ),
    func=answer_director_codirectors,
)

DIRECTOR_FILMOGRAPHY_BY_ID_TOOL = Tool.from_function(
    name="get_director_filmography",
    description=(
        "Filmography of a DIRECTOR by ID (efficient path, no hits). Use if you "
        "already resolved the director_id."
    ),
    func=get_director_filmography,
)

DIRECTOR_CODIRECTORS_BY_ID_TOOL = Tool.from_function(
    name="get_director_codirectors",
    description=(
        "Co-directors of a DIRECTOR by ID. Use if you already resolved the "
        "director_id."
    ),
    func=get_director_codirectors,
)

COMMON_PROJECTS_BY_IDS_TOOL = Tool.from_function(
    name="get_common_projects_actor_director",
    description=(
        "Common projects between an ACTOR and DIRECTOR using combined ID format. "
        "Expected input: 'actor_id_director_id' (e.g., '1302077_239033')."
    ),
    func=get_common_projects_wrapper,
)

# =============================================================================
# Platform and availability tools
# =============================================================================
PLATFORMS_FOR_UID_BY_COUNTRY_TOOL = Tool.from_function(
    name="query_platforms_for_uid_by_country",
    description=(
        "List platforms for a specific UID, optionally filtered by ISO-2 "
        "country. Preferred over title-based comparison due to precision.\n"
        f"{POLICY_COUNTRY}"
    ),
    func=query_platforms_for_uid_by_country,
)

PLATFORM_EXCLUSIVES_TOOL = Tool.from_function(
    name="get_platform_exclusives",
    description=(
        "Exclusive, active titles for a platform within a country (ISO-2). "
        "Params: platform_name:str, country:str, limit:int.\n"
        f"{POLICY_COUNTRY}"
    ),
    func=get_platform_exclusives,
)

RECENT_PREMIERES_BY_COUNTRY_TOOL = Tool.from_function(
    name="get_recent_premieres_by_country",
    description=(
        "Recent premieres/out_on within a day-window for a country (ISO-2). "
        "Params: country:str, days_back:int=7, limit:int.\n"
        f"{POLICY_COUNTRY}"
    ),
    func=get_recent_premieres_by_country_tool,
)

AVAILABILITY_BY_UID_TOOL = Tool.from_function(
    name="fetch_availability_by_uid",
    description=(
        "Gets current availability for a UID in presence. Filter by country "
        "(ISO-2) ONLY if user specified. Optional: with_prices=True to include "
        "latest price. "
        f"{POLICY_COUNTRY}"
    ),
    func=fetch_availability_by_uid,
)

# =============================================================================
# Analytics and ranking tools
# =============================================================================
TOP_GENERIC_TOOL = StructuredTool.from_function(
    name="get_top_generic_tool",
    description=(
        "Top, popular, rating or ranking by hits with filters for content "
        "type, genre, country(ISO-2)|region|countries_list, platform, time "
        "range and year."
    ),
    func=get_top_generic_tool,
)

TOP_BY_UID_TOOL = Tool.from_function(
    name="get_top_by_uid",
    description=(
        "Top records for a given UID (hits-based). Params: uid:str, "
        "limit_related:int."
    ),
    func=get_top_by_uid,
)

PLATFORM_EXCLUSIVITY_COUNTRY_TOOL = StructuredTool.from_function(
    name="get_platform_exclusivity_by_country",
    description=(
        "Count of exclusive titles per platform in a given country (ISO-2). "
        "Params: platform_name:str, country:str, limit:int. "
        f"{POLICY_COUNTRY}"
    ),
    func=lambda platform_name, country, limit=100: (
        get_platform_exclusivity_by_country(platform_name, country, limit)
    ),
)

# =============================================================================
# Platform analytics tools
# =============================================================================
# PLATFORM_ACTORS_ANALYSIS_TOOL = Tool.from_function(
#     name="analyze_platform_actor_preferences",
#     description=(
#         "Actor coverage for a platform in a given country (ISO-2). Params: "
#         "platform:str, country:str, min_titles:int=2, limit:int.\n"
#         f"{POLICY_COUNTRY}"
#     ),
#     func=analyze_platform_actors,
# )

# PLATFORM_DIRECTORS_ANALYSIS_TOOL = Tool.from_function(
#     name="analyze_platform_directors",
#     description=(
#         "Director coverage for a platform in a given country (ISO-2). Params: "
#         "platform:str, country:str, min_titles:int=2, limit:int.\n"
#         f"{POLICY_COUNTRY}"
#     ),
#     func=analyze_platform_directors,
# )

# DIRECTOR_PLATFORM_DISTRIBUTION_TOOL = Tool.from_function(
#     name="analyze_director_platform_distribution",
#     description=(
#         "Distribution of a director's titles across platforms, optional "
#         "country filter. Params: director:str, country?:str, limit:int.\n"
#         f"{POLICY_COUNTRY}"
#     ),
#     func=analyze_platform_actors,
# )

CATALOG_SIMILARITY_TOOL = Tool.from_function(
    name="catalog_similarity_for_platform",
    description=(
        "Calculates similarity (Jaccard) of platform catalog between two "
        "countries (ISO-2)."
    ),
    func=analyze_platform_talent_summary,
)

EXCLUSIVES_IN_REGION_TOOL = Tool.from_function(
    name="platforms_with_most_exclusives_in_region",
    description=(
        "Ranks platforms by number of exclusive titles within a region/"
        "continent using only valid ISOs."
    ),
    func=platforms_with_most_exclusives_in_region,
)

# TITLES_DIFFERENCE_TOOL = Tool.from_function(
#     name="titles_in_A_not_in_B",
#     description=(
#         "Titles available in country_a and NOT in country_b using ISO-2. "
#         "Optionally filter by platform (same platform in both countries). "
#         f"{POLICY_COUNTRY}"
#     ),
#     func=titles_in_A_not_in_B_tool,
# )

# =============================================================================
# Quality and pricing tools
# =============================================================================
HITS_WITH_QUALITY_TOOL = StructuredTool.from_function(
    name="hits_with_quality",
    description=(
        "Platforms/prices by UID with quality/license filters. Params: uid "
        "(req), country?, definition?, license_?, limit?, scoped_by_country?"
    ),
    func=hits_with_quality_adapter,
)



PRICES_BY_UID_TOOL = Tool.from_function(
    name="prices_by_uid_query",
    description=(
        "With a UID, gets its hash_unique and then retrieves prices from "
        "ms.new_cp_presence_prices. Parameters: active_only_presence (True by "
        "default), iso_alpha2, platform_name, platform_code, latest_only "
        "(True: only latest price per hash_unique), active_only_price (True), "
        "currency (e.g. JPY), price_type, license, definition, select, limit, "
        "offset. Available columns: uid, hash_unique, platform_name, "
        "platform_code, iso_alpha2, price, currency, price_type, definition, "
        "license, out_on, created_at."
    ),
    func=query_prices_by_uid,
)

# =============================================================================
# Metadata query tools
# =============================================================================
METADATA_COUNT_TOOL = Tool.from_function(
    name="metadata_simple_all_count",
    description="Count of titles in ms.metadata_simple_all.",
    func=tool_metadata_count,
)

METADATA_LIST_TOOL = Tool.from_function(
    name="metadata_simple_all_list",
    description=(
        "Basic listing of ms.metadata_simple_all (search, pagination, order)."
    ),
    func=tool_metadata_list,
)

METADATA_DISTINCT_TOOL = Tool.from_function(
    name="metadata_simple_all_distinct",
    description=(
        "Unique values of safe metadata columns like type, country, title."
    ),
    func=tool_metadata_distinct,
)

METADATA_STATS_TOOL = Tool.from_function(
    name="metadata_simple_all_stats",
    description=(
        "Stats (count/min/max year, avg/median duration) in ms.metadata_simple_all."
    ),
    func=tool_metadata_stats,
)

METADATA_QUERY_TOOL = Tool.from_function(
    name="metadata_simple_all_query",
    description=(
        "Query metadata information with filters (type, year range, duration, "
        "genre/languages/country/directors/writers/cast) and search by title/"
        "synopsis. Safe parameters, ordering, limit and pagination. Use "
        "'count_only=True' to get only the count."
    ),
    func=query_metadata_simple_all,
)

# =============================================================================
# Presence query tools
# =============================================================================
PRESENCE_COUNT_TOOL = StructuredTool.from_function(
    name="new_cp_presence_count",
    description=(
        "Count rows/titles in new_cp_presence with common filters (country "
        "ISO-2 or alias iso/iso_alpha2, platform/platform_name, type, kids, "
        "exclusive, dates, active)."
    ),
    func=tool_presence_count,
)

PRESENCE_DISTINCT_TOOL = StructuredTool.from_function(
    name="new_cp_presence_distinct",
    description=(
        "Unique values from presence new_cp_presence. Params: column "
        "(platform_name|platform_code|iso_alpha2|plan_name|type), country?, "
        "limit?"
    ),
    func=tool_presence_distinct
)

PRESENCE_STATS_TOOL = Tool.from_function(
    name="new_cp_presence_stats",
    description=(
        "Basic stats about new_cp_presence (rows, unique titles, avg/median "
        "duration)."
    ),
    func=tool_presence_stats,
)

PRESENCE_QUERY_TOOL = Tool.from_function(
    name="presence_simple_query",
    description=(
        "Safe query on availability in ms.new_cp_presence table. Allows "
        "filtering by UID, country, platform, plan, package, title attributes "
        "and boolean flags (is_exclusive, is_original, etc.). By default "
        "returns only active titles (active_only=True: and "
        "(out_on IS NULL and registry_status='active').\n\n"
        "Use count_only=True to get only the count.\n"
        "Supported parameters: uid, iso_alpha2, platform_name, platform_code, "
        "package_code, package_code2, plan_name, type, title_like, "
        "is_exclusive, is_original, is_kids, is_local, isbranded, "
        "duration_min/duration_max, out_from/out_to, "
        "registry_status, active_only.\n"
        "Columns can be specified with select=[...] argument."
    ),
    func=query_presence_simple,
)

PRESENCE_WITH_PRICE_TOOL = Tool.from_function(
    name="query_presence_prices",
    description=(
        "Returns availability from ms.new_cp_presence along with LATEST valid "
        "price from ms.new_cp_presence_prices (JOIN by hash_unique using LEFT "
        "JOIN LATERAL). By default: active_only_presence=True and "
        "active_only_price=True. Selectable columns: all presence columns (id, "
        "uid, clean_title, type, platform_name, platform_code, iso_alpha2, "
        "enter_on, out_on, plan_name, etc.) and price-derived columns with "
        "'price_' prefix: price_amount, price_currency (e.g. JPY), "
        "price_type, price_definition, price_license, "
        "price_out_on, price_created_at. Supports count_only=True."
    ),
    func=query_presence_with_price,
)

# =============================================================================
# Trend analysis tools
# =============================================================================
GENRE_TRENDS_TOOL = Tool(
    name="genre_momentum_by_region",
    func=tool_genre_momentum_by_region,
    description=(
        "Compares presence by genre between the last quarter and previous "
        "quarter for a region (e.g., Asia). Accepts optional genres (list or "
        "JSON string). Returns delta and percentage change."
    ),
)

# =============================================================================
# Complete tool registry
# =============================================================================
ALL_SQL_TOOLS = [
    # Validation tools
    VALIDATE_TITLE_TOOL,
    VALIDATE_ACTOR_TOOL,
    VALIDATE_DIRECTOR_TOOL,

    # Content information
    TITLE_RATING_TOOL,
    ANSWER_FILMOGRAPHY_BY_UID,

    # Actor analysis
    ACTOR_FILMOGRAPHY_BY_NAME_TOOL,
    ACTOR_COACTORS_BY_NAME_TOOL,
    ACTOR_FILMOGRAPHY_BY_ID_TOOL,
    ACTOR_COACTORS_BY_ID_TOOL,

    # Director analysis
    DIRECTOR_FILMOGRAPHY_BY_NAME_TOOL,
    DIRECTOR_CODIRECTORS_BY_NAME_TOOL,
    DIRECTOR_FILMOGRAPHY_BY_ID_TOOL,
    DIRECTOR_CODIRECTORS_BY_ID_TOOL,
    COMMON_PROJECTS_BY_IDS_TOOL,

    # Platform and availability
    PLATFORMS_FOR_UID_BY_COUNTRY_TOOL,
    PLATFORM_EXCLUSIVES_TOOL,
    RECENT_PREMIERES_BY_COUNTRY_TOOL,
    AVAILABILITY_BY_UID_TOOL,

    # Analytics and ranking
    TOP_GENERIC_TOOL,
    TOP_BY_UID_TOOL,
    PLATFORM_EXCLUSIVITY_COUNTRY_TOOL,

    # Platform analytics
    # PLATFORM_ACTORS_ANALYSIS_TOOL,
    # PLATFORM_DIRECTORS_ANALYSIS_TOOL,
    # DIRECTOR_PLATFORM_DISTRIBUTION_TOOL,
    CATALOG_SIMILARITY_TOOL,
    EXCLUSIVES_IN_REGION_TOOL,
    # TITLES_DIFFERENCE_TOOL,

    # Quality and pricing
    HITS_WITH_QUALITY_TOOL,
    PRICES_BY_UID_TOOL,

    # Metadata queries
    METADATA_COUNT_TOOL,
    METADATA_LIST_TOOL,
    METADATA_DISTINCT_TOOL,
    METADATA_STATS_TOOL,
    METADATA_QUERY_TOOL,

    # Presence queries
    PRESENCE_COUNT_TOOL,
    PRESENCE_DISTINCT_TOOL,
    PRESENCE_STATS_TOOL,
    PRESENCE_QUERY_TOOL,
    PRESENCE_WITH_PRICE_TOOL,

    # Trend analysis
    GENRE_TRENDS_TOOL,

    # Raw SQL (admin use)
    RAW_SQL_TOOL,
]

# =============================================================================
# Exports
# =============================================================================
__all__ = [
    # Tool groups
    "ALL_TOOLS",

    # Individual tools (legacy compatibility)
    "validate_title",
    "PRICES_BY_UID_TOOL",
    "VALIDATE_ACTOR_TOOL",
    "VALIDATE_DIRECTOR_TOOL",
    "ANSWER_FILMOGRAPHY_BY_UID",
    "ACTOR_FILMOGRAPHY_BY_NAME_TOOL",
    "ACTOR_COACTORS_BY_NAME_TOOL",
    "ACTOR_FILMOGRAPHY_BY_ID_TOOL",
    "ACTOR_COACTORS_BY_ID_TOOL",
    "DIRECTOR_FILMOGRAPHY_BY_NAME_TOOL",
    "DIRECTOR_CODIRECTORS_BY_NAME_TOOL",
    "DIRECTOR_FILMOGRAPHY_BY_ID_TOOL",
    "DIRECTOR_CODIRECTORS_BY_ID_TOOL",
    "COMMON_PROJECTS_BY_IDS_TOOL",
    "PLATFORMS_FOR_UID_BY_COUNTRY_TOOL",
    "PLATFORM_EXCLUSIVES_TOOL",
    "RECENT_PREMIERES_BY_COUNTRY_TOOL",
    "TOP_GENERIC_TOOL",
    "TOP_BY_UID_TOOL",
    "PLATFORM_EXCLUSIVITY_COUNTRY_TOOL",
    "TITLE_RATING_TOOL",
    # "DIRECTOR_PLATFORM_DISTRIBUTION_TOOL",
    # "PLATFORM_ACTORS_ANALYSIS_TOOL",
    # "PLATFORM_DIRECTORS_ANALYSIS_TOOL",
    "HITS_WITH_QUALITY_TOOL",
    "METADATA_COUNT_TOOL",
    "METADATA_LIST_TOOL",
    "METADATA_DISTINCT_TOOL",
    "METADATA_STATS_TOOL",
    "METADATA_QUERY_TOOL",
    "PRESENCE_COUNT_TOOL",
    "PRESENCE_DISTINCT_TOOL",
    "PRESENCE_STATS_TOOL",
    "CATALOG_SIMILARITY_TOOL",
    "EXCLUSIVES_IN_REGION_TOOL",
    # "TITLES_DIFFERENCE_TOOL",
    "AVAILABILITY_BY_UID_TOOL",
    "PRESENCE_QUERY_TOOL",
    "GENRE_TRENDS_TOOL",
    "PRESENCE_WITH_PRICE_TOOL",
    "RAW_SQL_TOOL",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deprecated_alias(*_args: Any, **_kwargs: Any) -> Any:
    """Temporary shim for the legacy alias used in some flows.

    Keep until all external references are migrated to the newer tool names.
    """
    # The original function behind this alias was identical to the tool
    # registered here. Keeping the alias prevents import/runtime errors when
    # upgrading. If you want this alias to forward to a concrete function,
    # replace the implementation here.
    return {
        "message": (
            "'answer_filmography_by_uid' is a legacy alias. Please migrate to "
            "a direct tool call or the updated function name."
        )
    }
