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

MIN_CONFIDENCE_NO_CLARIFICATION = 0.50

GRAPHS_REQUIRING_VALIDATION = ["talent", "content", "business", "platform"]


def should_use_parallel_execution(confidence: float, num_candidates: int) -> bool:
    return confidence < CONFIDENCE_THRESHOLD and num_candidates >= 2


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
        score1, score2 = valid_candidates[0][1], valid_candidates[1][1]
        if score2 < score1 - SCORE_GAP:
            k = 1
    
    return k


def has_side_effects(question: str) -> bool:
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in SIDE_EFFECT_KEYWORDS)


def is_safe_to_parallelize(question: str, candidates: list) -> bool:
    if has_side_effects(question):
        return False
    
    if any(graph_name in UNSAFE_PARALLEL_GRAPHS for graph_name, _ in candidates):
        return False
    
    return any(g in SAFE_PARALLEL_GRAPHS for g, _ in candidates)


def filter_safe_candidates(candidates: list) -> list:
    return [(graph, score) for graph, score in candidates if graph in SAFE_PARALLEL_GRAPHS]