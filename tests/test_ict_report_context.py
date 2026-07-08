"""Testes do contexto analítico determinístico do ICT."""

import json
import math

import pytest

from pipelines.gold.compute_ict_report_context import (
    SCOPE_UNSUPPORTED_MSG,
    build_report_context,
    dataframe_to_json_safe,
    finite_number,
    list_available_ictt_months,
    read_ictt_table,
    validate_report_context,
)


def test_finite_number_handles_null_and_strings():
    assert finite_number(None) is None
    assert finite_number("") is None
    assert finite_number("18.7") == 18.7
    assert finite_number(float("nan")) is None


def test_unsupported_scope_raises():
    with pytest.raises(ValueError, match=SCOPE_UNSUPPORTED_MSG):
        build_report_context(2026, 4, "br")


@pytest.mark.skipif(
    not (
        __import__("pathlib").Path(
            "data-lake/gold/caged/ano=2026/mes=04/tabela_ictt_municipio_pr.parquet"
        ).is_file()
    ),
    reason="Gold ICTT de 2026-04 ausente",
)
def test_build_report_context_april_2026():
    context = build_report_context(2026, 4, "pr")
    assert context["metadata"]["indicator"] == "ICT"
    assert context["summary"]["municipios_total"] == 399
    assert context["summary"]["municipios_com_ict"] == 103
    assert context["summary"]["municipios_sem_base"] == 296
    assert context["top_10"][0]["municipio"] == "Curitiba"
    assert validate_report_context(context) == []

    serialized = json.dumps(context, ensure_ascii=False)
    assert "NaN" not in serialized
    parsed = json.loads(serialized)
    assert not _contains_non_finite(parsed)


def _contains_non_finite(obj) -> bool:
    if isinstance(obj, dict):
        return any(_contains_non_finite(value) for value in obj.values())
    if isinstance(obj, list):
        return any(_contains_non_finite(value) for value in obj)
    return isinstance(obj, float) and not math.isfinite(obj)


@pytest.mark.skipif(
    not (
        __import__("pathlib").Path(
            "data-lake/gold/caged/ano=2026/mes=04/tabela_ictt_municipio_pr.parquet"
        ).is_file()
    ),
    reason="Gold ICTT de 2026-04 ausente",
)
def test_list_available_ictt_months_up_to_april_2026():
    months = list_available_ictt_months("pr", 2026, 4)
    assert (2026, 1) in months
    assert (2026, 4) in months


def test_dataframe_to_json_safe_converts_nan_to_null():
    payload = dataframe_to_json_safe({"value": float("nan"), "ok": 1.23456})
    assert payload == {"value": None, "ok": 1.23}
