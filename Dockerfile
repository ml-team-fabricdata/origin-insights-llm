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
    PYTHONUNBUFFERED=1 \
    BUILD_META_FILE=/code/.build-meta.json

# --- Metadata de build (opcional) ---
ARG BUILD_SHA=unknown
ARG BUILD_REF=unknown
ARG BUILD_TIME=unknown
ENV BUILD_SHA=${BUILD_SHA} \
    BUILD_REF=${BUILD_REF} \
    BUILD_TIME=${BUILD_TIME} \
    IMAGE_BUILD_SHA=${BUILD_SHA} \
    IMAGE_BUILD_REF=${BUILD_REF} \
    IMAGE_BUILD_TIME=${BUILD_TIME} \
    APP_BUILD_SHA=${BUILD_SHA} \
    APP_BUILD_REF=${BUILD_REF} \
    APP_BUILD_TIME=${BUILD_TIME}

LABEL org.opencontainers.image.revision="${BUILD_SHA}" \
      org.opencontainers.image.source="${BUILD_REF}" \
      org.opencontainers.image.created="${BUILD_TIME}"

# Persistir metadata también en archivo para fallback en runtime
RUN python - <<'PY'
import json
import os
from pathlib import Path

payload = {
    "sha": os.getenv("BUILD_SHA", "unknown"),
    "ref": os.getenv("BUILD_REF", "unknown"),
    "time": os.getenv("BUILD_TIME", "unknown"),
}

aliases = {
    "sha": {
        "BUILD_SHA": os.getenv("BUILD_SHA", "unknown"),
        "IMAGE_BUILD_SHA": os.getenv("IMAGE_BUILD_SHA", "unknown"),
        "APP_BUILD_SHA": os.getenv("APP_BUILD_SHA", "unknown"),
    },
    "ref": {
        "BUILD_REF": os.getenv("BUILD_REF", "unknown"),
        "IMAGE_BUILD_REF": os.getenv("IMAGE_BUILD_REF", "unknown"),
        "APP_BUILD_REF": os.getenv("APP_BUILD_REF", "unknown"),
    },
    "time": {
        "BUILD_TIME": os.getenv("BUILD_TIME", "unknown"),
        "IMAGE_BUILD_TIME": os.getenv("IMAGE_BUILD_TIME", "unknown"),
        "APP_BUILD_TIME": os.getenv("APP_BUILD_TIME", "unknown"),
    },
}

alias_snapshot = {
    key: {k: v for k, v in values.items() if v and v != "unknown"}
    for key, values in aliases.items()
}
alias_snapshot = {k: v for k, v in alias_snapshot.items() if v}

if alias_snapshot:
    payload["aliases"] = alias_snapshot

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
