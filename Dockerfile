FROM python:3.11-slim

# Copiar todo el repo
COPY . /code

# Definir workdir y permitir imports desde raíz
WORKDIR /code
ENV PYTHONPATH=/code \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# --- Metadata de build ---
ARG BUILD_SHA=unknown
ARG BUILD_REF=unknown
ARG BUILD_TIME=unknown
ENV BUILD_SHA=${BUILD_SHA} \
    BUILD_REF=${BUILD_REF} \
    BUILD_TIME=${BUILD_TIME}

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -e .

# Puerto y comando de ejecución
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]