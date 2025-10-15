import json
from strands import Agent
from src.strands.utils.config import MODEL_CLASSIFIER
from .state import MainRouterState
from .prompts import ADVANCED_ROUTER_PROMPT


GRAPHS_REQUIRING_VALIDATION = {"talent", "content"}


async def advanced_router_node(state: MainRouterState) -> MainRouterState:
    print("\n" + "="*80)
    print("🎯 ADVANCED ROUTER")
    print("="*80)
    print(f"📝 Pregunta: {state['question']}")
    
    if state.get("routing_done") and not state.get("needs_rerouting", False):
        print("[ROUTER] Ya clasificado, saltando...")
        return state
    
    visited = state.get("visited_graphs", [])
    max_hops = state.get("max_hops", 2)
    current_hop = len(visited)
    
    if state.get("needs_rerouting", False):
        print(f"[ROUTER] 🔄 Re-routing (hop {current_hop}/{max_hops})")
        if current_hop >= max_hops:
            print(f"[ROUTER] ❌ Max hops alcanzado ({max_hops})")
            return {
                **state,
                "error": f"Max re-routing hops reached ({max_hops})",
                "needs_clarification": True,
                "clarification_message": f"I've tried {max_hops} different approaches but couldn't find a satisfactory answer. Could you rephrase your question?"
            }
    
    agent = Agent(
        model=MODEL_CLASSIFIER,
        system_prompt=ADVANCED_ROUTER_PROMPT
    )
    
    response = await agent.invoke_async(state['question'])
    
    if hasattr(response, 'message'):
        message = response.message
        if isinstance(message, dict) and 'content' in message:
            result_str = message['content'][0]['text']
        elif isinstance(message, str):
            result_str = message
        else:
            result_str = str(message)
    elif isinstance(response, dict):
        if 'content' in response and isinstance(response['content'], list):
            result_str = response['content'][0].get('text', '')
        elif 'message' in response:
            result_str = response['message']
        else:
            result_str = str(response)
    else:
        result_str = str(response)
    
    try:
        json_start = result_str.find('{')
        json_end = result_str.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            json_str = result_str[json_start:json_end]
            result = json.loads(json_str)
        else:
            result = json.loads(result_str)
        primary = result.get("primary", "COMMON").upper()
        confidence = float(result.get("confidence", 0.5))
        candidates_raw = result.get("candidates", [])
        
        candidates = []
        for cand in candidates_raw:
            cat = cand.get("category", "").upper().lower()
            conf = float(cand.get("confidence", 0.0))
            if cat not in visited:
                candidates.append((cat, conf))
        
        candidates = sorted(candidates, key=lambda x: x[1], reverse=True)
        
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[ROUTER] ⚠️ Error parsing JSON, usando fallback: {e}")
        primary = "COMMON"
        confidence = 0.5
        candidates = [(primary.lower(), confidence)]
    
    selected_graph = primary.lower()
    
    if selected_graph in visited:
        print(f"[ROUTER] ⚠️ {selected_graph} ya visitado, buscando alternativa...")
        for alt_graph, alt_conf in candidates:
            if alt_graph not in visited:
                selected_graph = alt_graph
                confidence = alt_conf
                print(f"[ROUTER] ✅ Alternativa encontrada: {selected_graph} ({alt_conf:.2f})")
                break
        else:
            print(f"[ROUTER] ❌ No hay alternativas disponibles")
            return {
                **state,
                "error": "No alternative graphs available",
                "needs_clarification": True
            }
    
    skip_validation = selected_graph not in GRAPHS_REQUIRING_VALIDATION
    
    print(f"[ROUTER] ✅ Grafo seleccionado: {selected_graph}")
    print(f"[ROUTER] 📊 Confidence: {confidence:.2f}")
    print(f"[ROUTER] 🔢 Candidatos: {len(candidates)}")
    if skip_validation:
        print(f"[ROUTER] ⏭️  Validación no requerida")
    print("="*80 + "\n")
    
    new_visited = visited + [selected_graph]
    
    return {
        **state,
        "selected_graph": selected_graph,
        "routing_done": True,
        "routing_confidence": confidence,
        "routing_candidates": candidates,
        "visited_graphs": new_visited,
        "skip_validation": skip_validation,
        "needs_rerouting": False
    }
