from .state import MainRouterState
from .config import MAX_PARALLEL_CANDIDATES
from src.strands.business.graph_core.graph import process_question as business_process
from src.strands.talent.graph_core.graph import process_question as talent_process
from src.strands.content.graph_core.graph import process_question as content_process
from src.strands.platform.graph_core.graph import process_question as platform_process
from src.strands.common.graph_core.graph import process_question as common_process


GRAPH_PROCESSORS = {
    "business": business_process,
    "talent": talent_process,
    "content": content_process,
    "platform": platform_process,
    "common": common_process
}


def _execute_graph_tasks(candidates_to_execute: list, question: str, state: MainRouterState) -> list:
    tasks = []
    for graph_name, confidence in candidates_to_execute:
        processor = GRAPH_PROCESSORS.get(graph_name)
        if processor:
            task = processor(question, max_iterations=3)
            tasks.append((graph_name, confidence, task))
    return tasks


async def _await_parallel_results(tasks: list) -> list:
    results = []
    for graph_name, confidence, task in tasks:
        result = await task
        results.append({
            "graph": graph_name,
            "confidence": confidence,
            "result": result,
            "status": "success"
        })
        print(f"[PARALLEL] {graph_name} completado")
    
    return results


async def parallel_executor_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print(" PARALLEL EXECUTOR")
    print("="*80)
    
    candidates = state.get("routing_candidates", [])
    parallel_k = state.get("parallel_k", min(len(candidates), MAX_PARALLEL_CANDIDATES))
    
    if len(candidates) < 2:
        print("[PARALLEL] Menos de 2 candidatos, no se requiere ejecución paralela")
        return state
    
    candidates_to_execute = candidates[:parallel_k]
    
    print(f"[PARALLEL] Ejecutando K={len(candidates_to_execute)}/{len(candidates)} grafos en paralelo:")
    for graph, conf in candidates_to_execute:
        print(f"  - {graph} (confidence: {conf:.2f})")
    
    tasks = _execute_graph_tasks(candidates_to_execute, state['question'], state)
    results = await _await_parallel_results(tasks)
    
    print("="*80 + "\n")
    
    return {
        **state,
        "parallel_results": results,
        "parallel_execution": True
    }


def _calculate_result_score(result: dict) -> float:
    graph_result = result.get("result", {})
    accumulated_data = graph_result.get("accumulated_data", "")
    routing_conf = result.get("confidence", 0.0)
    data_quality = min(len(accumulated_data) / 500, 1.0)
    
    return routing_conf * 0.5 + data_quality * 0.5


def _find_best_result(successful_results: list) -> dict:
    best_result = None
    best_score = -1
    
    for result in successful_results:
        score = _calculate_result_score(result)
        
        print(f"[AGGREGATOR] {result['graph']}: score={score:.2f} (conf={result.get('confidence', 0):.2f})")
        
        if score > best_score:
            best_score = score
            best_result = result
    
    return best_result, best_score


async def aggregator_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print(" AGGREGATOR")
    print("="*80)
    
    parallel_results = state.get("parallel_results", [])
    
    if not parallel_results:
        print("[AGGREGATOR] No hay resultados paralelos para agregar")
        return state
    
    successful_results = [r for r in parallel_results if r.get("status") == "success"]
    
    if not successful_results:
        print("[AGGREGATOR]  Ningún grafo completó exitosamente")
        return {
            **state,
            "error": "All parallel executions failed",
            "domain_graph_status": "error"
        }
    
    best_result, best_score = _find_best_result(successful_results)
    
    if best_result:
        selected_graph = best_result["graph"]
        graph_result = best_result["result"]
        
        print(f"[AGGREGATOR]  Mejor resultado: {selected_graph} (score={best_score:.2f})")
        print("="*80 + "\n")
        
        return {
            **state,
            "selected_graph": selected_graph,
            "answer": graph_result.get("answer", ""),
            "aggregated_result": best_result,
            "domain_graph_status": "success"
        }
    
    print("[AGGREGATOR]  No se pudo seleccionar un mejor resultado")
    print("="*80 + "\n")
    
    return {
        **state,
        "error": "Could not aggregate results",
        "domain_graph_status": "error"
    }