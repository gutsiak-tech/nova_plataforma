"""ICTT v2.0 — implementação paralela à V1 (PCA)."""

from pipelines.gold.ictt_v2.spec import (
    SalarioMinimoNaoConfiguradoError,
    frozen_spec,
    get_salario_minimo,
    score_frozen,
)

__all__ = [
    "SalarioMinimoNaoConfiguradoError",
    "frozen_spec",
    "get_salario_minimo",
    "score_frozen",
]
