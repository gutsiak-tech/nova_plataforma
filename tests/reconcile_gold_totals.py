from pathlib import Path
import pandas as pd

root = Path("data-lake/gold/caged")
metric_cols = ["admissoes", "desligamentos", "saldo"]

print("=" * 100)
print("TESTE 5 — RECONCILIAÇÃO ENTRE TABELAS GOLD")
print("=" * 100)

errors = []
warnings = []

def read_table(partition, name):
    path = partition / name
    if not path.exists():
        warnings.append((partition.as_posix(), f"arquivo ausente: {name}"))
        return None
    return pd.read_parquet(path)

def totals(df):
    return {col: int(df[col].sum()) for col in metric_cols}

def compare_totals(partition, reference_name, candidate_name, reference_totals, candidate_totals):
    for col in metric_cols:
        ref = reference_totals[col]
        cand = candidate_totals[col]
        if ref != cand:
            errors.append((
                partition.as_posix(),
                f"{candidate_name}.{col}={cand} diferente de {reference_name}.{col}={ref}"
            ))

partitions = sorted(root.glob("ano=*/mes=*"))

if not partitions:
    raise SystemExit("ERRO: nenhuma partição ano=*/mes=* encontrada")

for partition in partitions:
    print("\n" + "-" * 100)
    print(f"Partição: {partition.as_posix()}")

    resumo = read_table(partition, "tabela_resumo.parquet")
    municipio = read_table(partition, "tabela_municipio.parquet")
    uf = read_table(partition, "tabela_uf.parquet")
    setor = read_table(partition, "tabela_setor.parquet")

    if resumo is None or municipio is None:
        errors.append((partition.as_posix(), "não foi possível comparar resumo e município"))
        continue

    if len(resumo) != 1:
        errors.append((partition.as_posix(), f"tabela_resumo deveria ter 1 linha, mas tem {len(resumo)}"))
        continue

    resumo_totals = {
        col: int(resumo.iloc[0][col])
        for col in metric_cols
    }

    municipio_totals = totals(municipio)

    print(f"Resumo:   {resumo_totals}")
    print(f"Município:{municipio_totals}")

    compare_totals(
        partition,
        "tabela_resumo",
        "tabela_municipio",
        resumo_totals,
        municipio_totals
    )

    if uf is not None:
        uf_totals = totals(uf)
        print(f"UF:       {uf_totals}")
        compare_totals(
            partition,
            "tabela_resumo",
            "tabela_uf",
            resumo_totals,
            uf_totals
        )

    if setor is not None:
        setor_totals = totals(setor)
        print(f"Setor:    {setor_totals}")
        compare_totals(
            partition,
            "tabela_resumo",
            "tabela_setor",
            resumo_totals,
            setor_totals
        )

    # Reconciliação interna Paraná
    municipio_pr = read_table(partition, "tabela_municipio_pr.parquet")
    setor_pr = read_table(partition, "tabela_setor_pr.parquet")

    if municipio_pr is not None and setor_pr is not None:
        municipio_pr_totals = totals(municipio_pr)
        setor_pr_totals = totals(setor_pr)

        print(f"Município PR: {municipio_pr_totals}")
        print(f"Setor PR:     {setor_pr_totals}")

        compare_totals(
            partition,
            "tabela_municipio_pr",
            "tabela_setor_pr",
            municipio_pr_totals,
            setor_pr_totals
        )

    # Reconciliação interna RMC
    municipio_rmc = read_table(partition, "tabela_municipio_rmc.parquet")
    setor_rmc = read_table(partition, "tabela_setor_rmc.parquet")

    if municipio_rmc is not None and setor_rmc is not None:
        municipio_rmc_totals = totals(municipio_rmc)
        setor_rmc_totals = totals(setor_rmc)

        print(f"Município RMC: {municipio_rmc_totals}")
        print(f"Setor RMC:     {setor_rmc_totals}")

        compare_totals(
            partition,
            "tabela_municipio_rmc",
            "tabela_setor_rmc",
            municipio_rmc_totals,
            setor_rmc_totals
        )

print("\n" + "=" * 100)
print("RESUMO DO TESTE 5")
print("=" * 100)
print(f"Partições avaliadas: {len(partitions)}")
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
print("FIM DO TESTE 5")
print("=" * 100)
