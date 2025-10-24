from langgraph.graph import StateGraph, END
from .state import State, create_initial_state
from .supervisor import business_classifier, main_supervisor, route_from_main_supervisor
from src.strands.business.nodes.intelligence import intelligence_node
from src.strands.business.nodes.rankings import rankings_node
from src.strands.business.nodes.pricing import pricing_node


def _route_from_classifier(state: State) -> str:
    task = state.get("task", "").lower()
    if task == "rankings":
        return "rankings_node"
    elif task == "pricing":
        return "pricing_node"
    return "intelligence_node"


def create_streaming_graph():
    """Create business graph without validation node."""
    print("\n" + "="*80)
    print(" CREATING BUSINESS GRAPH - NO VALIDATION NODE")
    print("="*80)
    graph = StateGraph(State)

    graph.add_node("main_supervisor", main_supervisor)
    graph.add_node("business_classifier", business_classifier)
    graph.add_node("intelligence_node", intelligence_node)
    graph.add_node("rankings_node", rankings_node)
    graph.add_node("pricing_node", pricing_node)

    graph.set_entry_point("main_supervisor")
    
    print("[BUSINESS GRAPH] Compiled with nodes: main_supervisor, business_classifier, intelligence_node, rankings_node, pricing_node")
    print("[BUSINESS GRAPH] Entry point: main_supervisor (NO validation node, NO format_response)")

    graph.add_conditional_edges(
        "main_supervisor",
        route_from_main_supervisor,
        {
            "business_classifier": "business_classifier",
            "format_response": END,  # Si está COMPLETO, terminar
            "return_to_main_router": END
        }
    )

    graph.add_conditional_edges(
        "business_classifier",
        _route_from_classifier,
        {
            "rankings_node": "rankings_node",
            "pricing_node": "pricing_node",
            "intelligence_node": "intelligence_node"
        }
    )

    graph.add_edge("rankings_node", "main_supervisor")
    graph.add_edge("pricing_node", "main_supervisor")
    graph.add_edge("intelligence_node", "main_supervisor")

    return graph.compile()


async def process_question(question: str, max_iterations: int = 3, validated_entities: dict = None) -> State:
    print("\n" + ""*40)
    print(" BUSINESS PROCESS_QUESTION CALLED")
    print(""*40)
    
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
