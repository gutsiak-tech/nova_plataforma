import requests
import json

BASE_URL = "http://127.0.0.1:8000"

endpoints = [
    "/catalog",
    "/competencias",
    "/meta",
    "/overview",
]

print("=" * 100)
print("TESTE 9 — SMOKE TEST DAS ROTAS GOLD")
print("=" * 100)

errors = []

for endpoint in endpoints:
    url = BASE_URL + endpoint

    print("\n" + "-" * 100)
    print(f"GET {url}")

    try:
        response = requests.get(url, timeout=10)
    except Exception as e:
        errors.append((endpoint, f"erro de conexão: {e}"))
        print(f"ERRO: {e}")
        continue

    print(f"status_code: {response.status_code}")

    if response.status_code != 200:
        errors.append((endpoint, f"status_code {response.status_code}"))
        print(response.text[:1000])
        continue

    try:
        data = response.json()
        print("json: OK")

        if isinstance(data, dict):
            print(f"chaves: {list(data.keys())[:20]}")
        elif isinstance(data, list):
            print(f"lista com {len(data)} itens")
            if data:
                print(f"primeiro item: {data[0]}")
        else:
            print(f"tipo retornado: {type(data)}")

    except Exception as e:
        errors.append((endpoint, f"resposta não é JSON válido: {e}"))
        print(f"ERRO JSON: {e}")
        print(response.text[:1000])

print("\n" + "=" * 100)
print("RESUMO DO TESTE 9")
print("=" * 100)
print(f"Endpoints avaliados: {len(endpoints)}")
print(f"Erros encontrados: {len(errors)}")

if errors:
    print("\nERROS")
    print("-" * 100)
    for endpoint, msg in errors:
        print(f"[ERRO] {endpoint} -> {msg}")
else:
    print("\nNenhum erro encontrado.")

print("\n" + "=" * 100)
print("FIM DO TESTE 9")
print("=" * 100)
