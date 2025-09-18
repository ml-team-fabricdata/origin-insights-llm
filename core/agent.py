# src/core/agent.py - Versión corregida
import asyncio
import concurrent.futures
from urllib.parse import quote_plus

from langchain_aws import ChatBedrock
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.postgres import PostgresSaver

import psycopg

from src.sql_db import get_secret
from src.prompt_templates.prompt import prompt as SYSTEM_PROMPT
from src.sql.core.tools import ALL_SQL_TOOLS

VERBOSE = True


def run_in_new_thread(coro):
    """Ejecuta corrutina en un thread separado con nuevo event loop"""
    def thread_target():
        return asyncio.run(coro)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(thread_target)
        return future.result(timeout=60)  # 60 segundos timeout


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
        # Si Aurora requiere SSL:
        # sslmode="require",
    )

    # Crear schema ms si no existe (idempotente)
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS ms;")

    saver = PostgresSaver(conn)
    saver.setup()
    return saver


def get_postgres_saver():
    """Versión síncrona que maneja event loops correctamente"""
    try:
        # Verificar si hay un loop corriendo
        loop = asyncio.get_running_loop()
        # Si llegamos aquí, hay loop activo - usar thread separado
        return run_in_new_thread(get_postgres_saver_async())
    except RuntimeError:
        # No hay loop activo, usar asyncio.run directamente
        return asyncio.run(get_postgres_saver_async())


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


def get_agent(model_api='bedrock'):
    """Versión síncrona que maneja event loops correctamente"""
    if model_api == 'bedrock':
        llm = ChatBedrock(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            temperature=0
        )
    else:
        raise ValueError("Invalid 'model_api' value")

    tools = ALL_SQL_TOOLS
    
    # Obtener memory manejando event loop correctamente
    memory = get_postgres_saver()

    agent = create_react_agent(
        llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
        checkpointer=memory
    )
    return agent