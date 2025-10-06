# app/router_llm.py
from fastapi import APIRouter, Query
import os
from app.supervisor import handle_query  # OK mantenerlo

router = APIRouter()

# Metadatos de build inyectados por GitHub Actions
BUILD_META = {
    "sha": os.getenv("BUILD_SHA", "unknown"),
    "ref": os.getenv("BUILD_REF", "unknown"),
    "time": os.getenv("BUILD_TIME", "unknown"),
}

@router.post("/llm/ask")
def ask_llm(
    query: str,
    user_id: str | None = None,
    thread_id: str | None = None,
    lang: str | None = None,
):
    return handle_query(query, user_id=user_id, thread_id=thread_id, lang=lang)

@router.get("/llm/ping")
def ping_llm():
    return {"ok": True, "model": "bedrock", "status": "live"}

@router.get("/llm/test_llm1")
def test_llm1(prompt: str = Query(..., description="Prompt para Claude 3.5 Haiku")):
    # Lazy import para evitar fallas en import-time
    from infra.bedrock import call_bedrock_llm1
    response = call_bedrock_llm1(prompt)
    return {
        "model_used": "claude-3.5-haiku",
        "prompt": prompt,
        "response": response,
        "build": BUILD_META
    }

@router.get("/llm/test_llm2")
def test_llm2(prompt: str = Query(..., description="Prompt para Claude 3 Sonnet")):
    # Lazy import para evitar fallas en import-time
    from infra.bedrock import call_bedrock_llm2
    response = call_bedrock_llm2(prompt)
    return {
        "model_used": "claude-3-sonnet",
        "prompt": prompt,
        "response": response,
        "build": BUILD_META
    }
