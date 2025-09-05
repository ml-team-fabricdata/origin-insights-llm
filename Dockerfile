FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# === Build metadata que inyecta el workflow ===
ARG BUILD_SHA=unknown
ARG BUILD_REF=unknown
ARG BUILD_TIME=unknown
ENV BUILD_SHA=${BUILD_SHA} \
    BUILD_REF=${BUILD_REF} \
    BUILD_TIME=${BUILD_TIME}

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# App Runner usa 8080 (pero lo dejamos configurable)
ENV PORT=8080
EXPOSE 8080

# CMD mas robusto: usa ${PORT:-8080}
CMD ["sh","-c","python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
