# app/modules/__init__.py

# --- titles ---
from .titles import (
    normalize_title_query,
    term_without_years,
    term_tokens_no_numbers,
    search_title_candidates,
    detect_hint,
    select_title_by_hint,
    safe_autopick,
    extract_title_query,
)

# --- countries ---
from .countries import (
    guess_country,
    is_country_only_followup,
    COUNTRIES_EN_ES,
)

# --- metadata ---
from .metadata import (
    get_metadata_by_uid,
    get_metadata_by_imdb,
    resolve_uid_by_imdb,
)

# --- availability ---
from .availability import (
    fetch_availability_by_uid,
    render_availability_summary,
    render_availability,
)

# --- hits ---
from .hits import (
    get_default_hits_year,
    ensure_hits_range,
    extract_date_range,
    get_hits_by_uid,
    get_top_hits_by_period,
    render_top_hits,
    render_hits,
)

# --- similar ---
from .similar import (
    kb_semantic_search,
    search_titles_by_topic,
    render_similar_list,
)

__all__ = [
    # titles
    "normalize_title_query",
    "term_without_years",
    "term_tokens_no_numbers",
    "search_title_candidates",
    "detect_hint",
    "select_title_by_hint",
    "safe_autopick",
    "extract_title_query",
    # countries
    "guess_country",
    "is_country_only_followup",
    "COUNTRIES_EN_ES",
    # metadata
    "get_metadata_by_uid",
    "get_metadata_by_imdb",
    "resolve_uid_by_imdb",
    # availability
    "fetch_availability_by_uid",
    "render_availability_summary",
    "render_availability",
    # hits
    "get_default_hits_year",
    "ensure_hits_range",
    "extract_date_range",
    "get_hits_by_uid",
    "get_top_hits_by_period",
    "render_top_hits",
    "render_hits",
    # similar
    "kb_semantic_search",
    "search_titles_by_topic",
    "render_similar_list",
]