"""Parâmetros congelados do ICTT v2.0.

O runtime apenas lê esta configuração. P05/P95 (NORM_B) não são recalculados
em produção nem durante backfill. A fonte de verdade da versão metodológica
é ``methodology_v2.json``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

SPEC_FILENAME = "methodology_v2.json"
SPEC_PATH = Path(__file__).resolve().parent / SPEC_FILENAME

RELIABILITY_REDUCED = "reduced"
RELIABILITY_HIGHER = "higher"
WEIGHT_SUM_ATOL = 1e-9


class SalarioMinimoNaoConfiguradoError(ValueError):
    """Ano sem salário mínimo versionado — falha explícita, sem fallback."""


class IcttV2SpecError(ValueError):
    """Configuração metodológica v2 inválida."""


@dataclass(frozen=True)
class FrozenBounds:
    p05: float
    p95: float


@dataclass(frozen=True)
class IcttV2Spec:
    methodology_version: str
    normalization_version: str
    reference_scope: str
    reference_start: str
    reference_end: str
    reference_min_admissions: int
    reference_pooled_n: int
    shannon_universe: str
    weight_absorption: float
    weight_remuneration: float
    weight_contract_quality: float
    weight_diversification: float
    absorption_volume_weight: float
    absorption_balance_weight: float
    contract_quality_partial_weight: float
    contract_quality_intermittent_weight: float
    diversification_cbo_weight: float
    diversification_subclasse_weight: float
    diversification_secao_weight: float
    balance_c: float
    balance_lambda: float
    partial_penalty_k: float
    intermittent_penalty_k: float
    min_admissions_calculable: int
    robust_admissions_threshold: int
    r4_salary_lower_sm: float
    r4_salary_upper_sm: float
    salario_minimo_por_ano: Mapping[int, float]
    a_volume: FrozenBounds
    salario_relativo_r4: FrozenBounds
    shannon_cbo: FrozenBounds
    shannon_subclasse: FrozenBounds
    shannon_secao: FrozenBounds
    published_fingerprints_4dp: Mapping[str, Mapping[str, float]]
    raw: Mapping[str, Any]

    @property
    def reference_period(self) -> str:
        return f"{self.reference_start}/{self.reference_end}"


def _bounds(payload: Mapping[str, Any]) -> FrozenBounds:
    return FrozenBounds(p05=float(payload["p05"]), p95=float(payload["p95"]))


def _require_unit_sum(values: Sequence[float], label: str) -> None:
    total = float(sum(values))
    if abs(total - 1.0) > WEIGHT_SUM_ATOL:
        raise IcttV2SpecError(
            f"Pesos de {label} somam {total}, esperado 1.0 (atol={WEIGHT_SUM_ATOL})."
        )


def _validate_weight_groups(spec: IcttV2Spec) -> None:
    _require_unit_sum(
        (
            spec.weight_absorption,
            spec.weight_remuneration,
            spec.weight_contract_quality,
            spec.weight_diversification,
        ),
        "ICTT v2",
    )
    _require_unit_sum(
        (spec.absorption_volume_weight, spec.absorption_balance_weight),
        "absorção",
    )
    _require_unit_sum(
        (
            spec.contract_quality_partial_weight,
            spec.contract_quality_intermittent_weight,
        ),
        "qualidade contratual",
    )
    _require_unit_sum(
        (
            spec.diversification_cbo_weight,
            spec.diversification_subclasse_weight,
            spec.diversification_secao_weight,
        ),
        "diversificação",
    )


@lru_cache(maxsize=1)
def frozen_spec() -> IcttV2Spec:
    payload = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    sm_raw = payload["salario_minimo_por_ano"]
    salario_minimo = {int(year): float(value) for year, value in sm_raw.items()}
    norm = payload["norm_b"]
    spec = IcttV2Spec(
        methodology_version=str(payload["methodology_version"]),
        normalization_version=str(payload["normalization_version"]),
        reference_scope=str(payload["reference_scope"]),
        reference_start=str(payload["reference_start"]),
        reference_end=str(payload["reference_end"]),
        reference_min_admissions=int(payload["reference_min_admissions"]),
        reference_pooled_n=int(payload["reference_pooled_n"]),
        shannon_universe=str(payload["shannon_universe"]),
        weight_absorption=float(payload["weight_absorption"]),
        weight_remuneration=float(payload["weight_remuneration"]),
        weight_contract_quality=float(payload["weight_contract_quality"]),
        weight_diversification=float(payload["weight_diversification"]),
        absorption_volume_weight=float(payload["absorption_volume_weight"]),
        absorption_balance_weight=float(payload["absorption_balance_weight"]),
        contract_quality_partial_weight=float(payload["contract_quality_partial_weight"]),
        contract_quality_intermittent_weight=float(
            payload["contract_quality_intermittent_weight"]
        ),
        diversification_cbo_weight=float(payload["diversification_cbo_weight"]),
        diversification_subclasse_weight=float(payload["diversification_subclasse_weight"]),
        diversification_secao_weight=float(payload["diversification_secao_weight"]),
        balance_c=float(payload["balance_c"]),
        balance_lambda=float(payload["balance_lambda"]),
        partial_penalty_k=float(payload["partial_penalty_k"]),
        intermittent_penalty_k=float(payload["intermittent_penalty_k"]),
        min_admissions_calculable=int(payload["min_admissions_calculable"]),
        robust_admissions_threshold=int(payload["robust_admissions_threshold"]),
        r4_salary_lower_sm=float(payload["r4_salary_lower_sm"]),
        r4_salary_upper_sm=float(payload["r4_salary_upper_sm"]),
        salario_minimo_por_ano=salario_minimo,
        a_volume=_bounds(norm["a_volume_raw"]),
        salario_relativo_r4=_bounds(norm["salario_relativo_r4"]),
        shannon_cbo=_bounds(norm["shannon_cbo"]),
        shannon_subclasse=_bounds(norm["shannon_subclasse"]),
        shannon_secao=_bounds(norm["shannon_secao"]),
        published_fingerprints_4dp=payload["published_fingerprints_4dp"],
        raw=payload,
    )
    _validate_weight_groups(spec)
    return spec


def get_salario_minimo(year: int, spec: IcttV2Spec | None = None) -> float:
    """Retorna o salário mínimo versionado do ano. Sem fallback silencioso."""
    cfg = spec or frozen_spec()
    year_key = int(year)
    if year_key not in cfg.salario_minimo_por_ano:
        raise SalarioMinimoNaoConfiguradoError(
            f"Salário mínimo não configurado para o ano {year_key}."
        )
    return float(cfg.salario_minimo_por_ano[year_key])


def score_frozen(
    x: float | np.ndarray | pd.Series,
    p05: float,
    p95: float,
) -> float | np.ndarray | pd.Series:
    """Normalização NORM_B: 100 * clip((x - P05) / (P95 - P05), 0, 1)."""
    span = float(p95) - float(p05)
    if span == 0.0:
        raise ValueError("Intervalo P05/P95 nulo na normalização congelada.")

    if isinstance(x, pd.Series):
        values = pd.to_numeric(x, errors="coerce")
        scaled = (values - float(p05)) / span
        return 100.0 * scaled.clip(lower=0.0, upper=1.0)

    arr = np.asarray(x, dtype=float)
    scaled = (arr - float(p05)) / span
    scored = 100.0 * np.clip(scaled, 0.0, 1.0)
    if np.ndim(arr) == 0:
        return float(scored)
    return scored


def absorption_balance(
    admissoes: float | np.ndarray | pd.Series,
    desligamentos: float | np.ndarray | pd.Series,
    *,
    c: float | None = None,
    lam: float | None = None,
) -> float | np.ndarray | pd.Series:
    spec = frozen_spec()
    c_val = spec.balance_c if c is None else float(c)
    lam_val = spec.balance_lambda if lam is None else float(lam)
    adm = pd.to_numeric(admissoes, errors="coerce") if isinstance(admissoes, pd.Series) else np.asarray(admissoes, dtype=float)
    des = pd.to_numeric(desligamentos, errors="coerce") if isinstance(desligamentos, pd.Series) else np.asarray(desligamentos, dtype=float)
    result = 100.0 * (adm + c_val) / (adm + des + lam_val)
    if np.ndim(np.asarray(result)) == 0:
        return float(result)
    return result


def quality_component(percent: float | np.ndarray | pd.Series, penalty_k: float) -> float | np.ndarray | pd.Series:
    """Q = 100 - min(100, k * perc). perc na escala 0–100."""
    if isinstance(percent, pd.Series):
        perc = pd.to_numeric(percent, errors="coerce")
        return 100.0 - (penalty_k * perc).clip(upper=100.0)
    arr = np.asarray(percent, dtype=float)
    scored = 100.0 - np.minimum(100.0, penalty_k * arr)
    if np.ndim(arr) == 0:
        return float(scored)
    return scored


def classify_reliability(
    admissoes: pd.Series,
    *,
    min_calculable: int | None = None,
    robust_threshold: int | None = None,
) -> tuple[pd.Series, pd.Series]:
    spec = frozen_spec()
    min_n = spec.min_admissions_calculable if min_calculable is None else int(min_calculable)
    robust_n = spec.robust_admissions_threshold if robust_threshold is None else int(robust_threshold)
    adm = pd.to_numeric(admissoes, errors="coerce").fillna(0)
    calculavel = adm >= min_n
    reliability = pd.Series(pd.NA, index=adm.index, dtype="string")
    reliability = reliability.mask((adm >= min_n) & (adm < robust_n), RELIABILITY_REDUCED)
    reliability = reliability.mask(adm >= robust_n, RELIABILITY_HIGHER)
    return calculavel.astype("boolean"), reliability


def r4_eligible_mask(
    salario: pd.Series,
    indtrabintermitente: pd.Series,
    salario_minimo: float,
    *,
    spec: IcttV2Spec | None = None,
) -> pd.Series:
    """Elegibilidade R4: não intermitente (indtrabintermitente==Sim) e faixa salarial."""
    from pipelines.gold.compute_ictt import _is_sim, _valid_salary

    cfg = spec or frozen_spec()
    sal = _valid_salary(salario)
    intermittent = _is_sim(indtrabintermitente)
    lo = cfg.r4_salary_lower_sm * float(salario_minimo)
    hi = cfg.r4_salary_upper_sm * float(salario_minimo)
    return sal.notna() & ~intermittent & (sal >= lo) & (sal <= hi)
