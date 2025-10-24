from typing import Dict, Callable, TypeVar, Any
import time
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
        
        start_time = time.time()
        result = await self._execute_with_agent(state, tool_fn)
        execution_time = time.time() - start_time
        
        return self._update_state(state, result, tool_name, execution_time)

    def _log_header(self, state: T):
        print("\n" + "=" * 80)
        print(f"[{self.node_name.upper()} NODE]")
        print("=" * 80)
        print(f"Question: {state['question']}")
        print("Current state:")
        print(f"   Task: {state.get('task', 'N/A')}")
        print(f"   Previous tool calls: {state.get('tool_calls_count', 0)}")
        print(f"   Accumulated data: {len(state.get('accumulated_data', ''))} characters")

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
        
        enhanced_question = (
            f"{question_with_context}\n\n"
            f"IMPORTANT: You MUST use the available tool to answer this question. "
            f"Do not provide a generic response or apologize for lack of data."
        )
        
        result = await agent.invoke_async(enhanced_question)
        
        tool_used = False
        if hasattr(result, 'tool_calls') and result.tool_calls:
            tool_used = True
            print(f"[SUCCESS]  Tool was called: {len(result.tool_calls)} call(s)")
        elif hasattr(result, 'content'):
            content_str = str(result.content) if hasattr(result.content, '__str__') else str(result)
            if 'tool_use' in content_str.lower() or 'function_call' in content_str.lower():
                tool_used = True
                print(f"[SUCCESS]  Tool usage detected in content")
        
        if not tool_used:
            print(f"[WARNING]   Agent did NOT use any tools!")
            print(f"[WARNING] This may indicate the agent is providing a generic response.")
            print(f"[WARNING] The response may be incomplete or incorrect.")
        
        return getattr(result, "message", str(result))

    def _build_context(self, state: T) -> str:
        validated_entities = state.get('validated_entities', {})
        if not validated_entities or validated_entities.get('status') == 'skipped':
            return state['question']
        
        context_parts = [state['question']]
        
        if 'uid' in validated_entities:
            uid = validated_entities['uid']
            title_name = validated_entities.get('name', 'Unknown')
            print(f"[VALIDATED] Using uid: {uid} ({title_name})")
            context_parts.append(f"\n🔑 VALIDATED UID: {uid}")
            context_parts.append(f"   Title: '{title_name}'")
            context_parts.append(f"   ⚠️ USE THIS UID IN YOUR TOOL CALL: uid=\"{uid}\"")
        
        if 'actor_id' in validated_entities:
            actor_id = validated_entities['actor_id']
            actor_name = validated_entities.get('actor_name', validated_entities.get('name', 'Unknown'))
            print(f"[VALIDATED] Using actor_id: {actor_id} ({actor_name})")
            context_parts.append(f"\n🔑 VALIDATED ACTOR_ID: {actor_id}")
            context_parts.append(f"   Actor: '{actor_name}'")
            context_parts.append(f"   ⚠️ USE THIS ID IN YOUR TOOL CALL: actor_id=\"{actor_id}\"")
        
        if 'director_id' in validated_entities:
            director_id = validated_entities['director_id']
            director_name = validated_entities.get('director_name', validated_entities.get('name', 'Unknown'))
            print(f"[VALIDATED] Using director_id: {director_id} ({director_name})")
            context_parts.append(f"\n🔑 VALIDATED DIRECTOR_ID: {director_id}")
            context_parts.append(f"   Director: '{director_name}'")
            context_parts.append(f"   ⚠️ USE THIS ID IN YOUR TOOL CALL: director_id=\"{director_id}\"")
        
        return "\n".join(context_parts)

    def _update_state(self, state: T, result: str, tool_name: str, execution_time: float) -> T:
        print(f"[DATA] Obtained: {len(result)} characters")
        print(f"[TIMING] Tool execution time: {execution_time:.2f}s")
        print(f"[PREVIEW] {result[:200]}..." if len(result) > 200 else f"[DATA] {result}")
        state = dict(state)
        source = f"{self.node_name}_node/{tool_name}"
        state['accumulated_data'] = f"{state.get('accumulated_data', '')}\n\n--- Data from {source} ---\n{result}"
        state['tool_calls_count'] = state.get('tool_calls_count', 0) + 1
        state['last_node'] = f"{self.node_name}_node"
        
        if 'tool_execution_times' not in state:
            state['tool_execution_times'] = {}
        state['tool_execution_times'][f"{self.node_name}/{tool_name}"] = execution_time
        
        print(f"\n[SUCCESS] {self.node_name.capitalize()} node completed")
        print(f"   Total tool calls: {state.get('tool_calls_count')}")
        print(f"   Total accumulated data: {len(state.get('accumulated_data', ''))} characters")
        print(f"   Last node: {state.get('last_node', 'N/A')}")
        print("=" * 80 + "\n")
        return state