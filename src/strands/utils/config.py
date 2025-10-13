# config.py - Configuración centralizada del módulo platform

# Modelos
MODEL_CLASSIFIER = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
MODEL_SUPERVISOR = "us.meta.llama3-3-70b-instruct-v1:0"
MODEL_NODE_EXECUTOR = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
MODEL_FORMATTER = "us.anthropic.claude-3-5-haiku-20241022-v1:0"

# Configuración del grafo
DEFAULT_MAX_ITERATIONS = 3
MIN_DATA_LENGTH = 50  # Mínimo de caracteres para considerar datos válidos

# Tareas disponibles
TASK_AVAILABILITY = "availability"
TASK_PRESENCE = "presence"
TASK_BUSINESS = "business"
TASK_TALENT = "talent"
TASK_CONTENT = "content"
TASK_ADMIN = "admin"

# Nodos del grafo
NODE_SUPERVISOR = "main_supervisor"
NODE_CLASSIFIER = "platform_node"
NODE_AVAILABILITY = "availability_node"
NODE_PRESENCE = "presence_node"
NODE_FORMATTER = "format_response"
NODE_BUSINESS = "business_node"
NODE_TALENT = "talent_node"
NODE_CONTENT = "content_node"
NODE_ADMIN = "admin_node"

# Decisiones del supervisor
DECISION_CLASSIFY = "NECESITA_CLASIFICACION"
DECISION_COMPLETE = "COMPLETO"
