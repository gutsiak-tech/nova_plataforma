import requests

BASE_URL = "http://127.0.0.1:8000"

tests = [
    {"ano": 2026, "mes": 1, "uf": "PR"},
    {"ano": 2026, "mes": 2, "uf": "PR"},
    {"ano": 2026, "mes": 3, "uf": "PR"},
    {"ano": 2026, "mes": 4, "uf": "PR"},
]

print("=" * 100)
print("TESTE 11B — SMOKE TEST DA ROTA DE MAPA")
print("=" * 100)

errors = []

for params in tests:
    url = f"{BASE_URL}/api/map/municipios"

    print("\n" + "-" * 100)
    print(f"GET {url}")
    print(f"params: {params}")

    try:
        response = requests.get(url, params=params, timeout=20)
    except Exception as e:
        errors.append((params, f"erro de conexão: {e}"))
        print(f"ERRO: {e}")
        continue

    print(f"status_code: {response.status_code}")

    if response.status_code != 200:
        errors.append((params, f"status_code {response.status_code}"))
        print(response.text[:2000])
        continue

    try:
        data = response.json()
    except Exception as e:
        errors.append((params, f"JSON inválido: {e}"))
        print(response.text[:2000])
        continue

    print(f"tipo resposta: {type(data)}")

    if isinstance(data, dict):
        print(f"chaves: {list(data.keys())[:30]}")

        # tenta detectar GeoJSON
        if data.get("type") == "FeatureCollection":
            features = data.get("features", [])
            print("formato: GeoJSON FeatureCollection")
            print(f"features: {len(features)}")

            if not features:
                errors.append((params, "FeatureCollection sem features"))
            else:
                first = features[0]
                print(f"primeira feature keys: {list(first.keys())}")
                print(f"primeiras propriedades: {first.get('properties', {})}")

        # tenta detectar resposta tabular/lista dentro de dict
        else:
            rows = None
            for key in ["items", "rows", "data", "records", "features"]:
                if key in data and isinstance(data[key], list):
                    rows = data[key]
                    print(f"lista detectada em '{key}': {len(rows)} itens")
                    if rows:
                        print("primeiro item:")
                        print(rows[0])
                    break

            if rows is None:
                print("Resposta parcial:")
                print(str(data)[:1500])

    elif isinstance(data, list):
        print(f"lista com {len(data)} itens")
        if data:
            print("primeiro item:")
            print(data[0])
        else:
            errors.append((params, "lista vazia"))

    else:
        errors.append((params, f"tipo inesperado: {type(data)}"))

print("\n" + "=" * 100)
print("RESUMO DO TESTE 11B")
print("=" * 100)
print(f"Consultas avaliadas: {len(tests)}")
print(f"Erros encontrados: {len(errors)}")

if errors:
    print("\nERROS")
    print("-" * 100)
    for params, msg in errors:
        print(f"[ERRO] {params} -> {msg}")
else:
    print("\nNenhum erro encontrado.")

print("\n" + "=" * 100)
print("FIM DO TESTE 11B")
print("=" * 100)
