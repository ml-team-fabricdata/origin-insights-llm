"""
Base class for executor nodes that run tools dynamically.

This eliminates code duplication across actors, directors, collaborations, etc.
"""

from typing import Dict, Callable, TypeVar, Any
from strands import Agent

T = TypeVar('T', bound=Dict[str, Any])


class BaseExecutorNode:
    """
    Base class for nodes that execute tools dynamically.
    
    Handles:
    - Tool routing
    - Agent execution
    - State updates
    - Logging
    - Error handling
    
    Usage:
        executor = BaseExecutorNode(
            node_name="directors",
            tools_map=DIRECTORS_TOOLS_MAP,
            router_fn=route_directors_tool,
            system_prompt=DIRECTORS_PROMPT,
            model=MODEL_NODE_EXECUTOR
        )
        
        async def directors_node(state: State) -> State:
            return await executor.execute(state)
    """
    
    def __init__(
        self,
        node_name: str,
        tools_map: Dict[str, Callable],
        router_fn: Callable,
        system_prompt: str,
        model: str,
        entity_key: str = None
    ):
        """
        Initialize the executor node.
        
        Args:
            node_name: Name of the node (e.g., "directors", "actors")
            tools_map: Dictionary mapping tool names to tool functions
            router_fn: Async function that routes to the correct tool
            system_prompt: System prompt for the Agent
            model: Model ID to use
            entity_key: Key for validated entity ID (e.g., "director_id")
                       If None, uses "{node_name}_id"
        """
        self.node_name = node_name
        self.tools_map = tools_map
        self.router_fn = router_fn
        self.system_prompt = system_prompt
        self.model = model
        self.entity_key = entity_key or f"{node_name}_id"
    
    async def execute(self, state: T) -> T:
        """
        Execute the node with the selected tool.
        
        Flow:
        1. Log header
        2. Route to tool
        3. Get tool function
        4. Execute with Agent
        5. Update state
        
        Args:
            state: Current state dictionary
            
        Returns:
            Updated state dictionary
        """
        self._log_header(state)
        
        # 1. Routing
        tool_name = await self._route_tool(state)
        
        # 2. Get tool
        tool_fn = self._get_tool(tool_name)
        if not tool_fn:
            return self._handle_tool_not_found(state, tool_name)
        
        # 3. Execute with Agent
        result = await self._execute_with_agent(state, tool_fn)
        
        # 4. Update state
        return self._update_state(state, result, tool_name)
    
    def _log_header(self, state: T):
        """Log the node header."""
        print(f"\n{'='*80}")
        print(f"[{self.node_name.upper()} NODE]")
        print(f"{'='*80}")
        print(f"Question: {state['question']}")
        print(f"Current state:")
        print(f"   • Task: {state.get('task', 'N/A')}")
        print(f"   • Previous tool calls: {state.get('tool_calls_count', 0)}")
        print(f"   • Accumulated data: {len(state.get('accumulated_data', ''))} characters")
    
    async def _route_tool(self, state: T) -> str:
        """Select the tool to use."""
        print(f"\n[ROUTING] Selecting tool...")
        tool_name = await self.router_fn(state)
        print(f"[SUCCESS] Tool selected: {tool_name}")
        return tool_name
    
    def _get_tool(self, tool_name: str) -> Callable:
        """Get the tool function from the map."""
        return self.tools_map.get(tool_name)
    
    def _handle_tool_not_found(self, state: T, tool_name: str) -> T:
        """Handle the case when tool is not found."""
        error_msg = f"Tool not found: {tool_name}"
        print(f"[ERROR] {error_msg}")
        
        # Update state manually to avoid import issues
        state = dict(state)
        if 'errors' not in state:
            state['errors'] = []
        state['errors'].append({
            'message': error_msg,
            'source': f"{self.node_name}_node"
        })
        state['tool_calls_count'] = state.get('tool_calls_count', 0) + 1
        state['last_node'] = f"{self.node_name}_node"
        
        return state
    
    async def _execute_with_agent(self, state: T, tool_fn: Callable) -> str:
        """Execute the tool with the Agent."""
        print(f"[AGENT] Executing tool with model: {self.model}...")
        
        question_with_context = self._build_context(state)
        
        agent = Agent(
            model=self.model,
            tools=[tool_fn],
            system_prompt=self.system_prompt
        )
        
        result = await agent.invoke_async(question_with_context)
        return getattr(result, "message", str(result))
    
    def _build_context(self, state: T) -> str:
        """
        Build the context with validated entities.
        
        If validated entity ID exists, append it to the question.
        """
        validated_entities = state.get('validated_entities', {})
        entity_id = validated_entities.get(self.entity_key) if validated_entities else None
        
        if entity_id:
            print(f"[VALIDATED] Using {self.entity_key}: {entity_id}")
            return f"{state['question']}\n\nValidated {self.entity_key}: {entity_id}"
        else:
            return state['question']
    
    def _update_state(self, state: T, result: str, tool_name: str) -> T:
        """Update the state with the result."""
        print(f"[DATA] Obtained: {len(result)} characters")
        print(f"[PREVIEW] {result[:200]}..." if len(result) > 200 else f"[DATA] {result}")
        
        # Update state manually to avoid import issues
        state = dict(state)
        
        # Append to accumulated data
        current_data = state.get('accumulated_data', '')
        source = f"{self.node_name}_node/{tool_name}"
        state['accumulated_data'] = f"{current_data}\n\n--- Data from {source} ---\n{result}"
        
        # Increment tool calls
        state['tool_calls_count'] = state.get('tool_calls_count', 0) + 1
        state['last_node'] = f"{self.node_name}_node"
        
        print(f"\n[SUCCESS] {self.node_name.capitalize()} node completed")
        print(f"   • Total tool calls: {state.get('tool_calls_count')}")
        print(f"   • Total accumulated data: {len(state.get('accumulated_data', ''))} characters")
        print(f"   • Last node: {state.get('last_node', 'N/A')}")
        print(f"{'='*80}\n")
        
        return state
