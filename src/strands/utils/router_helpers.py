from typing import Set, Optional, Any
from strands import Agent


def extract_agent_response(result) -> str:
    if not isinstance(result, dict):
        message_attr = getattr(result, "message", None)
        if message_attr:
            result = message_attr
        else:
            return str(result)
    if isinstance(result, dict):
        if 'role' in result and 'content' in result:
            content = result['content']
            if isinstance(content, list) and len(content) > 0:
                first_block = content[0]
                if isinstance(first_block, dict) and 'text' in first_block:
                    return first_block['text']
        if 'message' in result:
            return str(result['message'])
    return str(result)


async def route_with_llm(
    state: dict[str, Any],
    model: str,
    prompt: str,
    valid_tools: Set[str],
    fallback_tool: Optional[str] = None
) -> str:
    import time
    print(f"   🔍 Router LLM analizando pregunta...")
    print(f"   📋 Tools disponibles: {', '.join(sorted(valid_tools))}")
    agent = Agent(model=model, system_prompt=prompt)
    start_time = time.time()
    result = await agent.invoke_async(state['question'])
    elapsed_time = time.time() - start_time
    response = extract_agent_response(result).strip().lower()
    print(f"   💡 LLM sugiere: {response}")
    print(f"   ⏱️  Tiempo de respuesta: {elapsed_time:.2f}s")
    if response in valid_tools:
        print(f"   ✅ Tool válida, usando: {response}")
        return response
    error_msg = f"❌ Tool inválida: '{response}'. Tools válidas: {', '.join(sorted(valid_tools))}"
    print(f"   {error_msg}")
    raise ValueError(error_msg)


def create_router_function(
    model: str,
    prompt: str,
    valid_tools: Set[str],
    fallback_tool: str = None,
    router_name: str = "generic_router"
):
    async def router(state: dict[str, Any]) -> str:
        return await route_with_llm(
            state=state,
            model=model,
            prompt=prompt,
            valid_tools=valid_tools,
            fallback_tool=None
        )
    router.__name__ = router_name
    router.__doc__ = f"Router for {router_name} - selects from {len(valid_tools)} tools"
    return router
