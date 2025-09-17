# -*- coding: utf-8 -*-

from __future__ import annotations

import logging
import unicodedata
from typing import Any, Dict, List, Optional, Tuple, Union

from ...sql_db import db
from query import *
from ..db_utils_sql import handle_query_result

logger = logging.getLogger(__name__)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _clean_title(title: str) -> str:
    """
    Clean and normalize a title for search.

    Args:
        title: Title to clean

    Returns:
        Normalized title (no accents, lowercase)
    """
    if not title:
        return ""

    # Unicode NFKD normalization to separate combined characters
    normalized = unicodedata.normalize("NFKD", title).lower()
    # Remove combining characters (accents)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def _normalize_title(title: str) -> str:
    """
    Normalize title for grouping (same title with variations).

    Args:
        title: Title to normalize

    Returns:
        Normalized title for comparison
    """
    cleaned = (title or "").strip().lower()
    normalized = unicodedata.normalize("NFKD", cleaned)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def _normalize_name_input(name: Union[str, List[str], Any]) -> str:
    """
    Normalize name input, handling different input types.

    Args:
        name: Name that can be string, list, or any type

    Returns:
        Normalized string or empty string if cannot process
    """
    if not name:
        return ""

    # If it's a list, take the first element
    if isinstance(name, list):
        if len(name) > 0:
            name = name[0]
        else:
            return ""

    # Convert to string and clean
    try:
        return str(name).strip()
    except Exception:
        return ""


def _is_single_token(text: str) -> bool:
    """
    Check if text is a single word/token.

    Args:
        text: Text to check

    Returns:
        True if single word, False otherwise
    """
    if not text or not isinstance(text, str):
        return False
    return len(text.strip().split()) == 1


def _format_validation_options(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format validation options for uniform response.

    Args:
        rows: Database result rows

    Returns:
        List of formatted options
    """
    options: List[Dict[str, Any]] = []
    for row in rows:
        if not row:
            continue
        option = {
            "id": row.get("id"),
            "name": row.get("name") or row.get("clean_name") or str(row.get("id", "")),
            "score": float(row.get("sim", 0.0) or row.get("n_titles", 0.0) or 0.0),
            "n_titles": int(row.get("n_titles", 0) or 0),
        }
        options.append(option)
    return options


def _normalize_validation_threshold(threshold: Optional[float] = None) -> float:
    """
    Normalize validation threshold.

    Args:
        threshold: Optional threshold

    Returns:
        Validated threshold
    """
    if threshold is None:
        return FUZZY_THRESHOLD
    try:
        return max(0.1, min(1.0, float(threshold)))
    except (ValueError, TypeError):
        return FUZZY_THRESHOLD


def _should_be_ambiguous(results: List[Dict[str, Any]], top_title: str, top_similarity: float) -> bool:
    """
    Determine if results should be considered ambiguous.

    Args:
        results: List of results
        top_title: Normalized title of best result
        top_similarity: Similarity of best result

    Returns:
        True if should be ambiguous, False if clear result
    """
    if len(results) <= 1:
        return False

    # Group close results
    close_results = []
    for result in results:
        result_similarity = float(result.get("title_similarity", 0))
        result_title = _normalize_title(result.get("aka_title", ""))

        # Consider close if same normalized title or very close similarity
        if result_title == top_title or (top_similarity - result_similarity) < 0.05:
            close_results.append(result)

    if len(close_results) <= 1:
        return False

    # Ambiguous if different types or years
    types = {r.get("type", "Unknown") for r in close_results}
    years = {r.get("year") for r in close_results if r.get("year")}

    return len(types) > 1 or (len(years) > 1 and top_title)


# =============================================================================
# TITLE SEARCH FUNCTIONS
# =============================================================================

def search_title_exact(title: str) -> List[Dict[str, Any]]:
    """
    Exact title search.

    Args:
        title: Title to search

    Returns:
        List of exact results
    """
    if not title:
        return []

    normalized_title = _clean_title(title)
    if not normalized_title:
        return []

    logger.debug(f"Exact search for title: '{normalized_title}'")

    try:
        results = db.execute_query(EXACT_SEARCH_SQL, (normalized_title,))
        logger.debug(
            f"Exact search returned {len(results) if results else 0} results")
        return results or []
    except Exception as e:
        logger.error(f"Error in exact search: {e}")
        return []


def search_title_fuzzy(
    title: str,
    threshold: float = DEFAULT_FUZZY_THRESHOLD,
    limit: int = DEFAULT_FUZZY_LIMIT
) -> List[Dict[str, Any]]:
    """
    Fuzzy title search using pg_trgm.

    Args:
        title: Title to search
        threshold: Minimum similarity threshold
        limit: Result limit

    Returns:
        List of fuzzy results ordered by similarity
    """
    if not title:
        return []

    normalized_title = _clean_title(title)
    if not normalized_title:
        return []

    logger.debug(
        f"Fuzzy search for title: '{normalized_title}' with threshold {threshold}")

    try:
        # Parameters: normalized_title appears 8 times in the query
        params = (
            normalized_title, normalized_title, normalized_title, threshold,
            normalized_title, threshold, threshold, limit
        )

        results = db.execute_query(FUZZY_SEARCH_SQL, params)
        logger.debug(
            f"Fuzzy search returned {len(results) if results else 0} results")

        if results:
            logger.debug(f"Top results: {results[:3]}")

        return results or []

    except Exception as e:
        logger.error(f"Error in fuzzy search: {e}")
        return []


def search_title_with_fallback(
    title: str,
    initial_threshold: float = DEFAULT_FUZZY_THRESHOLD,
    limit: int = DEFAULT_FUZZY_LIMIT
) -> List[Dict[str, Any]]:
    """
    Search with fallback to lower thresholds if no results.

    Args:
        title: Title to search
        initial_threshold: Initial threshold
        limit: Result limit

    Returns:
        List of results with fallback
    """
    # Initial attempt
    results = search_title_fuzzy(title, initial_threshold, limit)
    if results:
        return results

    # Fallback with lower threshold
    if initial_threshold > 0.3:
        logger.debug(f"Trying fallback with threshold 0.3")
        results = search_title_fuzzy(title, 0.3, limit)
        if results:
            return results

    # Fallback with very low threshold
    if initial_threshold > 0.2:
        logger.debug(f"Trying fallback with threshold 0.2")
        results = search_title_fuzzy(title, 0.2, limit)

    return results or []


def search_title(
    title: str,
    *,
    threshold: float = DEFAULT_FUZZY_THRESHOLD,
    limit: int = DEFAULT_FUZZY_LIMIT
) -> Dict[str, Any]:
    """
    Main title search that handles ambiguity.

    Args:
        title: Title to search
        threshold: Similarity threshold
        limit: Result limit

    Returns:
        Dictionary with status and results:
        - {"status": "resolved", "result": {...}}
        - {"status": "ambiguous", "options": [...]}
        - {"status": "not_found"}
    """
    normalized_title = _clean_title(title or "")
    if not normalized_title:
        return {"status": "not_found"}

    logger.info(
        f"Searching title: '{title}' (normalized: '{normalized_title}')")

    # Fuzzy search with fallback
    results = search_title_with_fallback(normalized_title, threshold, limit)

    if not results:
        return {"status": "not_found"}

    # Add normalized titles for comparison
    for result in results:
        result["norm_title"] = _normalize_title(result.get("aka_title", ""))

    top_result = results[0]
    top_title = top_result["norm_title"]
    top_similarity = float(top_result.get("title_similarity", 0))

    # Check if ambiguous
    if _should_be_ambiguous(results, top_title, top_similarity):
        # Prepare limited options
        options = []
        for result in results[:8]:  # Maximum 8 options
            option = {
                "uid": result["uid"],
                "title": result["aka_title"],
                "year": result.get("year"),
                "imdb_id": result.get("imdb_id"),
                "type": result.get("type"),
                "title_similarity": float(result.get("title_similarity", 0))
            }
            options.append(option)

        return {"status": "ambiguous", "options": options}

    # Single clear result
    return {
        "status": "resolved",
        "result": {
            "uid": top_result["uid"],
            "aka_title": top_result["aka_title"],
            "imdb_id": top_result.get("imdb_id"),
            "year": top_result.get("year"),
            "type": top_result.get("type"),
            "title_similarity": top_similarity
        }
    }


# =============================================================================
# TITLE VALIDATION
# =============================================================================

def validate_title(title: str) -> Dict[str, Any]:
    """
    Title validation that prioritizes exact matches.

    Args:
        title: Title to validate

    Returns:
        Dictionary with status and results
    """
    normalized_title = (title or "").strip().lower()
    if not normalized_title:
        return {"status": "not_found"}

    logger.info(f"Validating title: '{title}'")

    # First exact search
    exact_results = search_title_exact(normalized_title)

    if exact_results:
        if len(exact_results) == 1:
            result = exact_results[0]
            return {
                "status": "resolved",
                "result": {
                    "uid": result["uid"],
                    "title": result["title"],
                    "imdb_id": result.get("imdb_id"),
                    "year": result.get("year"),
                    "type": result.get("type"),
                    "title_similarity": 1.0,
                    "aka_title": result["title"]
                }
            }

        # Multiple exact results - ambiguous
        options = []
        for result in exact_results:
            option = {
                "uid": result["uid"],
                "title": result["title"],
                "imdb_id": result.get("imdb_id"),
                "year": result.get("year"),
                "type": result.get("type")
            }
            options.append(option)

        return {"status": "ambiguous", "options": options}

    # No exact match - fuzzy search
    logger.debug("No exact match found, trying fuzzy search")
    return search_title(normalized_title)


# =============================================================================
# ACTOR VALIDATION
# =============================================================================

def validate_actor(name: Union[str, List[str], Any], threshold: Optional[float] = None) -> Dict[str, Any]:
    """
    Validate and search for an actor by name.

    Args:
        name: Actor name (can be string, list, etc.)
        threshold: Similarity threshold for fuzzy search

    Returns:
        Dictionary with status and results:
        - {"status": "ok", "id": int, "name": str}
        - {"status": "ambiguous", "options": [...]}
        - {"status": "not_found"}
    """
    query_text = _normalize_name_input(name)
    if not query_text:
        return {"status": "not_found"}

    threshold = _normalize_validation_threshold(threshold)

    logger.debug(
        f"Validating actor: '{query_text}' with threshold {threshold}")

    # 1. Exact search
    try:
        exact_results = db.execute_query(
            ACTOR_EXACT_SQL, (query_text, query_text))
        if exact_results:
            if len(exact_results) == 1:
                result = exact_results[0]
                return {"status": "ok", "id": result["id"], "name": result["name"]}

            # Multiple exact → ambiguous
            return {
                "status": "ambiguous",
                "options": _format_validation_options(exact_results[:5])
            }
    except Exception as e:
        logger.error(f"Error in actor exact search: {e}")

    # 2. Fuzzy search
    try:
        # Try trigram first
        fuzzy_results = db.execute_query(
            ACTOR_FUZZY_SQL_TRGM, (query_text, query_text, query_text))
    except Exception as e:
        logger.warning(f"Trigram search failed, using ILIKE fallback: {e}")
        try:
            fuzzy_results = db.execute_query(
                ACTOR_FUZZY_SQL_ILIKE, (query_text, query_text))
        except Exception as e2:
            logger.error(f"Both trigram and ILIKE searches failed: {e2}")
            return {"status": "not_found"}

    if not fuzzy_results:
        return {"status": "not_found"}

    # If single token (e.g., "Coppola"), force ambiguity if >1
    is_single_token = _is_single_token(query_text)

    if len(fuzzy_results) == 1 and not is_single_token:
        top_result = fuzzy_results[0]
        try:
            if float(top_result.get("sim", 0.0)) >= threshold:
                return {"status": "ok", "id": top_result["id"], "name": top_result["name"]}
        except (ValueError, TypeError):
            pass

    # All other cases → ambiguous
    return {
        "status": "ambiguous",
        "options": _format_validation_options(fuzzy_results[:5])
    }


# =============================================================================
# DIRECTOR VALIDATION
# =============================================================================

def validate_director(name: Union[str, List[str], Any], threshold: Optional[float] = None) -> Dict[str, Any]:
    """
    Validate and search for a director by name.

    Args:
        name: Director name (can be string, list, etc.)
        threshold: Similarity threshold for fuzzy search

    Returns:
        Dictionary with status and results:
        - {"status": "ok", "id": int, "name": str}
        - {"status": "ambiguous", "options": [...]}
        - {"status": "not_found"}
    """
    query_text = _normalize_name_input(name)
    if not query_text:
        return {"status": "not_found"}

    threshold = _normalize_validation_threshold(threshold)

    logger.debug(
        f"Validating director: '{query_text}' with threshold {threshold}")

    # 1. Exact search (ordered by productivity)
    try:
        exact_results = db.execute_query(
            DIRECTOR_EXACT_SQL, (query_text, query_text))
        if exact_results:
            if len(exact_results) == 1:
                result = exact_results[0]
                return {"status": "ok", "id": result["id"], "name": result["name"]}

            # Multiple exact → ambiguous
            return {
                "status": "ambiguous",
                "options": _format_validation_options(exact_results[:5])
            }
    except Exception as e:
        logger.error(f"Error in director exact search: {e}")

    # 2. Fuzzy search
    try:
        # Try trigram first
        fuzzy_results = db.execute_query(
            DIRECTOR_FUZZY_SQL_TRGM, (query_text, query_text, query_text, query_text))
    except Exception as e:
        logger.warning(f"Trigram search failed, using ILIKE fallback: {e}")
        try:
            fuzzy_results = db.execute_query(
                DIRECTOR_FUZZY_SQL_ILIKE, (query_text, query_text))
        except Exception as e2:
            logger.error(f"Both trigram and ILIKE searches failed: {e2}")
            return {"status": "not_found"}

    if not fuzzy_results:
        return {"status": "not_found"}

    # If single token (e.g., "Coppola"), force ambiguity if >1
    is_single_token = _is_single_token(query_text)

    if len(fuzzy_results) == 1 and not is_single_token:
        top_result = fuzzy_results[0]
        try:
            if float(top_result.get("sim", 0.0)) >= threshold:
                return {"status": "ok", "id": top_result["id"], "name": top_result["name"]}
        except (ValueError, TypeError):
            pass

    # All other cases → ambiguous
    return {
        "status": "ambiguous",
        "options": _format_validation_options(fuzzy_results[:5])
    }
