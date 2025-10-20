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
        
        telemetry_data = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "total_time": time.time() - self.start_time,
            "question": state.get("question", ""),
            "final_answer": state.get("answer", "")[:200],
            "route_summary": self._build_route_summary(state),
            "events": self.events,
            "budget_status": state.get("budget_status", {}),
            "final_state": {
                "selected_graph": state.get("selected_graph"),
                "routing_confidence": state.get("routing_confidence"),
                "visited_graphs": state.get("visited_graphs", []),
                "parallel_execution": state.get("parallel_execution"),
                "parallel_k": state.get("parallel_k"),
                "needs_clarification": state.get("needs_clarification"),
                "budget_exhausted": state.get("budget_exhausted"),
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


def log_budget_exhausted(logger: TelemetryLogger, reason: str, elapsed_time: float, tokens_used: int):
    logger.log_event("BUDGET_EXHAUSTED", {
        "reason": reason,
        "elapsed_time": round(elapsed_time, 2),
        "tokens_used": tokens_used
    })


def log_schema_validation(logger: TelemetryLogger, valid: bool, errors: List[str], warnings: List[str]):
    logger.log_event("SCHEMA_VALIDATION", {
        "valid": valid,
        "errors": errors,
        "warnings": warnings
    })


def log_node_execution(logger: TelemetryLogger, node_name: str, execution_time: float, tokens_used: int, status: str = "success"):
    logger.log_event("NODE_EXECUTION", {
        "node": node_name,
        "execution_time": round(execution_time, 2),
        "tokens_used": tokens_used,
        "status": status
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
    
    budget_status = state.get("budget_status", {})
    print("\nExecution Times:")
    print(f"   Total: {budget_status.get('elapsed_time', 0):.2f}s")
    
    node_times = budget_status.get("node_execution_times", {})
    if node_times:
        print("   By node:")
        for node, time_val in sorted(node_times.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {node}: {time_val:.2f}s")
    
    print("\nToken Usage:")
    print(f"   Total: {budget_status.get('total_tokens_used', 0)}")
    
    node_tokens = budget_status.get("node_token_usage", {})
    if node_tokens:
        print("   By node:")
        for node, tokens in sorted(node_tokens.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {node}: {tokens}")
    
    print("\nFinal Status:")
    print(f"   Graph: {state.get('selected_graph', 'N/A')}")
    print(f"   Confidence: {state.get('routing_confidence', 0):.2f}")
    print(f"   Schema Valid: {state.get('schema_valid', False)}")
    print(f"   Budget Exhausted: {state.get('budget_exhausted', False)}")
    print(f"   Needs Clarification: {state.get('needs_clarification', False)}")
    
    print("="*80 + "\n")


def analyze_telemetry_file(filepath: str):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("\n" + "="*80)
    print(f"TELEMETRY ANALYSIS: {filepath}")
    print("="*80)
    
    print(f"\nQuestion: {data['question']}")
    print(f"Total Time: {data['total_time']:.2f}s")
    
    route = data['route_summary']
    print(f"\nRoute: {' -> '.join(route['visited_graphs'])}")
    print(f"   Total Hops: {route['total_hops']}")
    print(f"   Parallel: {route['parallel_executed']} (K={route['parallel_k']})")
    
    events_by_type = {}
    for event in data['events']:
        event_type = event['event_type']
        events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
    
    print("\nEvents:")
    for event_type, count in sorted(events_by_type.items()):
        print(f"   {event_type}: {count}")
    
    print("="*80 + "\n")