"""
Content-specific filter and validation helpers.
Extracted from metadata.py to reduce complexity.
"""
import re
from typing import Dict, List, Any, Tuple, Optional
from src.strands.utils.validators import (
    resolve_country_iso, 
    resolve_content_type,
    get_region_iso_list
)

NO_FILTER_KEYWORDS = {
    "*", "all", "any", "todos", "todo",
    "metadata", "titles", "content", "catalog",
    "database", "db", "full", "complete", "everything",
    "total", "general", "global", "universe"
}


def normalize_args_kwargs(args, kwargs, parse_arg1=False):
    """Normalize positional args into kwargs."""
    from src.strands.utils.validators import normalize_args_kwargs as base_normalize
    kwargs = base_normalize(args, kwargs)

    if parse_arg1 and "__arg1" in kwargs:
        arg1_value = kwargs.get("__arg1", "")
        if str(arg1_value).strip().lower() not in NO_FILTER_KEYWORDS:
            kwargs = parse_arg1_basic(kwargs.pop("__arg1"), kwargs)
        else:
            kwargs.pop("__arg1", None)

    return kwargs


def process_primary_argument(kwargs, allow_type=True, allow_country=True):
    """Process primary argument to extract type or country."""
    primary_arg = kwargs.get("__arg1")

    if not primary_arg or kwargs.get("countries_iso") or kwargs.get("type"):
        return

    normalized_arg = str(primary_arg).strip().lower()

    if normalized_arg in NO_FILTER_KEYWORDS:
        return

    if allow_country and len(normalized_arg) == 2 and normalized_arg.isalpha():
        iso_code = resolve_country_iso(normalized_arg)
        if iso_code:
            kwargs["countries_iso"] = normalized_arg
    elif allow_type:
        content_type = resolve_content_type(normalized_arg)
        if content_type in ["Movie", "Series"]:
            kwargs["type"] = normalized_arg


def build_filters_common(kwargs) -> Tuple[List[str], List[Any], List[str]]:
    """
    Build WHERE conditions, params, and filter descriptions.
    
    Returns:
        Tuple of (conditions, params, applied_filters)
    """
    conditions, params, applied_filters = [], [], []

    # Type filter
    type_param = kwargs.get("type")
    if type_param:
        content_type = resolve_content_type(type_param)
        if content_type:
            conditions.append("type = %s")
            params.append(content_type)
            applied_filters.append(f"type={content_type}")

    # Country/Region filter
    country_iso = kwargs.get("countries_iso")
    if country_iso:
        region_isos = get_region_iso_list(country_iso)
        if region_isos:
            if len(region_isos) == 1:
                conditions.append("countries_iso = %s")
                params.append(region_isos[0])
                applied_filters.append(f"country={region_isos[0]}")
            else:
                placeholders = ", ".join(["%s"] * len(region_isos))
                conditions.append(f"countries_iso IN ({placeholders})")
                params.extend(region_isos)
                applied_filters.append(f"region={country_iso}")
        else:
            iso_code = resolve_country_iso(country_iso)
            if iso_code:
                conditions.append("countries_iso = %s")
                params.append(iso_code)
                applied_filters.append(f"country={iso_code}")

    # Year filters
    for year_param, operator, label in [
        ("year_from", ">=", "from"),
        ("year_to", "<=", "to")
    ]:
        year_value = kwargs.get(year_param)
        if year_value is not None:
            if isinstance(year_value, int) or (isinstance(year_value, str) and str(year_value).isdigit()):
                year_int = int(year_value)
                if 1900 <= year_int <= 2100:
                    conditions.append(f"year {operator} %s")
                    params.append(year_int)
                    applied_filters.append(f"year_{label}={year_int}")

    return conditions, params, applied_filters


_DEF_SEP = re.compile(r"[\s,;/]+")


def parse_arg1_basic(a1: str, kwargs: dict) -> dict:
    """Parse first argument to extract filters (country, year range)."""
    s = (a1 or "").strip()
    if not s or s.lower() in NO_FILTER_KEYWORDS:
        return kwargs

    toks = [t for t in _DEF_SEP.split(s) if t]
    out = dict(kwargs)

    # Extract country ISO
    if "countries_iso" not in out:
        iso = next((t.upper() for t in toks if len(t) == 2 and t.isalpha()), None)
        if iso:
            resolved_iso = resolve_country_iso(iso)
            if resolved_iso:
                out["countries_iso"] = resolved_iso

    # Extract year range
    year_pattern = re.compile(r'\b(19|20)\d{2}\b')
    years = [int(m.group()) for m in year_pattern.finditer(s)]
    if len(years) >= 2:
        out.setdefault("year_from", min(years))
        out.setdefault("year_to", max(years))
    elif len(years) == 1:
        if any(word in s.lower() for word in ["desde", "from", "after", "since"]):
            out.setdefault("year_from", years[0])
        elif any(word in s.lower() for word in ["hasta", "until", "before", "to"]):
            out.setdefault("year_to", years[0])

    return out
