from pathlib import Path
import pandas as pd

root = Path("data-lake/gold/caged")

print("=" * 100)
print("TESTE 6A — INVESTIGAÇÃO DO MUNICÍPIO IGNORADO")
print("=" * 100)

for partition in sorted(root.glob("ano=*/mes=*")):
    path = partition / "tabela_municipio_pr.parquet"

    if not path.exists():
        continue

    df = pd.read_parquet(path)

    mask = df["municipio"].astype(str).str.upper().str.strip() == "IGNORADO"
    ignored = df[mask]

    print("\n" + "-" * 100)
    print(partition.as_posix())

    if ignored.empty:
        print("Nenhuma linha IGNORADO encontrada.")
        continue

    print(ignored)

    total = df[["admissoes", "desligamentos", "saldo"]].sum()
    ignored_total = ignored[["admissoes", "desligamentos", "saldo"]].sum()

    print("\nTotais PR:")
    print(total.to_dict())

    print("Totais IGNORADO:")
    print(ignored_total.to_dict())

    print("Participação do IGNORADO no total PR:")
    for col in ["admissoes", "desligamentos", "saldo"]:
        if total[col] != 0:
            pct = ignored_total[col] / total[col] * 100
            print(f"{col}: {pct:.4f}%")
        else:
            print(f"{col}: total zero, percentual não calculado")

print("\n" + "=" * 100)
print("FIM DO TESTE 6A")
print("=" * 100)
