from langgraph.graph import StateGraph, END
from .state import State, create_initial_state
from .supervisor import talent_classifier, main_supervisor, route_from_main_supervisor, format_response
from src.strands.talent.nodes.actors import actors_node
from src.strands.talent.nodes.directors import directors_node
from src.strands.talent.nodes.collaborations import collaborations_node


def _route_from_classifier(state: State) -> str:
    """Route from classifier. Collaborations requires prior validation."""
    task = state.get("task", "").lower()
    
    if task == "collaborations":
        validated_entities = state.get("validated_entities") or {}
        has_actor = bool(validated_entities.get("actor_id"))
        has_director = bool(validated_entities.get("director_id"))
        
        if not has_actor and not has_director:
            return "actors_node"
        
        return "collaborations_node"
    
    if task == "actors":
        return "actors_node"
    elif task == "directors":
        return "directors_node"
    
    return "actors_node"


def create_streaming_graph():
    """Create optimized talent graph (no internal validation)."""
    graph = StateGraph(State)

    graph.add_node("main_supervisor", main_supervisor)
    graph.add_node("talent_classifier", talent_classifier)
    graph.add_node("actors_node", actors_node)
    graph.add_node("directors_node", directors_node)
    graph.add_node("collaborations_node", collaborations_node)
    graph.add_node("format_response", format_response)

    graph.set_entry_point("main_supervisor")

    graph.add_conditional_edges(
        "main_supervisor",
        route_from_main_supervisor,
        {
            "talent_classifier": "talent_classifier",
            "format_response": "format_response",
            "return_to_main_router": END
        }
    )

    graph.add_conditional_edges(
        "talent_classifier",
        _route_from_classifier,
        {
            "actors_node": "actors_node",
            "directors_node": "directors_node",
            "collaborations_node": "collaborations_node"
        }
    )

    graph.add_edge("actors_node", "main_supervisor")
    graph.add_edge("directors_node", "main_supervisor")
    graph.add_edge("collaborations_node", "main_supervisor")
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

