# app/modules/titles.py
import re
from typing import Any, Dict, List, Optional, Callable, Tuple

from infra.db import run_sql
from infra.config import SETTINGS

__all__ = [
    "normalize_title_query",
    "term_without_years",
    "term_tokens_no_numbers",
    "search_title_candidates",
    "detect_hint",
    "select_title_by_hint",
    "safe_autopick",
    "extract_title_query",
]

_ws = re.compile(r"\s+")
_year = re.compile(r"\b(19[0-9]{2}|20[0-3][0-9])\b")

# --------------------------
# Normalización de consultas
# --------------------------
def normalize_title_query(s: str) -> str:
    """
    Normaliza comillas y espacios. No quita acentos para favorecer trigram.
    """
    s = (s or "").strip()
    s = s.replace("“", '"').replace("”", '"').replace("’", "'")
    s = _ws.sub(" ", s)
    return s.strip()


def term_without_years(s: str) -> Optional[str]:
    """
    Elimina años (YYYY) para búsquedas menos sesgadas.
    """
    if not s:
        return None
    t = _year.sub(" ", s)
    t = _ws.sub(" ", t).strip()
    return t or None


def term_tokens_no_numbers(s: str) -> Optional[str]:
    """
    Elimina tokens numéricos puros y deja palabras alfabéticas 4+.
    """
    if not s:
        return None
    t = re.sub(r"\b\d+\b", " ", s)
    t = _ws.sub(" ", t).strip()
    toks = [w for w in t.split() if re.match(r"[a-zA-ZáéíóúñÁÉÍÓÚÑ]{4,}$", w)]
    return " ".join(toks) or None


# --------------------------
# Búsqueda de candidatos
# --------------------------
def search_title_candidates(
    term: str,
    top_k: Optional[int] = None,
    min_similarity: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Busca candidatos con trigram sobre ms.akas.clean_title y une con metadatos.
    Respeta SETTINGS.top_k_default y SETTINGS.min_sim_default si no se especifica.
    """
    term = (term or "").strip()
    if not term or SETTINGS.offline_mode:
        return []

    top_k = int(top_k or SETTINGS.top_k_default)
    min_similarity = float(min_similarity or SETTINGS.min_sim_default)

    sql = """
    WITH c AS (
      SELECT a.uid, similarity(a.clean_title, %(t)s) AS sim
      FROM ms.akas a
      WHERE a.clean_title %% %(t)s
        AND similarity(a.clean_title, %(t)s) >= %(minsim)s
      ORDER BY 2 DESC
      LIMIT %(k)s
    )
    SELECT
      m.uid,
      m.imdb_id,
      m.title,
      m.year,
      m.type,
      m.directors,
      m.synopsis,
      c.sim
    FROM c
    JOIN ms.new_cp_metadata_estandar m ON m.uid = c.uid
    ORDER BY c.sim DESC, m.year DESC NULLS LAST;
    """
    return run_sql(sql, {"t": term, "k": top_k, "minsim": min_similarity}) or []


# --------------------------
# Hints y selección por hint
# --------------------------
_ordinal_es = {
    "primera": 1, "primer": 1, "primero": 1, "la primera": 1, "el primero": 1,
    "segunda": 2, "segundo": 2, "la segunda": 2, "el segundo": 2,
    "tercera": 3, "tercero": 3, "la tercera": 3, "el tercero": 3,
    "cuarta": 4, "cuarto": 4, "la cuarta": 4, "el cuarto": 4,
    "quinta": 5, "quinto": 5, "la quinta": 5, "el quinto": 5,
}
_ordinal_en = {
    "first": 1, "the first": 1,
    "second": 2, "the second": 2,
    "third": 3, "the third": 3,
    "fourth": 4, "the fourth": 4,
    "fifth": 5, "the fifth": 5,
}

def detect_hint(text: str) -> Dict[str, Any]:
    """
    Extrae pistas: imdb_id (tt\\d+), uid (hex), year, ordinal, director ("de X" | "by X").
    """
    t = (text or "").strip()

    # IMDb
    m = re.search(r"\btt(\d{6,9})\b", t, flags=re.I)
    if m:
        return {"imdb_id": f"tt{m.group(1)}"}

    # UID estilo hash
    m = re.search(r"\b[a-f0-9]{16,}\b", t, flags=re.I)
    if m:
        return {"uid": m.group(0)}

    # Año
    y = _year.search(t)
    if y:
        try:
            return {"year": int(y.group(1))}
        except Exception:
            pass

    # Ordinal
    low = t.lower().strip()
    if low in _ordinal_es:
        return {"ordinal": _ordinal_es[low]}
    if low in _ordinal_en:
        return {"ordinal": _ordinal_en[low]}

    # Director (heurístico al final)
    md = re.search(r"(?:de|del|by)\s+([A-Za-zÁÉÍÓÚÑáéíóúñ][\w\s\.\-']{2,})$", t, flags=re.I)
    if md:
        return {"director": md.group(1).strip()}

    return {}


def select_title_by_hint(candidates: List[Dict[str, Any]], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Aplica heurísticas para elegir 1 candidato según el hint detectado.
    """
    if not candidates or not hint:
        return None

    # 1) UID
    if "uid" in hint:
        for c in candidates:
            if (c.get("uid") or "").lower() == hint["uid"].lower():
                return c

    # 2) IMDb
    if "imdb_id" in hint:
        for c in candidates:
            if (c.get("imdb_id") or "").lower() == hint["imdb_id"].lower():
                return c

    # 3) Año
    if "year" in hint:
        same_year = [c for c in candidates if str(c.get("year") or "") == str(hint["year"])]
        if len(same_year) == 1:
            return same_year[0]
        if same_year:
            return same_year[0]

    # 4) Ordinal (1..n)
    if "ordinal" in hint and 1 <= hint["ordinal"] <= len(candidates):
        return candidates[hint["ordinal"] - 1]

    # 5) Director (contiene substring)
    if "director" in hint:
        dlow = hint["director"].lower()
        for c in candidates:
            if dlow in (c.get("directors") or "").lower():
                return c

    return None


def safe_autopick(cands: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Autoselecciona el primer candidato si sim es alta y hay distancia clara con el segundo.
    """
    if not cands:
        return None
    c0 = cands[0]
    s0 = float(c0.get("sim") or 0.0)
    s1 = float(cands[1].get("sim") or 0.0) if len(cands) > 1 else 0.0
    if s0 >= SETTINGS.autopick_sim and (s0 - s1) >= SETTINGS.autopick_delta:
        return c0
    return None


# --------------------------
# Stop-phrases & extractor
# --------------------------
_STOP_PHRASES = [
    "donde ver", "dónde ver", "donde esta", "dónde está",
    "en que plataforma", "en qué plataforma", "availability", "available on",
    "where to watch", "where is it streaming",
    "sinopsis", "de que trata", "de qué trata", "resumen", "trama",
    "argumento", "de qué va", "de que va",
    "plot", "overview", "popularidad", "hits", "top", "ranking",

    # variantes naturales
    "donde puedo ver", "dónde puedo ver",
    "donde puedo verla", "dónde puedo verla",
    "donde puedo verlo", "dónde puedo verlo",
    "puedo ver", "puedo verla", "puedo verlo",
    "verla", "verlo", "se ve", "donde se ve", "dónde se ve",
    "plataforma", "plataformas",
]

def extract_title_query(
    text: str,
    *,
    strip_country: bool = True,
    guess_country_fn: Optional[Callable[[str], Tuple[Optional[str], Optional[str]]]] = None
) -> Optional[str]:
    """
    Intenta extraer el término de título desde texto libre:
      - Limpia stop-phrases (“dónde ver…”, “availability”, “hits”, etc.).
      - Si strip_country=True y se pasa guess_country_fn, elimina el país (ISO2 y nombre).
    """
    s = normalize_title_query(text or "")
    if not s:
        return None

    low = s.lower()
    for p in _STOP_PHRASES:
        low = low.replace(p, " ")

    if strip_country and guess_country_fn:
        try:
            iso2, pretty = guess_country_fn(s)
        except Exception:
            iso2, pretty = None, None
        if iso2:
            low = low.replace(iso2.lower(), " ")
        if pretty:
            low = low.replace(str(pretty).lower(), " ")

    return _ws.sub(" ", low).strip() or None