# nodes/presence.py - Nodo de presencia
from strands import Agent
from src.strands.platform.graph_core.state import State, increment_tool_calls, append_to_accumulated_data, add_error
from src.strands.platform.nodes.routers import route_presence_tool
from src.strands.platform.config import MODEL_NODE_EXECUTOR

# Importar tools
from src.sql.modules.platform.presence import (
    presence_count, 
    presence_list, 
    presence_statistics, 
    platform_count_by_country, 
    country_platform_summary
)

# Importar prompts
from src.strands.platform.prompts import PRESENCE_PROMPT

# Mapeo de tools
PRESENCE_TOOLS_MAP = {
    "presence_count": presence_count,
    "presence_list": presence_list,
    "presence_statistics": presence_statistics,
    "platform_count_by_country": platform_count_by_country,
    "country_platform_summary": country_platform_summary
}


async def presence_node(state: State) -> State:
    """Nodo que ejecuta tools de presencia dinámicamente"""
    
    print("[NODE] Presence node ejecutando...")
    
    # 1. Usar el router para seleccionar la tool
    tool_name = await route_presence_tool(state)
    print(f"[NODE] Tool seleccionada: {tool_name}")
    
    # 2. Obtener la tool del mapeo
    tool_fn = PRESENCE_TOOLS_MAP.get(tool_name)
    
    if not tool_fn:
        error_msg = f"Tool no encontrada: {tool_name}"
        print(f"[ERROR] {error_msg}")
        state = add_error(state, error_msg, "presence_node")
        state = increment_tool_calls(state, worker_name="presence_node")
        return state
    
    # 3. Ejecutar la tool con Agent
    agent = Agent(
        model=MODEL_NODE_EXECUTOR,
        tools=[tool_fn],
        system_prompt=PRESENCE_PROMPT
    )
    
    result = await agent.invoke_async(state['question'])
    
    # 4. Extraer datos del resultado
    new_data = getattr(result, "message", str(result))
    print(f"[NODE] Datos obtenidos: {len(new_data)} caracteres")
    
    # 5. Actualizar estado usando helpers
    state = append_to_accumulated_data(
        state, 
        new_data, 
        source=f"presence_node/{tool_name}"
    )
    
    state = increment_tool_calls(state, worker_name="presence_node")
    
    print(f"[NODE] Presence node completado (tool #{state.get('tool_calls_count')})")
    return state
