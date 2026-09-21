"""Testes de monotonicidade da especificação congelada do ICTT v2.0."""

from __future__ import annotations

import numpy as np

from pipelines.gold.ictt_v2.spec import (
    absorption_balance,
    frozen_spec,
    quality_component,
    score_frozen,
)


def _ictt(absorcao: float, remuneracao: float, qualidade: float, diversificacao: float) -> float:
    spec = frozen_spec()
    return (
        spec.weight_absorption * absorcao
        + spec.weight_remuneration * remuneracao
        + spec.weight_contract_quality * qualidade
        + spec.weight_diversification * diversificacao
    )


def test_more_admissions_volume_score_does_not_fall() -> None:
    spec = frozen_spec()
    adm = np.arange(0, 400, dtype=float)
    raw = np.log1p(adm)
    scores = np.array(
        [score_frozen(x, spec.a_volume.p05, spec.a_volume.p95) for x in raw],
        dtype=float,
    )
    assert np.all(np.diff(scores) >= -1e-12)


def test_more_admissions_ceteris_paribus_balance_does_not_fall() -> None:
    des = 40.0
    adm = np.arange(0, 200, dtype=float)
    scores = np.array([absorption_balance(a, des) for a in adm], dtype=float)
    assert np.all(np.diff(scores) >= -1e-12)


def test_more_separations_balance_does_not_rise() -> None:
    adm = 80.0
    des = np.arange(0, 200, dtype=float)
    scores = np.array([absorption_balance(adm, d) for d in des], dtype=float)
    assert np.all(np.diff(scores) <= 1e-12)


def test_higher_relative_wage_remuneration_does_not_fall() -> None:
    spec = frozen_spec()
    rel = np.linspace(0.7, 1.3, 61)
    scores = np.array(
        [score_frozen(x, spec.salario_relativo_r4.p05, spec.salario_relativo_r4.p95) for x in rel],
        dtype=float,
    )
    assert np.all(np.diff(scores) >= -1e-12)


def test_higher_partial_quality_does_not_rise() -> None:
    spec = frozen_spec()
    perc = np.linspace(0, 20, 41)
    scores = np.array([quality_component(p, spec.partial_penalty_k) for p in perc], dtype=float)
    assert np.all(np.diff(scores) <= 1e-12)


def test_higher_intermittent_quality_does_not_rise() -> None:
    spec = frozen_spec()
    perc = np.linspace(0, 20, 41)
    scores = np.array(
        [quality_component(p, spec.intermittent_penalty_k) for p in perc], dtype=float
    )
    assert np.all(np.diff(scores) <= 1e-12)


def test_higher_shannon_diversification_does_not_fall() -> None:
    spec = frozen_spec()
    sh = np.linspace(0, 5, 51)
    d_cbo = np.array([score_frozen(x, spec.shannon_cbo.p05, spec.shannon_cbo.p95) for x in sh])
    d_sub = np.array(
        [score_frozen(x, spec.shannon_subclasse.p05, spec.shannon_subclasse.p95) for x in sh]
    )
    d_sec = np.array([score_frozen(x, spec.shannon_secao.p05, spec.shannon_secao.p95) for x in sh])
    divers = (d_cbo + d_sub + d_sec) / 3.0
    assert np.all(np.diff(d_cbo) >= -1e-12)
    assert np.all(np.diff(d_sub) >= -1e-12)
    assert np.all(np.diff(d_sec) >= -1e-12)
    assert np.all(np.diff(divers) >= -1e-12)


def test_raising_each_dimension_does_not_lower_ictt() -> None:
    base = _ictt(40, 40, 40, 40)
    assert _ictt(50, 40, 40, 40) >= base
    assert _ictt(40, 50, 40, 40) >= base
    assert _ictt(40, 40, 50, 40) >= base
    assert _ictt(40, 40, 40, 50) >= base
    grid = np.linspace(0, 100, 11)
    for name in ("absorcao", "remuneracao", "qualidade", "diversificacao"):
        scores = []
        for value in grid:
            kwargs = dict(absorcao=40.0, remuneracao=40.0, qualidade=40.0, diversificacao=40.0)
            kwargs[name] = float(value)
            scores.append(_ictt(**kwargs))
        assert np.all(np.diff(np.array(scores)) >= -1e-12), name
