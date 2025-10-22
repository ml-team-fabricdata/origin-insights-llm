# test_llm.py

def test_model(prompt: str):
    # Lazy imports para no romper en contextos donde boto3/bedrock no están disponibles
    from infra.bedrock import call_bedrock_llm1, call_bedrock_llm2

    print("\n=== Haiku (rápido) ===")
    response1 = call_bedrock_llm1(prompt)
    print(response1.get("completion", "[sin respuesta]"))

    print("\n=== Sonnet (smart) ===")
    response2 = call_bedrock_llm2(prompt)
    print(response2.get("completion", "[sin respuesta]"))

if __name__ == "__main__":
    # solo prueba
    prompt = "donde puedo ver stranger things?"
    test_model(prompt)