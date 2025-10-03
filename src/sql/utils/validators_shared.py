from src.sql.utils.default_import import *
from .db_utils_sql import resolve_value_rapidfuzz, handle_query_result, _is_valid_json
from .constants_sql import REGION_TO_ISO2, REGION_ALIASES

# =============================================================================
# MODULE INITIALIZATION
# =============================================================================

def get_validation(field_name: str) -> List[Dict]:
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


def _initialize_allowed_iso_codes() -> Set[str]:
    """
    Initialize the set of allowed ISO-2 codes from validation catalog.
    This is called once at module load time.
    
    Returns:
        Set of allowed ISO-2 codes in lowercase
    """
    validation_rows = get_validation("platform_name_iso")
    allowed_codes = set()
    
    for row in validation_rows:
        if not isinstance(row, dict):
            continue
            
        iso_code = row.get("platform_name_iso")
        if isinstance(iso_code, str) and len(iso_code.strip()) == 2:
            allowed_codes.add(iso_code.strip().lower())
            
    return allowed_codes


# Initialize global constants
ALLOWED_ISO_CODES: Set[str] = _initialize_allowed_iso_codes()

# =============================================================================
# CONTENT TYPE VALIDATORS
# =============================================================================

# Content type mappings
MOVIE_TYPES = {"movie", "movies", "film", "films", "película", "pelicula"}
SERIES_TYPES = {"series", "tv", "show", "shows", "serie", "television"}

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

def normalize_iso(iso_code: Optional[str]) -> str:
    """
    Normalize ISO code to lowercase and strip whitespace.
    
    Args:
        iso_code: Raw ISO code
        
    Returns:
        Normalized ISO code in lowercase
        
    Examples:
        >>> normalize_iso(" US ")
        'us'
        >>> normalize_iso("GB")
        'gb'
    """
    if not iso_code:
        return ""
    
    return str(iso_code).strip().lower()


def resolve_country_iso(country: Optional[str]) -> Optional[str]:
    """
    Resolve country name or code to ISO-2 format.
    
    Handles various country formats:
    - Full names: "United States", "United Kingdom"
    - Common names: "USA", "UK"
    - ISO codes: "US", "GB"
    
    Args:
        country: Country name, code, or abbreviation
        
    Returns:
        ISO-2 country code in uppercase, or None if not found
        
    Examples:
        >>> resolve_country_iso("United States")
        'US'
        >>> resolve_country_iso("uk")
        'GB'
    """
    if not country:
        return None
    
    # Get validation data
    validation_rows = get_validation("platform_name_iso")
    if not validation_rows:
        return None
    
    # Use fuzzy matching to find best match
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
    
    # Normalize the key
    normalized_key = normalize_iso(region_key)
    
    # Check for aliases first
    if normalized_key in REGION_ALIASES:
        normalized_key = REGION_ALIASES[normalized_key]
    
    # Check if it's a known region
    if normalized_key in REGION_TO_ISO2:
        # Return uppercase ISO codes
        return [code.upper() for code in REGION_TO_ISO2[normalized_key]]
    
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
    
    # Filter against allowed countries
    valid_isos = []
    for iso_code in iso_list:
        normalized = normalize_iso(iso_code)
        if normalized in ALLOWED_ISO_CODES:
            valid_isos.append(iso_code.upper())
    
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
    
    # Get validation data
    validation_rows = get_validation("platform_name")
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
    
    # Get validation data
    validation_rows = get_validation("currency")
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
    
    # Ahora el validation_rows es tu JSONL cargado
    validation_rows = get_validation("primary_genre")
    if not validation_rows:
        return None
    
    # Aplanamos todas las opciones de alias con su canónico
    alias_map = {}
    for row in validation_rows:
        canonical = row.get("primary_genre")
        terms = row.get("terms", []) + [canonical]
        for t in terms:
            alias_map[t] = canonical
    
    # 1) Exact match rápido
    if genre in alias_map:
        return alias_map[genre]
    
    # 2) Fuzzy matching con RapidFuzz sobre los alias
    match, _ , _ = process.extractOne(
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


def validate_all_fields(
    content_type: Optional[str] = None,
    country: Optional[str] = None,
    platform: Optional[str] = None,
    currency: Optional[str] = None,
    genre: Optional[str] = None
) -> dict:
    """
    Validate multiple fields in a single call.
    
    Args:
        content_type: Content type to validate
        country: Country to validate
        platform: Platform to validate
        currency: Currency to validate
        genre: Genre to validate
        
    Returns:
        Dictionary with validated values
        
    Example:
        >>> validate_all_fields(content_type="movie", country="US")
        {'content_type': 'Movie', 'country': 'US', ...}
    """
    return {
        'content_type': resolve_content_type(content_type) if content_type else None,
        'country': resolve_country_iso(country) if country else None,
        'platform': resolve_platform_name(platform) if platform else None,
        'currency': resolve_currency(currency) if currency else None,
        'genre': resolve_primary_genre(genre) if genre else None
    }
# VALIDATION STATUS HELPERS
# =============================================================================

def get_validation_report() -> dict:
    """
    Get a report of available validation data.
    
    Returns:
        Dictionary with counts and status of validation data
    """
    return {
        'allowed_countries': len(ALLOWED_ISO_CODES),
        'regions_defined': len(REGION_TO_ISO2),
        'region_aliases': len(REGION_ALIASES),
        'movie_types': len(MOVIE_TYPES),
        'series_types': len(SERIES_TYPES)
    }


# =============================================================================
# DATE UTILITIES
# =============================================================================

# get_date_range() moved to db_utils_sql.py to avoid duplication
# Import it from there if needed:
# from src.sql.utils.db_utils_sql import get_date_range


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