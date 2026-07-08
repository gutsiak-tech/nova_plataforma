#!/usr/bin/env python3
"""Diagnóstico não destrutivo da chave territorial (Gold × GeoJSON).

Não altera CSV/Parquet, banco, frontend nem Tegola.
Usa pandas (já no projeto) e a biblioteca padrão.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD_CAGED = PROJECT_ROOT / "data-lake" / "gold" / "caged"
GEO_PUBLIC = PROJECT_ROOT / "dashboard" / "public" / "geo"

CODE_CANDIDATES = (
    "cod_municipio",
    "codigo_municipio",
    "cod_ibge",
    "codigo_ibge",
    "CD_MUN",
    "CD_MUNIBGE",
    "id",
    "geocodigo",
)

NAME_CANDIDATES = (
    "municipio",
    "nome",
    "NM_MUN",
    "name",
    "nome_municipio",
    "municipio_norm",
)

PUNCT_RE = re.compile(r"[.,;:/\-_|]+")

# Categorias nao territoriais: reportar, mas nao contar como falha de cobertura.
NON_TERRITORIAL_KEYS = frozenset({"IGNORADO"})


def normalize_key(value: object) -> str | None:
    """Normalização alinhada ao projeto (geoJoin / text_normalize), com pontuação simples removida."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    text = "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )
    text = PUNCT_RE.sub(" ", text)
    text = " ".join(text.lower().split())
    return text.upper() if text else None


def detect_field(fields: list[str], candidates: tuple[str, ...]) -> str | None:
    lower_map = {f.lower(): f for f in fields}
    for cand in candidates:
        if cand in fields:
            return cand
        hit = lower_map.get(cand.lower())
        if hit:
            return hit
    return None


def resolve_gold_table(ano: int, mes: int, base_name: str) -> Path | None:
    folder = GOLD_CAGED / f"ano={ano}" / f"mes={mes:02d}"
    parquet = folder / f"{base_name}.parquet"
    csv = folder / f"{base_name}.csv"
    if parquet.is_file():
        return parquet
    if csv.is_file():
        return csv
    return None


def read_gold_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def load_geojson_props(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    features = payload.get("features") or []
    props_list: list[dict[str, Any]] = []
    keys: set[str] = set()
    for feat in features:
        props = feat.get("properties") or {}
        if isinstance(props, dict):
            props_list.append(props)
            keys.update(props.keys())
    return props_list, sorted(keys)


def gold_name_series(df: pd.DataFrame, name_col: str | None) -> pd.Series:
    if name_col and name_col in df.columns:
        return df[name_col]
    if "municipio_norm" in df.columns:
        return df["municipio_norm"]
    if "municipio" in df.columns:
        return df["municipio"]
    raise ValueError(f"Sem coluna de nome municipal. Colunas: {list(df.columns)}")


def join_coverage(
    *,
    label: str,
    gold_keys: set[str],
    geo_keys: set[str],
) -> dict[str, Any]:
    non_territorial = sorted(k for k in gold_keys if k in NON_TERRITORIAL_KEYS)
    territorial = {k for k in gold_keys if k not in NON_TERRITORIAL_KEYS}
    matched = sorted(territorial & geo_keys)
    unmatched_real = sorted(territorial - geo_keys)
    unmatched_geo = sorted(geo_keys - territorial)
    denom = len(territorial)
    coverage = (len(matched) / denom) if denom else 0.0
    return {
        "label": label,
        "gold_total": len(gold_keys),
        "gold_territorial": denom,
        "geo_total": len(geo_keys),
        "matched": len(matched),
        "unmatched_real": unmatched_real,
        "non_territorial": non_territorial,
        "unmatched_geo": unmatched_geo,
        "coverage_pct": round(100.0 * coverage, 2),
        "ok": len(unmatched_real) == 0 and denom > 0,
    }


def print_join_report(result: dict[str, Any]) -> None:
    print(f"--- Join: {result['label']} ---")
    print(f"  Gold (chaves unicos):     {result['gold_total']}")
    print(f"  Gold (municipios reais):  {result['gold_territorial']}")
    print(f"  GeoJSON (chaves unicos):  {result['geo_total']}")
    print(f"  Casados (nome norm):      {result['matched']}")
    print(f"  Sem match real:           {len(result['unmatched_real'])}")
    print(f"  Nao territoriais:         {len(result['non_territorial'])}")
    print(f"  GeoJSON sem Gold:         {len(result['unmatched_geo'])}")
    print(f"  Cobertura municipios reais Gold->GeoJSON: {result['coverage_pct']}%")
    unmatched = result["unmatched_real"]
    if unmatched:
        print("  Primeiros sem match real:")
        for item in unmatched[:20]:
            print(f"    - {item}")
    non_terr = result["non_territorial"]
    if non_terr:
        print("  Categorias nao territoriais (ignoradas no exit):")
        for item in non_terr[:20]:
            print(f"    - {item}")
    leftover = result["unmatched_geo"]
    if leftover:
        preview = leftover[:10]
        print(f"  Amostra GeoJSON sem Gold ({len(leftover)}): {preview}")
    print("")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Diagnóstico não destrutivo Gold × GeoJSON (cod_municipio / join por nome)."
    )
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--mes", type=int, default=4)
    args = parser.parse_args(argv)

    ano, mes = args.ano, args.mes
    print(f"Diagnóstico territorial | competencia={ano}-{mes:02d}")
    print(f"ROOT={PROJECT_ROOT}")
    print("")

    gold_tables = [
        "tabela_municipio",
        "tabela_municipio_pr",
        "tabela_municipio_rmc",
        "tabela_ictt_municipio_pr",
    ]
    loaded: dict[str, pd.DataFrame] = {}

    print("=== Colunas Gold municipais ===")
    for name in gold_tables:
        path = resolve_gold_table(ano, mes, name)
        if path is None:
            print(f"  {name}: AUSENTE")
            continue
        df = read_gold_table(path)
        loaded[name] = df
        cols = list(df.columns)
        code_col = detect_field(cols, CODE_CANDIDATES)
        name_col = detect_field(cols, NAME_CANDIDATES)
        print(f"  {name} ({path.name})")
        print(f"    rows={len(df)} cols={cols}")
        print(f"    code_field={code_col!r} name_field={name_col!r}")
        has_cod = code_col is not None and code_col.lower() in {
            c.lower() for c in ("cod_municipio", "codigo_municipio", "cod_ibge", "codigo_ibge", "CD_MUN", "CD_MUNIBGE", "geocodigo")
        }
        # 'id' alone is weak; report separately
        if code_col == "id":
            print("    nota: campo 'id' detectado (fraco para IBGE; verificar significado)")
        elif has_cod or (code_col and code_col.lower() != "id"):
            non_null = int(df[code_col].notna().sum()) if code_col else 0
            print(f"    code_non_null={non_null}/{len(df)}")
        else:
            print("    cod_municipio: NAO PRESENTE")
    print("")

    geo_files = {
        "municipios_pr": GEO_PUBLIC / "municipios_pr.geojson",
        "municipios_rmc": GEO_PUBLIC / "municipios_rmc.geojson",
    }
    geo_props: dict[str, list[dict[str, Any]]] = {}
    geo_code_field: dict[str, str | None] = {}
    geo_name_field: dict[str, str | None] = {}

    print("=== Properties GeoJSON ===")
    for key, path in geo_files.items():
        if not path.is_file():
            print(f"  {key}: AUSENTE ({path})")
            continue
        props_list, keys = load_geojson_props(path)
        geo_props[key] = props_list
        code_col = detect_field(keys, CODE_CANDIDATES)
        name_col = detect_field(keys, NAME_CANDIDATES)
        # Prefer municipio_norm when present for join diagnostics.
        if "municipio_norm" in keys:
            name_col = "municipio_norm"
        geo_code_field[key] = code_col
        geo_name_field[key] = name_col
        codes = [
            str(p.get(code_col)).strip()
            for p in props_list
            if code_col and p.get(code_col) is not None and str(p.get(code_col)).strip()
        ]
        print(f"  {path.name}")
        print(f"    features={len(props_list)} properties={keys}")
        print(f"    code_field={code_col!r} name_field={name_col!r}")
        print(f"    code_non_empty={len(codes)}/{len(props_list)}")
        if codes:
            print(f"    code_sample={codes[:3]}")
    print("")

    joins: list[dict[str, Any]] = []

    def build_keys_from_gold(df: pd.DataFrame) -> set[str]:
        series = gold_name_series(df, detect_field(list(df.columns), NAME_CANDIDATES))
        # Prefer municipio_norm if available and named as such
        if "municipio_norm" in df.columns:
            series = df["municipio_norm"]
        elif "municipio" in df.columns:
            series = df["municipio"]
        keys = {normalize_key(v) for v in series.tolist()}
        return {k for k in keys if k}

    def build_keys_from_geo(props_list: list[dict[str, Any]], name_field: str | None) -> set[str]:
        keys: set[str] = set()
        for props in props_list:
            raw = None
            if name_field and props.get(name_field) is not None:
                raw = props.get(name_field)
            elif props.get("municipio_norm") is not None:
                raw = props.get("municipio_norm")
            elif props.get("municipio") is not None:
                raw = props.get("municipio")
            norm = normalize_key(raw)
            if norm:
                keys.add(norm)
        return keys

    pairs = [
        ("tabela_municipio_pr × municipios_pr", "tabela_municipio_pr", "municipios_pr"),
        ("tabela_municipio_rmc × municipios_rmc", "tabela_municipio_rmc", "municipios_rmc"),
        ("tabela_ictt_municipio_pr × municipios_pr", "tabela_ictt_municipio_pr", "municipios_pr"),
    ]

    print("=== Cobertura de join por nome normalizado ===")
    for label, gold_name, geo_name in pairs:
        if gold_name not in loaded:
            print(f"--- Join: {label} ---")
            print("  SKIP: tabela Gold ausente")
            print("")
            continue
        if geo_name not in geo_props:
            print(f"--- Join: {label} ---")
            print("  SKIP: GeoJSON ausente")
            print("")
            continue
        gold_keys = build_keys_from_gold(loaded[gold_name])
        geo_keys = build_keys_from_geo(geo_props[geo_name], geo_name_field.get(geo_name))
        result = join_coverage(label=label, gold_keys=gold_keys, geo_keys=geo_keys)
        joins.append(result)
        print_join_report(result)

    print("=== Conclusão rápida ===")
    gold_has_cod = any(
        detect_field(list(df.columns), CODE_CANDIDATES) not in (None, "id")
        for name, df in loaded.items()
        if name.startswith("tabela_municipio")
    )
    print(f"  Gold municipal possui cod_municipio? {'SIM' if gold_has_cod else 'NAO'}")
    geo_codes = {k: geo_code_field.get(k) for k in geo_files}
    print(f"  Código no GeoJSON: {geo_codes}")
    print("  Join frontend atual: por nome normalizado (municipio_norm / uf_norm).")
    print("  Chave futura recomendada PostGIS/Tegola: cod_municipio (IBGE 7 dígitos).")
    print("")

    principal = [
        j for j in joins if j["label"].startswith("tabela_municipio_pr")
        or j["label"].startswith("tabela_municipio_rmc")
    ]
    # Cobertura principal = 100% dos municípios Gold casam no GeoJSON
    all_ok = bool(principal) and all(j["ok"] for j in principal)
    # ICTT também entra se presente
    ictt = [j for j in joins if "ictt" in j["label"]]
    if ictt:
        all_ok = all_ok and all(j["ok"] for j in ictt)

    if all_ok:
        print(
            "RESULTADO: cobertura de municipios reais 100% "
            "(IGNORADO/nao territoriais nao contam como falha). exit=0"
        )
        return 0

    print("RESULTADO: falhas de cobertura em municipios reais. exit=1")
    return 1


if __name__ == "__main__":
    sys.exit(main())
