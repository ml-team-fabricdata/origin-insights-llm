# app/router_query.py

import hashlib
import time
from fastapi import APIRouter
from pydantic import BaseModel
from app.db.message_history import load_messages, save_message
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
# Endpoint principal del asistente
# ---------------------------------------------------------------------
@router.post("/query")
async def query(payload: QueryIn):
    thread_id = get_thread_id(payload.user_id, payload.session_id)
    question = payload.message

    print(f"[QUERY] Thread ID usado: {thread_id}")

    history = load_messages(payload.session_id, question)
    result = await process_question_advanced(
        question=question,
        thread_id=thread_id,
        max_hops=3,
        enable_telemetry=False,
        history=history
    )
    save_message(payload.session_id, question, result["answer"])

    return {
        "thread_id": thread_id,
        "response": result.get("answer", ""),
        "selected_graph": result.get("selected_graph"),
        "domain_status": result.get("domain_graph_status"),
        "pending_disambiguation": result.get("pending_disambiguation", False),
        "options": result.get("disambiguation_options", [])
    }