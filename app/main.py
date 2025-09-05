from fastapi import FastAPI
from pydantic import BaseModel
import os

app = FastAPI(title="origin-insights-llm")

@app.get("/")
def root():
    return {"ok": True, "env": os.getenv("APP_ENV", "unknown")}

@app.get("/healthz")
def health():
    # placeholder: ok siempre
    return {"ok": True, "db": True}

@app.get("/version")
def version():
    return {
        "app": "origin-insights-llm",
        "env": os.getenv("APP_ENV", "unknown"),
        "build": {
            "sha": os.getenv("BUILD_SHA", "unknown"),
            "ref": os.getenv("BUILD_REF", "unknown"),
            "time": os.getenv("BUILD_TIME", "unknown"),
        },
    }

class QueryIn(BaseModel):
    prompt: str

@app.post("/query")
def query(body: QueryIn):
    return {"ok": True, "answer": f"Echo: {body.prompt}"}
