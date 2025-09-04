FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# App Runner usa 8080; dejamos PORT configurable
ENV PORT=8080
EXPOSE 8080

# ¡usar shell para expandir !
CMD ["sh","-c","python -m uvicorn app.main:app --host 0.0.0.0 --port "]
