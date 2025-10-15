import asyncio
from .state import MainRouterState
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


async def parallel_executor_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print("⚡ PARALLEL EXECUTOR")
    print("="*80)
    
    candidates = state.get("routing_candidates", [])
    
    if len(candidates) < 2:
        print("[PARALLEL] Menos de 2 candidatos, no se requiere ejecución paralela")
        return state
    
    print(f"[PARALLEL] Ejecutando {len(candidates)} grafos en paralelo:")
    for graph, conf in candidates:
        print(f"  - {graph} (confidence: {conf:.2f})")
    
    tasks = []
    for graph_name, confidence in candidates:
        processor = GRAPH_PROCESSORS.get(graph_name)
        if processor:
            task = processor(state['question'], max_iterations=3)
            tasks.append((graph_name, confidence, task))
    
    results = []
    for graph_name, confidence, task in tasks:
        try:
            result = await task
            results.append({
                "graph": graph_name,
                "confidence": confidence,
                "result": result,
                "status": "success"
            })
            print(f"[PARALLEL] ✅ {graph_name} completado")
        except Exception as e:
            results.append({
                "graph": graph_name,
                "confidence": confidence,
                "error": str(e),
                "status": "error"
            })
            print(f"[PARALLEL] ❌ {graph_name} falló: {e}")
    
    print("="*80 + "\n")
    
    return {
        **state,
        "parallel_results": results,
        "parallel_execution": True
    }


async def aggregator_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print("🔀 AGGREGATOR")
    print("="*80)
    
    parallel_results = state.get("parallel_results", [])
    
    if not parallel_results:
        print("[AGGREGATOR] No hay resultados paralelos para agregar")
        return state
    
    successful_results = [r for r in parallel_results if r.get("status") == "success"]
    
    if not successful_results:
        print("[AGGREGATOR] ❌ Ningún grafo completó exitosamente")
        return {
            **state,
            "error": "All parallel executions failed",
            "domain_graph_status": "error"
        }
    
    best_result = None
    best_score = -1
    
    for result in successful_results:
        graph_result = result.get("result", {})
        answer = graph_result.get("answer", "")
        accumulated_data = graph_result.get("accumulated_data", "")
        
        routing_conf = result.get("confidence", 0.0)
        data_quality = min(len(accumulated_data) / 500, 1.0)
        
        score = routing_conf * 0.5 + data_quality * 0.5
        
        print(f"[AGGREGATOR] {result['graph']}: score={score:.2f} (conf={routing_conf:.2f}, quality={data_quality:.2f})")
        
        if score > best_score:
            best_score = score
            best_result = result
    
    if best_result:
        selected_graph = best_result["graph"]
        graph_result = best_result["result"]
        
        print(f"[AGGREGATOR] ✅ Mejor resultado: {selected_graph} (score={best_score:.2f})")
        print("="*80 + "\n")
        
        return {
            **state,
            "selected_graph": selected_graph,
            "answer": graph_result.get("answer", ""),
            "aggregated_result": best_result,
            "domain_graph_status": "success"
        }
    
    print("[AGGREGATOR] ⚠️ No se pudo seleccionar un mejor resultado")
    print("="*80 + "\n")
    
    return {
        **state,
        "error": "Could not aggregate results",
        "domain_graph_status": "error"
    }
