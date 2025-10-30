import requests
import json

url = "http://localhost:8000/strand/ask"

print("=" * 80)
print("TEST: JSON Response Format")
print("=" * 80)

# Test con pregunta simple
response = requests.post(url, json={
    "question": "películas de Francis Ford Coppola",
    "thread_id": "test-json-001"
})

print(f"\nStatus Code: {response.status_code}")
print("\nResponse JSON:")
print("=" * 80)
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
print("=" * 80)

# Verificar estructura
data = response.json()
print("\n✅ Verificación de estructura:")
print(f"  - ok: {data.get('ok')}")
print(f"  - thread_id: {data.get('thread_id')}")
print(f"  - response presente: {'response' in data}")
print(f"  - selected_graph: {data.get('selected_graph')}")
print(f"  - domain_status: {data.get('domain_status')}")
print(f"  - pending_disambiguation: {data.get('pending_disambiguation')}")

if data.get("ok"):
    print("\n✅ Test PASSED - JSON estructurado retornado correctamente")
else:
    print(f"\n❌ Test FAILED - Error: {data.get('error')}")
