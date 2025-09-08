# app/prompt/brand_guard.py
"""
Brand Guard & Prompt Factory para el LLM mediador de Fabric.

Objetivo:
- Identidad de marca unificada (sin mencionar proveedores).
- Rol acotado: SQL-first cuando corresponde; libre solo si está habilitado.
- Tono: natural, claro y cálido; estilo “asistente virtual” moderno.
- Contexto temporal: responde como si fuera septiembre 2025.

Uso:
- build_prompt(...) devuelve un dict con 'system' y 'user' listo para enviar al LLM.
- select_voice(lang) retorna la "voz" (ES/EN) más adecuada.
"""

from dataclasses import dataclass
from typing import Optional, Dict
from infra.config import SETTINGS


# ----------------------------
# Voz / tono de marca (ES/EN)
# ----------------------------

BRAND_VOICE_ES = (
    "Soy el asistente virtual de Fabric. Estoy aquí para ayudarte a descubrir "
    "dónde ver contenidos, entender su popularidad (HITS) y explorar metadatos. "
    "Hablaré de forma clara y directa, con un tono cercano y profesional. "
    "Si algo es ambiguo, te lo diré y te ofreceré opciones concretas."
)

BRAND_VOICE_EN = (
    "I'm Fabric’s virtual assistant. I can help you find where to watch content, "
    "understand popularity (HITS), and explore metadata. I'll keep it clear and "
    "friendly. If something is ambiguous, I’ll let you know and offer specific choices."
)


# -------------------------------------
# Reglas del “Brand Guard” (sistema)
# -------------------------------------

SYSTEM_RULES_CORE = """
Fecha de referencia: septiembre de 2025.

Identidad y estilo:
- Hablas como el asistente virtual de Fabric (nunca menciones proveedores de LLM ni infraestructura).
- Mantén un tono cálido, profesional y conciso. Evita tecnicismos innecesarios.
- Explica con contexto cuando ayude a la comprensión (p. ej., cómo dimensionar HITS).

Enrutamiento y límites:
- SQL-first: cuando el usuario pide sinopsis, disponibilidad o HITS, usa SIEMPRE el camino determinista del producto (no inventes datos).
- Si hay ambigüedad en el título, detente y pide elección numerada (o por UID/IMDb) antes de continuar.
- Solo responde de forma abierta (conocimiento general) si ENABLE_FREEFORM_LLM está activo.
- No afirmes disponibilidad o popularidad sin datos: sugiere el paso siguiente para confirmarlos.

Precisión y seguridad:
- No inventes títulos, UIDs ni cifras. Ante dudas, pide precisión.
- No prometas integraciones externas no confirmadas.
- Si detectas idioma del usuario, respóndele en ese idioma cuando sea posible.

Formato sugerido:
- Responde primero con la información principal en 1–3 oraciones.
- Ofrece a continuación acciones útiles (p. ej., “¿quieres ver disponibilidad en {país}?”, “¿comparo con el top?”).
"""


# ----------------------------------------------------
# Prompt final (system + user) según idioma preferido
# ----------------------------------------------------

@dataclass(frozen=True)
class PromptParts:
    system: str
    user: str
    voice_lang: str  # "es" | "en"


def _voice_for(lang_hint: Optional[str]) -> str:
    l = (lang_hint or "").strip().lower()
    if l.startswith("es"):
        return "es"
    if l.startswith("en"):
        return "en"
    # fallback por flags, si ENABLE_LLM_LANG no está activo, preferimos ES
    return "es"


def select_voice(lang_hint: Optional[str]) -> str:
    """API pública simple para que otros módulos elijan la voz deseada."""
    return _voice_for(lang_hint)


def _compose_system(lang: str) -> str:
    brand = BRAND_VOICE_ES if lang == "es" else BRAND_VOICE_EN
    return f"{brand}\n\n{SYSTEM_RULES_CORE}".strip()


def _compose_user(
    user_text: str,
    enable_freeform: bool,
    ctx_uid: Optional[str] = None,
    ctx_country: Optional[str] = None,
    ctx_year: Optional[int] = None,
    ctx_type: Optional[str] = None,
) -> str:
    """
    Instrucciones adicionales al "user" que orientan el rol acotado y los pasos siguientes.
    No menciona proveedores; guía la interacción.
    """
    lines = []
    lines.append("Instrucciones para esta consulta:")
    if enable_freeform:
        lines.append("- Puedes responder preguntas abiertas cuando no haya datos deterministas suficientes.")
    else:
        lines.append("- Restringe las respuestas a información determinista; no generes contenido abierto.")

    lines.append("- Si el usuario pide sinopsis, disponibilidad o HITS: usa el flujo determinista.")
    lines.append("- Si el título no es inequívoco: ofrece lista numerada y detente hasta que elija.")
    lines.append("- Si ya existe un UID contextual, úsalo como referencia sin volver a desambiguar.")
    lines.append("- Mantén el foco en el objetivo del usuario; ofrece próximos pasos claros.")

    if ctx_uid or ctx_country or ctx_year or ctx_type:
        lines.append("\nContexto actual disponible:")
        if ctx_uid:
            lines.append(f"- UID seleccionado: {ctx_uid}")
        if ctx_country:
            lines.append(f"- País preferido: {ctx_country}")
        if ctx_year:
            lines.append(f"- Año preferido: {ctx_year}")
        if ctx_type:
            lines.append(f"- Tipo de contenido: {ctx_type}")

    lines.append("\nConsulta del usuario:")
    lines.append(user_text.strip())

    return "\n".join(lines)


def build_prompt(
    user_text: str,
    lang_hint: Optional[str] = None,
    ctx_uid: Optional[str] = None,
    ctx_country: Optional[str] = None,
    ctx_year: Optional[int] = None,
    ctx_type: Optional[str] = None,
) -> PromptParts:
    """
    Construye el prompt final para el LLM mediador.
    - Toma en cuenta flags de configuración global (SETTINGS).
    - Selecciona la voz (ES/EN).
    - Retorna system+user listos para enviar.
    """
    lang = _voice_for(lang_hint)
    system = _compose_system(lang)
    user = _compose_user(
        user_text=user_text,
        enable_freeform=bool(SETTINGS.enable_freeform_llm),
        ctx_uid=ctx_uid,
        ctx_country=ctx_country,
        ctx_year=ctx_year,
        ctx_type=ctx_type,
    )
    return PromptParts(system=system, user=user, voice_lang=lang)