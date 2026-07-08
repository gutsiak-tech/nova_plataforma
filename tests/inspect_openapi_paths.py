import requests

BASE_URL = "http://127.0.0.1:8000"

print("=" * 100)
print("TESTE 9A — INVENTÁRIO REAL VIA OPENAPI")
print("=" * 100)

response = requests.get(f"{BASE_URL}/openapi.json", timeout=10)

print(f"status_code: {response.status_code}")

if response.status_code != 200:
    print(response.text[:1000])
    raise SystemExit("ERRO: não foi possível obter /openapi.json")

data = response.json()

paths = data.get("paths", {})

print(f"paths encontrados: {len(paths)}")

for path, methods in sorted(paths.items()):
    method_names = ", ".join(methods.keys()).upper()
    print(f"{method_names:20} {path}")

print("\n" + "=" * 100)
print("FIM DO TESTE 9A")
print("=" * 100)
