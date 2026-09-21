"""Persistência atômica, idempotência e fail-fast de backfill vazio (tmp_path)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipelines.gold.compute_ictt_v2 import (
    CANONICAL_ARTIFACT,
    CSV_ARTIFACT_ROLE,
    OUTPUT_COLUMNS,
    OUTPUT_STEM,
    save_ictt_v2_table,
)
from pipelines.gold.ictt_v2.spec import frozen_spec
from pipelines.jobs.run_ictt_v2_backfill import BackfillSummary, main as backfill_main


def _tiny_v2_table() -> tuple[pd.DataFrame, dict]:
    spec = frozen_spec()
    df = pd.DataFrame(
        {
            "competencia": ["2026-04", "2026-04"],
            "uf": ["Paraná", "Paraná"],
            "cod_municipio": ["4106902", "4108304"],
            "municipio": ["Curitiba", "Foz do Iguaçu"],
            "municipio_norm": ["CURITIBA", "FOZ DO IGUACU"],
            "admissoes": [25, 9],
            "desligamentos": [10, 3],
            "n_movimentacoes": [35, 12],
            "saldo": [15, 6],
            "calculavel": pd.array([True, False], dtype="boolean"),
            "reliability_class": pd.array(["higher", pd.NA], dtype="string"),
            "a_volume_raw": [3.2, 2.3],
            "a_volume_score": [40.0, 0.0],
            "a_saldo": [55.0, 50.0],
            "absorcao": [47.5, 25.0],
            "n_salarios_r4": [20, 0],
            "salario_mediano_r4_municipio": [2000.0, np.nan],
            "salario_mediano_r4_pr": [2000.0, 2000.0],
            "salario_relativo_r4": [1.0, np.nan],
            "remuneracao": [50.0, np.nan],
            "n_parcial": [0, 0],
            "perc_parcial_admissao": [0.0, np.nan],
            "q_parcial": [100.0, np.nan],
            "n_intermitente": [0, 0],
            "perc_intermitente_admissao": [0.0, np.nan],
            "q_intermitente": [100.0, np.nan],
            "qualidade_contratual": [100.0, np.nan],
            "shannon_cbo": [1.0, np.nan],
            "shannon_subclasse": [1.0, np.nan],
            "shannon_secao": [1.0, np.nan],
            "d_cbo": [40.0, np.nan],
            "d_subclasse": [40.0, np.nan],
            "d_secao": [40.0, np.nan],
            "diversificacao": [40.0, np.nan],
            "ictt_v2": [70.123, np.nan],
            "rank_n10": pd.array([1, pd.NA], dtype="Int64"),
            "rank_n20": pd.array([1, pd.NA], dtype="Int64"),
            "methodology_version": [spec.methodology_version, spec.methodology_version],
            "normalization_version": [spec.normalization_version, spec.normalization_version],
            "reference_period": [spec.reference_period, spec.reference_period],
        }
    )
    df = df.reindex(columns=list(OUTPUT_COLUMNS))
    audit = {
        "competencia": "2026-04",
        "methodology_version": spec.methodology_version,
        "normalization_version": spec.normalization_version,
        "malha_municipios": 2,
        "canonical_artifact": CANONICAL_ARTIFACT,
        "csv_role": CSV_ARTIFACT_ROLE,
    }
    return df, audit


def _canonical_paths(root: Path) -> tuple[Path, Path, Path]:
    return (
        root / f"{OUTPUT_STEM}.parquet",
        root / f"{OUTPUT_STEM}.csv",
        root / f"{OUTPUT_STEM}.metadata.json",
    )


def test_first_and_second_write_are_logically_idempotent(tmp_path: Path) -> None:
    df, audit = _tiny_v2_table()
    save_ictt_v2_table(df, audit, 2026, 4, output_dir=tmp_path)
    parquet, csv_path, meta = _canonical_paths(tmp_path)
    first = pd.read_parquet(parquet)
    save_ictt_v2_table(df, audit, 2026, 4, output_dir=tmp_path)
    second = pd.read_parquet(parquet)
    assert len(first) == len(second) == 2
    assert first["ictt_v2"].fillna(-1).equals(second["ictt_v2"].fillna(-1))
    assert first["rank_n10"].equals(second["rank_n10"])
    assert csv_path.is_file()
    assert meta.is_file()
    assert not list(tmp_path.glob("*.tmp"))


def test_failure_during_temp_write_keeps_previous_gold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    df, audit = _tiny_v2_table()
    save_ictt_v2_table(df, audit, 2026, 4, output_dir=tmp_path)
    parquet, _, _ = _canonical_paths(tmp_path)
    before = parquet.read_bytes()
    original = pd.DataFrame.to_csv

    def exploding(self, path=None, *args, **kwargs):
        if path is not None and str(path).endswith(".csv.tmp"):
            raise OSError("simulated csv tmp failure")
        return original(self, path, *args, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "to_csv", exploding)
    with pytest.raises(OSError, match="simulated csv tmp failure"):
        save_ictt_v2_table(df, audit, 2026, 4, output_dir=tmp_path)
    assert parquet.read_bytes() == before
    assert not list(tmp_path.glob("*.tmp"))


def test_failure_during_publish_keeps_previous_gold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import pipelines.gold.compute_ictt_v2 as module

    df, audit = _tiny_v2_table()
    save_ictt_v2_table(df, audit, 2026, 4, output_dir=tmp_path)
    parquet, _, _ = _canonical_paths(tmp_path)
    before = parquet.read_bytes()

    def exploding(src, dst):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(module, "_replace_atomic", exploding)
    with pytest.raises(OSError, match="simulated replace failure"):
        save_ictt_v2_table(df, audit, 2026, 4, output_dir=tmp_path)
    assert parquet.read_bytes() == before
    assert not list(tmp_path.glob("*.tmp"))


def test_valid_write_after_failure_replaces_gold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import pipelines.gold.compute_ictt_v2 as module

    df, audit = _tiny_v2_table()
    save_ictt_v2_table(df, audit, 2026, 4, output_dir=tmp_path)

    def exploding(src, dst):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(module, "_replace_atomic", exploding)
    with pytest.raises(OSError):
        save_ictt_v2_table(df, audit, 2026, 4, output_dir=tmp_path)
    monkeypatch.undo()

    df2 = df.copy()
    df2.loc[0, "ictt_v2"] = 71.5
    save_ictt_v2_table(df2, audit, 2026, 4, output_dir=tmp_path)
    parquet, _, _ = _canonical_paths(tmp_path)
    reloaded = pd.read_parquet(parquet)
    assert reloaded.loc[0, "ictt_v2"] == pytest.approx(71.5)
    assert not list(tmp_path.glob("*.tmp"))
    assert not any(path.name.endswith(".tmp") for path in tmp_path.iterdir())


def test_tmp_is_not_canonical_gold_name(tmp_path: Path) -> None:
    df, audit = _tiny_v2_table()
    parquet, csv_path, meta = save_ictt_v2_table(df, audit, 2026, 4, output_dir=tmp_path)
    assert parquet.name == f"{OUTPUT_STEM}.parquet"
    assert csv_path.name == f"{OUTPUT_STEM}.csv"
    assert meta.name == f"{OUTPUT_STEM}.metadata.json"
    assert CANONICAL_ARTIFACT == "parquet"
    loaded = pd.read_parquet(parquet)
    assert str(loaded["calculavel"].dtype) == "boolean"
    assert str(loaded["rank_n10"].dtype) == "Int64"
    assert str(loaded["rank_n20"].dtype) == "Int64"
    assert pd.api.types.is_float_dtype(loaded["ictt_v2"])


def test_backfill_empty_interval_exits_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    import pipelines.jobs.run_ictt_v2_backfill as job

    empty = BackfillSummary(dry_run=False, overwrite=True, results=[])
    monkeypatch.setattr(job, "run_backfill", lambda **kwargs: empty)
    assert backfill_main(["--start", "2099-01", "--end", "2099-01"]) == 1
