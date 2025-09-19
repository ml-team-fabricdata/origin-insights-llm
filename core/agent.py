# src/core/agent.py
from urllib.parse import quote_plus

from langchain_aws import ChatBedrock
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.postgres import PostgresSaver

import psycopg

from src.sql_db import SQLConnectionManager  
from src.prompt_templates.prompt import prompt as SYSTEM_PROMPT
from src.sql.tools import ALL_SQL_TOOLS

VERBOSE = True

def get_postgres_saver():
    """
    Crea una conexión psycopg v3 con search_path=ms,public
    usando las mismas credenciales del SQLConnectionManager (psycopg2),
    y la pasa a PostgresSaver.
    """
    mgr = SQLConnectionManager()  # obtiene credenciales desde Secrets Manager
    cfg = mgr.conn_params         # {'host','port','dbname','user','password',...}

    host = cfg["host"]
    port = cfg["port"]
    db   = cfg["dbname"]
    user = cfg["user"]
    pwd  = cfg["password"]

    # psycopg v3: fijamos search_path via options y habilitamos autocommit
    conn = psycopg.connect(
        host=host,
        port=port,
        dbname=db,
        user=user,
        password=pwd,
        options="-c search_path=ms",
        autocommit=True,

    )

    # Crear schema ms si no existe (idempotente)
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS ms;")

    saver = PostgresSaver(conn)  
    saver.setup()
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
    memory = get_postgres_saver() 

    agent = create_react_agent(
        llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
        checkpointer=memory
    )
    return agent