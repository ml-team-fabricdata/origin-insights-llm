from fastapi import APIRouter
from app.supervisor import handle_query

router = APIRouter()

@router.post("/llm/ask")
def ask_llm(query: str):
    return handle_query(query)

@router.get("/llm/ping")
def ping_llm():
    return {"ok": True, "model": "bedrock", "status": "live"}