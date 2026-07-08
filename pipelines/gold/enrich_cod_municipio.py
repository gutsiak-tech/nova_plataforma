"""Enriquecimento idempotente de cod_municipio na Gold territorial (PR/RMC/ICTT PR).

Lookup via GeoJSON (property cod_municipio) por nome normalizado.
Preserva colunas/linhas existentes; IGNORADO permanece sem código.
Não altera frontend, PostGIS, Tegola nem contratos da API.
"""

from __future__ import annotations

import json
import re
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import PROJECT_ROOT

NAME_CANDIDATES = (
    "municipio_norm",
    "municipio",
    "nome_municipio",
    "NM_MUN",
    "nome",
    "name",
)

SPECIAL_NON_MUNICIPIO = frozenset({"IGNORADO"})

PUNCT_RE = re.compile(r"[.,;:/\-_|]+")

ENRICH_TARGETS: tuple[tuple[str, str], ...] = (
    ("tabela_municipio_pr", "pr"),
    ("tabela_municipio_rmc", "rmc"),
    ("tabela_ictt_municipio_pr", "pr"),
)

DIAGNOSE_ONLY = ("tabela_municipio",)

DEFAULT_GOLD_ROOT = PROJECT_ROOT / "data-lake" / "gold" / "caged"
DEFAULT_GEO_PR = PROJECT_ROOT / "dashboard" / "public" / "geo" / "municipios_pr.geojson"
DEFAULT_GEO_RMC = PROJECT_ROOT / "dashboard" / "public" / "geo" / "municipios_rmc.geojson"


def normalize_key(value: object) -> str | None:
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


def is_code_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text == "" or text.lower() in {"nan", "none", "null", "<na>"}


def format_cod_municipio(value: object) -> str | None:
    if is_code_missing(value):
        return None
    text = str(value).strip()
    if text.endswith(".0") and text.replace(".", "", 1).isdigit():
        text = text[:-2]
    if text.isdigit() and len(text) < 7:
        text = text.zfill(7)
    return text


def load_geo_lookup(path: Path, *, quiet: bool = False) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError(f"GeoJSON nao encontrado: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    features = payload.get("features") or []
    if not features:
        raise ValueError(f"GeoJSON sem features: {path}")

    sample_keys: list[str] = []
    for feat in features:
        props = feat.get("properties") or {}
        if isinstance(props, dict):
            sample_keys = list(props.keys())
            break

    name_field = detect_field(sample_keys, NAME_CANDIDATES)
    if name_field is None:
        raise ValueError(f"Campo de nome municipal nao encontrado em {path}: {sample_keys}")

    code_key = next((k for k in sample_keys if k.lower() == "cod_municipio"), None)
    if code_key is None:
        raise ValueError(f"Property cod_municipio ausente em {path}: {sample_keys}")

    lookup: dict[str, str] = {}
    collisions: list[str] = []
    for feat in features:
        props = feat.get("properties") or {}
        if not isinstance(props, dict):
            continue
        raw_name = props.get(name_field)
        if raw_name is None and name_field != "municipio" and props.get("municipio") is not None:
            raw_name = props.get("municipio")
        key = normalize_key(raw_name)
        code = format_cod_municipio(props.get(code_key))
        if key is None or code is None:
            continue
        if key in lookup and lookup[key] != code:
            collisions.append(f"{key}:{lookup[key]}vs{code}")
            continue
        lookup[key] = code

    if collisions:
        preview = ", ".join(collisions[:5])
        raise ValueError(f"Colisao de nomes no lookup {path.name}: {preview}")

    if not quiet:
        print(f"  Lookup {path.name}: name_field={name_field!r} codes={len(lookup)}")
    return lookup


def resolve_table_paths(partition: Path, base_name: str) -> list[Path]:
    paths: list[Path] = []
    parquet = partition / f"{base_name}.parquet"
    csv = partition / f"{base_name}.csv"
    if parquet.is_file():
        paths.append(parquet)
    if csv.is_file():
        paths.append(csv)
    return paths


def read_table(paths: list[Path]) -> tuple[pd.DataFrame, Path]:
    parquet = next((p for p in paths if p.suffix.lower() == ".parquet"), None)
    csv = next((p for p in paths if p.suffix.lower() == ".csv"), None)
    if parquet is not None:
        return pd.read_parquet(parquet), parquet
    if csv is not None:
        return pd.read_csv(csv), csv
    raise FileNotFoundError("Tabela sem arquivos parquet/csv")


def count_filled(series: pd.Series) -> int:
    return int(sum(not is_code_missing(v) for v in series.tolist()))


def gold_name_series(df: pd.DataFrame) -> pd.Series:
    if "municipio_norm" in df.columns:
        return df["municipio_norm"]
    if "municipio" in df.columns:
        return df["municipio"]
    name_col = detect_field(list(df.columns), NAME_CANDIDATES)
    if name_col is None:
        raise ValueError(f"Coluna de municipio ausente: {list(df.columns)}")
    return df[name_col]


def enrich_dataframe(
    df: pd.DataFrame,
    lookup: dict[str, str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    out = df.copy()
    before_filled = 0
    if "cod_municipio" not in out.columns:
        out["cod_municipio"] = pd.NA
    else:
        before_filled = count_filled(out["cod_municipio"])
        out["cod_municipio"] = out["cod_municipio"].map(
            lambda v: format_cod_municipio(v) if not is_code_missing(v) else pd.NA
        )

    names = gold_name_series(out)
    unmatched_real: list[str] = []
    ignored_rows = 0
    filled_now = 0
    new_codes: list[object] = []

    for idx, raw_name in enumerate(names.tolist()):
        current = out["cod_municipio"].iloc[idx]
        key = normalize_key(raw_name)
        if key in SPECIAL_NON_MUNICIPIO:
            ignored_rows += 1
            if is_code_missing(current):
                new_codes.append(pd.NA)
            else:
                new_codes.append(format_cod_municipio(current))
            continue

        if not is_code_missing(current):
            new_codes.append(format_cod_municipio(current))
            continue

        code = lookup.get(key) if key else None
        if code is None:
            unmatched_real.append(key or str(raw_name))
            new_codes.append(pd.NA)
        else:
            filled_now += 1
            new_codes.append(code)

    out["cod_municipio"] = new_codes
    after_filled = count_filled(out["cod_municipio"])
    report = {
        "table": None,
        "rows": len(out),
        "before_filled": before_filled,
        "after_filled": after_filled,
        "filled_this_run": filled_now,
        "ignored_rows": ignored_rows,
        "unmatched_real": unmatched_real,
        "columns": list(out.columns),
    }
    return out, report


def write_table(
    df: pd.DataFrame,
    paths: list[Path],
    *,
    dry_run: bool,
    do_backup: bool,
    stamp: str,
) -> tuple[list[str], list[str]]:
    would: list[str] = []
    changed: list[str] = []
    for path in paths:
        would.append(str(path))
        if dry_run:
            continue
        if do_backup and path.is_file():
            bak = path.with_name(f"{path.name}.bak_{stamp}")
            shutil.copy2(path, bak)
            changed.append(str(bak))
        if path.suffix.lower() == ".parquet":
            df.to_parquet(path, index=False)
        else:
            df.to_csv(path, index=False)
        changed.append(str(path))
    return would, changed


def print_table_report(
    name: str,
    report: dict[str, Any],
    would: list[str],
    changed: list[str],
    *,
    dry_run: bool,
    diagnose_only: bool = False,
) -> None:
    mode = "DIAGNOSE-ONLY" if diagnose_only else ("DRY-RUN" if dry_run else "APPLY")
    print(f"--- {name} [{mode}] ---")
    print(f"  rows={report['rows']}")
    print(f"  cod_municipio preenchido antes={report['before_filled']}")
    print(f"  cod_municipio preenchido depois={report['after_filled']}")
    print(f"  preenchidos nesta execucao={report['filled_this_run']}")
    print(f"  linhas IGNORADO={report['ignored_rows']}")
    print(f"  sem match (municipio real)={len(report['unmatched_real'])}")
    unmatched = report["unmatched_real"]
    if unmatched:
        print("  primeiros sem match:")
        for item in unmatched[:20]:
            print(f"    - {item}")
    if diagnose_only:
        print("  (nao sera escrita nesta etapa)")
    else:
        label = "arquivos que seriam alterados" if dry_run else "arquivos efetivamente alterados"
        print(f"  {label}:")
        for p in would if dry_run else changed:
            print(f"    - {p}")
    print("")


def enrich_competencia(
    *,
    ano: int,
    mes: int,
    gold_root: Path | None = None,
    geo_pr: Path | None = None,
    geo_rmc: Path | None = None,
    dry_run: bool = False,
    backup: bool = False,
    strict: bool = False,
    diagnose_national: bool = True,
    quiet_lookup: bool = False,
) -> dict[str, Any]:
    """Enriquece uma competência Gold. Retorna relatório estruturado.

    Raises:
        FileNotFoundError / ValueError em erros de leitura ou lookup.
    """
    root = Path(gold_root) if gold_root is not None else DEFAULT_GOLD_ROOT
    if not root.is_absolute():
        root = PROJECT_ROOT / root
    path_pr = Path(geo_pr) if geo_pr is not None else DEFAULT_GEO_PR
    path_rmc = Path(geo_rmc) if geo_rmc is not None else DEFAULT_GEO_RMC
    if not path_pr.is_absolute():
        path_pr = PROJECT_ROOT / path_pr
    if not path_rmc.is_absolute():
        path_rmc = PROJECT_ROOT / path_rmc

    partition = root / f"ano={ano}" / f"mes={mes:02d}"
    if not partition.is_dir():
        raise FileNotFoundError(f"Particao Gold nao encontrada: {partition}")

    if not quiet_lookup:
        print("=== Lookups GeoJSON ===")
    lookups = {
        "pr": load_geo_lookup(path_pr, quiet=quiet_lookup),
        "rmc": load_geo_lookup(path_rmc, quiet=quiet_lookup),
    }
    if not quiet_lookup:
        print("")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    table_reports: list[dict[str, Any]] = []
    any_target = False
    strict_fail = False

    if not quiet_lookup:
        print("=== Enriquecimento (PR / RMC / ICTT PR) ===")

    for table_name, geo_key in ENRICH_TARGETS:
        paths = resolve_table_paths(partition, table_name)
        if not paths:
            print(f"--- {table_name} ---")
            print("  AUSENTE (skip)")
            print("")
            continue
        df, _ = read_table(paths)
        out, report = enrich_dataframe(df, lookups[geo_key])
        report["table"] = table_name
        would, changed = write_table(
            out,
            paths,
            dry_run=dry_run,
            do_backup=backup,
            stamp=stamp,
        )
        any_target = True
        print_table_report(table_name, report, would, changed, dry_run=dry_run)
        table_reports.append(
            {
                **report,
                "would_change": would,
                "changed": changed,
            }
        )
        if strict and report["unmatched_real"]:
            strict_fail = True

    if diagnose_national:
        print("=== Diagnostico opcional (sem escrita): tabela_municipio ===")
        for table_name in DIAGNOSE_ONLY:
            paths = resolve_table_paths(partition, table_name)
            if not paths:
                print(f"--- {table_name} ---")
                print("  AUSENTE")
                print("")
                continue
            df, _ = read_table(paths)
            _, report_pr = enrich_dataframe(df, lookups["pr"])
            print(f"--- {table_name} [DIAGNOSE-ONLY] ---")
            print(f"  rows={report_pr['rows']}")
            print(
                "  nota: tabela nacional nao e enriquecida nesta etapa "
                "(lookup PR casaria apenas municipios do Parana)."
            )
            print(
                f"  hipotese lookup PR: preenchidos={report_pr['after_filled']} "
                f"sem match real={len(report_pr['unmatched_real'])} "
                f"(inclui UFs fora do PR; esperado)"
            )
            print("  (nenhum arquivo sera alterado)")
            print("")

    if not any_target:
        raise FileNotFoundError(
            f"Nenhuma tabela alvo encontrada em {partition} "
            f"({', '.join(t for t, _ in ENRICH_TARGETS)})"
        )

    result = {
        "ano": ano,
        "mes": mes,
        "partition": str(partition),
        "dry_run": dry_run,
        "backup": backup,
        "strict": strict,
        "strict_fail": strict_fail,
        "ok": not strict_fail,
        "tables": table_reports,
        "stamp": stamp,
    }
    return result


def run_enrich_cod_municipio(
    ano: int,
    mes: int,
    *,
    gold_root: Path | str | None = None,
    geo_pr: Path | str | None = None,
    geo_rmc: Path | str | None = None,
    dry_run: bool = False,
    backup: bool = False,
    strict: bool = False,
    diagnose_national: bool = True,
) -> dict[str, Any]:
    """API operacional para jobs/CLI. Retorna relatório; levanta em erro de I/O."""
    root = Path(gold_root) if gold_root is not None else None
    pr = Path(geo_pr) if geo_pr is not None else None
    rmc = Path(geo_rmc) if geo_rmc is not None else None
    print(
        f"Enrich cod_municipio | competencia={ano}-{mes:02d} "
        f"| dry_run={dry_run} backup={backup} strict={strict}"
    )
    if root is not None:
        print(f"gold_root={root}")
    print("")
    result = enrich_competencia(
        ano=ano,
        mes=mes,
        gold_root=root,
        geo_pr=pr,
        geo_rmc=rmc,
        dry_run=dry_run,
        backup=backup,
        strict=strict,
        diagnose_national=diagnose_national,
    )
    if result["strict_fail"]:
        print("RESULTADO: strict falhou (municipio real sem match).")
    else:
        mode = "dry-run OK" if dry_run else "aplicacao OK"
        print(f"RESULTADO: {mode}.")
    return result
