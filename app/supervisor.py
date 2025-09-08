# app/supervisor.py
import re
from typing import Optional, Dict, Any, List

from infra.config import SETTINGS
from app.llm.postprocess import rewrite_for_user_language

# ---------- Reusamos routers deterministas como librerías internas ----------
# Popularidad / TOP (ya integrado)
from app.router_popularity import popularity_entrypoint, QueryIn as PopQueryIn  # type: ignore

# Sinopsis / Disponibilidad (opcional, con fallback si no existen)
try:
    from app.router_query import query_entrypoint, QueryIn as GenericQueryIn  # type: ignore
    _HAS_GENERIC_QUERY = True
except Exception:
    _HAS_GENERIC_QUERY = False


# ---------- Intents ----------
_RE_TOP = re.compile(r"\b(top\s*\d{0,3}|ranking|más\s+populares|mas\s+populares|populares)\b", re.IGNORECASE)
_RE_POP = re.compile(r"\b(popularidad|hits?)\b", re.IGNORECASE)

_RE_SYNOPSIS_ES = re.compile(r"\b(sinopsis|resumen|de\ qué\ trata|de\ que\ trata|trama|argumento)\b", re.IGNORECASE)
_RE_SYNOPSIS_EN = re.compile(r"\b(synopsis|plot|what(?:’|')?s it about|what is it about|storyline)\b", re.IGNORECASE)

_RE_AVAIL_ES = re.compile(r"\b(disponibilidad|dónde\s+ver|donde\s+ver|en\s+qué\s+plataforma|plataformas?)\b", re.IGNORECASE)
_RE_AVAIL_EN = re.compile(r"\b(where\s+to\s+watch|availability|platforms?)\b", re.IGNORECASE)

_RE_TRANSLATE_ES = re.compile(r"\b(traduc[ei]r?|traduce|traducción)\b", re.IGNORECASE)
_RE_TRANSLATE_EN = re.compile(r"\b(translate|translation|translate\s+to)\b", re.IGNORECASE)

def _is_popularity_or_top(q: str) -> bool:
    t = q or ""
    return bool(_RE_TOP.search(t)) or bool(_RE_POP.search(t))

def _is_synopsis(q: str) -> bool:
    t = q or ""
    return bool(_RE_SYNOPSIS_ES.search(t) or _RE_SYNOPSIS_EN.search(t))

def _is_availability(q: str) -> bool:
    t = q or ""
    return bool(_RE_AVAIL_ES.search(t) or _RE_AVAIL_EN.search(t))

def _wants_translation(q: str) -> Optional[str]:
    """
    Detecta si el usuario pidió explícitamente traducir y a qué idioma.
    Retorna 'es'/'en' o None.
    """
    ql = (q or "").lower()
    if _RE_TRANSLATE_ES.search(ql):
        if "ingl" in ql or "english" in ql:
            return "en"
        if "espa" in ql:
            return "es"
        return "es"
    if _RE_TRANSLATE_EN.search(ql):
        if "spanish" in ql or "español" in ql or "esp" in ql:
            return "es"
        return "en"
    return None

def _lang_hint(q: str) -> str:
    ql = (q or "").lower()
    if "¿" in q or "¡" in q or any(w in ql for w in ["qué", "cual", "popularidad", "disponibilidad", "sinopsis", "dónde ver", "donde ver"]):
        return "es"
    return "en"


# ---------- Render helpers: Popularidad ----------
def _render_popularity_payload(payload: Dict[str, Any]) -> str:
    kind = payload.get("kind")
    data = payload.get("payload") or {}

    if kind == "not_found":
        return "No encontré coincidencias para ese título. ¿Querés que te muestre opciones similares?"

    if kind == "ambiguous":
        opts = data.get("options", [])
        if not opts:
            return "Necesito que me confirmes el título exacto. ¿Podés precisar el año o darme más detalles?"
        lines = ["Encontré varios títulos. Decime cuál elegís (número, UID o IMDb):"]
        for i, r in enumerate(opts, start=1):
            t = r.get("title") or "-"
            y = r.get("year") or "-"
            imdb = r.get("imdb_id") or "-"
            lines.append(f"{i}. {t} ({y}) — IMDb: {imdb}")
        return "\n".join(lines)

    if kind == "top_list":
        scope = data.get("scope_pretty") or (data.get("scope") or "Global")
        year = data.get("year")
        ctype = data.get("content_type")
        items = data.get("items", [])
        hdr = f"TOP {len(items)}{' ' + ('películas' if ctype=='movie' else 'series' if ctype=='series' else 'títulos')} por HITS en {scope} ({year})."
        lines = [hdr]
        for i, it in enumerate(items, start=1):
            t = it.get("title") or "-"
            s = int(round(it.get("hits_sum") or 0))
            lines.append(f"{i}. {t} — HITS={s}")
        return "\n".join(lines)

    if kind == "title_popularity":
        msgs = data.get("messages") or {}
        base = msgs.get("es") or msgs.get("en") or "Aquí tienes la popularidad del título."
        return base

    return "Puedo ayudarte con popularidad (HITS), disponibilidad y metadatos. ¿Qué te gustaría explorar?"


# ---------- Render helpers: Sinopsis / Disponibilidad (genérico) ----------
def _render_generic_payload(kind: str, data: Dict[str, Any]) -> str:
    """
    Intenta formatear de forma amable resultados de sinopsis o disponibilidad,
    sin acoplarse a un esquema rígido (para no romper si cambia el payload).
    """
    # Sinopsis
    if "synopsis" in data or "sinopsis" in data:
        title = data.get("title") or data.get("titulo") or data.get("name") or ""
        year = data.get("year") or data.get("anio")
        syn = data.get("synopsis") or data.get("sinopsis") or ""
        head = f"Sinopsis de «{title}»" + (f" ({year})" if year else "")
        return f"{head}:\n{syn}".strip()

    # Disponibilidad (lista por país/plataforma)
    if "availability" in data or "presences" in data or "items" in data:
        items: List[Dict[str, Any]] = (
            data.get("availability")
            or data.get("presences")
            or data.get("items")
            or []
        )
        scope = data.get("country") or data.get("country_pretty") or data.get("scope") or ""
        title = data.get("title") or ""
        year = data.get("year")
        lines = []
        if title:
            hdr = f"Disponibilidad de «{title}»" + (f" ({year})" if year else "")
            if scope:
                hdr += f" — {scope}"
            lines.append(hdr + ":")
        for it in items:
            plat = it.get("platform_name") or it.get("platform") or "-"
            country = it.get("platform_country") or it.get("country") or ""
            url = it.get("permalink") or it.get("url") or ""
            when_in = it.get("enter_on") or it.get("in") or None
            when_out = it.get("out_on") or it.get("out") or None
            line = f"- {plat}"
            if country:
                line += f" ({country})"
            if when_in or when_out:
                line += " — "
                if when_in:
                    line += f"desde {when_in}"
                if when_out:
                    line += f" hasta {when_out}"
            if url:
                line += f" — {url}"
            lines.append(line)
        if lines:
            return "\n".join(lines)
        return "Puedo listar disponibilidad por país y plataforma si me confirmás el título (y opcionalmente el país)."

    # Fallback
    if kind.lower().startswith("synop"):
        return "Puedo darte la sinopsis si me confirmás el título (y el año si hay varias opciones)."
    if "avail" in kind.lower() or "dispon" in kind.lower():
        return "Puedo mostrar disponibilidad por país/plataforma si me indicás el título (y el país)."

    return "¿Querés que busque sinopsis o disponibilidad para un título específico?"


# ---------- LLM libre como fallback (opcional) ----------
def _call_llm_freeform(text: str, lang: Optional[str]) -> Optional[str]:
    if not SETTINGS.enable_freeform_llm:
        return None
    try:
        from app.router_llm import ask_llm, LLMQueryIn  # type: ignore
        r = ask_llm(LLMQueryIn(text=text, lang=lang))
        if r and isinstance(r.payload, dict):
            return r.payload.get("answer") or r.payload.get("message")
    except Exception:
        pass
    return None


# ---------- Supervisor API ----------
def handle_query(user_query: str, lang: Optional[str] = None) -> Dict[str, Any]:
    """
    Decide el camino (determinista vs LLM) y postprocesa la respuesta para el idioma del usuario.
    Retorna dict con 'text' y 'meta'.
    """
    q = user_query or ""
    lang_hint = lang or _lang_hint(q)

    # 1) Popularidad / TOP → determinista + postprocess
    if _is_popularity_or_top(q):
        pop_resp = popularity_entrypoint(PopQueryIn(text=q))
        base_text = _render_popularity_payload({"kind": pop_resp.kind, "payload": pop_resp.payload})
        explicit_target = _wants_translation(q)
        target_lang = explicit_target or lang_hint
        final_text = rewrite_for_user_language(base_text, user_query=q, target_lang_hint=target_lang)
        return {
            "text": final_text,
            "meta": {
                "path": "deterministic.popularity",
                "lang_hint": lang_hint,
                "translated": bool(final_text != base_text),
                "llm_used": bool(final_text != base_text),
            }
        }

    # 2) Sinopsis / Disponibilidad → determinista + postprocess (si hay entrypoint)
    if _HAS_GENERIC_QUERY and (_is_synopsis(q) or _is_availability(q)):
        try:
            resp = query_entrypoint(GenericQueryIn(text=q))  # type: ignore
            kind = getattr(resp, "kind", "generic")
            payload = getattr(resp, "payload", {}) or {}
            base_text = _render_generic_payload(kind, payload)

            explicit_target = _wants_translation(q)
            target_lang = explicit_target or lang_hint
            final_text = rewrite_for_user_language(base_text, user_query=q, target_lang_hint=target_lang)

            return {
                "text": final_text,
                "meta": {
                    "path": f"deterministic.{kind}",
                    "lang_hint": lang_hint,
                    "translated": bool(final_text != base_text),
                    "llm_used": bool(final_text != base_text),
                }
            }
        except Exception:
            # Si algo cambia en router_query, no rompemos el flujo
            pass

    # 3) Fallback: LLM libre si está habilitado
    freeform = _call_llm_freeform(q, lang_hint)
    if freeform:
        return {
            "text": freeform,
            "meta": {
                "path": "llm.freeform",
                "lang_hint": lang_hint,
                "llm_used": True,
            }
        }

    # 4) Si el LLM libre no está disponible / deshabilitado → mensaje guía
    if lang_hint == "es":
        msg = ("Puedo ayudarte con sinopsis, disponibilidad por país/plataforma y popularidad (HITS). "
               "Por ejemplo: “popularidad de Conclave (2025)”, “top 10 películas global 2025”, "
               "o “dónde ver The Office en Argentina”.")
    else:
        msg = ("I can help with synopsis, availability by country/platform, and popularity (HITS). "
               "For example: “popularity of Conclave (2025)”, “top 10 movies global 2025”, "
               "or “where to watch The Office in Argentina”.")
    return {
        "text": msg,
        "meta": {
            "path": "help",
            "lang_hint": lang_hint,
            "llm_used": False,
        }
    }