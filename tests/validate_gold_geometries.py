from pathlib import Path
import pandas as pd
import geopandas as gpd
import unicodedata

print("=" * 100)
print("TESTE 6 — GEOMETRIAS E COMPATIBILIDADE COM GOLD")
print("=" * 100)

errors = []
warnings = []

geo_files = {
    "municipios_pr": Path("data-lake/geo/processed/municipios_pr.geojson"),
    "municipios_rmc": Path("data-lake/geo/processed/municipios_rmc.geojson"),
    "ufs": Path("data-lake/geo/processed/ufs.geojson"),
}

gold_root = Path("data-lake/gold/caged")

def norm_text(x):
    if pd.isna(x):
        return None
    x = str(x).strip().upper()
    x = unicodedata.normalize("NFKD", x)
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    return x

def find_name_column(gdf):
    candidates = [
        "municipio",
        "nome",
        "name",
        "nm_mun",
        "nm_municipio",
        "nm_municip",
        "NM_MUN",
        "NM_MUNICIP",
        "NM_MUNICIPIO",
        "NM_MUNICIP",
        "NOME",
    ]

    lower_map = {c.lower(): c for c in gdf.columns}

    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]

    text_cols = [
        c for c in gdf.columns
        if c != "geometry" and pd.api.types.is_object_dtype(gdf[c])
    ]

    if text_cols:
        return text_cols[0]

    return None

loaded_geo = {}

for name, path in geo_files.items():
    print("\n" + "-" * 100)
    print(f"GeoJSON: {name}")
    print(f"Caminho: {path.as_posix()}")

    if not path.exists():
        errors.append((name, f"arquivo não encontrado: {path.as_posix()}"))
        continue

    try:
        gdf = gpd.read_file(path)
    except Exception as e:
        errors.append((name, f"erro ao ler GeoJSON: {e}"))
        continue

    loaded_geo[name] = gdf

    print(f"linhas: {len(gdf)}")
    print(f"colunas: {list(gdf.columns)}")
    print(f"CRS: {gdf.crs}")

    if gdf.empty:
        errors.append((name, "GeoJSON vazio"))
        continue

    null_geom = gdf.geometry.isna().sum()
    invalid_geom = (~gdf.geometry.is_valid).sum()

    print(f"geometrias nulas: {null_geom}")
    print(f"geometrias inválidas: {invalid_geom}")

    if null_geom > 0:
        errors.append((name, f"{null_geom} geometrias nulas"))

    if invalid_geom > 0:
        errors.append((name, f"{invalid_geom} geometrias inválidas"))

    name_col = find_name_column(gdf)
    print(f"coluna de nome detectada: {name_col}")

    if name_col is None and name in ["municipios_pr", "municipios_rmc"]:
        errors.append((name, "não foi possível detectar coluna de nome do município"))

print("\n" + "-" * 100)
print("Compatibilidade Gold PR/RMC com GeoJSON")

partitions = sorted(gold_root.glob("ano=*/mes=*"))

if not partitions:
    errors.append(("gold", "nenhuma partição Gold encontrada"))

def check_gold_vs_geo(partition, gold_file, geo_key):
    gold_path = partition / gold_file

    if not gold_path.exists():
        warnings.append((partition.as_posix(), f"arquivo Gold ausente: {gold_file}"))
        return

    if geo_key not in loaded_geo:
        errors.append((partition.as_posix(), f"GeoJSON não carregado: {geo_key}"))
        return

    gold = pd.read_parquet(gold_path)
    gdf = loaded_geo[geo_key]

    if "municipio" not in gold.columns:
        errors.append((gold_path.as_posix(), "coluna municipio ausente no Gold"))
        return

    geo_name_col = find_name_column(gdf)

    if geo_name_col is None:
        errors.append((geo_key, "não foi possível detectar coluna de município no GeoJSON"))
        return

    gold_names = set(gold["municipio"].map(norm_text).dropna())
    geo_names = set(gdf[geo_name_col].map(norm_text).dropna())

    missing_in_geo = sorted(gold_names - geo_names)

    print("\n" + partition.as_posix())
    print(f"{gold_file} versus {geo_key}")
    print(f"municípios no Gold: {len(gold_names)}")
    print(f"municípios no GeoJSON: {len(geo_names)}")
    print(f"municípios Gold não encontrados no GeoJSON: {len(missing_in_geo)}")

    if missing_in_geo:
        errors.append((
            gold_path.as_posix(),
            f"{len(missing_in_geo)} municípios do Gold não encontrados no GeoJSON: {missing_in_geo[:20]}"
        ))

for partition in partitions:
    check_gold_vs_geo(partition, "tabela_municipio_pr.parquet", "municipios_pr")
    check_gold_vs_geo(partition, "tabela_municipio_rmc.parquet", "municipios_rmc")

print("\n" + "=" * 100)
print("RESUMO DO TESTE 6")
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
print("FIM DO TESTE 6")
print("=" * 100)
