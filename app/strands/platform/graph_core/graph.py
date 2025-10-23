from langgraph.graph import StateGraph, END
from .state import State, create_initial_state
from .supervisor import platform_classifier, main_supervisor, route_from_main_supervisor, format_response
from app.strands.platform.nodes.availability import availability_node
from app.strands.platform.nodes.presence import presence_node
from app.strands.core.nodes.param_validation import validation_node, create_validation_edge


def _route_from_classifier(state: State) -> str:
    task = state.get("task", "").lower()
    if task == "availability":
        return "availability_node"
    return "presence_node"


def create_streaming_graph():
    """Create platform graph with validation node."""
    graph = StateGraph(State)

    graph.add_node("validation", validation_node)
    graph.add_node("main_supervisor", main_supervisor)
    graph.add_node("platform_node", platform_classifier)
    graph.add_node("availability_node", availability_node)
    graph.add_node("presence_node", presence_node)
    graph.add_node("format_response", format_response)

    graph.set_entry_point("validation")
    
    graph.add_conditional_edges(
        "validation",
        create_validation_edge,
        {
            "continue": "main_supervisor",
            "format_response": "format_response"
        }
    )

    graph.add_conditional_edges(
        "main_supervisor",
        route_from_main_supervisor,
        {
            "platform_node": "platform_node",
            "format_response": "format_response",
            "return_to_main_router": END
        }
    )

    graph.add_conditional_edges(
        "platform_node",
        _route_from_classifier,
        {
            "availability_node": "availability_node",
            "presence_node": "presence_node"
        }
    )

    graph.add_edge("availability_node", "main_supervisor")
    graph.add_edge("presence_node", "main_supervisor")
    graph.add_edge("format_response", END)

    return graph.compile()


async def process_question(question: str, max_iterations: int = 3, validated_entities: dict = None) -> State:
    initial_state = create_initial_state(question, max_iterations)
    
    if validated_entities:
        initial_state['validated_entities'] = validated_entities
    
    graph = create_streaming_graph()
    result = await graph.ainvoke(initial_state)
    return result


async def process_question_streaming(question: str, max_iterations: int = 3):
    initial_state = create_initial_state(question, max_iterations)
    graph = create_streaming_graph()

    async for event in graph.astream(initial_state):
        node_name = list(event.keys())[0]
        state_output = event[node_name]

        print(f"Node: {node_name}")
        print(f"Tool calls: {state_output.get('tool_calls_count', 0)}")
        print(f"Decision: {state_output.get('supervisor_decision', 'N/A')}")
        print("---")

    return state_output
