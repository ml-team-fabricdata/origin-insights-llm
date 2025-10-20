"""
DEPRECATED: This module has been renamed to validators.py

Please update your imports:
  from src.strands.utils.validator_node import resolve_country_iso
  →
  from src.strands.utils.validators import resolve_country_iso

This compatibility wrapper will be removed in a future version.
"""

import warnings

# Re-export everything from the new module
from src.strands.utils.validators import (
    resolve_country_iso,
    resolve_content_type,
    resolve_platform_name,
    resolve_currency,
    resolve_primary_genre,
    resolve_region_isos,
    get_region_iso_list,
    validate_uid,
    parse_uid_with_country,
    normalize_iso,
    validate_country_list,
    normalize_langgraph_params,
    get_validation,
    clear_validation_cache,
    ALLOWED_ISO_CODES,
    MOVIE_TYPES,
    SERIES_TYPES
)

# Emit deprecation warning
warnings.warn(
    "validator_node.py is deprecated. Use validators.py instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    "resolve_country_iso",
    "resolve_content_type",
    "resolve_platform_name",
    "resolve_currency",
    "resolve_primary_genre",
    "resolve_region_isos",
    "get_region_iso_list",
    "validate_uid",
    "parse_uid_with_country",
    "normalize_iso",
    "validate_country_list",
    "normalize_langgraph_params",
    "get_validation",
    "clear_validation_cache",
    "ALLOWED_ISO_CODES",
    "MOVIE_TYPES",
    "SERIES_TYPES"
]
