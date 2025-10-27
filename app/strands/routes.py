# app/strands/routes.py
import asyncio
from fastapi import APIRouter, Request
from app.strands.main_router.graph import process_question_advanced

router = APIRouter()

@router.post("/ask")
async def strand_ask(request: Request):
    """
    Ejecuta el grafo avanzado de Strands con una pregunta en lenguaje natural.
    """
    payload = await request.json()
    question = payload.get("question", "")

    if not question:
        return {"ok": False, "error": "Missing 'question' field"}

    try:
        # Obtener thread_id de la sesión (si existe) o generar uno nuevo
        thread_id = payload.get("thread_id", "default")
        
        result = await process_question_advanced(question, thread_id=thread_id)
        
        # DEBUG: Ver qué campos tiene el resultado
        print(f"\n[API DEBUG] Result keys: {list(result.keys())}")
        print(f"[API DEBUG] pending_disambiguation: {result.get('pending_disambiguation')}")
        print(f"[API DEBUG] disambiguation_options: {result.get('disambiguation_options')}")
        
        answer = result.get("answer", "") or result.get("accumulated_data", "")
        
        # Detectar si hay disambiguación pendiente
        pending_disambiguation = result.get("pending_disambiguation", False)
        disambiguation_options = result.get("disambiguation_options", [])
        
        return {
            "ok": True,
            "question": question,
            "answer": answer,
            "graph": result.get("selected_graph"),
            "status": result.get("domain_graph_status"),
            "visited_graphs": result.get("visited_graphs", []),
            "needs_clarification": result.get("needs_clarification", False),
            "pending_disambiguation": pending_disambiguation,
            "disambiguation_options": disambiguation_options,
            "thread_id": thread_id,
            "tool_times": result.get("tool_execution_times", {}),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}