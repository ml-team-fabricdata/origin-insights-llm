
from __future__ import annotations

# Standard library imports
import asyncio
from datetime import datetime, timedelta
import concurrent
from functools import wraps
from rapidfuzz import process, fuzz
from src.sql.constants_sql import *
from typing import Any, Callable, Optional, Dict, List, Tuple, Union, Literal
import re, unicodedata as ud
import logging, json
logger = logging.getLogger(__name__)


# Definir el tipo Status que falta
Status = Tuple[Literal["resolved", "ambiguous", "not_found"], Optional[Union[str, List[str]]]]


# -----------------------------------------------------------------------------
# Validation helpers
# -----------------------------------------------------------------------------
def validate_limit(
    limit: int | None,
    default: int = 20,
    max_limit: int = 500,
    *,
    lo: int | None = None,
    hi: int | None = None,  # ✅ Definir como parámetro explícito
    **_ignored,
) -> int:
    # Lógica corregida para manejar lo/hi
    if lo is not None:
        default = max(default, int(lo))
    if hi is not None:
        max_limit = int(hi)    
    # Validar y normalizar limit
    try:
        n = int(limit) if limit is not None else None
    except (TypeError, ValueError):
        n = None
    
    if not isinstance(n, int) or n <= 0:
        return int(default)
    
    return min(n, int(max_limit))

def validate_days_back(days_back: int | None, default: int = 30) -> int:
    """Validate relative days window (1..365)."""
    if not isinstance(days_back, int) or days_back <= 0:
        return default
    return min(days_back, 365)

def get_date_range(days_back: int) -> Tuple[str, str]:
    """Return an ISO (date_from, date_to) pair for the last 'days_back' days inclusive."""
    today = datetime.now().date()
    date_from = today - timedelta(days=days_back)
    
    return (date_from.isoformat(), today.isoformat())


# -----------------------------------------------------------------------------
# Result helpers
# -----------------------------------------------------------------------------
def handle_query_result(result: List[Dict], operation: str, identifier: str) -> List[Dict]:
    """Normalize empty/error results into a consistent shape for tools/agents."""
    if not result:
        logger.debug("No results for %s '%s'", operation, identifier)
        return [{"message": f"No se encontraron resultados para {operation} '{identifier}'"}]
    if isinstance(result, list) and len(result) == 1 and isinstance(result[0], dict) and "error" in result[0]:
        return result
    return result

def get_validation(field_name: str) -> List[Dict]:
    """
    Obtiene la validación para un campo específico.
    Handles empty lines and malformed JSON gracefully.
    """
    result = []
    try:
        with open(f"data/{field_name}.jsonl", "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                try:
                    parsed = json.loads(line)
                    result.append(parsed)
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping malformed JSON in {field_name}.jsonl line {line_num}: {e}")
                    continue
                    
        logger.info(f"✅ {field_name} consultados, total: {len(result)}")
        return handle_query_result(result, f"{field_name}", "all")
        
    except FileNotFoundError:
        logger.error(f"Validation file not found: data/{field_name}.jsonl")
        return [{"error": f"Validation file not found: {field_name}"}]
    except Exception as e:
        logger.error(f"Error reading validation file {field_name}: {e}")
        return [{"error": f"Error reading validation file: {str(e)}"}]


def normalize(s: Optional[str]) -> str:
    s = ud.normalize("NFKC", (s or "").casefold()).strip()
    s = (s or "").lower().strip()
    s = re.sub(r"[^\w\s-]", " ", s)     # quita puntuación
    s = re.sub(r"\s+", "", s)            # colapsa espacios
    s = re.sub(r"-+", "", s)             # colapsa guiones
    return s


def best_match_rapidfuzz(query: str, candidates: list[str], cutoff: float = 80):
    # Elegí el scorer según tus datos: fuzz.WRatio, fuzz.token_set_ratio, fuzz.token_sort_ratio, fuzz.partial_ratio...
    scorer = fuzz.token_set_ratio
    # extractOne devuelve (match, score, idx)
    res = process.extractOne(
        query,
        candidates,
        scorer=scorer,
        score_cutoff=cutoff
    )
    return res

_CJK_RE = re.compile(r"[\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]")

def as_tool_payload(rows: Any, *, ident: str = "") -> str:
    """
    Convierte cualquier resultado en un string JSON NO vacío para Bedrock/Anthropic.
    - Si rows está vacío, devuelve un mensaje informativo.
    - Si rows no es string, lo serializa a JSON.
    """
    if rows in (None, [], ()):
        payload = [{"message": f"No results{f' for {ident}' if ident else ''}"}]
    else:
        payload = rows
    if isinstance(payload, str):
        # Garantiza no vaciar
        return payload if payload.strip() else '{"message":"ok"}'
    return json.dumps(payload, ensure_ascii=False)

def _tokens(s: Optional[str]) -> List[str]:
    norm = normalize(s)
    if _CJK_RE.search(norm):
        return list(norm.replace(" ", ""))  # tokeniza por carácter para CJK
    return norm.split()

def _choose_scorer(text: str, sample: List[str]):
    blob = text + " " + " ".join(sample[:50])
    return fuzz.WRatio if _CJK_RE.search(blob) else fuzz.token_set_ratio

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
    Devuelve: ("resolved", str) | ("ambiguous", [str]) | ("not_found", None)
    Multilingüe: Unicode, diacríticos ignorados; CJK soportado con scorer/tokenización adaptativa.
    """
    user_text = user_text.lower()
    q_norm = normalize(user_text)
    q_tok  = _tokens(user_text)

    def get_val(r: Dict) -> Optional[str]:
        return extractor(r) if extractor else (r.get(field_name) if isinstance(r, dict) else None)

    seen, candidates = set(), []
    for r in rows:
        v = get_val(r)
        if v and v not in seen:
            seen.add(v); candidates.append(v)

    if not candidates:
        return "not_found", None

    norm_map = { normalize(c): c for c in candidates }
    if q_norm and q_norm in norm_map:
        return "resolved", norm_map[q_norm]

    if q_tok:
        for cand in candidates:
            if set(q_tok).issubset(set(_tokens(cand))):
                return "resolved", cand

    scorer = _choose_scorer(user_text, candidates)
    scored = process.extract(
        user_text, candidates, scorer=scorer, limit=max(ambiguous_limit, 5)
    )
    if not scored:
        return "not_found", None

    best_cand, best_score, _ = scored[0]
    if best_score < cutoff:
        return "not_found", None

    near = [c for c, s, _ in scored if s >= best_score - ambiguous_delta and s >= cutoff]
    if len(near) > 1:
        return "ambiguous", [n for n in near[:ambiguous_limit]]
    return "resolved", best_cand




def validate_limit(limit: Optional[int], default: int = 20, max_limit: int = 100) -> int:
    if not isinstance(limit, int) or limit <= 0:
        return default
    return min(limit, max_limit)

def clean_text(text: str) -> str:
    if not text:
        return ""
    normalized = ud.normalize("NFKD", text).lower()
    return "".join(c for c in normalized if not ud.combining(c))


def normalize_input(input_data: Union[str, List[str], Any]) -> str:
    if not input_data:
        return ""
    if isinstance(input_data, list):
        return input_data[0] if input_data else ""
    return str(input_data).strip() if input_data else ""



def is_single_token(text: str) -> bool:
    if not text or not isinstance(text, str):
        return False
    return len(text.strip().split()) == 1


def normalize_threshold(threshold: Optional[float] = None) -> float:
    if threshold is None:
        return FUZZY_THRESHOLD
    return max(0.1, min(1.0, float(threshold) if isinstance(threshold, (int, float)) else FUZZY_THRESHOLD))


def async_to_sync(async_func):
    """
    Decorador genérico que convierte cualquier función asíncrona en síncrona
    """
    @wraps(async_func)
    def sync_wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(async_func(*args, **kwargs))
        else:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, async_func(*args, **kwargs))
                return future.result()
    return sync_wrapper