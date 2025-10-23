# =============================================================================
# STANDARD LIBRARY IMPORTS
# =============================================================================
import base64
import json
import logging
import os
from functools import lru_cache

# =============================================================================
# THIRD PARTY IMPORTS
# =============================================================================
import boto3
import psycopg
from botocore.exceptions import ClientError
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

# =============================================================================
# LOGGER
# =============================================================================
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_secret() -> dict:
    """
    Lee de AWS Secrets Manager con caché.
    
    Env vars:
      - DB_SECRET_ID  (nombre o ARN del secreto; default: 'aurora-postgres-origin-insights-secret-er')
      - AWS_REGION / AWS_DEFAULT_REGION (default: 'us-east-1')

    Devuelve un dict normalizado con claves:
      host, port, db, user, password
      
    Note:
      Uses @lru_cache to avoid repeated AWS API calls.
    """

    secret_id = os.getenv("DB_SECRET_ID", "aurora-postgres-origin-insights-secret-er")
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"

    client = boto3.session.Session().client("secretsmanager", region_name=region)
    try:
        val = client.get_secret_value(SecretId=secret_id)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code == "AccessDeniedException":
            raise RuntimeError(
                "AccessDenied en Secrets Manager. Asignará al Instance Role permisos "
                "'secretsmanager:GetSecretValue' (y si aplica 'kms:Decrypt')."
            ) from e
        if code == "ResourceNotFoundException":
            raise RuntimeError(f"El secreto '{secret_id}' no existe en la región {region}.") from e
        raise

    if "SecretString" in val:
        raw = json.loads(val["SecretString"])
    else:
        raw = json.loads(base64.b64decode(val["SecretBinary"]).decode("utf-8"))

    # Normalizar claves esperadas por el resto del código
    cfg = {
        "host": raw.get("host"),
        "port": int(raw.get("port", 5432)),
        "db": raw.get("db") or raw.get("dbname"),
        "user": raw.get("user") or raw.get("username"),
        "password": raw.get("password"),
    }

    missing = [k for k, v in cfg.items() if v in (None, "")]
    if missing:
        raise RuntimeError(f"Secreto incompleto; faltan claves: {', '.join(missing)}")

    return cfg


class SQLConnectionManager:
    """PostgreSQL con reintentos."""

    def __init__(self):
        self._cfg = get_secret()
        self._connection_uri = f"postgresql://{self._cfg['user']}:{self._cfg['password']}@{self._cfg['host']}:{self._cfg['port']}/{self._cfg['db']}"
        self.conn_options = "-c search_path=public,ms"
        self._connection_pool = None
        self._initialized = False
        self._initialize_connection()

    def _initialize_connection(self):
        self._connection_pool = ConnectionPool(self._connection_uri, min_size=1, max_size=10, options=self.conn_options)
        if not self._initialized:
            print(
                f"✅ Connected to PostgreSQL: {self._cfg['db']}@"
                f"{self._cfg['host']}:{self._cfg['port']}"
            )
            self._initialized = True

    def execute_query(self, query, params=None, operation_name=None):
        """
        Execute a query and return results.

        Args:
            query: SQL query string
            params: Optional parameters for the query
            operation_name: Optional name for the operation (for compatibility with tools)
        """
        with self._connection_pool.connection() as conn:
            try:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(query, params)

                    # Para DDL y DML hacer commit explícito
                    query_upper = query.strip().upper()
                    if query_upper.startswith(('CREATE', 'DROP', 'ALTER', 'INSERT', 'UPDATE', 'DELETE')):
                        conn.commit()
                    if cur.description:  # SELECT query
                        return cur.fetchall()
                    else:  # INSERT/UPDATE/DELETE
                        return cur.rowcount
            except psycopg.Error as e:
                print(f"❌ Query execution failed: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass
                raise


db = SQLConnectionManager()