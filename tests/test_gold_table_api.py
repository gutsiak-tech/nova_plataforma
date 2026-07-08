import requests

BASE_URL = "http://127.0.0.1:8000"

tests = [
    {
        "base_name": "tabela_resumo",
        "params": {"scope": "br", "ano": 2026, "mes": 1, "limit": 10}
    },
    {
        "base_name": "tabela_municipio",
        "params": {"scope": "br", "ano": 2026, "mes": 1, "limit": 10, "sort_by": "saldo"}
    },
    {
        "base_name": "tabela_municipio",
        "params": {"scope": "pr", "ano": 2026, "mes": 1, "limit": 10, "sort_by": "saldo"}
    },
    {
        "base_name": "tabela_municipio",
        "params": {"scope": "rmc", "ano": 2026, "mes": 1, "limit": 10, "sort_by": "saldo"}
    },
    {
        "base_name": "tabela_setor",
        "params": {"scope": "br", "ano": 2026, "mes": 1, "limit": 10, "sort_by": "saldo"}
    },
    {
        "base_name": "tabela_setor",
        "params": {"scope": "pr", "ano": 2026, "mes": 1, "limit": 10, "sort_by": "saldo"}
    },
    {
        "base_name": "tabela_setor",
        "params": {"scope": "rmc", "ano": 2026, "mes": 1, "limit": 10, "sort_by": "saldo"}
    },
]

print("=" * 100)
print("TESTE 10B — CONSULTA DE TABELAS GOLD PELA API")
print("=" * 100)

errors = []

for test in tests:
    base_name = test["base_name"]
    params = test["params"]

    url = f"{BASE_URL}/api/gold/v1/table/{base_name}"

    print("\n" + "-" * 100)
    print(f"GET {url}")
    print(f"params: {params}")

    try:
        response = requests.get(url, params=params, timeout=10)
    except Exception as e:
        errors.append((base_name, params, f"erro de conexão: {e}"))
        print(f"ERRO: {e}")
        continue

    print(f"status_code: {response.status_code}")

    if response.status_code != 200:
        errors.append((base_name, params, f"status_code {response.status_code}"))
        print(response.text[:1500])
        continue

    try:
        data = response.json()
    except Exception as e:
        errors.append((base_name, params, f"JSON inválido: {e}"))
        print(response.text[:1500])
        continue

    print(f"chaves: {list(data.keys()) if isinstance(data, dict) else type(data)}")

    if isinstance(data, dict):
        rows = None

        for key in ["items", "rows", "data", "records"]:
            if key in data and isinstance(data[key], list):
                rows = data[key]
                print(f"lista detectada em '{key}': {len(rows)} linhas")
                break

        if rows is not None and rows:
            print("primeira linha:")
            print(rows[0])
        elif rows == []:
            errors.append((base_name, params, "retornou lista vazia"))
            print("ERRO: lista vazia")
        else:
            print("Não encontrei lista padrão de registros; resposta parcial:")
            print(str(data)[:1000])

print("\n" + "=" * 100)
print("RESUMO DO TESTE 10B")
print("=" * 100)
print(f"Consultas avaliadas: {len(tests)}")
print(f"Erros encontrados: {len(errors)}")

if errors:
    print("\nERROS")
    print("-" * 100)
    for base_name, params, msg in errors:
        print(f"[ERRO] {base_name} {params} -> {msg}")
else:
    print("\nNenhum erro encontrado.")

print("\n" + "=" * 100)
print("FIM DO TESTE 10B")
print("=" * 100)
