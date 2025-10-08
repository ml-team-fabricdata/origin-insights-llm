# node_helper.py - Nodos dinámicos que ejecutan tools
import sys
from pathlib import Path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from src.strands.platform.graph.state import State, increment_tool_calls, append_to_accumulated_data, add_error
from src.strands.platform.graph.parent_routers import route_availability_tool, route_presence_tool
from strands import Agent

# Importar tools
from src.sql.modules.platform.availability import (
    get_availability_by_uid, 
    get_platform_exclusives, 
    compare_platforms_for_title, 
    get_recent_premieres_by_country
)
from src.sql.modules.platform.presence import (
    presence_count, 
    presence_list, 
    presence_statistics, 
    platform_count_by_country, 
    country_platform_summary
)

# Importar prompts
from src.strands.platform.prompt_platform import AVAILABILITY_PROMPT, PRESENCE_PROMPT


# Mapeo de nombres a tools
AVAILABILITY_TOOLS_MAP = {
    "availability_by_uid": get_availability_by_uid,
    "platform_exclusives": get_platform_exclusives,
    "compare_platforms": compare_platforms_for_title,
    "recent_premieres": get_recent_premieres_by_country
}

PRESENCE_TOOLS_MAP = {
    "presence_count": presence_count,
    "presence_list": presence_list,
    "presence_statistics": presence_statistics,
    "platform_count_by_country": platform_count_by_country,
    "country_platform_summary": country_platform_summary
}


async def availability_node(state: State) -> State:
    """Nodo que ejecuta tools de disponibilidad dinámicamente"""
    
    print("[NODE] Availability node ejecutando...")
    
    try:
        # 1. Usar el router para seleccionar la tool
        tool_name = await route_availability_tool(state)
        print(f"[NODE] Tool seleccionada: {tool_name}")
        
        # 2. Obtener la tool del mapeo
        tool_fn = AVAILABILITY_TOOLS_MAP.get(tool_name)
        
        if not tool_fn:
            error_msg = f"Tool no encontrada: {tool_name}"
            print(f"[ERROR] {error_msg}")
            state = add_error(state, error_msg, "availability_node")
            state = increment_tool_calls(state, worker_name="availability_node")
            return state
        
        # 3. Ejecutar la tool con Agent
        agent = Agent(
            model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            tools=[tool_fn],
            system_prompt=AVAILABILITY_PROMPT
        )
        
        result = await agent.invoke_async(state['question'])
        
        # 4. Extraer datos del resultado
        new_data = getattr(result, "message", str(result))
        print(f"[NODE] Datos obtenidos: {len(new_data)} caracteres")
        
        # 5. Actualizar estado usando helpers
        state = append_to_accumulated_data(
            state, 
            new_data, 
            source=f"availability_node/{tool_name}"
        )
        
        state = increment_tool_calls(state, worker_name="availability_node")
        
        print(f"[NODE] Availability node completado (tool #{state.get('tool_calls_count')})")
        return state
        
    except Exception as e:
        print(f"[ERROR] Availability node: {str(e)}")
        state = add_error(state, str(e), "availability_node")
        state = increment_tool_calls(state, worker_name="availability_node")
        return state


async def presence_node(state: State) -> State:
    """Nodo que ejecuta tools de presencia dinámicamente"""
    
    print("[NODE] Presence node ejecutando...")
    
    try:
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
            model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
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
        
    except Exception as e:
        print(f"[ERROR] Presence node: {str(e)}")
        state = add_error(state, str(e), "presence_node")
        state = increment_tool_calls(state, worker_name="presence_node")
        return state
