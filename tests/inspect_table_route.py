import requests
import json

BASE_URL = "http://127.0.0.1:8000"

print("=" * 100)
print("TESTE 10A — INSPEÇÃO DA ROTA /api/gold/v1/table/{base_name}")
print("=" * 100)

response = requests.get(f"{BASE_URL}/openapi.json", timeout=10)

print(f"status_code openapi: {response.status_code}")

if response.status_code != 200:
    print(response.text[:1000])
    raise SystemExit("ERRO: não foi possível ler o OpenAPI")

data = response.json()

path = "/api/gold/v1/table/{base_name}"
spec = data.get("paths", {}).get(path)

if spec is None:
    raise SystemExit(f"ERRO: rota {path} não encontrada no OpenAPI")

print("\nEspecificação encontrada para:")
print(path)

for method, details in spec.items():
    print("\n" + "-" * 100)
    print(f"Método: {method.upper()}")
    print(f"Resumo: {details.get('summary')}")
    print(f"Operation ID: {details.get('operationId')}")

    params = details.get("parameters", [])

    print("\nParâmetros:")
    if not params:
        print("Nenhum parâmetro declarado.")
    else:
        for p in params:
            name = p.get("name")
            location = p.get("in")
            required = p.get("required")
            schema = p.get("schema", {})
            default = schema.get("default")
            typ = schema.get("type")
            print(f"- {name} | in={location} | required={required} | type={typ} | default={default}")

    responses = details.get("responses", {})
    print("\nResponses:")
    for code, response_spec in responses.items():
        print(f"- {code}: {response_spec.get('description')}")

print("\n" + "=" * 100)
print("FIM DO TESTE 10A")
print("=" * 100)
