"""Shared constants."""

# Database table names
PRES_TBL = "ms.new_cp_presence"
META_TBL = "ms.metadata_simple_all"
PRICES_TBL = "ms.prices"
HITS_PRES_TBL = "ms.hits_presence"

# Default limits
DEFAULT_LIMIT = 50
MAX_LIMIT = 1000
DEFAULT_DAYS_BACK = 7
MAX_DAYS_BACK = 365

# Cache TTLs (minutes)
INTELLIGENCE_CACHE_TTL = 60
RANKINGS_CACHE_TTL = 30
PRICING_CACHE_TTL = 15
