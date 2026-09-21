"""Regressão holdout 2025 em memória. Não persiste no lake."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

from pipelines.bronze.prepare_migrantes_bronze import (
    filter_by_competencia,
    prepare_migrantes_dataframe,
    read_migrantes_csv,
)
from pipelines.common.dictionaries import mapeamentos
from pipelines.gold.compute_ictt_v2 import compute_ictt_v2
from pipelines.silver.clean_caged import (
    aplicar_mapeamentos_categoricos,
    classificar_faixa_etaria,
    converter_coluna_numerica,
    limpar_texto_geral,
    normalizar_nome_coluna,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HOLDOUT_RELATIVE = (
    _REPO_ROOT
    / "data-lake"
    / "raw"
    / "migrantes"
    / "ano=2025"
    / "RAIS_CTPS_CAGED_2025_MOV.csv"
)
HOLDOUT_2025_01 = {"n_calculable": 53, "mean_ictt": 62.64, "foz_rank": 1}
MEAN_ATOL = 0.08
_HOLDOUT_NOT_RUN = (
    "Holdout 2025 skipped: dataset externo ausente. "
    "Defina ICTT_V2_HOLDOUT_CSV ou coloque o CSV em "
    "data-lake/raw/migrantes/ano=2025/. O arquivo não é versionado."
)


def _holdout_path() -> Path | None:
    env = os.environ.get("ICTT_V2_HOLDOUT_CSV")
    if env:
        candidate = Path(env)
        if candidate.is_file():
            return candidate
    if _HOLDOUT_RELATIVE.is_file():
        return _HOLDOUT_RELATIVE
    return None


def silver_from_bronze_df(bronze: pd.DataFrame, ano: int, mes: int) -> pd.DataFrame:
    df = bronze.copy()
    df.columns = [normalizar_nome_coluna(col) for col in df.columns]
    df["ano"] = ano
    df["mes"] = mes
    df["competencia_str"] = f"{ano}-{mes:02d}"
    numeric_cols = [
        "idade",
        "horascontratuais",
        "salario",
        "valorsalariofixo",
        "saldomovimentacao",
        "subclasse",
        "cbo2002ocupacao",
        "municipio",
        "uf",
        "categoria",
        "indtrabparcial",
        "indtrabintermitente",
    ]
    for col in numeric_cols:
        if col in df.columns:
            converter_coluna_numerica(df, col, diagnosticar=False)
    if "idade" in df.columns:
        df["faixa_etaria"] = df["idade"].apply(classificar_faixa_etaria)
    df = df.dropna(subset=["saldomovimentacao"]).copy()
    df["admissao"] = (df["saldomovimentacao"] == 1).astype(int)
    df["desligamento"] = (df["saldomovimentacao"] == -1).astype(int)
    for col in df.select_dtypes(include=["object", "string"]).columns.tolist():
        df[col] = limpar_texto_geral(df[col])
    excluded = {
        "horascontratuais",
        "salario",
        "valorsalariofixo",
        "idade",
        "ano",
        "mes",
        "competencia_str",
        "admissao",
        "desligamento",
        "saldomovimentacao",
    }
    df = aplicar_mapeamentos_categoricos(df, mapeamentos, excluir_colunas=list(excluded))
    return df


@pytest.mark.integration
@pytest.mark.slow
def test_holdout_2025_in_memory_or_explicit_skip() -> None:
    path = _holdout_path()
    if path is None:
        pytest.skip(_HOLDOUT_NOT_RUN)

    raw = read_migrantes_csv(path)
    month = filter_by_competencia(raw, 2025, 1)
    prepared = prepare_migrantes_dataframe(month)
    silver = silver_from_bronze_df(prepared, 2025, 1)
    result = compute_ictt_v2(ano=2025, mes=1, persist=False, silver=silver)

    n_calc = int(result["ictt_v2"].notna().sum())
    mean_ictt = float(result["ictt_v2"].mean())
    foz = result.loc[result["municipio_norm"] == "FOZ DO IGUACU"].iloc[0]

    assert n_calc == HOLDOUT_2025_01["n_calculable"]
    assert mean_ictt == pytest.approx(HOLDOUT_2025_01["mean_ictt"], abs=MEAN_ATOL)
    assert int(foz["rank_n10"]) == HOLDOUT_2025_01["foz_rank"]
    assert result.loc[result["admissoes"] < 10, "ictt_v2"].isna().all()
