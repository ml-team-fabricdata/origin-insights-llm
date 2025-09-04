from fastapi import FastAPI
import os

app = FastAPI(title="origin-insights-llm")

@app.get("/")
def root():
    return {"ok": True, "env": os.getenv("APP_ENV", "unknown")}

@app.get("/healthz")
def health():
    # placeholder: siempre ok (luego podemos agregar check real a Aurora/Secrets)
    return {"ok": True, "db": True}
