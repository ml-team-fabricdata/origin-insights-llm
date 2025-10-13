# utils/router_helpers.py - Helpers genéricos para routers

from typing import Set, Optional, TypedDict, Any
from strands import Agent


def extract_agent_response(result) -> str:
    """
    Extrae el mensaje de la respuesta del Agent de forma robusta.
    Funciona con dict u objetos AgentResult.
    
    Args:
        result: Respuesta del Agent (puede ser dict, AgentResult u objeto)
        
    Returns:
        String con el mensaje extraído
    """
    # Si es un objeto (AgentResult), obtener el atributo message
    if not isinstance(result, dict):
        message_attr = getattr(result, "message", None)
        if message_attr:
            result = message_attr
        else:
            # Fallback: convertir a string
            return str(result)
    
    # Ahora result debería ser un dict
    if isinstance(result, dict):
        # Si tiene estructura de mensaje de Anthropic
        if 'role' in result and 'content' in result:
            content = result['content']
            if isinstance(content, list) and len(content) > 0:
                # Extraer el texto del primer bloque de contenido
                first_block = content[0]
                if isinstance(first_block, dict) and 'text' in first_block:
                    return first_block['text']
        # Fallback: si tiene 'message'
        if 'message' in result:
            return str(result['message'])
    
    # Último fallback
    return str(result)


async def route_with_llm(
    state: dict[str, Any],
    model: str,
    prompt: str,
    valid_tools: Set[str],
    fallback_tool: Optional[str] = None
) -> str:
    """
    Router genérico usando LLM para seleccionar una herramienta.
    
    Args:
        model: Modelo a usar para routing
        prompt: System prompt para el Agent
        valid_tools: Set de nombres de tools válidas
        fallback_tool: DEPRECATED - No se usa, lanza error si tool inválida
        
    Returns:
        Nombre de la tool seleccionada
        
    Raises:
        ValueError: Si el LLM retorna una tool inválida
    """
    import time
    
    print(f"   🔍 Router LLM analizando pregunta...")
    print(f"   📋 Tools disponibles: {', '.join(sorted(valid_tools))}")
    
    agent = Agent(
        model=model,
        system_prompt=prompt
    )
    
    start_time = time.time()
    result = await agent.invoke_async(state['question'])
    elapsed_time = time.time() - start_time
    
    # Extraer y normalizar respuesta
    response = extract_agent_response(result).strip().lower()
    print(f"   💡 LLM sugiere: {response}")
    print(f"   ⏱️  Tiempo de respuesta: {elapsed_time:.2f}s")
    
    # Validar contra tools válidas
    if response in valid_tools:
        print(f"   ✅ Tool válida, usando: {response}")
        return response
    
    # NO FALLBACK - Lanzar error explícito
    error_msg = f"❌ Tool inválida: '{response}'. Tools válidas: {', '.join(sorted(valid_tools))}"
    print(f"   {error_msg}")
    raise ValueError(error_msg)


def create_router_function(
    model: str,
    prompt: str,
    valid_tools: Set[str],
    fallback_tool: str = None,  # DEPRECATED
    router_name: str = "generic_router"
):
    """
    Factory function que crea una función de routing personalizada.
    
    Args:
        model: Modelo a usar
        prompt: System prompt
        valid_tools: Set de tools válidas
        fallback_tool: DEPRECATED - No se usa
        router_name: Nombre del router (para logging)
        
    Returns:
        Función async de routing que lanza error si tool inválida
    """
    async def router(state: dict[str, Any]) -> str:
        """Auto-generated router function"""
        return await route_with_llm(
            state=state,
            model=model,
            prompt=prompt,
            valid_tools=valid_tools,
            fallback_tool=None  # No fallback
        )
    
    # Set metadata para debugging
    router.__name__ = router_name
    router.__doc__ = f"Router for {router_name} - selects from {len(valid_tools)} tools"
    
    return router
