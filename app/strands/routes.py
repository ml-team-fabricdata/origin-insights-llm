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
        result = await process_question_advanced(question)
        answer = result.get("answer", "") or result.get("accumulated_data", "")
        return {
            "ok": True,
            "question": question,
            "answer": answer,
            "graph": result.get("selected_graph"),
            "status": result.get("domain_graph_status"),
            "visited_graphs": result.get("visited_graphs", []),
            "needs_clarification": result.get("needs_clarification", False),
            "tool_times": result.get("tool_execution_times", {}),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}