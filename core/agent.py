# src/core/agent.py
import asyncio
from urllib.parse import quote_plus

from langchain_aws import ChatBedrock
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.postgres import PostgresSaver

import psycopg

from src.sql_db import AsyncSQLConnectionManager, get_secret
from src.prompt_templates.prompt import prompt as SYSTEM_PROMPT
from src.sql.sql_tools import ALL_SQL_TOOLS

VERBOSE = True


def get_postgres_saver():
    """Versión que funciona en contextos síncronos y asíncronos"""
    # Obtener credenciales manejando ambos contextos
    loop = None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    
    if loop is not None:
        # Si hay un loop corriendo, crear una tarea
        import concurrent.futures
        import threading
        
        def run_in_thread():
            return asyncio.run(get_secret())
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            cfg = future.result()
    else:
        # Si no hay loop, crear uno para obtener las credenciales
        cfg = asyncio.run(get_secret())

    host = cfg["host"]
    port = cfg["port"]
    database = cfg["database"]  # Nota: era "dbname" en tu código original
    user = cfg["user"]
    password = cfg["password"]

    # psycopg v3: fijamos search_path via options y habilitamos autocommit
    conn = psycopg.connect(
        host=host,
        port=port,
        dbname=database,
        user=user,
        password=password,
        options="-c search_path=ms,public",
        autocommit=True,
        # Si necesitas SSL explícito (Aurora suele requerirlo), puedes agregar:
        # sslmode="require",
    )

    # Crear schema ms si no existe (idempotente)
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS ms;")

    saver = PostgresSaver(conn)  # ✅ acepta psycopg v3 connection
    saver.setup()                # crea/migra tablas (idempotente)
    return saver


async def get_postgres_saver_async():
    """Versión asíncrona para usar en contextos async"""
    cfg = await get_secret()

    host = cfg["host"]
    port = cfg["port"]
    database = cfg["database"]
    user = cfg["user"]
    password = cfg["password"]

    # psycopg v3: fijamos search_path via options y habilitamos autocommit
    conn = psycopg.connect(
        host=host,
        port=port,
        dbname=database,
        user=user,
        password=password,
        options="-c search_path=ms,public",
        autocommit=True,
        # Si necesitas SSL explícito (Aurora suele requerirlo), puedes agregar:
        # sslmode="require",
    )

    # Crear schema ms si no existe (idempotente)
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS ms;")

    saver = PostgresSaver(conn)  # ✅ acepta psycopg v3 connection
    saver.setup()                # crea/migra tablas (idempotente)
    return saver


def get_agent(model_api='bedrock'):
    if model_api == 'bedrock':
        llm = ChatBedrock(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            temperature=0
        )
    else:
        raise ValueError("Invalid 'model_api' value")

    tools = ALL_SQL_TOOLS
    memory = get_postgres_saver()  # reemplaza a MemorySaver

    agent = create_react_agent(
        llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
        checkpointer=memory
    )
    return agent


async def get_agent_async(model_api='bedrock'):
    """Versión asíncrona del agente"""
    if model_api == 'bedrock':
        llm = ChatBedrock(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            temperature=0
        )
    else:
        raise ValueError("Invalid 'model_api' value")

    tools = ALL_SQL_TOOLS
    memory = await get_postgres_saver_async()

    agent = create_react_agent(
        llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
        checkpointer=memory
    )
    return agent