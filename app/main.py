from fastapi import FastAPI
from app.supervisor import handle_query
from app.router_determinista import router as determinista_router
from app.router_llm import router as llm_router

app = FastAPI(title="Origin Insights LLM")

app.include_router(determinista_router)
app.include_router(llm_router)

@app.get("/")
def root():
    return {"ok": True}

@app.get("/healthz")
def health():
    return {"ok": True, "db": True}

@app.post("/ask")
def ask(query: str):
    return handle_query(query)

