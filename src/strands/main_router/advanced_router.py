import json
from strands import Agent
from src.strands.config.models import MODEL_CLASSIFIER
from .state import MainRouterState
from .prompts import ADVANCED_ROUTER_PROMPT
from .config import (
    CONFIDENCE_THRESHOLD,
    MAX_PARALLEL_CANDIDATES,
    MIN_CANDIDATE_SCORE,
    GRAPHS_REQUIRING_VALIDATION,
    should_use_parallel_execution,
    get_parallel_budget,
    is_safe_to_parallelize,
    has_side_effects,
    filter_safe_candidates
)
from .telemetry import log_router_decision, log_candidate_discard, log_rerouting
from .router_cache import get_router_cache


def _extract_response(response) -> str:
    if hasattr(response, 'message'):
        message = response.message
        if isinstance(message, dict) and 'content' in message:
            return message['content'][0]['text']
        elif isinstance(message, str):
            return message
        return str(message)
    elif isinstance(response, dict):
        if 'content' in response and isinstance(response['content'], list):
            return response['content'][0].get('text', '')
        elif 'message' in response:
            return response['message']
        return str(response)
    return str(response)


def _parse_json_response(result_str: str) -> dict:
    json_start = result_str.find('{')
    json_end = result_str.rfind('}') + 1
    
    if json_start != -1 and json_end > json_start:
        json_str = result_str[json_start:json_end]
        return json.loads(json_str)
    return json.loads(result_str)


def _filter_candidates(candidates_raw: list, visited: list) -> list:
    candidates = []
    for cand in candidates_raw:
        cat = cand.get("category", "").upper().lower()
        conf = float(cand.get("confidence", 0.0))
        if cat not in visited:
            candidates.append((cat, conf))
    return sorted(candidates, key=lambda x: x[1], reverse=True)


def _find_alternative(selected_graph: str, candidates: list, visited: list) -> tuple:
    if selected_graph not in visited:
        return selected_graph, None
    
    print(f"[ROUTER] {selected_graph} ya visitado, buscando alternativa...")
    for alt_graph, alt_conf in candidates:
        if alt_graph not in visited:
            print(f"[ROUTER] Alternativa encontrada: {alt_graph} ({alt_conf:.2f})")
            return alt_graph, alt_conf
    
    print("[ROUTER] No hay alternativas disponibles")
    return None, None


async def advanced_router_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print("ADVANCED ROUTER")
    print(f"Pregunta: {state['question']}")
    
    if state.get("routing_done") and not state.get("needs_rerouting", False):
        print("[ROUTER] Ya clasificado, saltando...")
        return state
    
    visited = state.get("visited_graphs", [])
    max_hops = state.get("max_hops", 2)
    current_hop = len(visited)
    
    if state.get("needs_rerouting", False):
        print(f"[ROUTER] Re-routing (hop {current_hop}/{max_hops})")
        if current_hop >= max_hops:
            print(f"[ROUTER] Max hops alcanzado ({max_hops})")
            return {
                **state,
                "error": f"Max re-routing hops reached ({max_hops})",
                "needs_clarification": True,
                "clarification_message": f"I've tried {max_hops} different approaches but couldn't find a satisfactory answer. Could you rephrase your question?"
            }
    
    # Check cache first
    cache = get_router_cache()
    cached_decision = cache.get(state['question'], visited)
    
    if cached_decision:
        primary = cached_decision["selected_graph"]
        confidence = cached_decision["confidence"]
        candidates = cached_decision["candidates"]
    else:
        # Build context-aware prompt for re-routing
        question_context = state['question']
        if state.get("needs_rerouting", False) and visited:
            question_context = f"{state['question']}\n\nNote: Already tried {', '.join(visited).upper()} graph(s). Consider alternative categories."
        
        agent = Agent(model=MODEL_CLASSIFIER, system_prompt=ADVANCED_ROUTER_PROMPT)
        response = await agent.invoke_async(question_context)
        result_str = _extract_response(response)
        
        try:
            result = _parse_json_response(result_str)
            primary = result.get("primary", "COMMON").upper()
            confidence = float(result.get("confidence", 0.5))
            candidates_raw = result.get("candidates", [])
            candidates = _filter_candidates(candidates_raw, visited)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[ROUTER] Error parsing JSON, usando fallback: {e}")
            primary = "COMMON"
            confidence = 0.5
            candidates = [(primary.lower(), confidence)]
    
    selected_graph, alt_conf = _find_alternative(primary.lower(), candidates, visited)
    
    # If no alternative found and we're re-routing, try 'common' as fallback
    if not selected_graph:
        if state.get("needs_rerouting", False) and "common" not in visited:
            print("[ROUTER] No alternatives found, using 'common' as fallback")
            selected_graph = "common"
            alt_conf = 0.5
        else:
            # No alternatives and common already tried or not re-routing
            print("[ROUTER] No alternatives available, requesting clarification")
            return {
                **state,
                "error": "No alternative graphs available",
                "needs_clarification": True,
                "clarification_message": (
                    f"I'm having trouble understanding your question.\n\n"
                    f"Your question: \"{state['question']}\"\n\n"
                    f"I've tried analyzing it from different perspectives but couldn't find the right approach. "
                    f"Could you please rephrase your question or provide more specific details?"
                )
            }
    
    if alt_conf:
        confidence = alt_conf
    
    skip_validation = selected_graph not in GRAPHS_REQUIRING_VALIDATION
    
    # Domain graphs will handle missing params via supervisor
    use_parallel = should_use_parallel_execution(confidence, len(candidates))
    
    if use_parallel:
        if has_side_effects(state['question']):
            print("[ROUTER] SIDE-EFFECTS detected, forcing SINGLE_GRAPH")
            use_parallel = False
        elif not is_safe_to_parallelize(state['question'], candidates):
            print("[ROUTER] UNSAFE candidates, forcing SINGLE_GRAPH")
            use_parallel = False
        else:
            safe_candidates = filter_safe_candidates(candidates)
            if len(safe_candidates) < 2:
                print("[ROUTER] Insufficient SAFE candidates, forcing SINGLE_GRAPH")
                use_parallel = False
            else:
                candidates = safe_candidates
                print(f"[ROUTER] SAFE to parallelize ({len(candidates)} safe candidates)")
    
    parallel_k = get_parallel_budget(candidates) if use_parallel else 1
    
    logger = state.get("telemetry_logger")
    if logger:
        reason = []
        if use_parallel:
            reason.append("parallel (conf < tau)")
        else:
            reason.append("single (conf >= tau)")
        
        if has_side_effects(state['question']):
            reason.append("side-effects detected")
        
        log_router_decision(
            logger, state, selected_graph, confidence,
            candidates, use_parallel, parallel_k,
            reason=", ".join(reason)
        )
        
        if use_parallel:
            discarded = candidates[parallel_k:]
            for graph, score in discarded:
                log_candidate_discard(logger, graph, score, f"K budget exceeded (K={parallel_k})")
    
    print(f"[ROUTER] Grafo seleccionado: {selected_graph}")
    print(f"[ROUTER] Confidence: {confidence:.2f} (tau={CONFIDENCE_THRESHOLD})")
    print(f"[ROUTER] Candidatos: {len(candidates)}")
    
    if use_parallel:
        print(f"[ROUTER] Modo: PARALLEL (K={parallel_k}/{MAX_PARALLEL_CANDIDATES})")
        print(f"[ROUTER] Ejecutando: {[c[0] for c in candidates[:parallel_k]]}")
    else:
        print(f"[ROUTER] Modo: SINGLE (conf >= tau)")
    
    if skip_validation:
        print("[ROUTER] Validacion no requerida")
    print("="*80 + "\n")
    
    new_visited = visited + [selected_graph]
    
    if state.get("needs_rerouting") and logger:
        previous = state.get("previous_graph", "unknown")
        log_rerouting(logger, previous, selected_graph, len(new_visited), "not_my_scope")
    
    # Cache the decision for future similar queries
    if not cached_decision:
        cache.set(state['question'], visited, selected_graph, confidence, candidates)
    
    return {
        **state,
        "selected_graph": selected_graph,
        "routing_done": True,
        "routing_confidence": confidence,
        "routing_candidates": candidates,
        "visited_graphs": new_visited,
        "skip_validation": skip_validation,
        "needs_rerouting": False,
        "parallel_execution": use_parallel,
        "parallel_k": parallel_k
    }