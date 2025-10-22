from __future__ import annotations
from src.strands.core.shared_imports import *
from src.strands.infrastructure.database.constants import *

Status = Tuple[str, Union[str, List[str], None]]

_CJK_RE = re.compile(r"[\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]")


def build_like_pattern(value: Optional[str]) -> str:
    if not value:
        return "%"
    escaped = str(value).strip().replace('%', '\\%').replace('_', '\\_')
    return f"%{escaped}%"


def build_like_any(col: str, values: List[str], params: Dict[str, Any], ph_prefix: str) -> str:
    if not values:
        return ""
        
    parts = []
    for i, v in enumerate(values):
        if not v or not str(v).strip():
            continue
        key = f"{ph_prefix}{i}"
        params[key] = build_like_pattern(str(v))
        parts.append(f"{col} ILIKE %({key})s")
        
    return "(" + " OR ".join(parts) + ")" if parts else ""


def build_in_clause(field: str, values: Optional[List[Any]]) -> Tuple[str, List[Any]]:
    if not values:
        return "", []
    placeholders = ", ".join(["%s"] * len(values))
    return f"{field} IN ({placeholders})", list(values)


def validate_limit(
    limit: Optional[int] = None,
    default: int = 20,
    max_limit: int = 500,
    *,
    lo: Optional[int] = None,
    hi: Optional[int] = None,
    **_ignored,
) -> int:
    if lo is not None and isinstance(lo, (int, float)):
        default = max(default, int(lo))
    if hi is not None and isinstance(hi, (int, float)):
        max_limit = int(hi)

    if limit is None:
        return int(default)

    if not isinstance(limit, (int, float)):
        return int(default)

    n = int(limit)
    if n <= 0:
        return int(default)

    return min(n, int(max_limit))


def normalize_threshold(threshold: Optional[float] = None) -> float:
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

    return str(input_data).strip()



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

    s = ud.normalize("NFKC", s.casefold()).strip()
    s = s.lower().strip()

    s = re.sub(r"[^\w\s-]", " ", s)
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"-+", "", s)

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

    normalized = ud.normalize("NFKD", text)
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
        where.append("p.iso_alpha2 = %s")
        params.append(iso)
    if platform_name:
        where.append("LOWER(p.platform_name) = %s")
        params.append(platform_name.lower())
    sql = f"SELECT DISTINCT p.hash_unique FROM {pres_tbl} p WHERE " + " AND ".join(
        where)
    rows = db.execute_query(sql, tuple(params)) or []
    return [r["hash_unique"] for r in rows if r.get("hash_unique")]



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

    if _CJK_RE.search(norm):
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

    safe_sample = sample[:50] if sample else []
    blob = text + " " + " ".join(str(s) for s in safe_sample if s)

    if _CJK_RE.search(blob):
        return fuzz.WRatio

    return fuzz.token_set_ratio



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

    norm_map = {normalize(c): c for c in candidates if c}
    if q_norm and q_norm in norm_map:
        return "resolved", norm_map[q_norm]

    if q_tok:
        for cand in candidates:
            cand_tokens = _tokens(cand)
            if cand_tokens and set(q_tok).issubset(set(cand_tokens)):
                return "resolved", cand

    scorer = _choose_scorer(user_text, candidates)
    scored = process.extract(
        user_text,
        candidates,
        scorer=scorer,
        limit=max(ambiguous_limit, 5)
    )

    if not scored:
        return "not_found", None

    if len(scored[0]) >= 3:
        best_cand, best_score, _ = scored[0]
    else:
        return "not_found", None

    if best_score < cutoff:
        return "not_found", None

    near = []
    for item in scored:
        if len(item) >= 2:
            c, s = item[0], item[1]
            if s >= best_score - ambiguous_delta and s >= cutoff:
                near.append(c)

    if len(near) > 1:
        return "ambiguous", near[:ambiguous_limit]

    return "resolved", best_cand



def get_date_range(days_back: int) -> Tuple[str, str]:
    """
    Return an ISO date range for the last 'days_back' days inclusive.

    Args:
        days_back: Number of days to look back

    Returns:
        Tuple of (date_from, date_to) in ISO format
    """
    days_back = validate_days_back(days_back, default=30)

    today = datetime.now().date()
    date_from = today - timedelta(days=days_back)

    return (date_from.isoformat(), today.isoformat())


_TIME_AGO_PATTERN = re.compile(
    r"^\s*(?:hace\s+)?(\d+(?:\.\d+)?)\s+"
    r"(anio|ano|año|anos|años|year|years|"
    r"mes|meses|month|months|"
    r"semana|semanas|week|weeks|"
    r"dia|dias|day|days)"
    r"(?:\s+(?:atras|atrás|ago))?\s*$",
    re.IGNORECASE
)

_DAYS_PATTERN = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*"
    r"(?:([ymwd])|"
    r"(anio|ano|año|anos|años|year|years|"
    r"mes|meses|month|months|"
    r"semana|semanas|week|weeks|"
    r"dia|dias|day|days))?\s*$",
    re.IGNORECASE
)

_UNIT_TO_DAYS = {
    'y': 365, 'anio': 365, 'ano': 365, 'año': 365,
    'anos': 365, 'años': 365, 'year': 365, 'years': 365,
    'm': 30, 'mes': 30, 'meses': 30, 'month': 30, 'months': 30,
    'w': 7, 'semana': 7, 'semanas': 7, 'week': 7, 'weeks': 7,
    'd': 1, 'dia': 1, 'dias': 1, 'day': 1, 'days': 1, '': 1
}

_ACCENT_TRANS = str.maketrans('áéíóú', 'aeiou')



def parse_time_to_days(
    value: NumberOrStr,
    *,
    default: int = 30,
    max_days: int = 36500
) -> int:
    """
    Convierte expresiones temporales a días.
    """
    if value is None:
        return default

    if isinstance(value, (int, float)):
        days = int(value)
        return default if days <= 0 else min(days, max_days)

    s = str(value).strip().lower().translate(_ACCENT_TRANS)

    match = _TIME_AGO_PATTERN.match(s)
    if match:
        qty = float(match.group(1))
        unit = match.group(2).lower()
        factor = _UNIT_TO_DAYS.get(unit, 1)
        days = int(qty * factor)
        return default if days <= 0 else min(days, max_days)

    match = _DAYS_PATTERN.match(s)
    if match:
        qty = float(match.group(1))
        unit = (match.group(2) or match.group(3) or '').lower()
        factor = _UNIT_TO_DAYS.get(unit, 1)
        days = int(qty * factor)
        return default if days <= 0 else min(days, max_days)

    return default


def validate_days_back(
    value: NumberOrStr,
    *,
    default: int = 30,
    max_days: int = 36500
) -> int:
    """
    Versión mejorada de validate_days_back que acepta expresiones naturales.

    Compatible con código existente pero ahora también acepta:
    - "hace 5 años"
    - "3 semanas atrás"
    - "2 meses"
    - "5y", "3m", "2w"

    Ejemplos:
        validate_days_back(30) → 30
        validate_days_back("hace 5 años") → 1825
        validate_days_back("3 semanas") → 21
        validate_days_back("5y") → 1825
    """
    return parse_time_to_days(value, default=default, max_days=max_days)


def normalize_args_kwargs(args, kwargs, parse_arg1=False):
    """
    Unified normalization function for args/kwargs in tool functions.
    
    Args:
        args: Positional arguments
        kwargs: Keyword arguments
        parse_arg1: If True, parse __arg1 for filters (requires NO_FILTER_KEYWORDS)
        
    Returns:
        Normalized kwargs dictionary
        
    Examples:
        >>> normalize_args_kwargs(("US",), {})
        {'__arg1': 'US'}
        >>> normalize_args_kwargs(({"country": "US"},), {"limit": 10})
        {'country': 'US', 'limit': 10}
    """
    if args:
        if len(args) == 1:
            a0 = args[0]
            if isinstance(a0, dict):
                merged = dict(a0)
                merged.update(kwargs or {})
                kwargs = merged
            else:
                kwargs = dict(kwargs or {})
                kwargs.setdefault("__arg1", a0)
        else:
            kwargs = dict(kwargs or {})
            kwargs.setdefault("__arg1", args[0])
    else:
        kwargs = kwargs or {}
    
    return kwargs


def safe_cast_float(value: Any, default: float = 0.0) -> float:
    """
    Safely cast value to float with default fallback.
    
    Args:
        value: Value to cast
        default: Default value if casting fails
        
    Returns:
        Float value or default
        
    Examples:
        >>> safe_cast_float("3.14")
        3.14
        >>> safe_cast_float(None, 0.0)
        0.0
        >>> safe_cast_float("invalid", 1.0)
        1.0
    """
    if value is None:
        return default
    return float(value)


def safe_cast_int(value: Any, default: int = 0) -> int:
    """
    Safely cast value to int with default fallback.
    
    Args:
        value: Value to cast
        default: Default value if casting fails
        
    Returns:
        Int value or default
        
    Examples:
        >>> safe_cast_int("42")
        42
        >>> safe_cast_int(None, 0)
        0
        >>> safe_cast_int("invalid", -1)
        -1
    """
    if value is None:
        return default
    return int(value)


def format_validation_options(options: List[Dict[str, Any]], entity_type: str = "option") -> str:
    """
    Format validation options for display (actors, directors, etc.).
    
    Args:
        options: List of option dictionaries with 'name', 'id', and optional 'score'
        entity_type: Type of entity for error messages (not used in current implementation)
        
    Returns:
        Formatted string with options list
        
    Examples:
        >>> opts = [{"name": "Brad Pitt", "id": "1234", "score": 0.95}]
        >>> format_validation_options(opts)
        '- Brad Pitt (id: 1234, score: 0.95)'
    """
    if not options:
        return ""
    
    return "\n".join(
        f"- {opt['name']} (id: {opt['id']}" +
        (f", score: {opt['score']:.2f}" if opt.get("score") else "") + ")"
        for opt in options
    )


def clamp_rolling(
    max_date: date,
    current_days: int,
    previous_days: int
) -> Tuple[date, date, date, date]:
    """
    Calcula rangos para período actual y anterior.

    Args:
        max_date: Fecha máxima de referencia
        current_days: Días del período actual
        previous_days: Días del período anterior

    Returns:
        (cur_from, cur_to, prev_from, prev_to)
    """
    cur_to = max_date
    cur_from = max_date - timedelta(days=current_days - 1)

    prev_to = cur_from - timedelta(days=1)
    prev_from = prev_to - timedelta(days=previous_days - 1)

    return cur_from, cur_to, prev_from, prev_to




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

    if isinstance(result, list) and len(result) == 1:
        first_elem = result[0]
        if isinstance(first_elem, dict) and "error" in first_elem:
            return result

    return result


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

    if text[0] in '{[' and text[-1] in '}]':
        return json.loads(text)

    return None


def _safe_json_dumps(obj: Any) -> Optional[str]:
    """
    Safely serialize object to JSON.

    Args:
        obj: Object to serialize

    Returns:
        JSON string or None if serialization fails
    """
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return json.dumps(obj, ensure_ascii=False)

    if isinstance(obj, (list, tuple)):
        return json.dumps(list(obj), ensure_ascii=False, default=str)

    if isinstance(obj, dict):
        return json.dumps(obj, ensure_ascii=False, default=str)

    return json.dumps(obj, ensure_ascii=False, default=str)
