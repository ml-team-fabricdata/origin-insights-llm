from __future__ import annotations
from typing import Dict, Tuple, FrozenSet

# =============================================================================
# DATABASE SCHEMAS AND TABLES
# =============================================================================

# Main schema
SCHEMA = "ms"

# Core tables
META_TBL = f"{SCHEMA}.metadata_simple_all"
META_ALL = f"{SCHEMA}.new_cp_metadata_estandar"
PRES_TBL = f"{SCHEMA}.new_cp_presence"
PRICES_TBL = f"{SCHEMA}.new_cp_presence_prices"
HITS_PRESENCE_TBL = f"{SCHEMA}.hits_presence_2"
HITS_GLOBAL_TBL = f"{SCHEMA}.hits_global"

# Additional tables
AKAS_TABLE = f"{SCHEMA}.akas_with_year"
METADATA_TABLE = f"{SCHEMA}.metadata_simple_all"
CAST_TABLE = f"{SCHEMA}.cast"
ACTED_IN_TABLE = f"{SCHEMA}.acted_in"
DIRECTOR_TABLE = f"{SCHEMA}.directors"
DIRECTED_TABLE = f"{SCHEMA}.directed_by"

# Table mappings
TABLE_MAP: Dict[str, str] = {
    "metadata_simple_all": META_TBL,
    "new_cp_metadata_estandar": META_ALL,
    "new_cp_presence": PRES_TBL,
    "new_cp_presence_prices": PRICES_TBL,
    "hits_presence_2": HITS_PRESENCE_TBL,
    "hits_global": HITS_GLOBAL_TBL,
}

ALLOWED_TABLES: FrozenSet[str] = frozenset(TABLE_MAP.values())

# PostgreSQL extension schema
PG_TRGM_SCHEMA = "ms"

# =============================================================================
# QUERY DEFAULTS AND LIMITS
# =============================================================================

# General query limits
DEFAULT_LIMIT = 10
MAX_LIMIT = 20
DEFAULT_DAYS_BACK = 30

# Fuzzy search configuration
DEFAULT_FUZZY_THRESHOLD = 0.4
FUZZY_THRESHOLD = 0.38
DEFAULT_FUZZY_LIMIT = 12
MAX_CANDIDATES = 25

# Content filtering
DEFAULT_MIN_TITLES = 3
DEFAULT_COUNTRY = 'US'

# Active window SQL condition
ACTIVE_SQL = "p.out_on IS NULL"

# =============================================================================
# COLUMN WHITELISTS BY TABLE
# =============================================================================

# Content Provider (CP) columns
CP_ALLOWED_SELECT: FrozenSet[str] = frozenset({
    "iso_alpha2", "plan_name", "platform_code", 
    "platform_name", "type"
})

# Metadata columns
META_ALLOWED_SELECT: FrozenSet[str] = frozenset({
    "uid", "title", "type", "year", "age", "duration", "synopsis",
    "primary_genre", "primary_language", "languages",
    "primary_country", "countries", "countries_iso",
    "primary_company", "production_companies",
    "directors", "full_cast", "writers",
})

META_ALLOWED_ORDER: FrozenSet[str] = frozenset({
    "title", "type", "year", "age", "duration",
    "primary_genre", "primary_language", "countries_iso",
})

# Presence table columns
PRESENCE_ALLOWED_SELECT: FrozenSet[str] = frozenset({
    # Identifiers
    "id", "sql_unique", "global_id", "content_id", "hash_unique", "uid",
    "imdb_id", "tmdb_id", "tvdb_id",
    
    # Location and platform
    "iso_alpha2", "iso_global", "platform_name", "platform_code",
    "package_code", "package_code2", "plan_name",
    
    # Content metadata
    "type", "clean_title", "duration", "permalink",
    "active_episodes", "active_seasons", "active_uid",
    
    # Status flags
    "is_original", "is_kids", "is_local", "isbranded", "is_exclusive",
    "content_status", "registry_status",
    
    # Timestamps
    "enter_on", "out_on", "created_at", "uid_updated",
})

PRESENCE_ALLOWED_ORDER: FrozenSet[str] = frozenset({
    "enter_on", "out_on", "created_at", "uid_updated",
    "platform_name", "platform_code", "package_code",
    "iso_alpha2", "platform_country", "type", "duration", "clean_title"
})

# Hits table columns
HITS_ALLOWED_SELECT: FrozenSet[str] = frozenset({
    # Basic info
    "uid", "imdb", "country", "content_type", "title", "year", "tmdb_id",
    
    # Hit metrics
    "date_hits", "hits", "week", "hits_relative", "average",
    
    # Score metrics
    "piracynormscore", "piracyscore", "imdbnormscore", "imdbscore",
    "twitternormscore", "twitterscore", "youtubenormscore", "youtubescore",
    "cdbscore", "cdbnormscore",
    
    # Time-related
    "currentyear", "release_date", "weeks_since_release", "input",
})

HITS_ALLOWED_ORDER: FrozenSet[str] = frozenset({
    "date_hits", "hits", "week", "year", 
    "currentyear", "release_date", "weeks_since_release"
})

# =============================================================================
# SQL FUNCTIONS WHITELIST
# =============================================================================

# Allowed SQL functions with (min_args, max_args)
# -1 means unlimited max args
ALLOWED_FUNCS: Dict[str, Tuple[int, int]] = {
    # String functions
    "LOWER": (1, 1),
    "UPPER": (1, 1),
    "INITCAP": (1, 1),
    
    # NULL handling
    "COALESCE": (2, -1),
    "NULLIF": (2, 2),
    
    # Comparison
    "GREATEST": (2, -1),
    "LEAST": (2, -1),
    
    # Date/Time
    "DATE_TRUNC": (2, 2),
    
    # Type casting
    "CAST": (1, 1),
    
    # Aggregation
    "SUM": (1, 1),
    "AVG": (1, 1),
    "MIN": (1, 1),
    "MAX": (1, 1),
    "COUNT": (0, 1),
    "PERCENTILE_CONT": (1, 1),
}

# =============================================================================
# CONTENT DEFINITIONS AND LICENSES
# =============================================================================

# Video definitions
VALID_DEFINITIONS = {"4K", "UHD", "HD", "SD", "SD/HD"}

DEF_ALIASES = {
    "ultra hd": "UHD",
    "ultrahd": "UHD",
    "uhd": "UHD",
    "2160p": "4K",
    "full hd": "HD",
    "fullhd": "HD",
    "sdhd": "SD/HD",
    "sd/hd": "SD/HD",
}

# License types
VALID_LICENSES = {"EST", "V", "VOD"}

LIC_ALIASES = {
    "electronic sell-through": "EST",
    "sell-through": "EST",
    "est": "EST",
    "vod": "VOD",
    "svod": "VOD",
    "v": "V",
}

# =============================================================================
# GEOGRAPHICAL REGIONS
# =============================================================================

REGION_TO_ISO2 = {
    # Europe - Complete
    'europe': [
        'AD', 'AL', 'AT', 'BA', 'BE', 'BG', 'BY', 'CH', 'CY', 'CZ',
        'DE', 'DK', 'EE', 'ES', 'FI', 'FO', 'FR', 'GB', 'GI', 'GR',
        'HR', 'HU', 'IE', 'IM', 'IT', 'LI', 'LT', 'LU', 'LV', 'MC',
        'MD', 'ME', 'MK', 'MT', 'NL', 'NO', 'PL', 'PT', 'RO', 'RS',
        'RU', 'SE', 'SI', 'SK', 'SM', 'TR', 'UA', 'VA', 'XK'
    ],
    
    # European Union
    'eu': [
        'AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI',
        'FR', 'GR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT',
        'NL', 'PL', 'PT', 'RO', 'SE', 'SI', 'SK'
    ],
    
    # European Subregions
    'western_europe': ['AT', 'BE', 'CH', 'DE', 'FR', 'LI', 'LU', 'MC', 'NL'],
    'northern_europe': ['DK', 'EE', 'FI', 'FO', 'GB', 'GL', 'IE', 'IM', 'LT', 'LV', 'NO', 'SE'],
    'southern_europe': ['AD', 'AL', 'BA', 'CY', 'ES', 'GI', 'GR', 'HR', 'IT', 'ME', 'MK', 'MT', 'PT', 'RS', 'SI', 'SM', 'VA', 'XK'],
    'eastern_europe': ['BG', 'BY', 'CZ', 'HU', 'MD', 'PL', 'RO', 'RU', 'SK', 'UA'],
    
    # Americas
    'north_america': ['BM', 'CA', 'GL', 'MX', 'US'],
    'central_america': ['BZ', 'CR', 'GT', 'HN', 'NI', 'PA', 'SV'],
    'south_america': ['AR', 'BO', 'BR', 'CL', 'CO', 'EC', 'FK', 'GY', 'PE', 'PY', 'SR', 'UY', 'VE'],
    
    # Latin America variants
    'latin_america': [
        'AR', 'BO', 'BR', 'CL', 'CO', 'CR', 'CU', 'DO', 'EC', 'GT',
        'HN', 'MX', 'NI', 'PA', 'PE', 'PR', 'PY', 'SV', 'UY', 'VE'
    ],
    'latam': [  # Same as latin_america
        'AR', 'BO', 'BR', 'CL', 'CO', 'CR', 'CU', 'DO', 'EC', 'GT',
        'HN', 'MX', 'NI', 'PA', 'PE', 'PR', 'PY', 'SV', 'UY', 'VE'
    ],
    'latino_america': [  # Same as latin_america
        'AR', 'BO', 'BR', 'CL', 'CO', 'CR', 'CU', 'DO', 'EC', 'GT',
        'HN', 'MX', 'NI', 'PA', 'PE', 'PR', 'PY', 'SV', 'UY', 'VE'
    ],
    'latin_america_extended': [  # Including Caribbean
        'AR', 'BO', 'BR', 'CL', 'CO', 'CR', 'CU', 'DO', 'EC', 'GT',
        'HN', 'MX', 'NI', 'PA', 'PE', 'PR', 'PY', 'SV', 'UY', 'VE',
        'BZ', 'GY', 'SR', 'GF', 'AI', 'AW', 'BB', 'CW', 'DM', 'GD',
        'GP', 'HT', 'JM', 'KN', 'LC', 'MQ', 'MS', 'TT', 'VG', 'VI'
    ],
    
    # Caribbean
    'caribbean': [
        'AG', 'AI', 'AW', 'BB', 'BS', 'CU', 'CW', 'DM', 'DO', 'GD',
        'GP', 'HT', 'JM', 'KN', 'LC', 'MQ', 'MS', 'PR', 'TC', 'TT',
        'VG', 'VI'
    ],
    
    # Asia
    'asia': [
        'AE', 'AF', 'AM', 'AZ', 'BD', 'BH', 'BN', 'BT', 'CN', 'GE',
        'HK', 'ID', 'IL', 'IN', 'IQ', 'IR', 'JO', 'JP', 'KG', 'KH',
        'KP', 'KR', 'KW', 'KZ', 'LA', 'LB', 'LK', 'MM', 'MN', 'MO',
        'MY', 'NP', 'OM', 'PH', 'PK', 'PS', 'QA', 'RU', 'SA', 'SG',
        'SY', 'TH', 'TJ', 'TL', 'TM', 'TR', 'TW', 'UZ', 'VN', 'YE'
    ],
    
    # Middle East
    'middle_east': [
        'AE', 'BH', 'CY', 'EG', 'IL', 'IQ', 'IR', 'JO', 'KW', 'LB',
        'OM', 'PS', 'QA', 'SA', 'SY', 'TR', 'YE'
    ],
    
    # Africa
    'africa': [
        'AO', 'BF', 'BI', 'BJ', 'BW', 'CD', 'CF', 'CG', 'CI', 'CM',
        'CV', 'DJ', 'DZ', 'EG', 'EH', 'ER', 'ET', 'GA', 'GH', 'GM',
        'GN', 'GQ', 'GW', 'KE', 'KM', 'LR', 'LS', 'LY', 'MA', 'MG',
        'ML', 'MR', 'MU', 'MW', 'MZ', 'NA', 'NE', 'NG', 'RE', 'RW',
        'SC', 'SD', 'SL', 'SN', 'SO', 'SS', 'ST', 'SZ', 'TD', 'TG',
        'TN', 'TZ', 'UG', 'ZA', 'ZM', 'ZW'
    ],
    
    # Oceania
    'oceania': [
        'AS', 'AU', 'CK', 'FJ', 'FM', 'GU', 'KI', 'MH', 'MP', 'NC',
        'NR', 'NZ', 'PF', 'PG', 'PW', 'SB', 'TO', 'TV', 'VU', 'WF', 'WS'
    ]
}

# Region name aliases and normalization
REGION_ALIASES = {
    # European Union aliases
    "ue": "eu",
    "european-union": "eu",
    "european union": "eu",
    "unión europea": "eu",
    "union europea": "eu",
    
    # Europe aliases
    "europa": "europe",
    
    # United Kingdom aliases
    "uk": "gb",
    "great britain": "gb",
    "england": "gb",
    "scotland": "gb",
    "wales": "gb",
    "northern ireland": "gb",
    "gbr": "gb",
    "united kingdom": "gb",
    
    # Region abbreviations
    'na': 'north_america',
    'sa': 'south_america',
    'ca': 'central_america',
    'we': 'western_europe',
    'ee': 'eastern_europe',
    'ne': 'northern_europe',
    'se': 'southern_europe',
    'me': 'middle_east',
    
    # Latin America aliases
    'latin america': 'latin_america',
    'latinamerica': 'latin_america',
    'latin-america': 'latin_america',
    'latam': 'latam',
    'latino america': 'latino_america',
    'latinoamerica': 'latino_america',
    'latino-america': 'latino_america',
    'america latina': 'latin_america',
    'americalatina': 'latin_america',
    'america-latina': 'latin_america',
    'la': 'latin_america',  # Note: could also mean Los Angeles
    'lac': 'latin_america',  # Latin America and Caribbean
    'ibero america': 'latin_america',
    'ibero-america': 'latin_america',
    'iberoamerica': 'latin_america',
    'hispanic america': 'latin_america',
    'hispanic-america': 'latin_america',
    'hispanicamerica': 'latin_america',
}

# =============================================================================
# SYSTEM POLICIES AND VALIDATION RULES
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
# PRESENCE COLUMNS
# =============================================================================

PRESENCE_ALLOWED_SELECT = {
    "id","sql_unique","out_on","global_id",
    "iso_alpha2","iso_global","platform_name","platform_code",
    "package_code","package_code2","content_id","hash_unique",
    "uid","type","clean_title","is_original","is_kids","is_local",
    "isbranded","is_exclusive","imdb_id","tmdb_id","tvdb_id",
    "duration","content_status","registry_status","uid_updated",
    "created_at","plan_name","permalink","active_episodes",
    "active_seasons","season_count","episode_count"
}

PRESENCE_PRICE_DERIVED_SELECT = {
    "price_amount","price_currency","price_type",
    "price_definition","price_license","price_out_on","price_created_at"
}

PRESENCE_DEFAULT_SELECT = [
    "uid","clean_title","type","platform_name","platform_code","iso_alpha2",
    "hash_unique","permalink",
    "price_amount","price_currency","price_type","price_definition","price_license","price_created_at"
]