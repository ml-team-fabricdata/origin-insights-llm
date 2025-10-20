import time
from typing import Dict, Optional, Tuple
from .state import MainRouterState
from .config import (
    TIME_BUDGET_PER_TURN,
    TOKEN_BUDGET_PER_TURN,
    NODE_TIME_LIMITS,
    NODE_TOKEN_LIMITS,
    BUDGET_EXHAUSTED_ACTION,
    TIMEOUT_MESSAGE,
    TOKEN_LIMIT_MESSAGE,
    MAX_HOPS
)


class BudgetManager:
    
    def __init__(self):
        self.start_time = time.time()
        self.total_tokens_used = 0
        self.node_execution_times = {}
        self.node_token_usage = {}
    
    def get_elapsed_time(self) -> float:
        return time.time() - self.start_time
    
    def get_remaining_time(self) -> float:
        return TIME_BUDGET_PER_TURN - self.get_elapsed_time()
    
    def get_remaining_tokens(self) -> int:
        return TOKEN_BUDGET_PER_TURN - self.total_tokens_used
    
    def is_time_budget_exhausted(self) -> bool:
        return self.get_elapsed_time() >= TIME_BUDGET_PER_TURN
    
    def is_token_budget_exhausted(self) -> bool:
        return self.total_tokens_used >= TOKEN_BUDGET_PER_TURN
    
    def is_budget_exhausted(self) -> bool:
        return self.is_time_budget_exhausted() or self.is_token_budget_exhausted()
    
    def record_node_execution(self, node_name: str, execution_time: float, tokens_used: int):
        self.node_execution_times[node_name] = execution_time
        self.node_token_usage[node_name] = tokens_used
        self.total_tokens_used += tokens_used
    
    def check_node_limits(self, node_name: str, execution_time: float, tokens_used: int) -> Tuple[bool, Optional[str]]:
        time_limit = NODE_TIME_LIMITS.get(node_name, 10.0)
        token_limit = NODE_TOKEN_LIMITS.get(node_name, 1000)
        
        if execution_time > time_limit:
            return True, f"Node '{node_name}' exceeded time limit ({execution_time:.2f}s > {time_limit}s)"
        
        if tokens_used > token_limit:
            return True, f"Node '{node_name}' exceeded token limit ({tokens_used} > {token_limit})"
        
        return False, None
    
    def get_budget_status(self) -> Dict:
        return {
            "elapsed_time": self.get_elapsed_time(),
            "remaining_time": self.get_remaining_time(),
            "total_tokens_used": self.total_tokens_used,
            "remaining_tokens": self.get_remaining_tokens(),
            "time_budget_exhausted": self.is_time_budget_exhausted(),
            "token_budget_exhausted": self.is_token_budget_exhausted(),
            "node_execution_times": self.node_execution_times,
            "node_token_usage": self.node_token_usage
        }
    
    def print_budget_status(self):
        status = self.get_budget_status()
        print(f"\n{'='*80}")
        print("BUDGET STATUS")
        print(f"{'='*80}")
        print(f"Time: {status['elapsed_time']:.2f}s / {TIME_BUDGET_PER_TURN}s (remaining: {status['remaining_time']:.2f}s)")
        print(f"Tokens: {status['total_tokens_used']} / {TOKEN_BUDGET_PER_TURN} (remaining: {status['remaining_tokens']})")
        
        if status['time_budget_exhausted']:
            print("TIME BUDGET EXHAUSTED!")
        if status['token_budget_exhausted']:
            print("TOKEN BUDGET EXHAUSTED!")
        
        print(f"{'='*80}\n")


def check_budget_before_node(state: MainRouterState, node_name: str) -> Tuple[bool, Optional[str]]:
    budget_status = state.get("budget_status", {})
    elapsed_time = budget_status.get("elapsed_time", 0)
    total_tokens = budget_status.get("total_tokens_used", 0)
    
    if elapsed_time >= TIME_BUDGET_PER_TURN:
        return False, TIMEOUT_MESSAGE
    
    if total_tokens >= TOKEN_BUDGET_PER_TURN:
        return False, TOKEN_LIMIT_MESSAGE
    
    visited_graphs = state.get("visited_graphs", [])
    if len(visited_graphs) > MAX_HOPS:
        return False, (
            f"Max Hops Exceeded\n\n"
            f"The request exceeded the maximum number of re-routings ({MAX_HOPS}).\n\n"
            f"Visited graphs: {', '.join(visited_graphs)}\n\n"
            f"Please try a more specific question."
        )
    
    return True, None


def update_budget_in_state(state: MainRouterState, budget_manager: BudgetManager) -> MainRouterState:
    return {
        **state,
        "budget_status": budget_manager.get_budget_status()
    }


def create_budget_exhausted_state(state: MainRouterState, reason: str) -> MainRouterState:
    action = BUDGET_EXHAUSTED_ACTION
    
    if action == "clarifier":
        return {
            **state,
            "answer": reason,
            "needs_clarification": True,
            "needs_user_input": True,
            "budget_exhausted": True,
            "budget_exhausted_reason": "timeout" if "Timeout" in reason else "tokens"
        }
    else:
        return {
            **state,
            "answer": reason,
            "error": reason,
            "budget_exhausted": True,
            "budget_exhausted_reason": "timeout" if "Timeout" in reason else "tokens"
        }


def should_cut_execution(state: MainRouterState) -> Tuple[bool, Optional[str]]:
    budget_status = state.get("budget_status", {})
    
    if budget_status.get("time_budget_exhausted"):
        return True, TIMEOUT_MESSAGE
    
    if budget_status.get("token_budget_exhausted"):
        return True, TOKEN_LIMIT_MESSAGE
    
    visited_graphs = state.get("visited_graphs", [])
    if len(visited_graphs) > MAX_HOPS:
        return True, (
            f"Max Hops Exceeded\n\n"
            f"Exceeded maximum re-routings ({MAX_HOPS}).\n"
            f"Visited: {', '.join(visited_graphs)}"
        )
    
    return False, None


def with_budget_check(node_func):
    async def wrapper(state: MainRouterState) -> MainRouterState:
        should_continue, error_msg = check_budget_before_node(state, node_func.__name__)
        
        if not should_continue:
            print(f"\n{'='*80}")
            print("BUDGET EXHAUSTED - Cutting execution")
            print(f"{'='*80}")
            print(f"Node: {node_func.__name__}")
            print(f"Reason: {error_msg[:100]}...")
            print(f"Action: {BUDGET_EXHAUSTED_ACTION}")
            print(f"{'='*80}\n")
            
            return create_budget_exhausted_state(state, error_msg)
        
        node_start_time = time.time()
        result = await node_func(state)
        node_execution_time = time.time() - node_start_time
        
        estimated_tokens = len(str(result.get("answer", ""))) // 4
        
        budget_status = state.get("budget_status", {
            "elapsed_time": 0,
            "total_tokens_used": 0,
            "node_execution_times": {},
            "node_token_usage": {}
        })
        
        budget_status["elapsed_time"] = budget_status.get("elapsed_time", 0) + node_execution_time
        budget_status["total_tokens_used"] = budget_status.get("total_tokens_used", 0) + estimated_tokens
        budget_status["node_execution_times"][node_func.__name__] = node_execution_time
        budget_status["node_token_usage"][node_func.__name__] = estimated_tokens
        
        result["budget_status"] = budget_status
        
        return result
    
    return wrapper