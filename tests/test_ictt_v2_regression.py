"""Invariância da V1, NORM_B congelado e regressão abril/2026 do ICTT v2.0."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipelines.gold.compute_ictt import (
    _has_sufficient_data,
    add_tooltip_resumo,
    aggregate_municipal_indicators,
    build_output_table,
    compute_dimension_scores,
    compute_final_ictt,
    compute_ictt_derivatives,
    ensure_input_columns,
    expand_to_municipality_universe,
    filter_scope,
    load_municipality_universe,
    silver_parquet_path,
)
from pipelines.gold.compute_ictt_v2 import (
    OUTPUT_STEM,
    V1_OUTPUT_STEM,
    compute_ictt_v2,
    gold_v2_parquet_path,
    v1_gold_parquet_path,
)
from pipelines.gold.ictt_v2.spec import frozen_spec, get_salario_minimo, r4_eligible_mask

# Fingerprints congelados a partir do Gold V2 de abril/2026 (não gerados pela função sob teste).
APRIL_FINGERPRINTS = {
    "FOZ DO IGUACU": {
        "ictt": 82.86469407999354,
        "rank_n10": 1,
        "rank_n20": 1,
        "reliability": "higher",
    },
    "SAO JOSE DOS PINHAIS": {
        "ictt": 78.42817799647243,
        "rank_n10": 2,
        "rank_n20": 2,
        "reliability": "higher",
    },
    "CURITIBA": {
        "ictt": 74.27650651359386,
        "rank_n10": 9,
        "rank_n20": 9,
        "reliability": "higher",
    },
    "LONDRINA": {
        "ictt": 71.30359095591106,
        "rank_n10": 11,
        "rank_n20": 11,
        "reliability": "higher",
    },
    "PONTA GROSSA": {
        "ictt": 64.10927566100817,
        "rank_n10": 27,
        "rank_n20": 24,
        "reliability": "higher",
    },
    "GUARAPUAVA": {
        "ictt": 59.70914772764678,
        "rank_n10": 37,
        "rank_n20": None,
        "reliability": "reduced",
    },
}
APRIL_N_CALCULABLE = 59
ICTT_ATOL = 1e-12


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_silver(ano: int, mes: int) -> Path:
    path = silver_parquet_path(ano, mes)
    if not path.is_file():
        pytest.skip(f"Silver ausente: {path}")
    return path


def reproduce_v1_in_memory(ano: int, mes: int) -> pd.DataFrame:
    silver = pd.read_parquet(silver_parquet_path(ano, mes))
    scoped = filter_scope(ensure_input_columns(silver), "pr")
    indicators = aggregate_municipal_indicators(scoped)
    universe = load_municipality_universe("pr")
    indicators = expand_to_municipality_universe(indicators, universe)
    sufficient = indicators.apply(_has_sufficient_data, axis=1)
    indicators = compute_dimension_scores(indicators, sufficient)
    indicators = compute_final_ictt(indicators)
    indicators = compute_ictt_derivatives(indicators)
    indicators = add_tooltip_resumo(indicators)
    return build_output_table(indicators, ano=ano, mes=mes)


def derive_norm_b_from_lake() -> dict[str, tuple[float, float]]:
    spec = frozen_spec()
    universe = load_municipality_universe("pr")
    frames: list[pd.DataFrame] = []
    start_y, start_m = map(int, spec.reference_start.split("-"))
    end_y, end_m = map(int, spec.reference_end.split("-"))
    assert (start_y, start_m) == (2026, 1)
    assert (end_y, end_m) == (2026, 4)

    for mes in range(1, 5):
        _require_silver(2026, mes)
        silver = pd.read_parquet(silver_parquet_path(2026, mes))
        scoped = filter_scope(ensure_input_columns(silver), "pr")
        mesh = expand_to_municipality_universe(
            aggregate_municipal_indicators(scoped), universe
        )
        sm = get_salario_minimo(2026)
        adm = scoped.loc[pd.to_numeric(scoped["admissao"], errors="coerce") == 1].copy()
        ok = r4_eligible_mask(adm["salario"], adm["indtrabintermitente"], sm)
        from pipelines.gold.compute_ictt import _valid_salary

        sal = _valid_salary(adm["salario"])
        work = adm.loc[ok].assign(_sal=sal.loc[ok])
        pr_r4 = float(work["_sal"].median())
        med = work.groupby("municipio_norm")["_sal"].median()
        n10 = mesh.loc[
            pd.to_numeric(mesh["admissoes"], errors="coerce") >= spec.reference_min_admissions
        ].copy()
        n10["a_volume_raw"] = np.log1p(pd.to_numeric(n10["admissoes"], errors="coerce"))
        n10["salario_relativo_r4"] = n10["municipio_norm"].map(med) / pr_r4
        frames.append(
            n10[
                [
                    "a_volume_raw",
                    "salario_relativo_r4",
                    "shannon_cbo",
                    "shannon_subclasse",
                    "shannon_secao",
                ]
            ]
        )

    pool = pd.concat(frames, ignore_index=True)
    assert len(pool) == spec.reference_pooled_n

    def bounds(col: str) -> tuple[float, float]:
        series = pd.to_numeric(pool[col], errors="coerce").dropna()
        return float(series.quantile(0.05)), float(series.quantile(0.95))

    return {
        "a_volume_raw": bounds("a_volume_raw"),
        "salario_relativo_r4": bounds("salario_relativo_r4"),
        "shannon_cbo": bounds("shannon_cbo"),
        "shannon_subclasse": bounds("shannon_subclasse"),
        "shannon_secao": bounds("shannon_secao"),
    }


def test_v1_gold_files_exist_for_invariance() -> None:
    for mes in range(1, 5):
        path = v1_gold_parquet_path(2026, mes)
        assert path.is_file(), path
        assert path.name == f"{V1_OUTPUT_STEM}.parquet"


def test_v1_invariance_in_memory_matches_gold() -> None:
    diffs: list[float] = []
    for mes in range(1, 5):
        gold_path = v1_gold_parquet_path(2026, mes)
        if not gold_path.is_file():
            pytest.skip(f"Gold V1 ausente: {gold_path}")
        _require_silver(2026, mes)
        gold = pd.read_parquet(gold_path)
        repro = reproduce_v1_in_memory(2026, mes)
        merged = gold.merge(
            repro,
            on="municipio_norm",
            suffixes=("_gold", "_repro"),
            how="inner",
        )
        delta = (
            pd.to_numeric(merged["ICTT_gold"], errors="coerce")
            - pd.to_numeric(merged["ICTT_repro"], errors="coerce")
        ).abs()
        comparable = merged["ICTT_gold"].notna() | merged["ICTT_repro"].notna()
        max_abs = float(delta.loc[comparable].max()) if comparable.any() else 0.0
        diffs.append(max_abs)
        rank_delta = (
            pd.to_numeric(merged["ranking_ictt_gold"], errors="coerce")
            - pd.to_numeric(merged["ranking_ictt_repro"], errors="coerce")
        ).abs()
        rank_max = float(np.nanmax(rank_delta.to_numpy())) if rank_delta.notna().any() else 0.0
        assert rank_max == 0.0
        status_mismatch = (
            merged["status_calculo_gold"].astype(str) != merged["status_calculo_repro"].astype(str)
        )
        assert not status_mismatch.any()
    assert max(diffs) == 0.0, diffs


def test_v2_output_path_is_not_v1_path() -> None:
    v2 = gold_v2_parquet_path(2026, 4)
    v1 = v1_gold_parquet_path(2026, 4)
    assert v2.resolve() != v1.resolve()
    assert v2.name == f"{OUTPUT_STEM}.parquet"
    assert V1_OUTPUT_STEM not in str(v2.parent)


def test_norm_b_reproduction_matches_frozen_full_precision() -> None:
    derived = derive_norm_b_from_lake()
    spec = frozen_spec()
    expected = {
        "a_volume_raw": spec.a_volume,
        "salario_relativo_r4": spec.salario_relativo_r4,
        "shannon_cbo": spec.shannon_cbo,
        "shannon_subclasse": spec.shannon_subclasse,
        "shannon_secao": spec.shannon_secao,
    }
    for key, bounds in expected.items():
        p05, p95 = derived[key]
        assert p05 == pytest.approx(bounds.p05, abs=1e-12), key
        assert p95 == pytest.approx(bounds.p95, abs=1e-12), key
        pub = spec.published_fingerprints_4dp[key]
        assert round(p05, 4) == pub["p05"]
        assert round(p95, 4) == pub["p95"]


def test_april_2026_regression_fingerprints() -> None:
    _require_silver(2026, 4)
    v1_path = v1_gold_parquet_path(2026, 4)
    v1_hash = _sha256(v1_path) if v1_path.is_file() else None
    v1_schema = list(pd.read_parquet(v1_path).columns) if v1_path.is_file() else None

    result = compute_ictt_v2(ano=2026, mes=4, persist=False)
    n_calc = int(result["ictt_v2"].notna().sum())
    assert n_calc == APRIL_N_CALCULABLE
    assert int((result["admissoes"] < 10).sum() + (result["admissoes"] >= 10).sum()) == len(result)
    assert result.loc[result["admissoes"] < 10, "ictt_v2"].isna().all()
    reduced = result.loc[
        (result["admissoes"] >= 10) & (result["admissoes"] < 20)
    ]
    higher = result.loc[result["admissoes"] >= 20]
    assert (reduced["reliability_class"] == "reduced").all()
    assert (higher["reliability_class"] == "higher").all()
    assert reduced["rank_n20"].isna().all()
    assert reduced["rank_n10"].notna().all()
    assert higher["rank_n20"].notna().all()

    by_name = result.set_index("municipio_norm")
    for name, expected in APRIL_FINGERPRINTS.items():
        row = by_name.loc[name]
        assert row["ictt_v2"] == pytest.approx(expected["ictt"], abs=ICTT_ATOL), name
        if expected.get("rank_n10") is not None:
            assert int(row["rank_n10"]) == expected["rank_n10"]
        if expected.get("rank_n20") is None:
            assert pd.isna(row["rank_n20"])
        else:
            assert int(row["rank_n20"]) == expected["rank_n20"]
        if expected.get("reliability"):
            assert row["reliability_class"] == expected["reliability"]

    if v1_hash is not None:
        assert _sha256(v1_path) == v1_hash
        assert list(pd.read_parquet(v1_path).columns) == v1_schema


def test_gold_v2_parquet_is_canonical_schema() -> None:
    path = gold_v2_parquet_path(2026, 4)
    if not path.is_file():
        pytest.skip(f"Gold V2 ausente: {path}")
    df = pd.read_parquet(path)
    assert str(df["calculavel"].dtype) == "boolean"
    assert str(df["rank_n10"].dtype) == "Int64"
    assert str(df["rank_n20"].dtype) == "Int64"
    assert pd.api.types.is_float_dtype(df["ictt_v2"])

