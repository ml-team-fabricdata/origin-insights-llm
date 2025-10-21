CONFIDENCE_THRESHOLD = 0.75
MAX_PARALLEL_CANDIDATES = 3
MIN_CANDIDATE_SCORE = 0.50
SCORE_GAP = 0.10

SAFE_PARALLEL_GRAPHS = {"talent", "content", "common"}
UNSAFE_PARALLEL_GRAPHS = {"business", "platform"}

SIDE_EFFECT_KEYWORDS = [
    "create", "insert", "update", "delete", "modify", "change",
    "add", "remove", "set", "write", "save", "store",
    "register", "unregister", "subscribe", "unsubscribe"
]

READ_ONLY_KEYWORDS = [
    "get", "fetch", "retrieve", "find", "search", "query",
    "list", "show", "display", "view", "read", "count",
    "who", "what", "when", "where", "how many", "which"
]

GRAPHS_REQUIRING_VALIDATION = ["talent", "content"]
VALIDATION_TIMEOUT = 3.0

EARLY_STOP_THRESHOLD = 0.85
TOOL_TIMEOUT = 2.0
BUDGET_TOOLS_PER_TURN = 6

DOMAIN_CONFIDENCE_THRESHOLDS = {
    "talent": 0.75,
    "platform": 0.70,
    "business": 0.70,
    "content": 0.68,
    "common": 0.50
}

COMMON_GRAPH_PENALTY = 0.15

MAX_HOPS = 3
MAX_VISITED_GRAPHS = 5

MIN_CONFIDENCE_NO_CLARIFICATION = 0.50
MAX_CLARIFICATION_FIELDS = 2

MIN_ANSWER_LENGTH = 50
MAX_ANSWER_LENGTH = 5000


def should_use_parallel_execution(confidence: float, num_candidates: int) -> bool:
    if confidence >= CONFIDENCE_THRESHOLD:
        return False
    if num_candidates < 2:
        return False
    return True


def get_parallel_budget(candidates: list) -> int:
    if not candidates:
        return 1
    
    valid_candidates = [
        (name, score) for name, score in candidates
        if score >= MIN_CANDIDATE_SCORE
    ]
    
    if not valid_candidates:
        return 1
    
    k = min(len(valid_candidates), MAX_PARALLEL_CANDIDATES)
    
    if k == 2 and len(valid_candidates) >= 2:
        score1 = valid_candidates[0][1]
        score2 = valid_candidates[1][1]
        
        if score2 < score1 - SCORE_GAP:
            k = 1
    
    return k


def get_domain_threshold(domain: str) -> float:
    return DOMAIN_CONFIDENCE_THRESHOLDS.get(domain, 0.60)


def is_common_graph_winner(selected_graph: str, confidence: float, other_scores: dict) -> bool:
    if selected_graph != "common":
        return True
    
    for graph, score in other_scores.items():
        if graph != "common" and score > DOMAIN_CONFIDENCE_THRESHOLDS.get(graph, 0.60):
            return False
    
    return True


def has_side_effects(question: str) -> bool:
    question_lower = question.lower()
    
    for keyword in SIDE_EFFECT_KEYWORDS:
        if keyword in question_lower:
            return True
    
    return False


def is_read_only_operation(question: str) -> bool:
    question_lower = question.lower()
    
    for keyword in READ_ONLY_KEYWORDS:
        if keyword in question_lower:
            return True
    
    return not has_side_effects(question)


def is_safe_to_parallelize(question: str, candidates: list) -> bool:
    if has_side_effects(question):
        return False
    
    for graph_name, _ in candidates:
        if graph_name in UNSAFE_PARALLEL_GRAPHS:
            return False
    
    safe_candidates = [g for g, _ in candidates if g in SAFE_PARALLEL_GRAPHS]
    if not safe_candidates:
        return False
    
    return True


def filter_safe_candidates(candidates: list) -> list:
    return [(graph, score) for graph, score in candidates 
            if graph in SAFE_PARALLEL_GRAPHS]