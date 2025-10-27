# app/router_query.py

import hashlib
import time
from fastapi import APIRouter
from pydantic import BaseModel
from app.strands.main_router.graph import process_question_advanced

router = APIRouter()

# ---------------------------------------------------------------------
# Modelo de entrada
# ---------------------------------------------------------------------
class QueryIn(BaseModel):
    message: str
    user_id: str | None = None
    session_id: str | None = None

# ---------------------------------------------------------------------
# Generador inteligente de thread_id
# ---------------------------------------------------------------------
def get_thread_id(user_id: str | None, session_id: str | None) -> str:
    """
    Genera un identificador de hilo (thread_id) estable y único.

    - Si el frontend ya provee un session_id (por ejemplo 'thread-uuid'),
      se usa directamente sin duplicar el prefijo.
    - Si no tiene prefijo, se antepone 'thread-'.
    - Si no hay session_id, se genera a partir del user_id o timestamp.
    """
    if session_id:
        # Evita duplicar el prefijo
        if session_id.startswith("thread-"):
            return session_id
        return f"thread-{session_id}"

    base_id = user_id or f"anon-{time.time()}"
    hashed = hashlib.sha1(base_id.encode()).hexdigest()[:12]
    return f"thread-{hashed}"

# ---------------------------------------------------------------------
# Formateo HTML para opciones de disambiguación
# ---------------------------------------------------------------------
def format_disambiguation_html(options: list) -> str:
    """Genera HTML formateado para las opciones de disambiguación"""
    html = '<div class="disambiguation-container">'
    html += '<p class="disambiguation-title">Encontré varias opciones. ¿A cuál te refieres?</p>'
    html += '<div class="disambiguation-options">'
    
    for opt in options:
        count = opt.get("count") or opt.get("n_titles", 0)
        html += f'''
        <button class="disambiguation-btn" data-option="{opt.get('option_number')}" onclick="selectOption({opt.get('option_number')})">
            <span class="option-number">{opt.get('option_number')}</span>
            <span class="option-name">{opt.get('name')}</span>
            <span class="option-count">({count} títulos)</span>
        </button>
        '''
    
    html += '</div></div>'
    return html

# ---------------------------------------------------------------------
# Endpoint principal del asistente
# ---------------------------------------------------------------------
@router.post("/query")
async def query(payload: QueryIn):
    thread_id = get_thread_id(payload.user_id, payload.session_id)

    print(f"[QUERY] Thread ID usado: {thread_id}")

    result = await process_question_advanced(
        question=payload.message,
        thread_id=thread_id,
        max_hops=3,
        enable_telemetry=False
    )

    pending_disambiguation = result.get("pending_disambiguation", False)
    options = result.get("disambiguation_options", [])
    response_text = result.get("answer", "")
    
    # Si hay disambiguación, agregar HTML formateado
    if pending_disambiguation and options:
        response_html = format_disambiguation_html(options)
    else:
        response_html = response_text

    return {
        "thread_id": thread_id,
        "response": response_text,  # Texto plano
        "response_html": response_html,  # HTML formateado (nuevo)
        "selected_graph": result.get("selected_graph"),
        "domain_status": result.get("domain_graph_status"),
        "pending_disambiguation": pending_disambiguation,
        "options": options
    }