# Origin Insights LLM

Asistente híbrido (determinista + LLM) para consultas sobre catálogo audiovisual  
(Disponibilidad, Popularidad HITS y Metadatos) desplegado en **AWS App Runner** con **Aurora PostgreSQL** como backend.

---

## 🚀 Arquitectura

- **FastAPI** — backend principal.
- **Aurora PostgreSQL** — base de datos con esquema `ms.*` (metadatos, hits, availability).
- **AWS App Runner** — despliegue serverless a partir de imágenes en **ECR**.
- **GitHub Actions** — CI/CD automático (build & push Docker → ECR → App Runner).
- **Bedrock (Claude 3.5 Haiku / Sonnet)** — LLMs para clasificación, traducción y consultas complejas.

---

## 📂 Estructura del repo

```
app/
  main.py                # Entrada FastAPI
  supervisor.py          # Router heurístico (elige nodo determinista/LLM)
  router_query.py        # Endpoint /query (multi-intents, traducción, país)
  router_llm.py          # Endpoints /llm/test*
  modules/               # Lógica determinista (hits, availability, metadata, etc.)
infra/
  config.py              # Configuración (ENV + Secrets Manager)
  db.py                  # Conexión Aurora (psycopg2 + pool)
test_llm.py              # Script de prueba rápida contra Bedrock
Dockerfile
requirements.txt
setup.py
terraform/              # Infraestructura IaC (mantener en Git, ignorar en Docker)
```

---

## ⚙️ Configuración

Variables de entorno principales (App Runner):

- `APP_ENV=main`
- `PORT=8080`
- `AWS_REGION=us-east-1`
- `ENABLE_LLM_COUNTRY=1`
- `ENABLE_LLM_LANG=1`
- `ENABLE_TRANSLATION=1`
- `OFFLINE_MODE=0`
- `AURORA_SECRET_ARN=arn:aws:secretsmanager:...:secret:aurora-postgres-origin-insights-secret-***`

El secreto en AWS Secrets Manager debe contener:

```json
{
  "host": "aurora-origin-pgsql.cluster-xxxx.us-east-1.rds.amazonaws.com",
  "port": "5432",
  "username": "administrador",
  "password": "*****",
  "database": "origin_insights"
}
```

---

## ▶️ Uso local

```bash
# Construir imagen
docker build -t oi:test .

# Correr API en local
docker run -it --rm -p 8080:8080 oi:test

# Probar endpoints
curl http://localhost:8080/healthz
curl http://localhost:8080/version
```

---

## 🌐 Despliegue

1. Push a rama (`main`, `rafa`, `ele`, `fran`).
2. GitHub Actions ejecuta `ecr-build.yml`:
   - Build Docker image con metadata (`BUILD_SHA`, `BUILD_REF`, `BUILD_TIME`).
   - Push a ECR.
   - Trigger `start-deployment` en App Runner.
3. Validación automática de `/healthz` y `/version`.

---

## 🧪 Test rápido LLM

```bash
python test_llm.py
```

---

## 📌 Pendientes

- Enriquecer logs y trazabilidad de nodos.
- Casos de prueba unitarios.
- Monitoreo básico en App Runner.
- Staging / producción con entornos separados.