from pathlib import Path
import pandas as pd

root = Path("data-lake/gold/caged")

targets = [
    "tabela_resumo.parquet",
    "tabela_municipio.parquet",
    "tabela_municipio_pr.parquet",
    "tabela_municipio_rmc.parquet",
    "tabela_uf.parquet",
    "tabela_setor.parquet",
    "tabela_setor_pr.parquet",
    "tabela_setor_rmc.parquet",
    "tabela_pais.parquet",
    "tabela_ocupacao.parquet",
]

print("=" * 100)
print("TESTE 3 — LEITURA E SCHEMA DAS TABELAS GOLD PRINCIPAIS")
print("=" * 100)

files = sorted(root.glob("ano=*/mes=*/*.parquet"))

selected = [
    f for f in files
    if f.name in targets
]

if not selected:
    raise SystemExit("ERRO: Nenhuma tabela principal encontrada.")

for path in selected:
    rel = path.as_posix()
    print("\n" + "-" * 100)
    print(rel)

    try:
        df = pd.read_parquet(path)
    except Exception as e:
        print(f"ERRO AO LER: {e}")
        continue

    print(f"linhas: {len(df)}")
    print(f"colunas: {len(df.columns)}")
    print("nomes_colunas:")
    print(list(df.columns))

    if len(df) == 0:
        print("ALERTA: tabela vazia")

print("\n" + "=" * 100)
print("FIM DO TESTE 3")
print("=" * 100)
