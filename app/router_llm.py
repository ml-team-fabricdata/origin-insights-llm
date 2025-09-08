# app/router_llm.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any

from infra.config import SETTINGS
from app.prompt.brand_guard import build_prompt, select_voice

router = APIRouter(prefix="/v1/llm", tags=["llm"])

# =========================
# Modelos I/O
# =========================

class LLMQueryIn(BaseModel):
    text: str
    lang: Optional[str] = None           # hint de idioma ("es", "en")
    session_id: Optional[str] = None     # si manejas sesión, úsala para contexto
    uid: Optional[str] = None            # UID contextual si ya hay título seleccionado
    country: Optional[str] = None        # ISO2 o nombre (hint)
    year: Optional[int] = None           # hint de año
    content_type: Optional[str] = None   # "movie" | "series" | None

class LLMQueryOut(BaseModel):
    kind: str   # "freeform_answer" | "disabled" | "unavailable"
    payload: Dict[str, Any]


# =========================
# Backend LLM (seguro)
# =========================

def _safe_call_llm(system_prompt: str, user_prompt: str) -> Optional[str]:
    """
    Intenta llamar a un backend LLM según un orden configurable.
    Ejemplo de orden por env:
      LLM_MODEL_ORDER="haiku-3.5,ii-3.7"
    """
    import os
    order = (os.getenv("LLM_MODEL_ORDER") or "haiku-3.5,ii-3.7").split(",")

    # 1) Bedrock
    for model in [m.strip() for m in order if m.strip()]:
        try:
            from infra.bedrock import call_bedrock_llm1  # type: ignore
            # Soporte opcional de 'model' si el wrapper lo acepta
            joined = f"[system]\n{system_prompt}\n\n[user]\n{user_prompt}"
            try:
                r = call_bedrock_llm1(joined, model=model) or {}
            except TypeError:
                # wrapper sin parámetro model
                r = call_bedrock_llm1(joined) or {}
            out = (r.get("completion") or r.get("text") or "").strip()
            if out:
                return out
        except Exception:
            continue

    # 2) Alternativa a futuro: otros backends internos opcionales (ej. openai, vertex, etc.) — siempre en try/except
    try:
        from infra.openai_backend import call_openai_llm  # type: ignore
        out = call_openai_llm(system_prompt=system_prompt, user_prompt=user_prompt) or ""
        if out.strip():
            return out.strip()
    except Exception:
        pass

    return None

# =========================
# Endpoint principal
# =========================

@router.post("/ask", response_model=LLMQueryOut)
def ask_llm(payload: LLMQueryIn) -> LLMQueryOut:
    """
    Mediador con Brand Guard:
    - Identidad Fabric (tono cálido + profesional).
    - SQL-first cuando corresponde (este endpoint es para freeform; tus routers deterministas siguen siendo la vía principal).
    - Respeta flags: si ENABLE_FREEFORM_LLM=0, responde con mensaje informativo.
    - No rompe si no hay backend LLM: devuelve 'unavailable' sin error 500.
    """
    # 1) Verificar flag global
    if not SETTINGS.enable_freeform_llm:
        lang = select_voice(payload.lang)
        msg = (
            "Por ahora me enfocaré en respuestas deterministas. "
            "Podemos ver sinopsis, disponibilidad y popularidad (HITS) de títulos. "
            "¿Querés que busque un título específico?"
            if lang == "es"
            else "For now I’m focused on deterministic answers only. "
                 "I can help with synopsis, availability, and popularity (HITS). "
                 "Would you like me to search for a specific title?"
        )
        return LLMQueryOut(kind="disabled", payload={"message": msg})

    # 2) Construir prompt con Brand Guard (voz según hint)
    p = build_prompt(
        user_text=payload.text,
        lang_hint=payload.lang,
        ctx_uid=payload.uid,
        ctx_country=payload.country,
        ctx_year=payload.year,
        ctx_type=payload.content_type,
    )

    # 3) Llamar a backend LLM (si existe)
    answer = _safe_call_llm(system_prompt=p.system, user_prompt=p.user)

    # 4) Si no hay backend configurado, no romper: devolver unavailable
    if not answer:
        msg = (
            "En este momento no tengo respuestas abiertas habilitadas. "
            "Si querés, puedo ayudarte con búsqueda de títulos, disponibilidad y HITS."
            if p.voice_lang == "es"
            else "Open-ended answers aren’t available right now. "
                 "I can help with title search, availability, and HITS if you’d like."
        )
        return LLMQueryOut(kind="unavailable", payload={"message": msg})

    # 5) Entrega de respuesta libre
    return LLMQueryOut(kind="freeform_answer", payload={
        "answer": answer,
        "voice_lang": p.voice_lang,
        "meta": {
            "enable_freeform_llm": bool(SETTINGS.enable_freeform_llm),
            "enable_llm_lang": bool(SETTINGS.enable_llm_lang),
            "enable_translation": bool(SETTINGS.enable_translation),
        }
    })