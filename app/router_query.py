# app/router_query.py
from fastapi import APIRouter
from pydantic import BaseModel
from app.strands.main_router.graph import process_question_advanced

router = APIRouter()

class QueryIn(BaseModel):
    message: str
    session_id: str | None = None
    language: str | None = None
    context_uid: str | None = None

@router.post("/query")
async def query(payload: QueryIn):
    """
    Nuevo flujo basado en Strands (supervisor + grafo avanzado).
    Reemplaza el router determinista clásico.
    """
    print("[ROUTER_QUERY] Strands pipeline activado (/query)")
    result = await process_question_advanced(
        payload.message,
    )
    return result