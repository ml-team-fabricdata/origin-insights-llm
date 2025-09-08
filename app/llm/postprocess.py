# app/llm/postprocess.py
"""
Post-procesador de salida determinista:
- Uniforma tono/idioma con identidad de marca Fabric.
- Traduce o reescribe (si procede), preservando datos estructurados (URLs, IDs, números).
- Falla en modo seguro (retorna el texto base) si no hay backend LLM.

APIs expuestas:
- rewrite_for_user_language(base_text: str, user_query: str, target_lang_hint: Optional[str]) -> str
"""

from __future__ import annotations
import os
import re
from typing import Optional

from infra.config import SETTINGS

# --------------------------------------------------------------------------------------
# Branding (una sola línea, tono cálido y profesional)
# --------------------------------------------------------------------------------------

_BRAND_ES = (
    "Soy el asistente virtual de Fabric: te ayudo a explorar sinopsis, disponibilidad por país/plataforma y popularidad (HITS)."
)

_BRAND_EN = (
    "I’m Fabric’s virtual assistant—here to help with synopsis, availability by country/platform, and popularity (HITS)."
)

def _brand_intro(lang: str) -> str:
    return _BRAND_ES if lang.startswith("es") else _BRAND_EN


# --------------------------------------------------------------------------------------
# Heurísticas livianas de idioma (sin dependencias extra)
# --------------------------------------------------------------------------------------

_RE_SP_HINT = re.compile(r"[¿¡áéíóúñ]|\b(cu[aá]l|qu[eé]|d[oó]nde|pel[ií]cula|serie|disponibilidad|popularidad)\b", re.I)
_RE_EN_HINT = re.compile(r"\b(what|where|movie|series|availability|popularity|top)\b", re.I)

def _guess_lang(text: str, fallback: str = "es") -> str:
    t = (text or "")
    tl = t.lower()
    if _RE_SP_HINT.search(tl):
        return "es"
    if _RE_EN_HINT.search(tl):
        return "en"
    # Preferimos hint de sistema si está activo
    if SETTINGS.enable_llm_lang:
        # Aun si el detector LLM estuviera apagado, no tiramos excepción
        try:
            from infra.bedrock import call_bedrock_llm1  # type: ignore
            prompt = (
                "Clasifica el idioma SOLO como 'es' o 'en'. Responde con una sola palabra.\n\n"
                f"Texto:\n{t}"
            )
            r = call_bedrock_llm1(prompt) or {}
            out = (r.get("completion") or "").strip().lower()
            if out.startswith("es"): return "es"
            if out.startswith("en"): return "en"
        except Exception:
            pass
    return fallback


# --------------------------------------------------------------------------------------
# Protección de tokens: URLs / IMDb IDs / UIDs / números (no se deben “traducir”)
# --------------------------------------------------------------------------------------

_URL_RE   = re.compile(r"(https?://[^\s)]+)")
_IMDB_RE  = re.compile(r"\btt\d{6,9}\b", re.I)
_UID_RE   = re.compile(r"\b[a-f0-9]{16,}\b", re.I)

def _mask_tokens(text: str) -> tuple[str, dict[str, str]]:
    mapping: dict[str, str] = {}
    counter = 0

    def repl(m: re.Match) -> str:
        nonlocal counter
        tok = m.group(0)
        key = f"[[KEEP_{counter}]]"
        mapping[key] = tok
        counter += 1
        return key

    # Orden: primero URLs, luego IDs (evita solapamientos extraños)
    t = _URL_RE.sub(repl, text or "")
    t = _IMDB_RE.sub(repl, t)
    t = _UID_RE.sub(repl, t)
    return t, mapping

def _unmask_tokens(text: str, mapping: dict[str, str]) -> str:
    out = text or ""
    for k, v in mapping.items():
        out = out.replace(k, v)
    return out


# --------------------------------------------------------------------------------------
# Núcleo: reescritura/traducción con LLM (fail-safe)
# --------------------------------------------------------------------------------------

def _llm_rewrite(text: str, user_query: str, target_lang: str) -> Optional[str]:
    """
    Llama a un backend LLM interno si está disponible.
    Debe devolver SOLO el texto final (sin bloques JSON ni metadatos).
    """
    try:
        from infra.bedrock import call_bedrock_llm1  # type: ignore

        # Instrucciones claras para preservar datos y estilo
        system_rules = (
            "Eres el asistente virtual de Fabric. No menciones proveedores ni modelos.\n"
            "Reescribe el texto al idioma objetivo manteniendo el significado y un tono claro y amable.\n"
            "No inventes datos. Respeta y NO modifiques los placeholders [[KEEP_N]].\n"
            "Preserva números, nombres propios y las URLs originales.\n"
            "Devuelve SOLO el texto final, sin comillas ni etiquetas."
        )

        # Enmarcamos “presente” en septiembre 2025 para coherencia temporal del tono
        locale = "Spanish" if target_lang.startswith("es") else "English"
        joined = (
            f"[system]\n{system_rules}\n\n"
            f"[meta]\nCurrent date: September 2025\n\n"
            f"[instructions]\nTarget language: {locale}\n"
            f"User query (for context): {user_query}\n\n"
            f"[text]\n{text}"
        )

        r = call_bedrock_llm1(joined) or {}
        out = (r.get("completion") or r.get("text") or "").strip()
        return out or None
    except Exception:
        return None


# --------------------------------------------------------------------------------------
# API pública
# --------------------------------------------------------------------------------------

def rewrite_for_user_language(
    base_text: str,
    user_query: str,
    target_lang_hint: Optional[str] = None,
) -> str:
    """
    Reescribe/adecúa el texto determinista al idioma del usuario y agrega brand intro.
    - Si la traducción está deshabilitada o el backend no responde, retorna base_text con brand intro (heurístico).
    - Preserva URLs/IDs/UIDs.
    """
    if not base_text:
        return base_text

    # 1) Determinar idioma objetivo
    target_lang = (target_lang_hint or "").lower().strip()
    if target_lang not in ("es", "en"):
        # Intento heurístico con la consulta del usuario
        target_lang = _guess_lang(user_query or "", fallback="es")

    # 2) Brand intro (se antepone siempre)
    brand = _brand_intro(target_lang)

    # 3) Si la traducción está deshabilitada a nivel de flags, devolvemos rápido
    if not SETTINGS.enable_translation and not SETTINGS.enable_llm_lang and not SETTINGS.enable_freeform_llm:
        # Solo añadimos branding y devolvemos
        return f"{brand}\n\n{base_text}".strip()

    # 4) Si ya está en el idioma objetivo, intentamos una ligera reescritura solo para tono/consistencia
    #    pero si no hay backend, devolvemos el texto base.
    text_to_process = base_text

    # 5) Proteger tokens
    masked, mapping = _mask_tokens(text_to_process)

    # 6) Llamar a LLM (si disponible)
    llm_out = _llm_rewrite(masked, user_query=user_query, target_lang=target_lang)

    if not llm_out:
        # Fallback: sin LLM, devolvemos branding + texto base tal cual
        return f"{brand}\n\n{base_text}".strip()

    # 7) Restaurar tokens protegidos
    final = _unmask_tokens(llm_out, mapping)

    # 8) Limpieza menor de espacios
    final = re.sub(r"\n{3,}", "\n\n", final).strip()

    # 9) Entregar con brand intro
    return f"{brand}\n\n{final}".strip()