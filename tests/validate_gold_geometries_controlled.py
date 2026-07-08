from pathlib import Path
import pandas as pd
import geopandas as gpd
import unicodedata

print("=" * 100)
print("TESTE 6B — COMPATIBILIDADE GEOGRÁFICA COM EXCEÇÃO CONTROLADA")
print("=" * 100)

gold_root = Path("data-lake/gold/caged")

geo_pr = gpd.read_file("data-lake/geo/processed/municipios_pr.geojson")
geo_rmc = gpd.read_file("data-lake/geo/processed/municipios_rmc.geojson")

allowed_non_mappable = {"IGNORADO"}

errors = []
warnings = []

def norm_text(x):
    if pd.isna(x):
        return None
    x = str(x).strip().upper()
    x = unicodedata.normalize("NFKD", x)
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    return x

geo_pr_names = set(geo_pr["municipio"].map(norm_text).dropna())
geo_rmc_names = set(geo_rmc["municipio"].map(norm_text).dropna())

def evaluate(partition, gold_file, geo_names, label):
    path = partition / gold_file
    df = pd.read_parquet(path)

    df["_municipio_norm"] = df["municipio"].map(norm_text)

    gold_names = set(df["_municipio_norm"].dropna())
    missing = sorted(gold_names - geo_names)

    unexpected_missing = [
        x for x in missing
        if x not in allowed_non_mappable
    ]

    non_mappable_df = df[df["_municipio_norm"].isin(allowed_non_mappable)]
    mappable_df = df[~df["_municipio_norm"].isin(allowed_non_mappable)]

    total = df[["admissoes", "desligamentos", "saldo"]].sum()
    mappable = mappable_df[["admissoes", "desligamentos", "saldo"]].sum()
    non_mappable = non_mappable_df[["admissoes", "desligamentos", "saldo"]].sum()

    print("\n" + "-" * 100)
    print(f"{partition.as_posix()} | {label}")
    print(f"municípios Gold: {len(gold_names)}")
    print(f"não encontrados no GeoJSON: {missing}")
    print(f"não mapeáveis permitidos: {sorted(set(missing) & allowed_non_mappable)}")
    print(f"não mapeáveis inesperados: {unexpected_missing}")

    print("total:")
    print(total.to_dict())

    print("mapeável:")
    print(mappable.to_dict())

    print("não mapeável:")
    print(non_mappable.to_dict())

    if len(non_mappable_df) > 0:
        for col in ["admissoes", "desligamentos", "saldo"]:
            if total[col] != 0:
                pct = non_mappable[col] / total[col] * 100
                print(f"participação não mapeável em {col}: {pct:.4f}%")

    if unexpected_missing:
        errors.append((
            path.as_posix(),
            f"municípios inesperados sem geometria: {unexpected_missing}"
        ))

for partition in sorted(gold_root.glob("ano=*/mes=*")):
    evaluate(partition, "tabela_municipio_pr.parquet", geo_pr_names, "PR")
    evaluate(partition, "tabela_municipio_rmc.parquet", geo_rmc_names, "RMC")

print("\n" + "=" * 100)
print("RESUMO DO TESTE 6B")
print("=" * 100)
print(f"Erros encontrados: {len(errors)}")
print(f"Avisos encontrados: {len(warnings)}")

if errors:
    print("\nERROS")
    print("-" * 100)
    for rel, msg in errors:
        print(f"[ERRO] {rel} -> {msg}")
else:
    print("\nNenhum erro encontrado fora das exceções controladas.")

print("\n" + "=" * 100)
print("FIM DO TESTE 6B")
print("=" * 100)
