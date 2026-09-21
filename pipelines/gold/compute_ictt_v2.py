"""
Cálculo do ICTT v2.0 — paralelo à V1.

Não substitui ``compute_ictt.py``. Não grava ``tabela_ictt_municipio_pr``.
Não recalcula P05/P95. Não altera API, frontend nem PostGIS.
"""

from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.core.config import PIPELINE_LOG_FILE
from app.core.logging import setup_logger
from pipelines.common.utils import ensure_dir, save_json
from pipelines.gold.aggregate_indicators import gold_mes_dir
from pipelines.gold.compute_ictt import (
    _is_sim,
    _valid_salary,
    aggregate_municipal_indicators,
    ensure_input_columns,
    expand_to_municipality_universe,
    filter_scope,
    load_municipality_universe,
    resolve_geojson_path,
    silver_parquet_path,
)
from pipelines.gold.enrich_cod_municipio import load_geo_lookup, normalize_key
from pipelines.gold.ictt_v2.spec import (
    RELIABILITY_HIGHER,
    RELIABILITY_REDUCED,
    classify_reliability,
    frozen_spec,
    get_salario_minimo,
    quality_component,
    r4_eligible_mask,
    score_frozen,
)

logger = setup_logger("gold.ictt_v2", PIPELINE_LOG_FILE)

OUTPUT_STEM = "tabela_ictt_v2_municipio_pr"
OUTPUT_SUBDIR = "ictt_v2"
V1_OUTPUT_STEM = "tabela_ictt_municipio_pr"
CANONICAL_ARTIFACT = "parquet"
CSV_ARTIFACT_ROLE = "auxiliary_export"

# Colunas Silver indispensáveis ao construto v2.0 (R4, Q3, Shannon, absorção).
REQUIRED_SILVER_COLUMNS_V2: tuple[str, ...] = (
    "municipio",
    "uf",
    "saldomovimentacao",
    "admissao",
    "desligamento",
    "salario",
    "indtrabintermitente",
    "indtrabparcial",
    "cbo2002ocupacao",
    "subclasse",
    "secao",
)

OUTPUT_COLUMNS: tuple[str, ...] = (
    "competencia",
    "uf",
    "cod_municipio",
    "municipio",
    "municipio_norm",
    "admissoes",
    "desligamentos",
    "n_movimentacoes",
    "saldo",
    "calculavel",
    "reliability_class",
    "a_volume_raw",
    "a_volume_score",
    "a_saldo",
    "absorcao",
    "n_salarios_r4",
    "salario_mediano_r4_municipio",
    "salario_mediano_r4_pr",
    "salario_relativo_r4",
    "remuneracao",
    "n_parcial",
    "perc_parcial_admissao",
    "q_parcial",
    "n_intermitente",
    "perc_intermitente_admissao",
    "q_intermitente",
    "qualidade_contratual",
    "shannon_cbo",
    "shannon_subclasse",
    "shannon_secao",
    "d_cbo",
    "d_subclasse",
    "d_secao",
    "diversificacao",
    "ictt_v2",
    "rank_n10",
    "rank_n20",
    "methodology_version",
    "normalization_version",
    "reference_period",
)


class IcttV2InputError(ValueError):
    """Silver sem colunas indispensáveis ao ICTT v2.0."""


class IcttV2PersistError(ValueError):
    """Falha na validação ou publicação dos artefatos Gold v2."""


def validate_v2_silver_columns(df: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_SILVER_COLUMNS_V2 if col not in df.columns]
    if missing:
        raise IcttV2InputError(
            "Colunas obrigatórias ausentes para ICTT v2.0: " + ", ".join(missing) + "."
        )


def gold_v2_dir(ano: int, mes: int) -> Path:
    return gold_mes_dir(ano, mes) / OUTPUT_SUBDIR


def gold_v2_parquet_path(ano: int, mes: int) -> Path:
    return gold_v2_dir(ano, mes) / f"{OUTPUT_STEM}.parquet"


def gold_v2_csv_path(ano: int, mes: int) -> Path:
    return gold_v2_dir(ano, mes) / f"{OUTPUT_STEM}.csv"


def gold_v2_metadata_path(ano: int, mes: int) -> Path:
    return gold_v2_dir(ano, mes) / f"{OUTPUT_STEM}.metadata.json"


def v1_gold_parquet_path(ano: int, mes: int) -> Path:
    return gold_mes_dir(ano, mes) / f"{V1_OUTPUT_STEM}.parquet"


def _cod_municipio_lookup() -> dict[str, str]:
    geo_path = resolve_geojson_path("pr")
    return load_geo_lookup(geo_path, quiet=True)


def aggregate_r4_admissions(
    admissions: pd.DataFrame,
    salario_minimo: float,
) -> tuple[pd.DataFrame, float]:
    if admissions.empty:
        empty = pd.DataFrame(
            columns=["municipio_norm", "n_salarios_r4", "salario_mediano_r4_municipio"]
        )
        return empty, float("nan")

    eligible = r4_eligible_mask(
        admissions["salario"],
        admissions["indtrabintermitente"],
        salario_minimo,
    )
    sal = _valid_salary(admissions["salario"])
    work = admissions.loc[eligible].copy()
    work["_sal"] = sal.loc[eligible]
    if work.empty:
        empty = pd.DataFrame(
            columns=["municipio_norm", "n_salarios_r4", "salario_mediano_r4_municipio"]
        )
        return empty, float("nan")

    pr_median = float(work["_sal"].median())
    municipal = (
        work.groupby("municipio_norm", dropna=False)["_sal"]
        .agg(salario_mediano_r4_municipio="median", n_salarios_r4="size")
        .reset_index()
    )
    return municipal, pr_median


def aggregate_contract_flags(admissions: pd.DataFrame) -> pd.DataFrame:
    if admissions.empty:
        return pd.DataFrame(columns=["municipio_norm", "n_parcial", "n_intermitente"])
    work = admissions.assign(
        _parcial=_is_sim(admissions["indtrabparcial"]),
        _intermitente=_is_sim(admissions["indtrabintermitente"]),
    )
    return (
        work.groupby("municipio_norm", dropna=False)
        .agg(
            n_parcial=("_parcial", "sum"),
            n_intermitente=("_intermitente", "sum"),
        )
        .reset_index()
    )


def assign_ranks(ictt: pd.Series, admissoes: pd.Series) -> tuple[pd.Series, pd.Series]:
    """rank_n10: dense desc entre N>=10 com ICTT; rank_n20: idem N>=20, senão NA."""
    spec = frozen_spec()
    adm = pd.to_numeric(admissoes, errors="coerce").fillna(0)
    score = pd.to_numeric(ictt, errors="coerce")

    rank_n10 = pd.Series(pd.NA, index=ictt.index, dtype="Int64")
    mask10 = (adm >= spec.min_admissions_calculable) & score.notna()
    if mask10.any():
        rank_n10.loc[mask10] = (
            score.loc[mask10].rank(method="dense", ascending=False).round().astype("int64")
        )

    rank_n20 = pd.Series(pd.NA, index=ictt.index, dtype="Int64")
    mask20 = (adm >= spec.robust_admissions_threshold) & score.notna()
    if mask20.any():
        rank_n20.loc[mask20] = (
            score.loc[mask20].rank(method="dense", ascending=False).round().astype("int64")
        )
    return rank_n10, rank_n20


def _join_residue_audit(
    scoped: pd.DataFrame,
    universe: pd.DataFrame,
    mesh: pd.DataFrame,
) -> dict[str, Any]:
    admissoes_pr_micro = int(pd.to_numeric(scoped["admissao"], errors="coerce").fillna(0).sum())
    admissoes_na_malha = int(pd.to_numeric(mesh["admissoes"], errors="coerce").fillna(0).sum())
    diferenca = admissoes_pr_micro - admissoes_na_malha
    percentual = (
        100.0 * diferenca / admissoes_pr_micro if admissoes_pr_micro else float("nan")
    )
    uni = set(universe["municipio_norm"].astype(str))
    extra_mask = ~scoped["municipio_norm"].astype(str).isin(uni)
    extra = scoped.loc[extra_mask]
    extra_names = sorted(extra["municipio_norm"].dropna().astype(str).unique().tolist())
    extra_adm = int(pd.to_numeric(extra["admissao"], errors="coerce").fillna(0).sum())
    return {
        "admissoes_pr_micro": admissoes_pr_micro,
        "admissoes_na_malha": admissoes_na_malha,
        "diferenca": diferenca,
        "percentual_residuo_join": percentual,
        "municipios_fora_da_malha": extra_names,
        "admissoes_fora_da_malha": extra_adm,
        "causa": (
            "Município IGNORADO no microdado PR, sem correspondente na malha GeoJSON de 399 municípios."
            if extra_names == ["IGNORADO"]
            else "Municípios do microdado PR sem match na malha GeoJSON."
        ),
        "representacao": (
            "A malha Gold v2 segue a convenção V1: 399 municípios do GeoJSON. "
            "IGNORADO não entra como linha territorial; o resíduo fica só na auditoria da competência."
        ),
    }


def compute_ictt_v2_from_silver_df(
    silver: pd.DataFrame,
    *,
    ano: int,
    mes: int,
    generated_at: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Calcula ICTT v2.0 em memória. Não persiste e não toca a V1."""
    validate_v2_silver_columns(silver)
    spec = frozen_spec()
    salario_minimo = get_salario_minimo(ano, spec)
    competencia = f"{ano}-{mes:02d}"
    generated = generated_at or datetime.now(timezone.utc).isoformat()

    scoped = filter_scope(ensure_input_columns(silver), "pr")
    indicators = aggregate_municipal_indicators(scoped)
    universe = load_municipality_universe("pr")
    mesh = expand_to_municipality_universe(indicators, universe)

    admissions = scoped.loc[pd.to_numeric(scoped["admissao"], errors="coerce") == 1].copy()
    r4_mun, pr_r4_median = aggregate_r4_admissions(admissions, salario_minimo)
    flags = aggregate_contract_flags(admissions)

    out = mesh.merge(r4_mun, on="municipio_norm", how="left")
    out = out.merge(flags, on="municipio_norm", how="left")

    lookup = _cod_municipio_lookup()
    out["cod_municipio"] = out["municipio_norm"].map(
        lambda name: lookup.get(normalize_key(name) or "")
    )

    admissoes = pd.to_numeric(out["admissoes"], errors="coerce").fillna(0)
    desligamentos = pd.to_numeric(out["desligamentos"], errors="coerce").fillna(0)

    out["n_parcial"] = pd.to_numeric(out.get("n_parcial"), errors="coerce").fillna(0).astype("int64")
    out["n_intermitente"] = (
        pd.to_numeric(out.get("n_intermitente"), errors="coerce").fillna(0).astype("int64")
    )
    out["n_salarios_r4"] = (
        pd.to_numeric(out.get("n_salarios_r4"), errors="coerce").fillna(0).astype("int64")
    )

    has_adm = admissoes > 0
    out["perc_parcial_admissao"] = pd.Series(np.nan, index=out.index, dtype="float64")
    out["perc_intermitente_admissao"] = pd.Series(np.nan, index=out.index, dtype="float64")
    out.loc[has_adm, "perc_parcial_admissao"] = (
        100.0 * out.loc[has_adm, "n_parcial"] / admissoes.loc[has_adm]
    )
    out.loc[has_adm, "perc_intermitente_admissao"] = (
        100.0 * out.loc[has_adm, "n_intermitente"] / admissoes.loc[has_adm]
    )

    out["a_volume_raw"] = np.log1p(admissoes)
    out["a_volume_score"] = score_frozen(
        out["a_volume_raw"], spec.a_volume.p05, spec.a_volume.p95
    )
    out["a_saldo"] = 100.0 * (admissoes + spec.balance_c) / (
        admissoes + desligamentos + spec.balance_lambda
    )
    out["absorcao"] = (
        spec.absorption_volume_weight * out["a_volume_score"]
        + spec.absorption_balance_weight * out["a_saldo"]
    )

    out["salario_mediano_r4_pr"] = pr_r4_median
    mun_median = pd.to_numeric(out["salario_mediano_r4_municipio"], errors="coerce")
    if pd.notna(pr_r4_median) and pr_r4_median != 0:
        out["salario_relativo_r4"] = mun_median / pr_r4_median
    else:
        out["salario_relativo_r4"] = np.nan
    out["remuneracao"] = score_frozen(
        out["salario_relativo_r4"],
        spec.salario_relativo_r4.p05,
        spec.salario_relativo_r4.p95,
    )

    out["q_parcial"] = quality_component(out["perc_parcial_admissao"], spec.partial_penalty_k)
    out["q_intermitente"] = quality_component(
        out["perc_intermitente_admissao"], spec.intermittent_penalty_k
    )
    out["qualidade_contratual"] = (
        spec.contract_quality_partial_weight * out["q_parcial"]
        + spec.contract_quality_intermittent_weight * out["q_intermitente"]
    )

    out["d_cbo"] = score_frozen(out["shannon_cbo"], spec.shannon_cbo.p05, spec.shannon_cbo.p95)
    out["d_subclasse"] = score_frozen(
        out["shannon_subclasse"], spec.shannon_subclasse.p05, spec.shannon_subclasse.p95
    )
    out["d_secao"] = score_frozen(
        out["shannon_secao"], spec.shannon_secao.p05, spec.shannon_secao.p95
    )
    out["diversificacao"] = (
        spec.diversification_cbo_weight * out["d_cbo"]
        + spec.diversification_subclasse_weight * out["d_subclasse"]
        + spec.diversification_secao_weight * out["d_secao"]
    )

    calculavel, reliability = classify_reliability(admissoes)
    out["calculavel"] = calculavel
    out["reliability_class"] = reliability

    components_ok = (
        out["absorcao"].notna()
        & out["remuneracao"].notna()
        & out["qualidade_contratual"].notna()
        & out["diversificacao"].notna()
    )
    ictt = (
        spec.weight_absorption * out["absorcao"]
        + spec.weight_remuneration * out["remuneracao"]
        + spec.weight_contract_quality * out["qualidade_contratual"]
        + spec.weight_diversification * out["diversificacao"]
    )
    out["ictt_v2"] = ictt.where(calculavel & components_ok)

    rank_n10, rank_n20 = assign_ranks(out["ictt_v2"], admissoes)
    out["rank_n10"] = rank_n10
    out["rank_n20"] = rank_n20

    out["competencia"] = competencia
    out["methodology_version"] = spec.methodology_version
    out["normalization_version"] = spec.normalization_version
    out["reference_period"] = spec.reference_period

    n_calc = int(out["ictt_v2"].notna().sum())
    n_reduced = int((out["reliability_class"] == RELIABILITY_REDUCED).sum())
    n_higher = int((out["reliability_class"] == RELIABILITY_HIGHER).sum())

    audit = _join_residue_audit(scoped, universe, out)
    audit.update(
        {
            "competencia": competencia,
            "ano": ano,
            "mes": mes,
            "methodology_version": spec.methodology_version,
            "normalization_version": spec.normalization_version,
            "reference_period": spec.reference_period,
            "salario_minimo": salario_minimo,
            "salario_mediano_r4_pr": pr_r4_median,
            "malha_municipios": int(len(out)),
            "n_calculavel": int(calculavel.sum()),
            "n_ictt_v2": n_calc,
            "n_reliability_reduced": n_reduced,
            "n_reliability_higher": n_higher,
            "generated_at": generated,
            "output_stem": OUTPUT_STEM,
            "canonical_artifact": CANONICAL_ARTIFACT,
            "csv_role": CSV_ARTIFACT_ROLE,
        }
    )

    result = out.reindex(columns=list(OUTPUT_COLUMNS))
    result = result.sort_values(["municipio_norm"], kind="mergesort").reset_index(drop=True)
    return result, audit


def _replace_atomic(src: Path, dst: Path) -> None:
    """Publica um arquivo completo no destino. Atômico no mesmo filesystem (Windows/POSIX)."""
    os.replace(src, dst)


def _unlink_quietly(path: Path) -> None:
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass


def _validate_staged_v2_data(
    df: pd.DataFrame,
    audit: dict[str, Any],
    parquet_tmp: Path,
    csv_tmp: Path,
) -> None:
    parquet_df = pd.read_parquet(parquet_tmp)
    csv_df = pd.read_csv(csv_tmp)
    expected_rows = len(df)
    if len(parquet_df) != expected_rows or len(csv_df) != expected_rows:
        raise IcttV2PersistError(
            f"Row count inconsistente nos temporários: df={expected_rows} "
            f"parquet={len(parquet_df)} csv={len(csv_df)}."
        )
    competencia = str(df["competencia"].iloc[0]) if expected_rows else str(audit.get("competencia"))
    parquet_comp = str(parquet_df["competencia"].iloc[0]) if not parquet_df.empty else ""
    csv_comp = str(csv_df["competencia"].iloc[0]) if not csv_df.empty else ""
    methodology = str(df["methodology_version"].iloc[0]) if expected_rows else str(audit.get("methodology_version"))
    normalization = str(df["normalization_version"].iloc[0]) if expected_rows else str(audit.get("normalization_version"))
    if parquet_comp != competencia or csv_comp != competencia:
        raise IcttV2PersistError(
            f"competencia inconsistente nos temporários: df={competencia} "
            f"parquet={parquet_comp} csv={csv_comp}."
        )
    if str(audit.get("competencia")) != competencia:
        raise IcttV2PersistError("competencia do metadata difere da tabela.")
    if str(audit.get("methodology_version")) != methodology:
        raise IcttV2PersistError("methodology_version do metadata difere da tabela.")
    if str(audit.get("normalization_version")) != normalization:
        raise IcttV2PersistError("normalization_version do metadata difere da tabela.")
    if int(audit.get("malha_municipios", -1)) != expected_rows:
        raise IcttV2PersistError("malha_municipios do metadata difere do row count.")


def _validate_staged_v2_metadata(audit: dict[str, Any], meta_tmp: Path) -> None:
    payload = json.loads(meta_tmp.read_text(encoding="utf-8"))
    for key in ("competencia", "methodology_version", "normalization_version"):
        if payload.get(key) != audit.get(key):
            raise IcttV2PersistError(f"metadata temporário divergente em {key}.")
    if payload.get("canonical_artifact") != CANONICAL_ARTIFACT:
        raise IcttV2PersistError("canonical_artifact ausente ou inválido no metadata.")


def save_ictt_v2_table(
    df: pd.DataFrame,
    audit: dict[str, Any],
    ano: int,
    mes: int,
    *,
    output_dir: Path | None = None,
) -> tuple[Path, Path, Path]:
    """Substitui a competência V2 de forma atômica. Não toca artefatos V1.

    Parquet é o artefato canônico para consumo programático/API.
    CSV é exportação auxiliar.

    Visibilidade em falha:
    a) antes dos temporários — Gold anterior intacto;
    b) durante temporários — Gold anterior intacto; ``*.tmp`` são removidos;
    c) durante ``os.replace`` — cada arquivo publicado já está completo (nunca
       truncado). Há uma janela residual entre replaces sucessivos do trio;
       o metadata só é publicado depois de parquet e CSV válidos.
    """
    out_dir = Path(output_dir) if output_dir is not None else gold_v2_dir(ano, mes)
    ensure_dir(out_dir)
    parquet_path = out_dir / f"{OUTPUT_STEM}.parquet"
    csv_path = out_dir / f"{OUTPUT_STEM}.csv"
    meta_path = out_dir / f"{OUTPUT_STEM}.metadata.json"

    v1_path = v1_gold_parquet_path(ano, mes)
    if parquet_path.resolve() == v1_path.resolve():
        raise RuntimeError("Recusa: caminho Gold V2 colide com a tabela V1.")

    token = uuid.uuid4().hex
    tmp_parquet = out_dir / f"{OUTPUT_STEM}.{token}.parquet.tmp"
    tmp_csv = out_dir / f"{OUTPUT_STEM}.{token}.csv.tmp"
    tmp_meta = out_dir / f"{OUTPUT_STEM}.{token}.metadata.json.tmp"
    temps = (tmp_parquet, tmp_csv, tmp_meta)

    try:
        df.to_parquet(tmp_parquet, index=False)
        df.to_csv(tmp_csv, index=False, encoding="utf-8-sig")
        _validate_staged_v2_data(df, audit, tmp_parquet, tmp_csv)
        save_json(audit, tmp_meta)
        _validate_staged_v2_metadata(audit, tmp_meta)

        _replace_atomic(tmp_parquet, parquet_path)
        _replace_atomic(tmp_csv, csv_path)
        _replace_atomic(tmp_meta, meta_path)
    except Exception:
        for path in temps:
            _unlink_quietly(path)
        raise

    return parquet_path, csv_path, meta_path


def compute_ictt_v2(
    ano: int,
    mes: int,
    *,
    persist: bool = True,
    silver: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if not (1 <= mes <= 12):
        raise ValueError(f"mês inválido: {mes}")

    if silver is None:
        silver_path = silver_parquet_path(ano, mes)
        if not silver_path.is_file():
            raise FileNotFoundError(
                f"Silver não encontrada: {silver_path}. Execute o pipeline Silver antes do ICTT v2."
            )
        logger.info(
            "Iniciando ICTT v2.0 | ano=%s | mes=%02d | silver=%s",
            ano,
            mes,
            silver_path,
        )
        silver_df = pd.read_parquet(silver_path)
    else:
        logger.info("Iniciando ICTT v2.0 em memória | ano=%s | mes=%02d", ano, mes)
        silver_df = silver

    result, audit = compute_ictt_v2_from_silver_df(silver_df, ano=ano, mes=mes)

    if persist:
        parquet_path, csv_path, meta_path = save_ictt_v2_table(result, audit, ano, mes)
        logger.info(
            "ICTT v2.0 salvo | linhas=%s | calculaveis=%s | parquet=%s | csv=%s | meta=%s",
            len(result),
            audit["n_ictt_v2"],
            parquet_path,
            csv_path,
            meta_path,
        )
        logger.info(
            "Resíduo join territorial | micro=%s | malha=%s | diff=%s | perc=%.4f | causa=%s",
            audit["admissoes_pr_micro"],
            audit["admissoes_na_malha"],
            audit["diferenca"],
            audit["percentual_residuo_join"],
            audit["causa"],
        )
    return result


def print_ictt_v2_summary(result: pd.DataFrame) -> None:
    n = int(result["ictt_v2"].notna().sum())
    print(f"ICTT v2.0 | linhas={len(result)} | calculáveis={n}")
    ranked = result.loc[result["ictt_v2"].notna()].sort_values("rank_n10", kind="mergesort")
    cols = [
        "municipio",
        "admissoes",
        "ictt_v2",
        "rank_n10",
        "rank_n20",
        "reliability_class",
    ]
    if not ranked.empty:
        print(ranked[cols].head(10).to_string(index=False))


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calcula ICTT v2.0 municipal (Gold paralelo à V1)."
    )
    parser.add_argument("--ano", type=int, required=True)
    parser.add_argument("--mes", type=int, required=True)
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Calcula em memória sem gravar Gold.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = compute_ictt_v2(ano=args.ano, mes=args.mes, persist=not args.no_persist)
    print_ictt_v2_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
