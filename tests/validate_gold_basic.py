from pathlib import Path
import pandas as pd

root = Path("data-lake/gold/caged")

metric_cols = {"admissoes", "desligamentos", "saldo"}

print("=" * 100)
print("TESTE 4 — VALIDAÇÃO BÁSICA DE DADOS GOLD")
print("=" * 100)

errors = []
warnings = []

files = sorted(root.glob("ano=*/mes=*/*.parquet"))

if not files:
    raise SystemExit("ERRO: Nenhum arquivo parquet encontrado em data-lake/gold/caged")

for path in files:
    rel = path.as_posix()

    try:
        df = pd.read_parquet(path)
    except Exception as e:
        errors.append((rel, f"erro_leitura: {e}"))
        continue

    # 1. Tabela vazia
    if df.empty:
        errors.append((rel, "tabela vazia"))
        continue

    cols = set(df.columns)

    # 2. Colunas métricas obrigatórias
    missing_metrics = metric_cols - cols
    if missing_metrics:
        errors.append((rel, f"colunas métricas ausentes: {sorted(missing_metrics)}"))
        continue

    # 3. Nulos nas métricas
    for col in metric_cols:
        nulls = df[col].isna().sum()
        if nulls > 0:
            errors.append((rel, f"{col} possui {nulls} nulos"))

    # 4. Saldo correto
    saldo_calc = df["admissoes"] - df["desligamentos"]
    saldo_diff = df[df["saldo"] != saldo_calc]

    if len(saldo_diff) > 0:
        errors.append((rel, f"{len(saldo_diff)} linhas com saldo != admissoes - desligamentos"))

    # 5. Valores negativos em admissoes/desligamentos
    for col in ["admissoes", "desligamentos"]:
        negatives = (df[col] < 0).sum()
        if negatives > 0:
            errors.append((rel, f"{col} possui {negatives} valores negativos"))

    # 6. Chave dimensional: tudo que não é métrica
    key_cols = [c for c in df.columns if c not in metric_cols]

    if not key_cols:
        warnings.append((rel, "sem colunas dimensionais para testar duplicidade"))
        continue

    # 7. Nulos nas chaves
    for col in key_cols:
        nulls = df[col].isna().sum()
        if nulls > 0:
            errors.append((rel, f"chave {col} possui {nulls} nulos"))

    # 8. Duplicidade nas chaves
    duplicated = df.duplicated(subset=key_cols, keep=False)
    if duplicated.any():
        n_dup = duplicated.sum()
        errors.append((rel, f"{n_dup} linhas duplicadas pela chave {key_cols}"))

print("\nRESUMO")
print("-" * 100)
print(f"Arquivos avaliados: {len(files)}")
print(f"Erros encontrados: {len(errors)}")
print(f"Avisos encontrados: {len(warnings)}")

if warnings:
    print("\nAVISOS")
    print("-" * 100)
    for rel, msg in warnings:
        print(f"[AVISO] {rel} -> {msg}")

if errors:
    print("\nERROS")
    print("-" * 100)
    for rel, msg in errors:
        print(f"[ERRO] {rel} -> {msg}")
else:
    print("\nNenhum erro encontrado.")

print("\n" + "=" * 100)
print("FIM DO TESTE 4")
print("=" * 100)
