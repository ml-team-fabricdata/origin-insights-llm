# content/nodes/admin.py
from strands import Agent
from src.strands.common.graph_core.state import State, increment_tool_calls, append_to_accumulated_data, add_error
from src.strands.common.nodes.routers import route_admin_tool
from src.strands.common.nodes.prompt_common import ADMIN_PROMPT
from src.strands.utils.config import MODEL_NODE_EXECUTOR


# Importar tools
from src.sql.modules.common.admin import (
    build_sql,
    validate_intent,
    run_sql_adapter
)


ADMIN_TOOLS_MAP = {
    "build_sql": build_sql,
    "validate_intent": validate_intent,
    "run_sql_adapter": run_sql_adapter
}


async def admin_node(state: State) -> State:
    """Nodo que ejecuta tools de discovery dinámicamente"""

    print("\n" + "="*80)
    print("🔹 ADMIN NODE")
    print("="*80)
    print(f"📝 Pregunta: {state['question']}")
    print(f"📊 Estado actual:")
    print(f"   • Task: {state.get('task', 'N/A')}")
    print(f"   • Tool calls previos: {state.get('tool_calls_count', 0)}")
    print(
        f"   • Datos acumulados: {len(state.get('accumulated_data', ''))} caracteres")

    # 1. Usar el router para seleccionar la tool
    print(f"\n🔀 Routing a tool específica...")
    tool_name = await route_admin_tool(state)
    print(f"✅ Tool seleccionada: {tool_name}")

    # 2. Obtener la tool del mapeo
    tool_fn = ADMIN_TOOLS_MAP.get(tool_name)

    if not tool_fn:
        error_msg = f"Tool no encontrada: {tool_name}"
        print(f"❌ ERROR: {error_msg}")
        state = add_error(state, error_msg, "admin_node")
        state = increment_tool_calls(state, worker_name="admin_node")
        return state

    # 3. Ejecutar la tool con Agent
    print(f"🤖 Ejecutando tool con Agent (modelo: {MODEL_NODE_EXECUTOR})...")
    agent = Agent(
        model=MODEL_NODE_EXECUTOR,
        tools=[tool_fn],
        system_prompt=ADMIN_PROMPT
    )

    result = await agent.invoke_async(state['question'])

    # 4. Extraer datos del resultado
    new_data = getattr(result, "message", str(result))

    print(f"📦 Datos obtenidos: {len(new_data)} caracteres")
    print(f"📄 Preview: {new_data[:200]}..." if len(
        new_data) > 200 else f"📄 Datos: {new_data}")

    # 5. Actualizar estado usando helpers
    state = append_to_accumulated_data(
        state,
        new_data,
        source=f"admin_node/{tool_name}"
    )

    state = increment_tool_calls(state, worker_name="admin_node")

    print(f"\n✅ Admin node completado")
    print(f"   • Total tool calls: {state.get('tool_calls_count')}")
    print(
        f"   • Total datos acumulados: {len(state.get('accumulated_data', ''))} caracteres")
    print(f"   • Último nodo: {state.get('last_node', 'N/A')}")
    print("="*80 + "\n")

    return state
