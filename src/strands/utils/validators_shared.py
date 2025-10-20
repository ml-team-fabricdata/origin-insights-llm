from src.strands.utils.default_import import *
from .db_utils_sql import resolve_value_rapidfuzz, handle_query_result, _is_valid_json
from .constants_sql import REGION_TO_ISO2, REGION_ALIASES
import pycountry

# =============================================================================
# MODULE INITIALIZATION
# =============================================================================

# Global cache for validation data (lazy loaded)
_VALIDATION_CACHE: Dict[str, List[Dict]] = {}


def _get_validation(field_name: str) -> List[Dict]:
    """
    Load validation data from a JSONL file.

    Handles empty lines and malformed JSON gracefully.

    Args:
        field_name: Name of the field/file to load

    Returns:
        List of validation dictionaries or error message
    """
    if not field_name:
        return [{"error": "Field name is required"}]

    result = []
    print(f"Loading validation data from {field_name}")
    file_path = Path(f"src/data/{field_name}.jsonl")

    # Check if file exists
    if not file_path.exists():
        logger.error(f"Validation file not found: {file_path}")
        return [{"error": f"Validation file not found: {field_name}"}]

    # Check if it's a file
    if not file_path.is_file():
        logger.error(f"Path is not a file: {file_path}")
        return [{"error": f"Invalid file path: {field_name}"}]

    # Read file line by line
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:  # Skip empty lines
                continue

            # Parse JSON without try/except
            # First check if it looks like JSON
            if not (line.startswith('{') or line.startswith('[')):
                logger.warning(
                    f"Skipping non-JSON line {line_num} in {field_name}.jsonl"
                )
                continue

            # Attempt to parse
            parsed = _is_valid_json(line)
            if parsed:
                result.append(parsed)
            else:
                logger.warning(
                    f"Skipping malformed JSON in {field_name}.jsonl line {line_num}"
                )

    logger.info(f"✅ {field_name} consultados, total: {len(result)}")
    return handle_query_result(result, field_name, "all")


def _get_validation_cached(field_name: str) -> List[Dict]:
    """
    Get validation data with caching to avoid repeated file I/O.
    
    Args:
        field_name: Name of the validation file
        
    Returns:
        Cached validation data
        
    Note:
        This function caches validation data in memory on first access.
        All resolve_* functions use this to avoid repeated disk reads.
    """
    if field_name not in _VALIDATION_CACHE:
        _VALIDATION_CACHE[field_name] = _get_validation(field_name)
    return _VALIDATION_CACHE[field_name]


# Backward compatibility alias
def get_validation(field_name: str) -> List[Dict]:
    """
    Public API for getting validation data.
    Prefer using this over _get_validation() for automatic caching.
    """
    return _get_validation_cached(field_name)


def clear_validation_cache(field_name: Optional[str] = None) -> None:
    """
    Clear validation cache for testing or when data files are updated.
    
    Args:
        field_name: Specific field to clear, or None to clear all cache
    """
    global _VALIDATION_CACHE, _GENRE_ALIAS_MAP
    
    if field_name:
        _VALIDATION_CACHE.pop(field_name, None)
        if field_name == "primary_genre":
            _GENRE_ALIAS_MAP = None
        logger.info(f"Cleared cache for: {field_name}")
    else:
        _VALIDATION_CACHE.clear()
        _GENRE_ALIAS_MAP = None
        logger.info("Cleared all validation cache")


def _initialize_allowed_iso_codes() -> Set[str]:
    """
    Initialize the set of allowed ISO-2 codes from validation catalog.
    This is called once at module load time.
    
    Returns:
        Set of allowed ISO-2 codes in uppercase
    """
    validation_rows = get_validation("platform_name_iso")
    allowed_codes = set()
    
    for row in validation_rows:
        if not isinstance(row, dict):
            continue
            
        iso_code = row.get("platform_name_iso")
        if isinstance(iso_code, str) and len(iso_code.strip()) == 2:
            allowed_codes.add(iso_code.strip().upper())
            
    return allowed_codes


# Initialize global constants
ALLOWED_ISO_CODES: Set[str] = _initialize_allowed_iso_codes()

# =============================================================================
# CONTENT TYPE VALIDATORS
# =============================================================================

# Content type mappings
MOVIE_TYPES = {"movie", "movies", "film", "films", "película", "pelicula"}
SERIES_TYPES = {"series", "tv", "show", "shows", "serie", "television", "tv show"}

def resolve_content_type(content_type: Optional[str]) -> Optional[str]:
    """
    Normalize content type to standard values ('Movie' or 'Series').
    
    Args:
        content_type: Raw content type string in any language/format
        
    Returns:
        'Movie', 'Series', or original value if not recognized
        
    Examples:
        >>> resolve_content_type("movies")
        'Movie'
        >>> resolve_content_type("TV Show")
        'Series'
        >>> resolve_content_type("Documentary")
        'Documentary'
    """
    if not content_type:
        return None
    
    # Normalize for comparison
    normalized = content_type.strip().lower()
    
    # Check against known types
    if normalized in MOVIE_TYPES:
        return "Movie"
    elif normalized in SERIES_TYPES:
        return "Series"
    
    # Return original if not recognized (might be special type)
    return None

# =============================================================================
# GEOGRAPHIC VALIDATORS
# =============================================================================

def validate_uid(uid: Optional[str]) -> Optional[str]:
    """
    Validate and normalize UID.
    
    Args:
        uid: UID string to validate
        
    Returns:
        Normalized UID or None if invalid
        
    Examples:
        >>> validate_uid("  tt1234567  ")
        'tt1234567'
        >>> validate_uid("")
        None
        >>> validate_uid(None)
        None
    """
    if not uid or not isinstance(uid, str):
        return None
    uid = uid.strip()
    return uid if uid else None


def parse_uid_with_country(uid: str, country: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse UID removing query params and extracting country suffix if present.
    
    Handles formats like:
    - "tt1234567?param=value" -> removes query params
    - "tt1234567_US" -> extracts country suffix
    - "tt1234567_US?param=value" -> both
    
    Args:
        uid: UID string to parse (may contain query params or country suffix)
        country: Explicit country code (takes precedence over suffix)
        
    Returns:
        Tuple of (cleaned_uid, country_code)
        
    Examples:
        >>> parse_uid_with_country("tt1234567?foo=bar")
        ('tt1234567', None)
        >>> parse_uid_with_country("tt1234567_US")
        ('tt1234567', 'US')
        >>> parse_uid_with_country("tt1234567_US", "GB")
        ('tt1234567', 'GB')
        >>> parse_uid_with_country("")
        (None, None)
    """
    if not uid:
        return None, country
    
    # Remove query parameters
    if '?' in uid:
        uid = uid.split('?')[0]
    
    if not uid:
        return None, country
    
    # Extract country suffix if present (format: uid_CC where CC is 2-letter ISO)
    if '_' in uid:
        parts = uid.split('_')
        if len(parts) == 2 and len(parts[1]) == 2 and parts[1].isalpha():
            base_uid, suffix = parts[0], parts[1].upper()
            # Only use suffix if no explicit country was provided
            if not country:
                country = suffix
            uid = base_uid
    
    return uid if uid else None, country


def normalize_iso(iso_code: Optional[str]) -> str:
    """
    Normalize ISO code to uppercase and strip whitespace.
    
    Args:
        iso_code: Raw ISO code
        
    Returns:
        Normalized ISO code in uppercase
        
    Examples:
        >>> normalize_iso(" US ")
        'US'
        >>> normalize_iso("GB")
        'GB'
    """
    if not iso_code:
        return ""
    
    return str(iso_code).strip().upper()


# Manual mappings for common Spanish names and aliases
_COUNTRY_ALIASES = {
    "ESTADOS UNIDOS": "US",
    "REINO UNIDO": "GB",
    "BRASIL": "BR",
    "ALEMANIA": "DE",
    "FRANCIA": "FR",
    "ITALIA": "IT",
    "ESPAÑA": "ES",
    "JAPON": "JP",
    "CHINA": "CN",
    "INDIA": "IN",
    "RUSIA": "RU",
    "COREA DEL SUR": "KR",
    "UK": "GB",
    "USA": "US",
}

def resolve_country_iso(country: Optional[str]) -> Optional[str]:
    """
    Resolve country name or code to ISO-2 format.
    
    Handles various country formats:
    - Full names: "United States", "United Kingdom", "Estados Unidos"
    - Common names: "USA", "UK", "America"
    - ISO codes: "US", "GB"
    - Spanish names: "Estados Unidos", "Reino Unido", "Brasil"
    
    Args:
        country: Country name, code, or abbreviation
        
    Returns:
        ISO-2 country code in uppercase, or None if not found
        
    Examples:
        >>> resolve_country_iso("United States")
        'US'
        >>> resolve_country_iso("Estados Unidos")
        'US'
        >>> resolve_country_iso("uk")
        'GB'
        >>> resolve_country_iso("México")
        'MX'
    """
    if not country:
        return None
    
    country_normalized = country.strip().upper()
    
    # 0. Check manual aliases first (for Spanish names and common abbreviations)
    if country_normalized in _COUNTRY_ALIASES:
        return _COUNTRY_ALIASES[country_normalized]
    
    # 1. Try exact match with ISO-2 code first
    if len(country_normalized) == 2 and country_normalized.isalpha():
        # Verify it's a valid ISO code
        validation_rows = _get_validation_cached("platform_name_iso")
        valid_codes = {row.get("platform_name_iso", "").upper() for row in validation_rows if isinstance(row, dict)}
        if country_normalized in valid_codes:
            return country_normalized


    # Try by name (English) - returns None if not found
    country_obj = pycountry.countries.get(name=country)
    if country_obj:
        return country_obj.alpha_2
    
    # Try by official name - returns None if not found
    country_obj = pycountry.countries.get(official_name=country)
    if country_obj:
        return country_obj.alpha_2
    
    # Try fuzzy search - raises LookupError if not found
    try:
        results = pycountry.countries.search_fuzzy(country)
        if results:
            return results[0].alpha_2
    except LookupError:
        # Fuzzy search found nothing, continue to fallback
        pass
 
    
    # 3. Fallback: Try fuzzy matching against our ISO list
    validation_rows = _get_validation_cached("platform_name_iso")
    if not validation_rows:
        return None
    
    status, result = resolve_value_rapidfuzz(
        user_text=country,
        rows=validation_rows,
        field_name="platform_name_iso",
        cutoff=75
    )
    
    if status == "resolved" and result:
        return result.upper()
    
    return None


def get_region_iso_list(region_key: str) -> Optional[List[str]]:
    """
    Convert region identifier to list of ISO-2 country codes.
    
    Args:
        region_key: Region name, alias, or individual country code
        
    Returns:
        List of ISO-2 codes in uppercase, or None if not recognized
        
    Examples:
        >>> get_region_iso_list("eu")
        ['AT', 'BE', 'BG', ...]
        >>> get_region_iso_list("US")
        ['US']
    """
    if not region_key:
        return None
    
    # Normalize the key to lowercase for lookup (constants use lowercase keys)
    normalized_key = region_key.strip().lower()
    
    # Check for aliases first (keys are lowercase)
    if normalized_key in REGION_ALIASES:
        normalized_key = REGION_ALIASES[normalized_key]
    
    # Check if it's a known region (keys are lowercase, values are uppercase)
    if normalized_key in REGION_TO_ISO2:
        # Values are already uppercase in constants
        return list(REGION_TO_ISO2[normalized_key])
    
    # Check if it's a single country ISO-2 code
    if len(normalized_key) == 2 and normalized_key.isalpha():
        return [normalized_key.upper()]
    
    return None


def resolve_region_isos(region: Optional[str]) -> List[str]:
    """
    Convert region to list of valid ISO-2 country codes.
    
    Filters results against allowed countries in the system catalog.
    
    Args:
        region: Region name, alias, or country code
        
    Returns:
        List of valid ISO-2 codes in uppercase
        
    Examples:
        >>> resolve_region_isos("europe")
        ['DE', 'FR', 'IT', ...]  # Only countries in our catalog
    """
    if not region:
        return []
    
    # Get all ISO codes for the region
    iso_list = get_region_iso_list(region)
    if not iso_list:
        return []
    
    # Filter against allowed countries (all in uppercase)
    valid_isos = []
    for iso_code in iso_list:
        normalized = normalize_iso(iso_code)  # Returns uppercase
        if normalized in ALLOWED_ISO_CODES:  # Set is now uppercase
            valid_isos.append(normalized)
    
    return valid_isos

# =============================================================================
# PLATFORM VALIDATORS
# =============================================================================

def resolve_platform_name(platform_name: Optional[str]) -> Optional[str]:
    """
    Normalize platform/streaming service name.
    
    Handles various platform name formats and aliases.
    
    Args:
        platform_name: Raw platform name or alias
        
    Returns:
        Normalized platform name, or None if not found
        
    Examples:
        >>> resolve_platform_name("Netflix")
        'netflix'
        >>> resolve_platform_name("HBO Max")
        'hbo_max'
    """
    if not platform_name:
        return None
    
    # Get validation data (cached)
    validation_rows = _get_validation_cached("platform_name")
    if not validation_rows:
        return None
    
    # Use fuzzy matching
    status, result = resolve_value_rapidfuzz(
        user_text=platform_name,
        rows=validation_rows,
        field_name="platform_name",
        cutoff=80  # Higher cutoff for platform names
    )
    
    if status == "resolved" and result:
        # Return lowercase for consistency
        return result.lower()
    
    return None

# =============================================================================
# FINANCIAL VALIDATORS
# =============================================================================

def resolve_currency(currency_name: Optional[str]) -> Optional[str]:
    """
    Normalize currency name or code to standard format.
    
    Handles:
    - Currency codes: "USD", "EUR", "GBP"
    - Currency names: "Dollar", "Euro", "Pound"
    - Symbols: "$", "€", "£"
    
    Args:
        currency_name: Raw currency identifier
        
    Returns:
        Normalized currency code in uppercase, or None if not found
        
    Examples:
        >>> resolve_currency("dollar")
        'USD'
        >>> resolve_currency("€")
        'EUR'
    """
    if not currency_name:
        return None
    
    # Get validation data (cached)
    validation_rows = _get_validation_cached("currency")
    if not validation_rows:
        return None
    
    # Use fuzzy matching
    status, result = resolve_value_rapidfuzz(
        user_text=currency_name,
        rows=validation_rows,
        field_name="currency",
        cutoff=75
    )
    
    if status == "resolved" and result:
        # Return uppercase for currency codes
        return result.upper()
    
    return None

# =============================================================================
# CONTENT METADATA VALIDATORS
# =============================================================================

# Cache for genre alias map (lazy loaded)
_GENRE_ALIAS_MAP: Optional[Dict[str, str]] = None


def _build_genre_alias_map() -> Dict[str, str]:
    """Build and cache genre alias map."""
    global _GENRE_ALIAS_MAP
    
    if _GENRE_ALIAS_MAP is not None:
        return _GENRE_ALIAS_MAP
    
    validation_rows = _get_validation_cached("primary_genre")
    if not validation_rows:
        _GENRE_ALIAS_MAP = {}
        return _GENRE_ALIAS_MAP
    
    alias_map = {}
    for row in validation_rows:
        canonical = row.get("primary_genre")
        terms = row.get("terms", []) + [canonical]
        for t in terms:
            alias_map[t] = canonical
    
    _GENRE_ALIAS_MAP = alias_map
    return alias_map


def resolve_primary_genre(genre: Optional[str]) -> Optional[str]:
    """
    Normalize content genre to standard classification.
    
    Args:
        genre: Raw genre name
        
    Returns:
        Normalized genre name, or None if not found
    """
    if not genre:
        return None
    
    # Get cached alias map
    alias_map = _build_genre_alias_map()
    if not alias_map:
        return None
    
    # 1) Exact match rápido
    if genre in alias_map:
        return alias_map[genre]
    
    # 2) Fuzzy matching con RapidFuzz sobre los alias
    match, _, _ = process.extractOne(
        genre,
        alias_map.keys(),
        score_cutoff=75
    )
    if match:
        return alias_map[match]
    
    return None

# =============================================================================
# BATCH VALIDATION UTILITIES
# =============================================================================

def validate_country_list(countries: List[str]) -> List[str]:
    """
    Validate and normalize a list of country identifiers.
    
    Args:
        countries: List of country names, codes, or regions
        
    Returns:
        List of valid ISO-2 codes in uppercase
        
    Examples:
        >>> validate_country_list(["USA", "uk", "Germany"])
        ['US', 'GB', 'DE']
    """
    valid_countries = []
    
    for country in countries:
        # Try as individual country first
        iso_code = resolve_country_iso(country)
        if iso_code:
            valid_countries.append(iso_code)
        else:
            # Try as region
            region_isos = resolve_region_isos(country)
            valid_countries.extend(region_isos)
    
    # Remove duplicates while preserving order
    seen = set()
    result = []
    for code in valid_countries:
        if code not in seen:
            seen.add(code)
            result.append(code)
    
    return result


# =============================================================================
# DATE UTILITIES
# =============================================================================

# get_date_range() moved to db_utils_sql.py to avoid duplication
# Import it from there if needed:
# from src.strands.utils.db_utils_sql import get_date_range


def normalize_langgraph_params(*args, **kwargs) -> dict:
    """
    Normalize parameters from LangGraph tool calls.
    Handles nested kwargs format: {'kwargs': {'param1': 'value1', ...}}
    
    Args:
        *args: Positional arguments (can be dict or JSON string)
        **kwargs: Keyword arguments (may contain nested 'kwargs' key)
        
    Returns:
        Normalized dictionary of parameters
        
    Examples:
        >>> normalize_langgraph_params({'country': 'US'})
        {'country': 'US'}
        >>> normalize_langgraph_params(kwargs={'country': 'US'})
        {'country': 'US'}
        >>> normalize_langgraph_params('{"country": "US"}')
        {'country': 'US'}
    """
    import json
    
    # Handle LangGraph nested kwargs format
    if "kwargs" in kwargs and isinstance(kwargs["kwargs"], dict):
        nested_kwargs = kwargs["kwargs"]
        other_params = {k: v for k, v in kwargs.items() if k != "kwargs"}
        merged = dict(nested_kwargs)
        merged.update(other_params)
        kwargs = merged

    # Handle positional arguments
    if args:
        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, dict):
                merged = dict(arg)
                merged.update(kwargs)
                return merged
            elif isinstance(arg, str):
                parsed = json.loads(arg) if arg.startswith("{") else None
                if isinstance(parsed, dict):
                    parsed.update(kwargs)
                    return parsed
                # Treat as simple parameter
                merged = dict(kwargs)
                merged.setdefault("__arg1", arg)
                return merged
        # Multiple positional args
        merged = dict(kwargs)
        merged.setdefault("__arg1", args[0])
        return merged

    return kwargs or {}