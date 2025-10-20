from langgraph.graph import StateGraph, END
from .state import State, create_initial_state
from .supervisor import content_classifier, main_supervisor, route_from_main_supervisor, format_response
from src.strands.content.nodes.discovery import discovery_node
from src.strands.utils.param_validation_node import validation_node, create_validation_edge


def _route_from_classifier(state: State) -> str:
    # Content only has discovery_node
    return "discovery_node"


def create_streaming_graph():
    """Create content graph with validation node."""
    graph = StateGraph(State)

    # Add validation node first
    graph.add_node("validation", validation_node)
    graph.add_node("main_supervisor", main_supervisor)
    graph.add_node("content_classifier", content_classifier)
    graph.add_node("discovery_node", discovery_node)
    graph.add_node("format_response", format_response)

    # Start with validation
    graph.set_entry_point("validation")
    
    # Route from validation: continue to supervisor or format error
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
            "content_classifier": "content_classifier",
            "format_response": "format_response",
            "return_to_main_router": END
        }
    )

    graph.add_conditional_edges(
        "content_classifier",
        _route_from_classifier,
        {
            "discovery_node": "discovery_node"
        }
    )

    graph.add_edge("discovery_node", "main_supervisor")
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
