import os
import json
import base64
import time
import psycopg2
import psycopg2.extras
import boto3
from botocore.exceptions import ClientError


def get_secret() -> dict:
    """
    Lee SIEMPRE de AWS Secrets Manager (sin hardcodear ARN).
    Env vars:
      - DB_SECRET_ID  (nombre o ARN del secreto; default: 'aurora-postgres-origin-insights-secret-er')
      - AWS_REGION / AWS_DEFAULT_REGION (default: 'us-east-1')

    Devuelve un dict normalizado con claves:
      host, port, db, user, password
    """
    now = time.time()

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
        cfg = get_secret()
        self.conn_params = {
            "host": cfg["host"],
            "port": cfg["port"],
            "dbname": cfg["db"],         # psycopg2 acepta 'dbname'
            "user": cfg["user"],
            "password": cfg["password"],
            "connect_timeout": 30,
            "application_name": "chatbot_app",
            "sslmode": "require",        # recomendado en Aurora Postgres
        }
        self._connection = None
        self._initialized = False
        self._initialize_connection()

    def _initialize_connection(self):
        try:
            self._connection = psycopg2.connect(**self.conn_params)
            if not self._initialized:
                print(
                    f"✅ Connected to PostgreSQL: {self.conn_params['dbname']}@"
                    f"{self.conn_params['host']}:{self.conn_params['port']}"
                )
                self._initialized = True
                
        except psycopg2.Error as e:
            print(f"❌ Initial connection failed: {e}")
            self._connection = None

    def get_connection(self, retry_count=3):
        for attempt in range(retry_count):
            try:
                if self._connection and not self._connection.closed:
                    try:
                        with self._connection.cursor() as c:
                            c.execute("SELECT 1")
                        return self._connection
                    except (psycopg2.Error, psycopg2.OperationalError):
                        self.close()

                if attempt == 0:
                    print("🔄 Creating new PostgreSQL connection")
                self._connection = psycopg2.connect(**self.conn_params)
                self._connection.autocommit = True
                return self._connection

            except psycopg2.Error as e:
                if attempt < retry_count - 1:
                    print(f"⚠️ Connection attempt {attempt+1} failed: {e}")
                    time.sleep(2 ** attempt)
                else:
                    print(f"❌ All connection attempts failed: {e}")
                    raise

    def cursor(self, dictionary=True):
        conn = self.get_connection()
        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) if dictionary else conn.cursor()

    def close(self):
        if self._connection and not self._connection.closed:
            try:
                self._connection.close()
            except Exception:
                pass
        self._connection = None

    def execute_query(self, query, params=None, operation_name=None):
        """
        Execute a query and return results.
        
        Args:
            query: SQL query string
            params: Optional parameters for the query
            operation_name: Optional name for the operation (for compatibility with tools)
        """
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)

                # Para DDL y DML hacer commit explícito
                query_upper = query.strip().upper()
                if query_upper.startswith(('CREATE', 'DROP', 'ALTER', 'INSERT', 'UPDATE', 'DELETE')):
                    conn.commit()
                if cur.description:  # SELECT query
                    return cur.fetchall()
                else:  # INSERT/UPDATE/DELETE
                    return cur.rowcount
        except psycopg2.Error as e:
            print(f"❌ Query execution failed: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            raise

    def execute_non_query(self, query, params=None, operation_name=None):
        """
        Execute non-query operations (INSERT, UPDATE, DELETE).
        Added for compatibility with tools that might call this method.
        
        Args:
            query: SQL query string
            params: Optional parameters for the query
            operation_name: Optional name for the operation
        """
        return self.execute_query(query, params, operation_name)


# Para compatibilidad con AsyncSQLConnectionManager si otras partes del código lo esperan
class AsyncSQLConnectionManager(SQLConnectionManager):
    """
    Wrapper de compatibilidad para código que espera AsyncSQLConnectionManager.
    No es realmente async, pero mantiene la interfaz.
    """
    
    async def execute_query(self, query, params=None, operation_name=None):
        """Wrapper async para compatibilidad"""
        return super().execute_query(query, params, operation_name)
    
    async def execute_non_query(self, query, params=None, operation_name=None):
        """Wrapper async para compatibilidad"""
        return super().execute_non_query(query, params, operation_name)
    
    async def close(self):
        """Wrapper async para compatibilidad"""
        return super().close()
    
    async def _ensure_initialized(self):
        """Para compatibilidad con código que espera este método"""
        pass


db = SQLConnectionManager()