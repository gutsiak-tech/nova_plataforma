"""Testes unitários do ICTT v2.0 (sem data lake)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pipelines.gold.compute_ictt_v2 import (
    IcttV2InputError,
    REQUIRED_SILVER_COLUMNS_V2,
    assign_ranks,
    compute_ictt_v2_from_silver_df,
)
from pipelines.gold.ictt_v2.spec import (
    RELIABILITY_HIGHER,
    RELIABILITY_REDUCED,
    SalarioMinimoNaoConfiguradoError,
    WEIGHT_SUM_ATOL,
    absorption_balance,
    classify_reliability,
    frozen_spec,
    get_salario_minimo,
    quality_component,
    r4_eligible_mask,
    score_frozen,
)


def test_score_frozen_below_p05_is_zero() -> None:
    assert score_frozen(0.0, 10.0, 20.0) == 0.0


def test_score_frozen_at_p05_is_zero() -> None:
    assert score_frozen(10.0, 10.0, 20.0) == 0.0


def test_score_frozen_midpoint() -> None:
    assert score_frozen(15.0, 10.0, 20.0) == pytest.approx(50.0)


def test_score_frozen_at_p95_is_100() -> None:
    assert score_frozen(20.0, 10.0, 20.0) == 100.0


def test_score_frozen_above_p95_is_100() -> None:
    assert score_frozen(30.0, 10.0, 20.0) == 100.0


def test_absorption_balance_equal_admissions_and_separations_near_50() -> None:
    score = absorption_balance(100, 100)
    assert score == pytest.approx(50.0, abs=1e-9)


def test_absorption_balance_more_admissions_increases_score() -> None:
    base = float(absorption_balance(100, 50))
    up = float(absorption_balance(120, 50))
    assert up > base


def test_absorption_balance_more_separations_decreases_score() -> None:
    base = float(absorption_balance(100, 50))
    down = float(absorption_balance(100, 80))
    assert down < base


def test_r4_excludes_intermittent() -> None:
    sm = 1621.0
    salario = pd.Series([2000.0, 2000.0])
    inter = pd.Series(["Não", "Sim"])
    mask = r4_eligible_mask(salario, inter, sm)
    assert mask.tolist() == [True, False]


def test_r4_excludes_below_0_3_sm() -> None:
    sm = 1621.0
    below = 0.3 * sm - 0.01
    salario = pd.Series([below])
    inter = pd.Series(["Não"])
    assert r4_eligible_mask(salario, inter, sm).tolist() == [False]


def test_r4_excludes_above_150_sm() -> None:
    sm = 1621.0
    above = 150 * sm + 0.01
    salario = pd.Series([above])
    inter = pd.Series(["Não"])
    assert r4_eligible_mask(salario, inter, sm).tolist() == [False]


def test_r4_includes_lower_bound() -> None:
    sm = 1621.0
    salario = pd.Series([0.3 * sm])
    inter = pd.Series(["Não"])
    assert r4_eligible_mask(salario, inter, sm).tolist() == [True]


def test_r4_includes_upper_bound() -> None:
    sm = 1621.0
    salario = pd.Series([150 * sm])
    inter = pd.Series(["Não"])
    assert r4_eligible_mask(salario, inter, sm).tolist() == [True]


def test_quality_zero_partial_is_100() -> None:
    assert quality_component(0.0, 10.0) == 100.0


def test_quality_ten_percent_partial_is_zero() -> None:
    assert quality_component(10.0, 10.0) == 0.0


def test_quality_above_ten_percent_stays_zero() -> None:
    assert quality_component(12.0, 10.0) == 0.0
    assert quality_component(50.0, 10.0) == 0.0


def test_quality_increasing_precarity_never_increases_q() -> None:
    percs = np.linspace(0, 20, 41)
    scores = np.array([quality_component(p, 10.0) for p in percs], dtype=float)
    assert np.all(np.diff(scores) <= 1e-12)


def test_reliability_9_not_calculable() -> None:
    calc, rel = classify_reliability(pd.Series([9]))
    assert bool(calc.iloc[0]) is False
    assert pd.isna(rel.iloc[0])


def test_reliability_10_reduced() -> None:
    calc, rel = classify_reliability(pd.Series([10]))
    assert bool(calc.iloc[0]) is True
    assert rel.iloc[0] == RELIABILITY_REDUCED


def test_reliability_19_reduced() -> None:
    calc, rel = classify_reliability(pd.Series([19]))
    assert bool(calc.iloc[0]) is True
    assert rel.iloc[0] == RELIABILITY_REDUCED


def test_reliability_20_higher() -> None:
    calc, rel = classify_reliability(pd.Series([20]))
    assert bool(calc.iloc[0]) is True
    assert rel.iloc[0] == RELIABILITY_HIGHER


def test_rank_n10_includes_n10_19_and_rank_n20_is_null() -> None:
    ictt = pd.Series([90.0, 80.0, 70.0, 60.0])
    adm = pd.Series([50, 15, 25, 9])
    rank_n10, rank_n20 = assign_ranks(ictt, adm)
    assert rank_n10.tolist() == [1, 2, 3, pd.NA]
    assert rank_n20.tolist() == [1, pd.NA, 2, pd.NA]


def test_salario_minimo_unknown_year_fails_explicitly() -> None:
    with pytest.raises(SalarioMinimoNaoConfiguradoError, match="Salário mínimo não configurado para o ano 2027"):
        get_salario_minimo(2027)


def test_salario_minimo_known_years() -> None:
    assert get_salario_minimo(2025) == 1518.0
    assert get_salario_minimo(2026) == 1621.0


def test_frozen_spec_equal_weights() -> None:
    spec = frozen_spec()
    assert spec.methodology_version == "2.0"
    assert spec.methodology_version == spec.raw["methodology_version"]
    assert spec.weight_absorption == spec.weight_remuneration == 0.25
    assert spec.weight_contract_quality == spec.weight_diversification == 0.25
    assert spec.shannon_universe == "all_movements"


def test_subdimension_weights_sum_to_one() -> None:
    spec = frozen_spec()
    assert spec.absorption_volume_weight + spec.absorption_balance_weight == pytest.approx(
        1.0, abs=WEIGHT_SUM_ATOL
    )
    assert (
        spec.contract_quality_partial_weight + spec.contract_quality_intermittent_weight
        == pytest.approx(1.0, abs=WEIGHT_SUM_ATOL)
    )
    assert (
        spec.diversification_cbo_weight
        + spec.diversification_subclasse_weight
        + spec.diversification_secao_weight
        == pytest.approx(1.0, abs=WEIGHT_SUM_ATOL)
    )


def _silver_stub_complete() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "municipio": ["Curitiba"],
            "uf": ["Paraná"],
            "saldomovimentacao": [1],
            "admissao": [1],
            "desligamento": [0],
            "salario": [2000.0],
            "indtrabintermitente": ["Não"],
            "indtrabparcial": ["Não"],
            "cbo2002ocupacao": ["517410"],
            "subclasse": ["5611201"],
            "secao": ["I"],
        }
    )


@pytest.mark.parametrize(
    "column",
    [
        "salario",
        "indtrabintermitente",
        "indtrabparcial",
        "cbo2002ocupacao",
        "subclasse",
        "secao",
    ],
)
def test_missing_required_v2_column_fails_fast(column: str) -> None:
    silver = _silver_stub_complete().drop(columns=[column])
    with pytest.raises(IcttV2InputError, match=column):
        compute_ictt_v2_from_silver_df(silver, ano=2026, mes=4)


def test_required_silver_columns_v2_are_canonical() -> None:
    assert REQUIRED_SILVER_COLUMNS_V2 == (
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


def test_published_fingerprints_match_frozen_rounding() -> None:
    spec = frozen_spec()
    mapping = {
        "a_volume_raw": spec.a_volume,
        "salario_relativo_r4": spec.salario_relativo_r4,
        "shannon_cbo": spec.shannon_cbo,
        "shannon_subclasse": spec.shannon_subclasse,
        "shannon_secao": spec.shannon_secao,
    }
    published = spec.published_fingerprints_4dp
    for key, bounds in mapping.items():
        assert round(bounds.p05, 4) == published[key]["p05"]
        assert round(bounds.p95, 4) == published[key]["p95"]
