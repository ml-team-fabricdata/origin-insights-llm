from fastapi import FastAPI, APIRouter
import os
from .routers.api import router as api_router
from starlette.responses import JSONResponse
import psycopg2

app = FastAPI(title="origin-insights-llm")

@app.get("/")
def root():
    return {"ok": True, "env": os.getenv("APP_ENV", "unknown")}

@app.get("/healthz")
def health():
    return {"ok": True, "db": True}

@app.get("/version")
def version():
    sha  = os.getenv("BUILD_SHA", "")
    ref  = os.getenv("BUILD_REF", "")
    time = os.getenv("BUILD_TIME", "")
    build = os.getenv("BUILD", (sha[:7] if sha else "unknown"))
    return {
        "sha":  (sha or "unknown"),
        "ref":  (ref or "unknown"),
        "time": (time or ""),
        "build": build
    }

# Nuevo endpoint de prueba SQL
router_query = APIRouter()

@router_query.get("/query/ping")
def ping_database():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DATABASE_HOST"),
            port=os.getenv("DATABASE_PORT", "5432"),
            database=os.getenv("DATABASE_NAME"),
            user=os.getenv("DATABASE_USER"),
            password=os.getenv("DATABASE_PASSWORD"),
        )
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            result = cur.fetchone()[0]
        conn.close()
        return JSONResponse(status_code=200, content={"ok": True, "result": result})
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})

# Incluir todos los routers
app.include_router(api_router)
app.include_router(router_query)