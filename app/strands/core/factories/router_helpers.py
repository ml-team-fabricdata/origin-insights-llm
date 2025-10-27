"""Router Helpers

Utilities for LLM-based routing between tools.
"""

import time
from typing import Set, Optional, Any
from strands import Agent


def extract_agent_response(result) -> str:
    """Extract text response from various Agent result formats."""
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
) -> Optional[str]:
    """Use LLM to select the appropriate tool from valid options.
    
    Args:
        state: Current state containing the question
        model: LLM model to use for routing
        prompt: System prompt for the router
        valid_tools: Set of valid tool names
        fallback_tool: Optional fallback if LLM returns invalid tool
        
    Returns:
        Selected tool name or None if no valid tool is found
    """
    print("   Router LLM analizando pregunta...")
    print(f"   Tools disponibles: {', '.join(sorted(valid_tools))}")
    
    agent = Agent(model=model, system_prompt=prompt)
    start_time = time.time()
    result = await agent.invoke_async(state['question'])
    elapsed_time = time.time() - start_time
    
    response = extract_agent_response(result).strip().lower()
    print(f"   LLM sugiere: {response}")
    print(f"   Tiempo de respuesta: {elapsed_time:.2f}s")
    
    tools_lower_map = {tool.lower(): tool for tool in valid_tools}
    
    if response in tools_lower_map:
        actual_tool = tools_lower_map[response]
        print(f"   Tool valida, usando: {actual_tool}")
        return actual_tool
    
    for tool_name in valid_tools:
        if tool_name.lower() in response:
            print(f"   Tool encontrada en texto: {tool_name}")
            return tool_name
    
    if fallback_tool:
        print(f"   Tool no encontrada, usando fallback: {fallback_tool}")
        return fallback_tool
    
    print(f"   Tool no encontrada, retornando None")
    return None