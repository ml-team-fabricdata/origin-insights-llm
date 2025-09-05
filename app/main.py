from fastapi import FastAPI
import os
from .routers.api import router as api_router

app = FastAPI(title="origin-insights-llm")

@app.get("/")
def root():
    return {"ok": True, "env": os.getenv("APP_ENV", "unknown")}

@app.get("/healthz")
def health():
    return {"ok": True, "db": True}

@app.get("/version")
def version():
    import os
    sha  = os.getenv("BUILD_SHA", "")
    ref  = os.getenv("BUILD_REF", "")
    time = os.getenv("BUILD_TIME", "")

    # compatibilidad: si alguien mira "build", devolvemos corto del SHA
    build = os.getenv("BUILD", (sha[:7] if sha else "unknown"))

    return {
        "sha":  (sha or "unknown"),
        "ref":  (ref or "unknown"),
        "time": (time or ""),
        "build": build
    }
