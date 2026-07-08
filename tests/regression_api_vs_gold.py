from pathlib import Path
import pandas as pd
import requests

BASE_URL = "http://127.0.0.1:8000"
GOLD_ROOT = Path("data-lake/gold/caged")

metric_cols = ["admissoes", "desligamentos", "saldo"]

print("=" * 100)
print("TESTE 16 — REGRESSÃO API × GOLD FILESYSTEM")
print("=" * 100)

errors = []

def read_gold_table(ano, mes, base_name, scope):
    partition = GOLD_ROOT / f"ano={ano}" / f"mes={mes:02d}"

    if scope == "br":
        filename = f"{base_name}.parquet"
    else:
        filename = f"{base_name}_{scope}.parquet"

    path = partition / filename

    if not path.exists():
        errors.append((ano, mes, scope, base_name, f"arquivo não encontrado: {path.as_posix()}"))
        return None

    return pd.read_parquet(path)

def api_table(ano, mes, base_name, scope, limit=2000):
    url = f"{BASE_URL}/api/gold/v1/table/{base_name}"
    params = {
        "ano": ano,
        "mes": mes,
        "scope": scope,
        "limit": limit,
        "offset": 0,
    }

    response = requests.get(url, params=params, timeout=20)

    if response.status_code != 200:
        errors.append((ano, mes, scope, base_name, f"API status_code {response.status_code}: {response.text[:500]}"))
        return None

    return response.json()

def totals_from_df(df):
    return {col: int(df[col].sum()) for col in metric_cols}

def totals_from_rows(rows):
    return {
        col: int(sum(row[col] for row in rows))
        for col in metric_cols
    }

tests = []

for mes in [1, 2, 3, 4]:
    for scope in ["br", "pr", "rmc"]:
        tests.append((2026, mes, "tabela_municipio", scope))
        tests.append((2026, mes, "tabela_setor", scope))

    tests.append((2026, mes, "tabela_resumo", "br"))

for ano, mes, base_name, scope in tests:
    print("\n" + "-" * 100)
    print(f"{ano}-{mes:02d} | {scope} | {base_name}")

    gold = read_gold_table(ano, mes, base_name, scope)
    api = api_table(ano, mes, base_name, scope)

    if gold is None or api is None:
        continue

    rows = api.get("rows", [])

    print(f"Gold linhas: {len(gold)}")
    print(f"API total declarado: {api.get('total')}")
    print(f"API rows retornadas: {len(rows)}")

    if api.get("total") != len(gold):
        errors.append((ano, mes, scope, base_name, f"API total={api.get('total')} diferente de linhas Gold={len(gold)}"))

    if len(rows) != len(gold):
        errors.append((ano, mes, scope, base_name, f"API rows={len(rows)} diferente de linhas Gold={len(gold)}"))
        continue

    gold_totals = totals_from_df(gold)
    api_totals = totals_from_rows(rows)

    print(f"Gold totais: {gold_totals}")
    print(f"API totais:  {api_totals}")

    if gold_totals != api_totals:
        errors.append((ano, mes, scope, base_name, f"totais diferentes: Gold={gold_totals}, API={api_totals}"))

print("\n" + "=" * 100)
print("RESUMO DO TESTE 16")
print("=" * 100)
print(f"Consultas avaliadas: {len(tests)}")
print(f"Erros encontrados: {len(errors)}")

if errors:
    print("\nERROS")
    print("-" * 100)
    for ano, mes, scope, base_name, msg in errors:
        print(f"[ERRO] {ano}-{mes:02d} | {scope} | {base_name} -> {msg}")
else:
    print("\nNenhum erro encontrado.")

print("\n" + "=" * 100)
print("FIM DO TESTE 16")
print("=" * 100)
