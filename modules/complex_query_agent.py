def run(query: str, model: str = "sonnet") -> dict:
    return {
        "type": "complex_query",
        "query": query,
        "data": f"Respuesta generada por LLM ({model})"
    }