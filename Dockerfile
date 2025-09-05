FROM python:3.11-slim

# --- Build metadata (se rellenan desde el workflow) ---
ARG BUILD_SHA=unknown
ARG BUILD_REF=unknown
ARG BUILD_TIME=unknown

# --- Runtime ---
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BUILD_SHA=${BUILD_SHA} \
    BUILD_REF=${BUILD_REF} \
    BUILD_TIME=${BUILD_TIME} \
    PORT=8080

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8080

# Usar shell para expandir ${PORT:-8080}
CMD ["sh","-c","python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

# Opcional (labels útiles en ECR/containers)
LABEL org.opencontainers.image.revision=${BUILD_SHA}
LABEL org.opencontainers.image.source="${BUILD_REF}"
LABEL org.opencontainers.image.created="${BUILD_TIME}"
