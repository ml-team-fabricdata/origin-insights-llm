from typing import Dict, Callable, TypeVar, Any
from strands import Agent

T = TypeVar('T', bound=Dict[str, Any])


class BaseExecutorNode:
    def __init__(
        self,
        node_name: str,
        tools_map: Dict[str, Callable],
        router_fn: Callable,
        system_prompt: str,
        model: str,
        entity_key: str = None
    ):
        self.node_name = node_name
        self.tools_map = tools_map
        self.router_fn = router_fn
        self.system_prompt = system_prompt
        self.model = model
        self.entity_key = entity_key or f"{node_name}_id"

    async def execute(self, state: T) -> T:
        self._log_header(state)
        tool_name = await self._route_tool(state)
        tool_fn = self._get_tool(tool_name)
        if not tool_fn:
            return self._handle_tool_not_found(state, tool_name)
        result = await self._execute_with_agent(state, tool_fn)
        return self._update_state(state, result, tool_name)

    def _log_header(self, state: T):
        print("\n" + "=" * 80)
        print(f"[{self.node_name.upper()} NODE]")
        print("=" * 80)
        print(f"Question: {state['question']}")
        print("Current state:")
        print(f"   • Task: {state.get('task', 'N/A')}")
        print(f"   • Previous tool calls: {state.get('tool_calls_count', 0)}")
        print(f"   • Accumulated data: {len(state.get('accumulated_data', ''))} characters")

    async def _route_tool(self, state: T) -> str:
        print("\n[ROUTING] Selecting tool...")
        tool_name = await self.router_fn(state)
        print(f"[SUCCESS] Tool selected: {tool_name}")
        return tool_name

    def _get_tool(self, tool_name: str) -> Callable:
        return self.tools_map.get(tool_name)

    def _handle_tool_not_found(self, state: T, tool_name: str) -> T:
        error_msg = f"Tool not found: {tool_name}"
        print(f"[ERROR] {error_msg}")
        state = dict(state)
        state.setdefault('errors', []).append({'message': error_msg, 'source': f"{self.node_name}_node"})
        state['tool_calls_count'] = state.get('tool_calls_count', 0) + 1
        state['last_node'] = f"{self.node_name}_node"
        return state

    async def _execute_with_agent(self, state: T, tool_fn: Callable) -> str:
        print(f"[AGENT] Executing tool with model: {self.model}...")
        question_with_context = self._build_context(state)
        agent = Agent(model=self.model, tools=[tool_fn], system_prompt=self.system_prompt)
        result = await agent.invoke_async(question_with_context)
        return getattr(result, "message", str(result))

    def _build_context(self, state: T) -> str:
        validated_entities = state.get('validated_entities', {})
        entity_id = validated_entities.get(self.entity_key) if validated_entities else None
        if entity_id:
            print(f"[VALIDATED] Using {self.entity_key}: {entity_id}")
            return f"{state['question']}\n\nValidated {self.entity_key}: {entity_id}"
        return state['question']

    def _update_state(self, state: T, result: str, tool_name: str) -> T:
        print(f"[DATA] Obtained: {len(result)} characters")
        print(f"[PREVIEW] {result[:200]}..." if len(result) > 200 else f"[DATA] {result}")
        state = dict(state)
        source = f"{self.node_name}_node/{tool_name}"
        state['accumulated_data'] = f"{state.get('accumulated_data', '')}\n\n--- Data from {source} ---\n{result}"
        state['tool_calls_count'] = state.get('tool_calls_count', 0) + 1
        state['last_node'] = f"{self.node_name}_node"
        print(f"\n[SUCCESS] {self.node_name.capitalize()} node completed")
        print(f"   • Total tool calls: {state.get('tool_calls_count')}")
        print(f"   • Total accumulated data: {len(state.get('accumulated_data', ''))} characters")
        print(f"   • Last node: {state.get('last_node', 'N/A')}")
        print("=" * 80 + "\n")
        return state
