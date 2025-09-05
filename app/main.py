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
    # lo podremos sobreescribir con un env BUILD desde CI si quieres
    return {"build": os.getenv("BUILD", "unknown")}

# Rutas de la API (incluye /query)
app.include_router(api_router)
