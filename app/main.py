from fastapi import FastAPI
import os

app = FastAPI(title="origin-insights-llm")

@app.get("/")
def root():
    return {"ok": True, "env": os.getenv("APP_ENV", "unknown")}

@app.get("/healthz")
def health():
    # placeholder
    return {"ok": True, "db": True}

@app.get("/version")
def version():
    return {
        "sha": os.getenv("BUILD_SHA", "unknown"),
        "ref": os.getenv("BUILD_REF", "unknown"),
        "time": os.getenv("BUILD_TIME", "unknown"),
    }
