# infra/config.py
import os
import json
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any

# --- utilidades env -----------------------------------------------------------
_AWS_SECRETS_ARN_RE = re.compile(
    r"^arn:aws:secretsmanager:[\w-]+:\d{12}:secret:[\w+=,.@/-]+$"
)

def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if (v is not None and v != "") else default

def _env_bool(name: str, default: bool = False) -> bool:
    v = _env(name)
    if v is None:
        return default
    return str(v).strip() in ("1", "true", "True", "yes", "on")

def _looks_like_secret_arn(v: Optional[str]) -> bool:
    return bool(v and _AWS_SECRETS_ARN_RE.match(v))  # pragma: no cover

def _looks_like_secret_json(v: Optional[str]) -> bool:
    if not v:
        return False
    v = v.strip()
    return v.startswith("{") and v.endswith("}")

# --- loaders de secreto -------------------------------------------------------
def _load_secret_payload_from_sm(secret_arn: str) -> Dict[str, Any]:
    """
    Carga un secreto de AWS Secrets Manager y devuelve el dict.
    No lanza: retorna {} si falla.
    """
    try:
        import boto3  # App Runner lo tiene disponible
        region = _env("AWS_REGION", "us-east-1")
        sm = boto3.client("secretsmanager", region_name=region)
        r = sm.get_secret_value(SecretId=secret_arn)
        if "SecretString" in r and r["SecretString"]:
            return json.loads(r["SecretString"])
        if "SecretBinary" in r and r["SecretBinary"]:
            import base64
            raw = base64.b64decode(r["SecretBinary"]).decode("utf-8", "ignore")
            return json.loads(raw)
    except Exception:
        pass
    return {}

def _load_secret_payload_from_env_json(env_value: str) -> Dict[str, Any]:
    try:
        return json.loads(env_value)
    except Exception:
        return {}

# --- settings ----------------------------------------------------------------
@dataclass(frozen=True)
class Settings:
    # Feature flags
    enable_llm_country: bool
    enable_llm_lang: bool
    enable_translation: bool
    offline_mode: bool

    # SQL defaults
    top_k_default: int
    min_sim_default: float
    hits_window_days: int
    autopick_sim: float
    autopick_delta: float
    pg_stmt_timeout_ms: int

    # DB
    aurora_host: str
    aurora_db: str
    aurora_user: str
    aurora_pass: str
    aurora_port: int

    # Derivados
    db_ready: bool
    db_source: str  # "env" | "secretsmanager:arn" | "env:json" | "none"

def _collect_db_from_plain_env() -> Dict[str, Any]:
    return {
        "host": _env("AURORA_HOST", ""),
        "database": _env("AURORA_DB", ""),
        "username": _env("AURORA_USER", ""),
        "password": _env("AURORA_PASSWORD", _env("AURORA_PASS", "")) or "",
        "port": int(_env("AURORA_PORT", "5432") or "5432"),
    }

def _find_any_secret_arn() -> Optional[str]:
    # 1) preferido
    arn = _env("AURORA_SECRET_ARN")
    if _looks_like_secret_arn(arn):
        return arn
    # 2) compat App Runner: cualquier env cuyo VALOR sea un ARN
    for _, v in os.environ.items():
        if _looks_like_secret_arn(v):
            return v
    return None

def _find_any_secret_json() -> Optional[str]:
    # 1) preferido
    js = _env("AURORA_SECRET_JSON")
    if _looks_like_secret_json(js):
        return js
    # 2) compat: si definiste una env con JSON plano
    for k, v in os.environ.items():
        if _looks_like_secret_json(v):
            # heurística suave: que tenga campos típicos
            try:
                d = json.loads(v)
                if any(k in d for k in ("host", "username", "password", "database", "port")):
                    return v
            except Exception:
                pass
    return None

def _coalesce_db_creds(plain: Dict[str, Any], secret: Dict[str, Any]) -> Dict[str, Any]:
    # prioridad: valores ya presentes en env > secretos
    out = dict(plain)
    for k in ("host", "database", "username", "password", "port"):
        if not out.get(k):
            out[k] = secret.get(k, out.get(k))
    # normalizaciones mínimas
    out["host"] = out.get("host") or ""
    out["database"] = out.get("database") or ""
    out["username"] = out.get("username") or ""
    out["password"] = out.get("password") or ""
    try:
        out["port"] = int(out.get("port") or 5432)
    except Exception:
        out["port"] = 5432
    return out

def _load_settings() -> Settings:
    # 1) base: env plano
    db_env = _collect_db_from_plain_env()
    db_source = "env"
    secret_dict: Dict[str, Any] = {}

    # 2) secrets manager por ARN (App Runner: “Secrets Manager”)
    arn = _find_any_secret_arn()
    if arn:
        secret_dict = _load_secret_payload_from_sm(arn)
        if secret_dict:
            db_source = "secretsmanager:arn"

    # 3) secret como JSON embebido en env (opción alternativa)
    if not secret_dict:
        js = _find_any_secret_json()
        if js:
            secret_dict = _load_secret_payload_from_env_json(js)
            if secret_dict:
                db_source = "env:json"

    # 4) fusionar (env tiene prioridad)
    merged = _coalesce_db_creds(db_env, secret_dict)

    # 5) flags
    enable_llm_country = _env_bool("ENABLE_LLM_COUNTRY", False)
    enable_llm_lang = _env_bool("ENABLE_LLM_LANG", False)
    enable_translation = _env_bool("ENABLE_TRANSLATION", False)
    offline_mode = _env_bool("OFFLINE_MODE", False)

    # 6) derivados
    db_ready = all(
        [
            merged.get("host"),
            merged.get("database"),
            merged.get("username"),
            merged.get("password") is not None,
            merged.get("port"),
        ]
    )

    # Si no hay DB y no estamos en offline, mantenemos db_ready=False;
    # infra/db.py decidirá qué hacer (p.ej. no levantar pool y loggear warning).
    return Settings(
        enable_llm_country=enable_llm_country,
        enable_llm_lang=enable_llm_lang,
        enable_translation=enable_translation,
        offline_mode=offline_mode,
        top_k_default=int(_env("TOP_K", "20") or "20"),
        min_sim_default=float(_env("MIN_SIMILARITY", "0.80") or "0.80"),
        hits_window_days=int(_env("HITS_WINDOW_DAYS", "364") or "364"),
        autopick_sim=float(_env("AUTOPICK_SIM", "0.94") or "0.94"),
        autopick_delta=float(_env("AUTOPICK_DELTA", "0.03") or "0.03"),
        pg_stmt_timeout_ms=int(_env("PG_STMT_TIMEOUT_MS", "10000") or "10000"),
        aurora_host=str(merged.get("host") or ""),
        aurora_db=str(merged.get("database") or ""),
        aurora_user=str(merged.get("username") or ""),
        aurora_pass=str(merged.get("password") or ""),
        aurora_port=int(merged.get("port") or 5432),
        db_ready=bool(db_ready),
        db_source=db_source if db_ready else "none",
    )

SETTINGS = _load_settings()