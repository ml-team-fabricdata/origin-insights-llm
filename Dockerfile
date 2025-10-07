# Dockerfile
FROM python:3.11-slim

# Evitar prompts de apt
ENV DEBIAN_FRONTEND=noninteractive

# Paquetes de sistema necesarios para psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Copiar repo
WORKDIR /code
COPY . /code

# Entorno Python
ENV PYTHONPATH=/code \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# --- Metadata de build (opcional) ---
ARG BUILD_SHA=unknown
ARG BUILD_REF=unknown
ARG BUILD_TIME=unknown
ENV BUILD_SHA=${BUILD_SHA} \
    BUILD_REF=${BUILD_REF} \
    BUILD_TIME=${BUILD_TIME}

# --- Persistir metadata también en archivo para fallback en runtime ---
RUN python - <<'PY'
import json
import os
from pathlib import Path

payload = {
    "sha": os.getenv("BUILD_SHA", "unknown"),
    "ref": os.getenv("BUILD_REF", "unknown"),
    "time": os.getenv("BUILD_TIME", "unknown"),
}

json_blob = json.dumps(payload, indent=2, sort_keys=True) + "\n"
for target in (Path("/code/.build-meta.json"), Path("/.build-meta.json")):
    target.write_text(json_blob, encoding="utf-8")

snapshot = (
    '"""Auto-generated build metadata snapshot.\n'
    "\n"
    "This file is regenerated on every Docker build so runtime code can import the\n"
    "latest commit information even if environment variables are temporarily\n"
    "unavailable (as observed in App Runner right after boot).\n"
    '"""\n'
)

body = snapshot + f"BUILD_SNAPSHOT = {payload!r}\n"
Path("/code/app/_build_meta_snapshot.py").write_text(body, encoding="utf-8")
PY

# Dependencias Python
RUN python -m pip install --no-cache-dir --upgrade pip \
 && python -m pip install --no-cache-dir -r requirements.txt

# Puerto (App Runner inyecta PORT)
ENV PORT=8080
EXPOSE 8080

# Importante: usar $PORT en tiempo de ejecución
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
