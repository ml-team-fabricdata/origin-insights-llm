# content/nodes/admin.py
from strands import Agent
from src.strands.talent.graph_core.state import State, increment_tool_calls, append_to_accumulated_data, add_error
from src.strands.talent.nodes.routers import route_directors_tool
from src.strands.talent.nodes.prompt_talent import DIRECTORS_PROMPT
from src.strands.utils.config import MODEL_NODE_EXECUTOR


# Importar tools
from src.sql.modules.talent.directors import (
    get_director_collaborators,
    get_director_filmography,

)


DIRECTORS_TOOLS_MAP = {
    "get_director_collaborators": get_director_collaborators,
    "get_director_filmography": get_director_filmography,
}


async def directors_node(state: State) -> State:
    """Nodo que ejecuta tools de discovery dinámicamente"""

    print("\n" + "="*80)
    print("🔹 DIRECTORS NODE")
    print("="*80)
    print(f"📝 Pregunta: {state['question']}")
    print(f"📊 Estado actual:")
    print(f"   • Task: {state.get('task', 'N/A')}")
    print(f"   • Tool calls previos: {state.get('tool_calls_count', 0)}")
    print(
        f"   • Datos acumulados: {len(state.get('accumulated_data', ''))} caracteres")

    # 1. Usar el router para seleccionar la tool
    print(f"\n🔀 Routing a tool específica...")
    tool_name = await route_directors_tool(state)
    print(f"✅ Tool seleccionada: {tool_name}")

    # 2. Obtener la tool del mapeo
    tool_fn = DIRECTORS_TOOLS_MAP.get(tool_name)

    if not tool_fn:
        error_msg = f"Tool no encontrada: {tool_name}"
        print(f"❌ ERROR: {error_msg}")
        state = add_error(state, error_msg, "directors_node")
        state = increment_tool_calls(state, worker_name="directors_node")
        return state

    # 3. Ejecutar la tool con Agent
    print(f"🤖 Ejecutando tool con Agent (modelo: {MODEL_NODE_EXECUTOR})...")
    
    # Construir mensaje con entidades validadas si existen
    question_with_context = state['question']
    validated_entities = state.get('validated_entities', {})
    
    if validated_entities and validated_entities.get('raw_validation'):
        # Agregar contexto de validación al prompt
        validation_info = validated_entities.get('raw_validation', '')
        question_with_context = f"""Question: {state['question']}

Validated entities from previous step:
{validation_info}

IMPORTANT: Use the validated IDs from above. Do NOT validate again."""
        print(f"📋 Usando entidades validadas del preprocessor")
    
    agent = Agent(
        model=MODEL_NODE_EXECUTOR,
        tools=[tool_fn],
        system_prompt=DIRECTORS_PROMPT
    )

    result = await agent.invoke_async(question_with_context)

    # 4. Extraer datos del resultado
    new_data = getattr(result, "message", str(result))

    print(f"📦 Datos obtenidos: {len(new_data)} caracteres")
    print(f"📄 Preview: {new_data[:200]}..." if len(
        new_data) > 200 else f"📄 Datos: {new_data}")

    # 5. Actualizar estado usando helpers
    state = append_to_accumulated_data(
        state,
        new_data,
        source=f"directors_node/{tool_name}"
    )

    state = increment_tool_calls(state, worker_name="directors_node")

    print(f"\n✅ Directors node completado")
    print(f"   • Total tool calls: {state.get('tool_calls_count')}")
    print(
        f"   • Total datos acumulados: {len(state.get('accumulated_data', ''))} caracteres")
    print(f"   • Último nodo: {state.get('last_node', 'N/A')}")
    print("="*80 + "\n")

    return state
