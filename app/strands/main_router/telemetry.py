import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from .state import MainRouterState


class TelemetryLogger:
    
    def __init__(self, log_to_file: bool = True, log_dir: str = "./telemetry_logs"):
        self.log_to_file = log_to_file
        self.log_dir = Path(log_dir)
        if log_to_file:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.start_time = time.time()
        self.events = []
    
    def log_event(self, event_type: str, data: Dict[str, Any]):
        event = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_time": time.time() - self.start_time,
            "event_type": event_type,
            "data": data
        }
        self.events.append(event)
        self._print_event(event)
    
    def _print_event(self, event: Dict):
        elapsed = event["elapsed_time"]
        event_type = event["event_type"]
        print(f"[{elapsed:6.2f}s] {event_type}")
    
    def save_to_file(self, state: MainRouterState):
        if not self.log_to_file:
            return
        
        filename = self.log_dir / f"telemetry_{self.session_id}.json"
        
        # Obtener answer - mantener estructura JSON si existe
        answer = state.get("answer", "")
        
        # Si answer es un dict (JSON estructurado), guardarlo completo
        if isinstance(answer, dict):
            final_answer = answer
        else:
            # Si es string, truncar para preview
            answer_str = str(answer) if not isinstance(answer, str) else answer
            final_answer = answer_str[:200] if len(answer_str) > 200 else answer_str
        
        telemetry_data = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "total_time": time.time() - self.start_time,
            "question": state.get("question", ""),
            "final_answer": final_answer,
            "route_summary": self._build_route_summary(state),
            "events": self.events,
            "tool_execution_times": state.get("tool_execution_times", {}),
            "final_state": {
                "selected_graph": state.get("selected_graph"),
                "routing_confidence": state.get("routing_confidence"),
                "visited_graphs": state.get("visited_graphs", []),
                "parallel_execution": state.get("parallel_execution"),
                "parallel_k": state.get("parallel_k"),
                "needs_clarification": state.get("needs_clarification"),
                "schema_valid": state.get("schema_valid")
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(telemetry_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nTelemetry saved to: {filename}")
    
    def _build_route_summary(self, state: MainRouterState) -> Dict:
        return {
            "visited_graphs": state.get("visited_graphs", []),
            "total_hops": len(state.get("visited_graphs", [])),
            "parallel_executed": state.get("parallel_execution", False),
            "parallel_k": state.get("parallel_k", 1),
            "final_graph": state.get("selected_graph")
        }


def log_router_decision(
    logger: TelemetryLogger,
    state: MainRouterState,
    selected_graph: str,
    confidence: float,
    candidates: List,
    use_parallel: bool,
    parallel_k: int,
    reason: str = ""
):
    logger.log_event("ROUTER_DECISION", {
        "selected_graph": selected_graph,
        "confidence": confidence,
        "candidates": [(g, round(c, 2)) for g, c in candidates],
        "num_candidates": len(candidates),
        "use_parallel": use_parallel,
        "parallel_k": parallel_k,
        "reason": reason,
        "visited_graphs": state.get("visited_graphs", [])
    })


def log_parallel_execution(logger: TelemetryLogger, candidates: List, k: int, safe_only: bool = False):
    logger.log_event("PARALLEL_EXECUTION", {
        "candidates": [(g, round(c, 2)) for g, c in candidates[:k]],
        "k": k,
        "safe_only": safe_only
    })


def log_candidate_discard(logger: TelemetryLogger, graph_name: str, score: float, reason: str):
    logger.log_event("CANDIDATE_DISCARD", {
        "graph": graph_name,
        "score": round(score, 2),
        "reason": reason
    })


def log_validation(logger: TelemetryLogger, status: str, entities: Optional[Dict] = None, skipped: bool = False):
    logger.log_event("VALIDATION", {
        "status": status,
        "skipped": skipped,
        "entities": list(entities.keys()) if entities else []
    })


def log_rerouting(logger: TelemetryLogger, from_graph: str, to_graph: str, hop_number: int, reason: str):
    logger.log_event("REROUTING", {
        "from_graph": from_graph,
        "to_graph": to_graph,
        "hop_number": hop_number,
        "reason": reason
    })


def log_clarification(logger: TelemetryLogger, missing_params: List[str], reason: str):
    logger.log_event("CLARIFICATION", {
        "missing_params": missing_params,
        "reason": reason
    })


def print_telemetry_summary(logger: TelemetryLogger, state: MainRouterState):
    print("\n" + "="*80)
    print("TELEMETRY SUMMARY")
    print("="*80)
    
    visited = state.get("visited_graphs", [])
    print("\nRoute Taken:")
    if visited:
        route = " -> ".join(visited)
        print(f"   {route}")
    else:
        print(f"   {state.get('selected_graph', 'N/A')}")
    
    if state.get("parallel_execution"):
        print("\nParallel Execution:")
        print(f"   K = {state.get('parallel_k', 1)} candidates")
        candidates = state.get("routing_candidates", [])[:state.get("parallel_k", 1)]
        for graph, score in candidates:
            print(f"   - {graph} (score: {score:.2f})")
    
    discard_events = [e for e in logger.events if e["event_type"] == "CANDIDATE_DISCARD"]
    if discard_events:
        print("\nDiscarded Candidates:")
        for event in discard_events:
            data = event["data"]
            print(f"   - {data['graph']} (score: {data['score']}) - {data['reason']}")
    
    rerouting_events = [e for e in logger.events if e["event_type"] == "REROUTING"]
    if rerouting_events:
        print(f"\nRe-routings: {len(rerouting_events)}")
        for event in rerouting_events:
            data = event["data"]
            print(f"   Hop {data['hop_number']}: {data['from_graph']} -> {data['to_graph']}")
            print(f"   Reason: {data['reason']}")
    
    tool_times = state.get("tool_execution_times", {})
    if tool_times:
        print("\nTool Execution Times:")
        for tool, time_val in sorted(tool_times.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {tool}: {time_val:.2f}s")
    
    print("\nFinal Status:")
    print(f"   Graph: {state.get('selected_graph', 'N/A')}")
    print(f"   Confidence: {state.get('routing_confidence', 0):.2f}")
    print(f"   Schema Valid: {state.get('schema_valid', False)}")
    print(f"   Needs Clarification: {state.get('needs_clarification', False)}")
    
    print("="*80 + "\n")