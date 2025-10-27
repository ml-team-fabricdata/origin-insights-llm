from langgraph.graph import StateGraph, END
from .state import State, create_initial_state
from .supervisor import governance_classifier, main_supervisor, route_from_main_supervisor, format_response
from app.strands.common.nodes.validation import validation_node
from app.strands.common.nodes.admin import admin_node


def _route_from_classifier(state: State) -> str:
    task = state.get("task", "").lower()
    if task == "validation":
        return "validation_node"
    return "admin_node"


def create_streaming_graph():
    graph = StateGraph(State)

    graph.add_node("main_supervisor", main_supervisor)
    graph.add_node("governance_node", governance_classifier)
    graph.add_node("validation_node", validation_node)
    graph.add_node("admin_node", admin_node)
    graph.add_node("format_response", format_response)

    graph.set_entry_point("main_supervisor")

    graph.add_conditional_edges(
        "main_supervisor",
        route_from_main_supervisor,
        {
            "governance_node": "governance_node",
            "COMPLETO": "format_response",
            "return_to_main_router": END
        }
    )

    graph.add_conditional_edges(
        "governance_node",
        _route_from_classifier,
        {
            "validation_node": "validation_node",
            "admin_node": "admin_node"
        }
    )

    graph.add_edge("validation_node", "main_supervisor")
    graph.add_edge("admin_node", "main_supervisor")
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
