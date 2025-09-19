# validators_shared.py
# -*- coding: utf-8 -*-
"""
Shared validation utilities for content type, country, platform, currency, 
genre, and region resolution.

This module provides functions to normalize and validate various data types
used across the multimedia database system.
"""

from typing import Optional, List
from .db_utils_sql import get_validation, resolve_value_rapidfuzz


# Content Type Validators
def resolve_content_type(content_type: Optional[str]) -> Optional[str]:
    """
    Normalize content type to standard values.
    
    Args:
        content_type: Raw content type string
        
    Returns:
        Normalized content type ('Movie' or 'Series') or original value
    """
    if not content_type:
        return None
        
    normalized = content_type.strip().lower()
    
    if normalized in {"movie", "movies", "film", "films"}:
        return "Movie"
    if normalized in {"series", "tv", "show", "shows"}:
        return "Series"
        
    return content_type


# Geographic Validators
def resolve_country_iso(country: Optional[str]) -> Optional[str]:
    """
    Normalize country name or code to ISO-2 format.
    
    Args:
        country: Country name or code
        
    Returns:
        ISO-2 country code in lowercase, or None if not found
    """
    if not country:
        return None
        
    validation_rows = get_validation("platform_name_iso")
    _, iso_code = resolve_value_rapidfuzz(
        country, validation_rows, field_name="platform_name_iso", cutoff=0
    )
    
    return iso_code.upper() if iso_code else None


def resolve_region_isos(region: Optional[str]) -> List[str]:
    """
    Convert region name to list of ISO-2 country codes.
    
    Converts region names like 'Europe', 'eu', etc. to their constituent
    ISO-2 country codes, filtered against allowed countries.
    
    Args:
        region: Region name or identifier
        
    Returns:
        List of ISO-2 country codes in lowercase
    """
    if not region:
        return []

    iso_list = get_region_iso_list(region) or []
    
    # Filter by allowed ISO codes from catalog
    return [
        normalize_iso(iso_code) 
        for iso_code in iso_list 
        if normalize_iso(iso_code) in ALLOWED_ISO
    ]


def get_region_iso_list(region_key: str) -> Optional[List[str]]:
    """
    Get list of ISO-2 codes for a known region.
    
    Args:
        region_key: Region identifier or country ISO-2 code
        
    Returns:
        List of ISO-2 codes, or None if region not recognized
    """
    normalized_key = normalize_iso(region_key)
    normalized_key = REGION_ALIASES.get(normalized_key, normalized_key)

    # Check if it's a known region
    if normalized_key in REGION_TO_ISO2:
        return REGION_TO_ISO2[normalized_key]

    # Fallback: treat as individual country ISO-2 code
    if len(normalized_key) == 2 and normalized_key.isalpha():
        return [normalized_key.upper()]

    return None


# Platform and Currency Validators
def resolve_platform_name(platform_name: Optional[str]) -> Optional[str]:
    """
    Normalize platform name using validation catalog.
    
    Args:
        platform_name: Raw platform name
        
    Returns:
        Normalized platform name in lowercase, or None if not found
    """
    if not platform_name:
        return None
        
    validation_rows = get_validation("platform_name")
    _, normalized_name = resolve_value_rapidfuzz(
        platform_name, validation_rows, field_name="platform_name", cutoff=0
    )
    
    return normalized_name if normalized_name else None


def resolve_currency(currency_name: Optional[str]) -> Optional[str]:
    """
    Normalize currency name or code.
    
    Args:
        currency_name: Raw currency name or code
        
    Returns:
        Normalized currency code in lowercase, or None if not found
    """
    if not currency_name:
        return None
        
    validation_rows = get_validation("currency")
    _, normalized_currency = resolve_value_rapidfuzz(
        currency_name, validation_rows, field_name="currency", cutoff=0
    )
    
    return normalized_currency.lower() if normalized_currency else None


# Genre Validators
def resolve_primary_genre(genre: Optional[str]) -> Optional[str]:
    """
    Normalize primary genre using validation catalog.
    
    Args:
        genre: Raw genre name
        
    Returns:
        Normalized genre name in lowercase
    """
    if not genre:
        return None
        
    validation_rows = get_validation("primary_genre")
    _, normalized_genre = resolve_value_rapidfuzz(
        genre, validation_rows, field_name="primary_genre", cutoff=0
    )
    
    return normalized_genre.lower() if normalized_genre else None


# Utility Functions
def normalize_iso(iso_code: str) -> str:
    """
    Normalize ISO code to lowercase and strip whitespace.
    
    Args:
        iso_code: Raw ISO code
        
    Returns:
        Normalized ISO code in lowercase
    """
    return (iso_code or "").strip().lower()


def _get_allowed_iso_set() -> set[str]:
    """
    Get set of allowed ISO-2 codes from validation catalog.
    
    Returns:
        Set of allowed ISO-2 codes in lowercase
    """
    validation_rows = get_validation("platform_name_iso")
    allowed_codes = set()
    
    for row in validation_rows:
        iso_code = row.get("platform_name_iso")
        if isinstance(iso_code, str) and len(iso_code.strip()) == 2:
            allowed_codes.add(iso_code.strip().lower())
            
    return allowed_codes


# Initialize allowed ISO codes
ALLOWED_ISO = _get_allowed_iso_set()

# Import region mappings and aliases from constants
from .constants_sql import REGION_TO_ISO2, REGION_ALIASES