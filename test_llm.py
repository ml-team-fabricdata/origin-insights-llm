# test_llm.py
from infra.bedrock import call_bedrock_llm1, call_bedrock_llm2

def test_model(prompt: str):
    print("\n=== Haiku (rápido) ===")
    response1 = call_bedrock_llm1(prompt)
    print(response1.get("completion", "[sin respuesta]"))

    print("\n=== Sonnet (smart) ===")
    response2 = call_bedrock_llm2(prompt)
    print(response2.get("completion", "[sin respuesta]"))

if __name__ == "__main__":
    # 🔁 Podés cambiar este prompt para hacer tests rápidos
    prompt = "¿Cuál fue la película más vista en Argentina durante el último mes?"
    test_model(prompt)