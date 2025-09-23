from __future__ import annotations
from src.sql.default_import import *
from src.sql.constants_sql import *

Status = Tuple[str, Union[str, List[str], None]]

# =============================================================================
# CONSTANTS
# =============================================================================

# Regular expression for CJK (Chinese, Japanese, Korean) characters
_CJK_RE = re.compile(r"[\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]")

# =============================================================================
# INPUT VALIDATION FUNCTIONS
# =============================================================================


def validate_limit(
    limit: Optional[int] = None,
    default: int = 20,
    max_limit: int = 500,
    *,
    lo: Optional[int] = None,
    hi: Optional[int] = None,
    **_ignored,
) -> int:
    """
    Validate and normalize a limit parameter.

    Args:
        limit: The limit value to validate
        default: Default value if limit is invalid
        max_limit: Maximum allowed limit
        lo: Optional minimum override
        hi: Optional maximum override

    Returns:
        Validated integer limit within allowed bounds
    """
    # Handle lo/hi overrides
    if lo is not None and isinstance(lo, (int, float)):
        default = max(default, int(lo))
    if hi is not None and isinstance(hi, (int, float)):
        max_limit = int(hi)

    # Validate limit without try/except
    if limit is None:
        return int(default)

    # Check if it's a valid numeric type
    if not isinstance(limit, (int, float)):
        return int(default)

    # Convert to int and validate range
    n = int(limit)
    if n <= 0:
        return int(default)

    return min(n, int(max_limit))


def validate_days_back(days_back: Optional[int], default: int = 30) -> int:
    """
    Validate relative days window (1..365).

    Args:
        days_back: Number of days to look back
        default: Default value if days_back is invalid

    Returns:
        Validated days value between 1 and 365
    """
    if days_back is None or not isinstance(days_back, (int, float)):
        return default

    days = int(days_back)
    if days <= 0:
        return default

    return min(days, 365)


def normalize_threshold(threshold: Optional[float] = None) -> float:
    """
    Normalize a fuzzy matching threshold to valid range.

    Args:
        threshold: Threshold value to normalize

    Returns:
        Float between 0.1 and 1.0
    """
    if threshold is None:
        return FUZZY_THRESHOLD

    if not isinstance(threshold, (int, float)):
        return FUZZY_THRESHOLD

    value = float(threshold)
    return max(0.1, min(1.0, value))


def normalize_input(input_data: Union[str, List[str], Any]) -> str:
    """
    Normalize various input types to a single string.

    Args:
        input_data: Input that could be string, list, or other type

    Returns:
        Normalized string representation
    """
    if not input_data:
        return ""

    if isinstance(input_data, str):
        return input_data.strip()

    if isinstance(input_data, list):
        if not input_data:
            return ""
        first_elem = input_data[0]
        return str(first_elem).strip() if first_elem else ""

    # For any other type, convert to string
    return str(input_data).strip()

# =============================================================================
# TEXT PROCESSING FUNCTIONS
# =============================================================================


def normalize(s: Optional[str]) -> str:
    """
    Normalize text for comparison by removing accents, punctuation, and extra spaces.
    Used for fuzzy matching and text comparison.

    Args:
        s: String to normalize

    Returns:
        Normalized lowercase string without punctuation or extra spaces
    """
    if not s:
        return ""

    if not isinstance(s, str):
        s = str(s)

    # Unicode normalization and lowercase
    s = ud.normalize("NFKC", s.casefold()).strip()
    s = s.lower().strip()

    # Remove punctuation, collapse spaces and hyphens
    s = re.sub(r"[^\w\s-]", " ", s)  # Remove punctuation
    s = re.sub(r"\s+", "", s)        # Collapse spaces
    s = re.sub(r"-+", "", s)          # Collapse hyphens

    return s


def clean_text(text: str) -> str:
    """
    Clean text by removing diacritical marks while preserving original structure.
    Different from normalize() as it preserves spaces and case for display.

    Args:
        text: Text to clean

    Returns:
        Cleaned text without combining characters but preserving structure
    """
    if not text:
        return ""

    if not isinstance(text, str):
        text = str(text)

    # NFKD decomposition to separate base characters from combining marks
    normalized = ud.normalize("NFKD", text)
    # Remove only combining characters (accents, diacritics)
    return "".join(c for c in normalized if not ud.combining(c))


def is_single_token(text: str) -> bool:
    """
    Check if text contains only a single word/token.

    Args:
        text: Text to check

    Returns:
        True if text is a single token, False otherwise
    """
    if not text or not isinstance(text, str):
        return False

    stripped = text.strip()
    if not stripped:
        return False

    return len(stripped.split()) == 1


def detect_id_kind(value: str, prices_tbl: str, pres_tbl: str) -> Tuple[str, Optional[str]]:
    """
    Devuelve ('hash_unique'|'uid'|'both'|'none', value-or-None)
    Detecta si 'value' existe como hash_unique en precios o como uid en presencia.
    """
    if not value:
        return "none", None
    # Verifica existencia mínima (más rápido que COUNT(*))
    has_hash = bool(db.execute_query(
        f"SELECT 1 FROM {prices_tbl} WHERE hash_unique = %s LIMIT 1", (value,)))
    has_uid = bool(db.execute_query(
        f"SELECT 1 FROM {pres_tbl}    WHERE uid         = %s LIMIT 1", (value,)))
    if has_hash and has_uid:
        return "both", value
    if has_hash:
        return "hash_unique", value
    if has_uid:
        return "uid", value
    return "none", None


def get_hashes_by_uid(uid: str, pres_tbl: str, *, iso: Optional[str] = None, platform_name: Optional[str] = None) -> List[str]:
    """
    Devuelve hashes asociados a un uid, con filtros opcionales de país y plataforma.
    """
    if not uid:
        return []
    where, params = ["p.uid = %s"], [uid]
    if iso:
        where.append("LOWER(p.iso_alpha2) = %s")
        params.append(iso.lower())
    if platform_name:
        where.append("LOWER(p.platform_name) = %s")
        params.append(platform_name)
    sql = f"SELECT DISTINCT p.hash_unique FROM {pres_tbl} p WHERE " + " AND ".join(
        where)
    rows = db.execute_query(sql, tuple(params)) or []
    return [r["hash_unique"] for r in rows if r.get("hash_unique")]

# =============================================================================
# TOKENIZATION FUNCTIONS (CJK-aware)
# =============================================================================


def _tokens(s: Optional[str]) -> List[str]:
    """
    Tokenize string with CJK awareness.

    Args:
        s: String to tokenize

    Returns:
        List of tokens (character-level for CJK, word-level otherwise)
    """
    if not s:
        return []

    norm = normalize(s)
    if not norm:
        return []

    # Check for CJK characters
    if _CJK_RE.search(norm):
        # Character-level tokenization for CJK
        return list(norm.replace(" ", ""))

    return norm.split()


def _choose_scorer(text: str, sample: List[str]) -> Callable:
    """
    Choose appropriate RapidFuzz scorer based on text characteristics.

    Args:
        text: Query text
        sample: Sample of candidates

    Returns:
        Appropriate scorer function for the text type
    """
    if not text:
        return fuzz.token_set_ratio

    # Build sample blob safely
    safe_sample = sample[:50] if sample else []
    blob = text + " " + " ".join(str(s) for s in safe_sample if s)

    # Check for CJK characters
    if _CJK_RE.search(blob):
        return fuzz.WRatio

    return fuzz.token_set_ratio

# =============================================================================
# FUZZY MATCHING FUNCTIONS
# =============================================================================


def best_match_rapidfuzz(
    query: str,
    candidates: List[str],
    cutoff: float = 80
) -> Optional[Tuple[str, float, int]]:
    """
    Find best fuzzy match using RapidFuzz.

    Args:
        query: Query string
        candidates: List of candidate strings
        cutoff: Minimum score threshold

    Returns:
        Tuple of (match, score, index) or None
    """
    if not query or not candidates:
        return None

    # Ensure cutoff is valid
    cutoff = max(0, min(100, cutoff))

    scorer = fuzz.token_set_ratio
    res = process.extractOne(
        query,
        candidates,
        scorer=scorer,
        score_cutoff=cutoff
    )
    return res


def resolve_value_rapidfuzz(
    user_text: str,
    rows: List[Dict],
    field_name: str,
    *,
    cutoff: int = 80,
    ambiguous_delta: int = 2,
    ambiguous_limit: int = 5,
    extractor: Optional[Callable[[Dict], Optional[str]]] = None,
) -> Status:
    """
    Resolve user text to a specific value using fuzzy matching.

    Multilingual support: Unicode, diacritics ignored; CJK supported with 
    adaptive scorer/tokenization.

    Args:
        user_text: User input text
        rows: List of dictionaries to search
        field_name: Field name to match against
        cutoff: Minimum similarity score
        ambiguous_delta: Score delta for ambiguity detection
        ambiguous_limit: Max number of ambiguous results to return
        extractor: Optional custom value extractor function

    Returns:
        Status tuple: 
        - ("resolved", str): Single match found
        - ("ambiguous", [str]): Multiple close matches
        - ("not_found", None): No suitable match
    """
    if not user_text or not rows:
        return "not_found", None

    user_text = user_text.lower()
    q_norm = normalize(user_text)
    q_tok = _tokens(user_text)

    def get_val(r: Dict) -> Optional[str]:
        if extractor:
            return extractor(r)

        if isinstance(r, dict):
            return r.get(field_name)

        return None

    # Build candidate list
    seen = set()
    candidates = []

    for r in rows:
        if not isinstance(r, dict):
            continue

        v = get_val(r)
        if v and v not in seen:
            seen.add(v)
            candidates.append(v)

    if not candidates:
        return "not_found", None

    # Try exact normalized match
    norm_map = {normalize(c): c for c in candidates if c}
    if q_norm and q_norm in norm_map:
        return "resolved", norm_map[q_norm]

    # Try token subset match
    if q_tok:
        for cand in candidates:
            cand_tokens = _tokens(cand)
            if cand_tokens and set(q_tok).issubset(set(cand_tokens)):
                return "resolved", cand

    # Fuzzy matching
    scorer = _choose_scorer(user_text, candidates)
    scored = process.extract(
        user_text,
        candidates,
        scorer=scorer,
        limit=max(ambiguous_limit, 5)
    )

    if not scored:
        return "not_found", None

    # Safely unpack first result
    if len(scored[0]) >= 3:
        best_cand, best_score, _ = scored[0]
    else:
        return "not_found", None

    if best_score < cutoff:
        return "not_found", None

    # Check for ambiguous matches
    near = []
    for item in scored:
        if len(item) >= 2:
            c, s = item[0], item[1]
            if s >= best_score - ambiguous_delta and s >= cutoff:
                near.append(c)

    if len(near) > 1:
        return "ambiguous", near[:ambiguous_limit]

    return "resolved", best_cand

# =============================================================================
# DATE AND TIME FUNCTIONS
# =============================================================================


def get_date_range(days_back: int) -> Tuple[str, str]:
    """
    Return an ISO date range for the last 'days_back' days inclusive.

    Args:
        days_back: Number of days to look back

    Returns:
        Tuple of (date_from, date_to) in ISO format
    """
    # Validate days_back
    days_back = validate_days_back(days_back, default=30)

    today = datetime.now().date()
    date_from = today - timedelta(days=days_back)

    return (date_from.isoformat(), today.isoformat())

# =============================================================================
# DATA HANDLING FUNCTIONS
# =============================================================================


def handle_query_result(
    result: List[Dict],
    operation: str,
    identifier: str
) -> List[Dict]:
    """
    Normalize empty/error results into a consistent shape for tools/agents.

    Args:
        result: Query result list
        operation: Name of the operation performed
        identifier: Identifier used in the query

    Returns:
        Normalized result list with error messages if needed
    """
    if not result:
        logger.debug("No results for %s '%s'", operation, identifier)
        return [{
            "message": f"No se encontraron resultados para {operation} '{identifier}'"
        }]

    # Check for error in single-element result
    if isinstance(result, list) and len(result) == 1:
        first_elem = result[0]
        if isinstance(first_elem, dict) and "error" in first_elem:
            return result

    return result


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
    file_path = Path(f"data/{field_name}.jsonl")

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


def _is_valid_json(text: str) -> Union[Dict, List, None]:
    """
    Parse JSON string and return the object, or None if invalid.

    Args:
        text: String to parse

    Returns:
        Parsed JSON object or None if invalid
    """
    if not text:
        return None

    text = text.strip()
    if not text:
        return None

    # Basic JSON structure check
    if text[0] in '{[' and text[-1] in '}]':
        # This is one case where try/except is appropriate
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None

    return None


def as_tool_payload(rows: Any, *, ident: str = "") -> str:
    """
    Convert query results to JSON for tools, ensuring non-empty response.

    Args:
        rows: Query result (list, dict, etc.)
        ident: Identifier for context in empty messages

    Returns:
        Valid JSON string, never empty
    """
    # Handle None and empty collections
    if rows is None or (hasattr(rows, '__len__') and len(rows) == 0):
        message = "No results found"
        if ident:
            message += f" for {ident}"
        return json.dumps({"message": message, "count": 0}, ensure_ascii=False)

    # Handle string input
    if isinstance(rows, str):
        rows = rows.strip()
        if not rows:
            return json.dumps({"message": "Empty result", "count": 0}, ensure_ascii=False)

        # Check if already valid JSON
        parsed = _is_valid_json(rows)
        if parsed is not None:
            return rows

        # Encapsulate non-JSON string
        return json.dumps({"data": rows}, ensure_ascii=False)

    # Normal serialization with safe fallback
    serialized = _safe_json_dumps(rows)

    if serialized and serialized.strip():
        return serialized

    return json.dumps({"message": "Empty serialization"}, ensure_ascii=False)


def _safe_json_dumps(obj: Any) -> Optional[str]:
    """
    Safely serialize object to JSON.

    Args:
        obj: Object to serialize

    Returns:
        JSON string or None if serialization fails
    """
    # Check for basic JSON-serializable types
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return json.dumps(obj, ensure_ascii=False)

    if isinstance(obj, (list, tuple)):
        # Convert to list and serialize
        return json.dumps(list(obj), ensure_ascii=False, default=str)

    if isinstance(obj, dict):
        return json.dumps(obj, ensure_ascii=False, default=str)

    # For complex objects, use default=str
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except (TypeError, ValueError) as e:
        # This is one case where try/except is appropriate for complex objects
        logger.error(f"JSON serialization failed: {e}")
        return None
