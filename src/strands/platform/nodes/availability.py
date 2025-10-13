# platform/nodes/availability.py - Nodo de disponibilidad
from strands import Agent
from src.strands.platform.graph_core.state import State, increment_tool_calls, append_to_accumulated_data, add_error
from src.strands.platform.nodes.routers import route_availability_tool
from src.strands.utils.config import MODEL_NODE_EXECUTOR

# Importar tools
from src.sql.modules.platform.availability import (
    get_availability_by_uid, 
    get_platform_exclusives, 
    compare_platforms_for_title, 
    get_recent_premieres_by_country
)

# Importar prompts
from src.strands.platform.prompt_platform import AVAILABILITY_PROMPT

# Mapeo de tools
AVAILABILITY_TOOLS_MAP = {
    "availability_by_uid": get_availability_by_uid,
    "platform_exclusives": get_platform_exclusives,
    "compare_platforms": compare_platforms_for_title,
    "recent_premieres": get_recent_premieres_by_country
}


async def availability_node(state: State) -> State:
    """Nodo que ejecuta tools de disponibilidad dinámicamente"""
    
    print("\n" + "="*80)
    print("🔹 AVAILABILITY NODE")
    print("="*80)
    print(f"📝 Pregunta: {state['question']}")
    print(f"📊 Estado actual:")
    print(f"   • Task: {state.get('task', 'N/A')}")
    print(f"   • Tool calls previos: {state.get('tool_calls_count', 0)}")
    print(f"   • Datos acumulados: {len(state.get('accumulated_data', ''))} caracteres")
    
    # 1. Usar el router para seleccionar la tool
    print(f"\n🔀 Routing a tool específica...")
    tool_name = await route_availability_tool(state)
    print(f"✅ Tool seleccionada: {tool_name}")
    
    # 2. Obtener la tool del mapeo
    tool_fn = AVAILABILITY_TOOLS_MAP.get(tool_name)
    
    if not tool_fn:
        error_msg = f"Tool no encontrada: {tool_name}"
        print(f"❌ ERROR: {error_msg}")
        state = add_error(state, error_msg, "availability_node")
        state = increment_tool_calls(state, worker_name="availability_node")
        return state
    
    # 3. Ejecutar la tool con Agent
    print(f"🤖 Ejecutando tool con Agent (modelo: {MODEL_NODE_EXECUTOR})...")
    agent = Agent(
        model=MODEL_NODE_EXECUTOR,
        tools=[tool_fn],
        system_prompt=AVAILABILITY_PROMPT
    )
    
    result = await agent.invoke_async(state['question'])
    
    # 4. Extraer datos del resultado (puede ser dict u objeto)
    if isinstance(result, dict):
        new_data = str(result.get('message', result))
    else:
        new_data = str(getattr(result, "message", result))
    
    print(f"📦 Datos obtenidos: {len(new_data)} caracteres")
    print(f"📄 Preview: {new_data[:200]}..." if len(new_data) > 200 else f"📄 Datos: {new_data}")
    
    # 5. Actualizar estado usando helpers
    state = append_to_accumulated_data(
        state, 
        new_data, 
        source=f"availability_node/{tool_name}"
    )
    
    state = increment_tool_calls(state, worker_name="availability_node")
    
    print(f"\n✅ Availability node completado")
    print(f"   • Total tool calls: {state.get('tool_calls_count')}")
    print(f"   • Total datos acumulados: {len(state.get('accumulated_data', ''))} caracteres")
    print(f"   • Último nodo: {state.get('last_node', 'N/A')}")
    print("="*80 + "\n")
    
    return state
