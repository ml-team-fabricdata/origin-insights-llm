from __future__ import annotations
from src.sql.utils.default_import import *
from src.sql.utils.db_utils_sql import *
from src.sql.queries.common.queries_validation import *

MAX_OPTIONS_DISPLAY = 8
MAX_VALIDATION_OPTIONS = 5
DEFAULT_FALLBACK_THRESHOLDS = [0.3, 0.2]
HIGH_SIMILARITY_THRESHOLD = 0.8
MEDIUM_SIMILARITY_THRESHOLD = 0.5
LOW_SIMILARITY_THRESHOLD = 0.3

@dataclass
class ValidationResult:
    """Represents a validation result with consistent structure."""
    status: str
    result: Optional[Dict[str, Any]] = None
    options: Optional[List[Dict[str, Any]]] = None

class ValidationResponseBuilder:
    """Builder for standardized validation responses."""

    @staticmethod
    def not_found() -> Dict[str, Any]:
        """Returns a not found response."""
        return {"status": "not_found"}

    @staticmethod
    def resolved(result: Dict[str, Any]) -> Dict[str, Any]:
        """Returns a resolved response with a single result."""
        return {"status": "resolved", "result": result}

    @staticmethod
    def ambiguous(options: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Returns an ambiguous response with multiple options."""
        return {"status": "ambiguous", "options": options}

    @staticmethod
    def ok(entity_id: str, name: str, aka_name: Optional[str] = None) -> Dict[str, Any]:
        """Returns an OK response for person validation."""
        return {"status": "ok", "id": entity_id, "name": name, "aka_name": aka_name}

def _build_title_result(row: Dict, is_fuzzy: bool = False) -> Dict[str, Any]:
    """Builds a standardized title result dictionary."""
    title_key = 'aka_title' if is_fuzzy else 'title'
    default_similarity = 1.0 if not is_fuzzy else 0.0

    return {
        "uid": row.get('uid'),
        "title": row.get(title_key),
        "aka_title": row.get(title_key),
        "imdb_id": row.get('imdb_id'),
        "year": row.get('year'),
        "type": row.get('type'),
        "directors": row.get('directors'),
        "cast": row.get('cast'),
        "title_similarity": safe_cast_float(row.get('title_similarity'), default_similarity)
    }

def _build_title_options(results: List[Dict], is_fuzzy: bool = False) -> List[Dict]:
    """Builds a list of title options from search results."""
    options = []
    title_key = 'aka_title' if is_fuzzy else 'title'

    for result in results[:MAX_OPTIONS_DISPLAY]:
        option = {
            "uid": result.get('uid'),
            "title": result.get(title_key),
            "imdb_id": result.get('imdb_id'),
            "year": result.get('year'),
            "type": result.get('type'),
            "directors": result.get('directors'),
            "cast": result.get('cast'),
        }
        if is_fuzzy:
            option["title_similarity"] = safe_cast_float(
                result.get('title_similarity'))
        options.append(option)

    return options

def _calculate_name_similarity(query_text: str, name: str) -> float:
    """Calculates similarity score between query text and a name."""
    normalized_query = query_text.lower()
    normalized_name = (name or '').lower()

    if normalized_name == normalized_query:
        return 1.0
    elif normalized_name.startswith(normalized_query):
        return HIGH_SIMILARITY_THRESHOLD
    elif normalized_query in normalized_name:
        return MEDIUM_SIMILARITY_THRESHOLD
    else:
        return LOW_SIMILARITY_THRESHOLD

def _normalize_and_validate_input(input_data: Union[str, List[str], Any]) -> Optional[str]:
    """Normalizes and validates input data using shared utilities."""
    normalized = normalize_input(input_data)
    if not normalized:
        return None

    cleaned = clean_text(normalized)
    return cleaned if cleaned else None

def _perform_exact_search(sql_query: str, params: tuple, search_type: str) -> List[Dict]:
    """Performs exact search with given SQL and parameters."""
    return db.execute_query(sql_query, params, f"{search_type} exact search")

def _perform_fuzzy_search(sql_query: str, params: tuple, search_type: str) -> List[Dict]:
    """Performs fuzzy search with given SQL and parameters."""
    return db.execute_query(sql_query, params, f"{search_type} fuzzy search")

def _try_exact_title_search(normalized_title: str) -> Optional[Dict[str, Any]]:
    """Attempts exact title search and returns appropriate response."""
    exact_results = _perform_exact_search(
        EXACT_SEARCH_SQL, (normalized_title,), "title")

    if not exact_results:
        return None

    if len(exact_results) == 1:
        return ValidationResponseBuilder.resolved(_build_title_result(exact_results[0]))

    return ValidationResponseBuilder.ambiguous(_build_title_options(exact_results))

def _try_fuzzy_title_search(normalized_title: str, threshold: Optional[float]) -> Dict[str, Any]:
    """Attempts fuzzy title search with fallback thresholds."""
    threshold = normalize_threshold(threshold)

    for current_threshold in [threshold] + DEFAULT_FALLBACK_THRESHOLDS:
        logger.debug(
            f"Trying title fuzzy search with threshold {current_threshold}")

        params = (normalized_title, normalized_title, DEFAULT_FUZZY_LIMIT)
        fuzzy_results = _perform_fuzzy_search(FUZZY_SEARCH_SQL, params, "title")

        if fuzzy_results:
            return _process_fuzzy_title_results(fuzzy_results, normalized_title, current_threshold)

    return ValidationResponseBuilder.not_found()

def _process_fuzzy_title_results(results: List[Dict], query_text: str, threshold: float) -> Dict[str, Any]:
    """Processes fuzzy title search results."""
    is_single_token_query = is_single_token(query_text)

    if len(results) == 1 and not is_single_token_query:
        result = results[0]
        similarity = safe_cast_float(result.get('title_similarity'))

        if similarity >= threshold:
            return ValidationResponseBuilder.resolved(_build_title_result(result, is_fuzzy=True))

    return ValidationResponseBuilder.ambiguous(_build_title_options(results, is_fuzzy=True))

def _filter_results_by_similarity(results: List[Dict], query_text: str, threshold: float) -> List[Dict]:
    """Filters fuzzy search results by similarity threshold."""
    valid_results = []

    for result in results:
        similarity = _calculate_name_similarity(query_text, result.get('name'))
        if similarity >= threshold:
            result_copy = dict(result)
            result_copy['similarity_score'] = similarity
            valid_results.append(result_copy)

    return valid_results

def _sort_person_results(results: List[Dict], sort_by_titles: bool = False) -> List[Dict]:
    """Sorts person validation results by similarity and optionally by number of titles."""
    if sort_by_titles:
        return sorted(results, key=lambda x: (x['similarity_score'], x.get('n_titles', 0)), reverse=True)
    else:
        return sorted(results, key=lambda x: x['similarity_score'], reverse=True)

def _build_person_options(results: List[Dict], include_titles_count: bool = False) -> List[Dict]:
    """Builds options list for person validation results."""
    options = []

    for result in results[:MAX_VALIDATION_OPTIONS]:
        option = {
            "id": result.get('id'),
            "name": result.get('name'),
            "score": safe_cast_float(result.get('similarity_score'))
        }
        if include_titles_count:
            option["n_titles"] = safe_cast_int(result.get('n_titles'))

        options.append(option)

    return options

def _validate_person_entity(
    query_text: str,
    exact_sql: str,
    fuzzy_sql: str,
    entity_type: str,
    threshold: Optional[float] = None,
    sort_by_titles: bool = False
) -> Dict[str, Any]:
    """Generic validation function for person entities (actors/directors)."""
    normalized_query = _normalize_and_validate_input(query_text)
    if not normalized_query:
        return ValidationResponseBuilder.not_found()

    threshold = normalize_threshold(threshold)
    logger.debug(
        f"Validating {entity_type}: '{normalized_query}' with threshold {threshold}")

    exact_results = _perform_exact_search(
        exact_sql, (normalized_query,), entity_type)
    if exact_results:
        if len(exact_results) == 1:
            result = exact_results[0]
            return ValidationResponseBuilder.ok(result.get('id'), result.get('name'))

        exact_options = []
        for result in exact_results[:MAX_VALIDATION_OPTIONS]:
            option = {"id": result.get(
                'id'), "name": result.get('name'), "score": 1.0}
            if sort_by_titles:
                option["n_titles"] = safe_cast_int(result.get('n_titles'))
            exact_options.append(option)

        return ValidationResponseBuilder.ambiguous(exact_options)

    for current_threshold in [threshold] + DEFAULT_FALLBACK_THRESHOLDS:
        logger.debug(
            f"Trying {entity_type} fuzzy search with threshold {current_threshold}")

        fuzzy_results = _perform_fuzzy_search(fuzzy_sql, (normalized_query,), entity_type)
        if not fuzzy_results:
            continue

        valid_results = _filter_results_by_similarity(
            fuzzy_results, normalized_query, current_threshold)
        if not valid_results:
            continue

        sorted_results = _sort_person_results(valid_results, sort_by_titles)

        if len(sorted_results) == 1 and not is_single_token(normalized_query):
            result = sorted_results[0]
            return ValidationResponseBuilder.ok(result.get('id'), result.get('name'))

        options = _build_person_options(sorted_results, sort_by_titles)
        return ValidationResponseBuilder.ambiguous(options)

    return ValidationResponseBuilder.not_found()

def search_title_exact(title: str) -> List[Dict[str, Any]]:
    """Performs exact title search."""
    if not title:
        return []

    normalized_title = clean_text(title)
    if not normalized_title:
        return []

    return db.execute_query(EXACT_SEARCH_SQL, (normalized_title,), "exact search")

def search_title_fuzzy(
    title: str,
    limit: int = DEFAULT_FUZZY_LIMIT
) -> List[Dict[str, Any]]:
    """Performs fuzzy title search."""
    if not title:
        return []

    normalized_title = clean_text(title)
    if not normalized_title:
        return []

    params = (normalized_title, normalized_title, limit)
    return db.execute_query(FUZZY_SEARCH_SQL, params, "fuzzy search")
def search_title(title: str, *, threshold: float = DEFAULT_FUZZY_THRESHOLD) -> Dict[str, Any]:
    """Searches for a title with validation."""
    return validate_title(title, threshold)

def validate_title(title: str, threshold: Optional[float] = None) -> Dict[str, Any]:
    """Valida y resuelve títulos para asegurar una identificación única.
    
    Validates and resolves movie/TV show titles for unique identification.
    Returns status 'ok' with UID if found, 'ambiguous' with options if multiple matches,
    or 'not_found' if no matches. Requires the title to validate as parameter.
    
    Args:
        title: Title to validate
        threshold: Optional similarity threshold for fuzzy matching
    
    Returns:
        Dict with validation result (status, uid, title, options, etc.)
    """
    normalized_query = _normalize_and_validate_input(title)
    if not normalized_query:
        return ValidationResponseBuilder.not_found()

    logger.debug(
        f"Validating title: '{title}' (normalized: '{normalized_query}')")

    exact_result = _try_exact_title_search(normalized_query)
    if exact_result:
        return exact_result

    return _try_fuzzy_title_search(normalized_query, threshold)

def validate_actor(name: Union[str, List[str], Any], threshold: Optional[float] = None) -> Dict[str, Any]:
    """Valida y resuelve nombres de actores para identificación única.
    
    Validates and resolves actor names for unique identification.
    Returns status 'ok' with actor ID if found, 'ambiguous' with options if multiple matches,
    or 'not_found' if no matches. Requires the actor name to validate as parameter.
    
    Args:
        name: Actor name to validate
        threshold: Optional similarity threshold for fuzzy matching
    
    Returns:
        Dict with validation result (status, id, name, options, etc.)
    """
    return _validate_person_entity(
        query_text=name,
        exact_sql=ACTOR_EXACT_SQL,
        fuzzy_sql=ACTOR_FUZZY_SQL_ILIKE,
        entity_type="actor",
        threshold=threshold,
        sort_by_titles=False
    )

def validate_director(name: Union[str, List[str], Any], threshold: Optional[float] = None) -> Dict[str, Any]:
    """Valida y resuelve nombres de directores para identificación única.
    
    Validates and resolves director names for unique identification.
    Returns status 'ok' with director ID if found, 'ambiguous' with options if multiple matches,
    or 'not_found' if no matches. Requires the director name to validate as parameter.
    
    Args:
        name: Director name to validate
        threshold: Optional similarity threshold for fuzzy matching
    
    Returns:
        Dict with validation result (status, id, name, options, etc.)
    """
    return _validate_person_entity(
        query_text=name,
        exact_sql=DIRECTOR_EXACT_SQL,
        fuzzy_sql=DIRECTOR_FUZZY_SQL_ILIKE,
        entity_type="director",
        sort_by_titles=True
    )