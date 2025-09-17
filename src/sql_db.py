import os
import json
import base64
import asyncpg
import boto3
from botocore.exceptions import ClientError


async def get_secret() -> dict:
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
        "database": raw.get("db") or raw.get("dbname"),
        "user": raw.get("user") or raw.get("username"),
        "password": raw.get("password"),
    }

    missing = [k for k, v in cfg.items() if v in (None, "")]
    if missing:
        raise RuntimeError(f"Secreto incompleto; faltan claves: {', '.join(missing)}")

    return cfg


class AsyncSQLConnectionManager:
    def __init__(self):
        self._pool = None
        self._config = None
        self._initialized = False

    async def _ensure_initialized(self):
        if self._initialized:
            return
        
        self._config = await get_secret()
        self._pool = await asyncpg.create_pool(
            host=self._config["host"],
            port=self._config["port"],
            database=self._config["database"],
            user=self._config["user"],
            password=self._config["password"],
            min_size=1,
            max_size=10,
            command_timeout=30
        )
        
        print(f"✅ Connected to PostgreSQL: {self._config['database']}@"
              f"{self._config['host']}:{self._config['port']}")
        self._initialized = True

    async def close(self):
        if self._pool:
            await self._pool.close()
        self._initialized = False

    async def execute_query(self, query: str, params=None, operation_name: str = "query"):
        await self._ensure_initialized()
        
        async with self._pool.acquire() as connection:
            if params:
                result = await connection.fetch(query, *params)
            else:
                result = await connection.fetch(query)
            
            return [dict(row) for row in result]

    async def execute_non_query(self, query: str, params=None, operation_name: str = "command"):
        await self._ensure_initialized()
        
        async with self._pool.acquire() as connection:
            if params:
                result = await connection.execute(query, *params)
            else:
                result = await connection.execute(query)
            
            return result


db = AsyncSQLConnectionManager()