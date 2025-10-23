# app/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from infra.db import db_health
from app.supervisor import handle_query

# --- Routers ---
# from app.router_determinista import router as determinista_router
from app.router_llm import router as llm_router
from app.router_query import router as query_router
from app.router_popularity import router as popularity_router
from app.router_agent import router as agent_router

# -----------------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------------
app = FastAPI(title="Origin Insights LLM")

# --- CORS configurable ---
_allow = (os.getenv("ALLOW_ORIGINS") or "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allow],
    allow_credentials=(os.getenv("ALLOW_CREDENTIALS", "1") == "1"),
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
# app.include_router(determinista_router)
app.include_router(llm_router)
app.include_router(query_router)
app.include_router(popularity_router)
app.include_router(agent_router)

# -----------------------------------------------------------------------------
# Endpoints básicos
# -----------------------------------------------------------------------------
@app.get("/")
def root():
    return {"ok": True}

@app.get("/healthz")
def health():
    return {"ok": True, "db": db_health()}

BUILD_META = {
    "sha": os.getenv("BUILD_SHA", "unknown"),
    "ref": os.getenv("BUILD_REF", "unknown"),
    "time": os.getenv("BUILD_TIME", "unknown"),
}

@app.get("/version")
def version():
    return BUILD_META

# -----------------------------------------------------------------------------
# Endpoint de supervisor (/ask)
# -----------------------------------------------------------------------------
class AskIn(BaseModel):
    query: str
    user_id: str | None = None
    lang: str | None = None

@app.post("/ask")
def ask(payload: AskIn):
    return handle_query(payload.query)
