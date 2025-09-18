from langchain_aws import ChatBedrock
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from src.prompt_templates.prompt import prompt as SYSTEM_PROMPT
from src.sql.tools import ALL_SQL_TOOLS

def get_fast_agent(model_api='bedrock'):
    """Agente ultra-rápido sin persistencia"""
    if model_api == 'bedrock':
        llm = ChatBedrock(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            temperature=0,
            # Timeouts agresivos
            client_kwargs={
                'config': {
                    'read_timeout': 10,
                    'connect_timeout': 5
                }
            }
        )
    
    # MemorySaver en lugar de PostgresSaver para velocidad
    memory = MemorySaver()
    
    agent = create_react_agent(
        llm,
        tools=ALL_SQL_TOOLS,
        prompt=SYSTEM_PROMPT,
        checkpointer=memory
    )
    return agent