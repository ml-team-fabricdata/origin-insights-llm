from langgraph.graph import StateGraph, END
from .state import State, create_initial_state
from .supervisor import main_supervisor, content_classifier
from app.strands.content.nodes.discovery import discovery_node
from app.strands.content.nodes.metadata import metadata_node


def _route_from_supervisor(state: State) -> str:
    """Route from supervisor: classifier or specific node or return to main router."""
    supervisor_decision = state.get("supervisor_decision", "")
    tool_calls = state.get("tool_calls_count", 0)
    
    if tool_calls == 0:
        return "content_classifier"
    
    if "COMPLETO" in supervisor_decision:
        return "return_to_main_router"
    
    if "VOLVER_MAIN_ROUTER" in supervisor_decision:
        return "return_to_main_router"
    
    task = state.get("task", "").lower()
    if task == "metadata":
        return "metadata_node"
    elif task == "discovery":
        return "discovery_node"
    
    return "metadata_node"


def _route_from_classifier(state: State) -> str:
    """Route from classifier to appropriate node."""
    task = state.get("task", "").lower()
    
    if task == "discovery":
        return "discovery_node"
    
    return "metadata_node"


def create_streaming_graph():
    """Create content graph with classifier and both metadata/discovery nodes."""
    graph = StateGraph(State)

    graph.add_node("main_supervisor", main_supervisor)
    graph.add_node("content_classifier", content_classifier)
    graph.add_node("metadata_node", metadata_node)
    graph.add_node("discovery_node", discovery_node)

    graph.set_entry_point("main_supervisor")

    graph.add_conditional_edges(
        "main_supervisor",
        _route_from_supervisor,
        {
            "content_classifier": "content_classifier",
            "metadata_node": "metadata_node",
            "discovery_node": "discovery_node",
            "COMPLETO": END,
            "return_to_main_router": END
        }
    )

    graph.add_conditional_edges(
        "content_classifier",
        _route_from_classifier,
        {
            "metadata_node": "metadata_node",
            "discovery_node": "discovery_node"
        }
    )

    graph.add_edge("metadata_node", "main_supervisor")
    graph.add_edge("discovery_node", "main_supervisor")

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
