import base64
import json
import logging
import os
import time
from functools import lru_cache

import boto3
import psycopg2
import psycopg2.extras
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_secret() -> dict:

    secret_id = os.getenv("DB_SECRET_ID", "aurora-postgres-origin-insights-secret-er")
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"

    client = boto3.session.Session().client("secretsmanager", region_name=region)
    val = client.get_secret_value(SecretId=secret_id)

    if "SecretString" in val:
        raw = json.loads(val["SecretString"])
    else:
        raw = json.loads(base64.b64decode(val["SecretBinary"]).decode("utf-8"))

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
            "dbname": cfg["db"],
            "user": cfg["user"],
            "password": cfg["password"],
            "connect_timeout": 30,
            "application_name": "chatbot_app",
            "sslmode": "require",
        }
        self._connection = None
        self._initialized = False
        self._initialize_connection()

    def _initialize_connection(self):
        self._connection = psycopg2.connect(**self.conn_params)
        if not self._initialized:
            logger.info(
                f" Connected to PostgreSQL: {self.conn_params['dbname']}@"
                f"{self.conn_params['host']}:{self.conn_params['port']}"
            )
            self._initialized = True

    def get_connection(self, retry_count=3):
        for attempt in range(retry_count):
            if self._connection and not self._connection.closed:
                with self._connection.cursor() as c:
                    c.execute("SELECT 1")
                return self._connection

            if attempt == 0:
                logger.info(" Creating new PostgreSQL connection")
            self._connection = psycopg2.connect(**self.conn_params)
            self._connection.autocommit = True
            return self._connection

    def _close(self):
        if self._connection and not self._connection.closed:
            self._connection.close()
        self._connection = None

    def execute_query(self, query, params=None, operation_name=None):
        import time
        
        print("\n" + "="*80)
        print(" SQL QUERY EJECUTADA")
        print("="*80)
        if operation_name:
            print(f" Operación: {operation_name}")
        print(f" Query:")
        print(query)
        if params:
            print(f" Parámetros: {params}")
        print("="*80 + "\n")
        
        conn = self.get_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            start_time = time.time()
            cur.execute(query, params)
            elapsed_time = time.time() - start_time

            query_upper = query.strip().upper()
            if query_upper.startswith(('CREATE', 'DROP', 'ALTER', 'INSERT', 'UPDATE', 'DELETE')):
                conn.commit()
            if cur.description:
                results = cur.fetchall()
                print(f" Query retornó {len(results)} filas en {elapsed_time:.3f}s\n")
                return results
            else:
                print(f" Query afectó {cur.rowcount} filas en {elapsed_time:.3f}s\n")
                return cur.rowcount


db = SQLConnectionManager()
