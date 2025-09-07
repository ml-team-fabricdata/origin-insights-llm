from modules import (
    metadata_query,
    popularity_query,
    comparison_query,
    kb_query,
    complex_query_agent,
    response_formatter,
)

# --- Clasificadores heurísticos ---
def is_metadata_query(query: str) -> bool:
    return "título" in query.lower() or "title" in query.lower()

def is_popularity_query(query: str) -> bool:
    return "popularidad" in query.lower() or "hits" in query.lower()

def is_comparison_query(query: str) -> bool:
    return "vs" in query.lower() or "comparar" in query.lower()

def is_kb_query(query: str) -> bool:
    return "sabías que" in query.lower() or "curiosidad" in query.lower()

def is_complex_query(query: str) -> bool:
    return any(kw in query.lower() for kw in ["cuántos", "ranking", "mayor", "menor", "más visto", "menos"])

# --- Supervisor ---
def handle_query(query: str) -> dict:
    if is_metadata_query(query):
        result = metadata_query.run(query)
        node = "metadata"

    elif is_popularity_query(query):
        result = popularity_query.run(query)
        node = "popularity"

    elif is_comparison_query(query):
        result = comparison_query.run(query)
        node = "comparison"

    elif is_kb_query(query):
        result = kb_query.run(query)
        node = "kb"

    elif is_complex_query(query):
        # Sonnet (lazy import aquí)
        from infra.bedrock import call_bedrock_llm2
        llm_response = call_bedrock_llm2(query)
        result = {"output": llm_response.get("completion", "[sin respuesta]")}
        node = "llm_sonnet"

    else:
        # Haiku (lazy import aquí)
        from infra.bedrock import call_bedrock_llm1
        llm_response = call_bedrock_llm1(query)
        result = {"output": llm_response.get("completion", "[sin respuesta]")}
        node = "llm_haiku"

    result["metadata"] = {"node_used": node}
    return response_formatter.format(result)