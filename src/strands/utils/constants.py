"""
Constants used across the strands codebase.

Eliminates magic strings and numbers.
"""

# ============================================================================
# SEPARATORS
# ============================================================================

SEPARATOR_LINE = "=" * 80
SEPARATOR_SHORT = "-" * 40
SEPARATOR_DOUBLE = "=" * 100


# ============================================================================
# STATE KEYS
# ============================================================================

# Main state keys
STATE_KEY_QUESTION = "question"
STATE_KEY_ANSWER = "answer"
STATE_KEY_ERROR = "error"

# Routing keys
STATE_KEY_SELECTED_GRAPH = "selected_graph"
STATE_KEY_ROUTING_DONE = "routing_done"
STATE_KEY_NEEDS_REROUTING = "needs_rerouting"
STATE_KEY_PREVIOUS_GRAPH = "previous_graph"
STATE_KEY_REROUTING_COUNT = "rerouting_count"

# Validation keys
STATE_KEY_VALIDATION_DONE = "validation_done"
STATE_KEY_VALIDATED_ENTITIES = "validated_entities"
STATE_KEY_NEEDS_VALIDATION = "needs_validation"
STATE_KEY_NEEDS_USER_INPUT = "needs_user_input"
STATE_KEY_VALIDATION_MESSAGE = "validation_message"

# Execution keys
STATE_KEY_TASK = "task"
STATE_KEY_TOOL_CALLS_COUNT = "tool_calls_count"
STATE_KEY_ACCUMULATED_DATA = "accumulated_data"
STATE_KEY_LAST_NODE = "last_node"
STATE_KEY_CLASSIFICATION_DONE = "classification_done"


# ============================================================================
# VALIDATED ENTITY KEYS
# ============================================================================

ENTITY_KEY_DIRECTOR_ID = "director_id"
ENTITY_KEY_ACTOR_ID = "actor_id"
ENTITY_KEY_TITLE_UID = "title_uid"
ENTITY_KEY_RAW_VALIDATION = "raw_validation"
ENTITY_KEY_HAS_VALID_ENTITIES = "has_valid_entities"


# ============================================================================
# LOGGING MARKERS (removed emojis for cleaner logs)
# ============================================================================

MARKER_NODE = "[NODE]"
MARKER_QUESTION = "[QUESTION]"
MARKER_ROUTING = "[ROUTING]"
MARKER_SUCCESS = "[SUCCESS]"
MARKER_ERROR = "[ERROR]"
MARKER_WARNING = "[WARNING]"
MARKER_ROBOT = "[AGENT]"
MARKER_DATA = "[DATA]"
MARKER_PREVIEW = "[PREVIEW]"
MARKER_STATS = "[STATS]"
MARKER_SEARCH = "[SEARCH]"
MARKER_VALIDATION = "[VALIDATED]"


# ============================================================================
# GRAPH NAMES
# ============================================================================

GRAPH_BUSINESS = "business"
GRAPH_TALENT = "talent"
GRAPH_CONTENT = "content"
GRAPH_PLATFORM = "platform"
GRAPH_COMMON = "common"

GRAPH_NODE_SUFFIX = "_graph"

# Map graph names to node names
GRAPH_TO_NODE = {
    GRAPH_BUSINESS: f"{GRAPH_BUSINESS}{GRAPH_NODE_SUFFIX}",
    GRAPH_TALENT: f"{GRAPH_TALENT}{GRAPH_NODE_SUFFIX}",
    GRAPH_CONTENT: f"{GRAPH_CONTENT}{GRAPH_NODE_SUFFIX}",
    GRAPH_PLATFORM: f"{GRAPH_PLATFORM}{GRAPH_NODE_SUFFIX}",
    GRAPH_COMMON: f"{GRAPH_COMMON}{GRAPH_NODE_SUFFIX}",
}


# ============================================================================
# TASK NAMES
# ============================================================================

TASK_ACTORS = "actors"
TASK_DIRECTORS = "directors"
TASK_COLLABORATIONS = "collaborations"

TASK_METADATA = "metadata"
TASK_DISCOVERY = "discovery"

TASK_AVAILABILITY = "availability"
TASK_PRESENCE = "presence"

TASK_PRICING = "pricing"
TASK_RANKINGS = "rankings"
TASK_INTELLIGENCE = "intelligence"


# ============================================================================
# VALIDATION STATUSES
# ============================================================================

VALIDATION_STATUS_VALIDATED = "validated"
VALIDATION_STATUS_AMBIGUOUS = "ambiguous"
VALIDATION_STATUS_NOT_NEEDED = "not_needed"
VALIDATION_STATUS_ERROR = "error"


# ============================================================================
# SUPERVISOR DECISIONS
# ============================================================================

DECISION_COMPLETE = "COMPLETO"
DECISION_CONTINUE = "CONTINUAR"
DECISION_CLASSIFY = "NECESITA_CLASIFICACION"


# ============================================================================
# LOGGING PREFIXES
# ============================================================================

LOG_PREFIX_ROUTER = "[ROUTER]"
LOG_PREFIX_VALIDATION = "[VALIDATION]"
LOG_PREFIX_SUPERVISOR = "[SUPERVISOR]"
LOG_PREFIX_CLASSIFIER = "[CLASSIFIER]"


# ============================================================================
# LIMITS
# ============================================================================

MIN_DATA_LENGTH = 50  # Minimum characters to consider valid data
DEFAULT_MAX_ITERATIONS = 3
DEFAULT_TOOL_LIMIT = 20  # Default limit for tool queries
MAX_REROUTING_COUNT = 3  # Maximum number of re-routings allowed


# ============================================================================
# REGEX PATTERNS (for validation extraction)
# ============================================================================

PATTERN_DIRECTOR_ID = r'director.*?ID:\s*(\d+)'
PATTERN_ACTOR_ID = r'actor.*?ID:\s*(\d+)'
PATTERN_TITLE_UID = r'título.*?UID:\s*(\d+)'
PATTERN_TITLE_UID_EN = r'title.*?UID:\s*(\d+)'

# All ID patterns
ID_PATTERNS = [
    (PATTERN_DIRECTOR_ID, ENTITY_KEY_DIRECTOR_ID),
    (PATTERN_ACTOR_ID, ENTITY_KEY_ACTOR_ID),
    (PATTERN_TITLE_UID, ENTITY_KEY_TITLE_UID),
    (PATTERN_TITLE_UID_EN, ENTITY_KEY_TITLE_UID),
]
