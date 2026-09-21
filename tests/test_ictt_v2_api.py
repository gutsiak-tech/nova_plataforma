"""API versionada do ICTT methodology version 2.0 (paralela à V1)."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories import ictt_v2_repository as repo_mod
from app.repositories.ictt_v2_repository import (
    ICTT_V2_PARQUET_STEM,
    ICTT_V2_SUBDIR,
    REQUIRED_COLUMNS,
    IcttV2InvalidCompetenciaError,
    IcttV2InvalidMunicipalityCodeError,
    IcttV2Repository,
    json_safe_value,
    parse_competencia,
    parse_municipality_code,
)
from pipelines.gold.ictt_v2.spec import frozen_spec

client = TestClient(app)

APRIL_PARQUET = Path(
    "data-lake/gold/caged/ano=2026/mes=04/ictt_v2/tabela_ictt_v2_municipio_pr.parquet"
)
SKIP_NO_GOLD = pytest.mark.skipif(
    not APRIL_PARQUET.is_file(),
    reason="Gold ICTT v2 de 2026-04 ausente",
)

# Fingerprints do Gold V2 validado de abril/2026 (não derivados do repository sob teste).
FOZ_CODIGO = "4108304"
FOZ_ICTT = 82.86469407999354
FOZ_RANK_N10 = 1
FOZ_RANK_N20 = 1

GUARAPUAVA_CODIGO = "4109401"
GUARAPUAVA_ICTT = 59.70914772764678
GUARAPUAVA_RANK_N10 = 37

IRATI_CODIGO = "4110706"

APRIL_N_MUNICIPALITIES = 399
APRIL_N_CALCULABLE = 59
APRIL_N20 = 39
ICTT_ATOL = 1e-9


def _reject_json_constants(token: str):
    raise AssertionError(f"JSON non-standard constant: {token}")


def assert_standard_json(response) -> dict:
    assert "NaN" not in response.text
    assert "Infinity" not in response.text
    payload = json.loads(response.text, parse_constant=_reject_json_constants)
    json.dumps(payload, allow_nan=False)
    return payload


def _minimal_partition(
    *,
    methodology_version: str | None = None,
    normalization_version: str | None = None,
) -> pd.DataFrame:
    spec = frozen_spec()
    return pd.DataFrame(
        {
            "competencia": ["2026-04"],
            "cod_municipio": ["4106902"],
            "municipio": ["Curitiba"],
            "calculavel": [True],
            "reliability_class": ["higher"],
            "admissoes": [25],
            "desligamentos": [10],
            "saldo": [15],
            "absorcao": [50.0],
            "remuneracao": [50.0],
            "qualidade_contratual": [50.0],
            "diversificacao": [50.0],
            "ictt_v2": [50.0],
            "rank_n10": [1],
            "rank_n20": [1],
            "methodology_version": [
                spec.methodology_version if methodology_version is None else methodology_version
            ],
            "normalization_version": [
                spec.normalization_version
                if normalization_version is None
                else normalization_version
            ],
        }
    )


def test_parse_competencia_accepts_canonical_month():
    ano, mes, key = parse_competencia("2026-04")
    assert (ano, mes, key) == (2026, 4, "2026-04")


@pytest.mark.parametrize(
    "value",
    [
        "2026-13",
        "2026-00",
        "26-04",
        "2026/04",
        "2026-04/../01",
        "../2026-04",
        r"..\2026-04",
        "2026-04\\..\\01",
        "",
        "not-a-month",
    ],
)
def test_parse_competencia_rejects_invalid_and_traversal(value: str):
    with pytest.raises(IcttV2InvalidCompetenciaError):
        parse_competencia(value)


def test_parse_municipality_code_rejects_traversal():
    with pytest.raises(IcttV2InvalidMunicipalityCodeError):
        parse_municipality_code("../etc/passwd")
    with pytest.raises(IcttV2InvalidMunicipalityCodeError):
        parse_municipality_code("4108304/../0000000")
    with pytest.raises(IcttV2InvalidMunicipalityCodeError):
        parse_municipality_code("abc")


@pytest.mark.parametrize(
    "value",
    [float("nan"), np.nan, pd.NA, np.float64("nan")],
)
def test_json_safe_value_converts_nan_to_none(value):
    assert json_safe_value(value) is None


def test_repository_source_is_parquet_serving_only():
    source = inspect.getsource(repo_mod)
    assert "read_csv" not in source
    assert "compute_ictt_v2" not in source
    assert "score_frozen" not in source
    assert "pd.read_parquet" in source


@SKIP_NO_GOLD
def test_competencias_lists_2026_01_to_04_chronologically():
    response = client.get("/api/ict/v2/competencias")
    assert response.status_code == 200
    body = assert_standard_json(response)
    assert body["methodology_version"] == "2.0"
    assert body["competencias"] == ["2026-01", "2026-02", "2026-03", "2026-04"]
    assert body["competencias"] == sorted(body["competencias"])


def test_methodology_exposes_frozen_public_contract():
    spec = frozen_spec()
    response = client.get("/api/ict/v2/methodology")
    assert response.status_code == 200
    body = assert_standard_json(response)
    assert body["methodology_version"] == "2.0"
    assert body["normalization_version"] == spec.normalization_version
    assert body["normalization_version"] == "NORM_B.2026-01_2026-04.N233"
    assert body["reference_scope"] == "PR"
    assert body["reference_period"] == {"start": "2026-01", "end": "2026-04"}
    assert body["eligibility"]["min_admissions"] == 10
    assert body["eligibility"]["higher_reliability_from"] == 20
    weights = {item["key"]: item["weight"] for item in body["dimensions"]}
    assert weights == {
        "absorcao": 0.25,
        "remuneracao": 0.25,
        "qualidade_contratual": 0.25,
        "diversificacao": 0.25,
    }


@SKIP_NO_GOLD
def test_municipal_list_april_2026_cardinalities():
    response = client.get(
        "/api/ict/v2/municipalities",
        params={"competencia": "2026-04"},
    )
    assert response.status_code == 200
    body = assert_standard_json(response)
    assert body["meta"]["competencia"] == "2026-04"
    assert body["meta"]["methodology_version"] == "2.0"
    assert body["meta"]["n_municipalities"] == APRIL_N_MUNICIPALITIES
    assert body["meta"]["n_calculable"] == APRIL_N_CALCULABLE
    assert len(body["data"]) == APRIL_N_MUNICIPALITIES
    assert sum(1 for row in body["data"] if row["calculavel"]) == APRIL_N_CALCULABLE


@SKIP_NO_GOLD
def test_foz_fingerprint_on_list_and_detail():
    listing = client.get(
        "/api/ict/v2/municipalities",
        params={"competencia": "2026-04"},
    )
    assert listing.status_code == 200
    foz = next(
        row
        for row in listing.json()["data"]
        if row["codigo_municipio"] == FOZ_CODIGO
    )
    assert foz["municipio"] == "Foz do Iguaçu"
    assert foz["calculavel"] is True
    assert foz["reliability_class"] == "higher"
    assert foz["ictt_v2"] == pytest.approx(FOZ_ICTT, abs=ICTT_ATOL)
    assert foz["rank_n10"] == FOZ_RANK_N10
    assert foz["rank_n20"] == FOZ_RANK_N20

    detail = client.get(
        f"/api/ict/v2/municipalities/{FOZ_CODIGO}",
        params={"competencia": "2026-04"},
    )
    assert detail.status_code == 200
    payload = assert_standard_json(detail)
    row = payload["data"]
    assert row["ictt_v2"] == pytest.approx(FOZ_ICTT, abs=ICTT_ATOL)
    assert row["rank_n10"] == 1
    assert row["rank_n20"] == 1
    assert row["a_volume_score"] is not None
    assert row["shannon_cbo"] is not None


@SKIP_NO_GOLD
def test_guarapuava_reduced_reliability_fingerprint():
    response = client.get(
        f"/api/ict/v2/municipalities/{GUARAPUAVA_CODIGO}",
        params={"competencia": "2026-04"},
    )
    assert response.status_code == 200
    row = assert_standard_json(response)["data"]
    assert row["municipio"] == "Guarapuava"
    assert row["calculavel"] is True
    assert row["reliability_class"] == "reduced"
    assert row["ictt_v2"] == pytest.approx(GUARAPUAVA_ICTT, abs=ICTT_ATOL)
    assert row["rank_n10"] == GUARAPUAVA_RANK_N10
    assert row["rank_n20"] is None


@SKIP_NO_GOLD
def test_ineligible_irati_has_null_index_and_ranks():
    response = client.get(
        f"/api/ict/v2/municipalities/{IRATI_CODIGO}",
        params={"competencia": "2026-04"},
    )
    assert response.status_code == 200
    raw = response.text
    assert "NaN" not in raw
    row = assert_standard_json(response)["data"]
    assert row["calculavel"] is False
    assert row["ictt_v2"] is None
    assert row["rank_n10"] is None
    assert row["rank_n20"] is None
    assert row["reliability_class"] is None
    assert row["admissoes"] < 10


@SKIP_NO_GOLD
def test_reduced_reliability_filter_is_not_an_error():
    response = client.get(
        "/api/ict/v2/municipalities",
        params={"competencia": "2026-04", "reliability": "reduced"},
    )
    assert response.status_code == 200
    body = assert_standard_json(response)
    codes = {row["codigo_municipio"] for row in body["data"]}
    assert GUARAPUAVA_CODIGO in codes
    assert FOZ_CODIGO not in codes
    assert all(row["reliability_class"] == "reduced" for row in body["data"])
    assert all(row["calculavel"] is True for row in body["data"])
    assert all(row["ictt_v2"] is not None for row in body["data"])


@SKIP_NO_GOLD
def test_ranking_n10_april():
    response = client.get(
        "/api/ict/v2/ranking",
        params={"competencia": "2026-04", "universe": "n10"},
    )
    assert response.status_code == 200
    body = assert_standard_json(response)
    assert body["meta"]["universe"] == "n10"
    assert body["meta"]["n_ranked"] == APRIL_N_CALCULABLE
    assert len(body["data"]) == APRIL_N_CALCULABLE
    assert body["data"][0]["codigo_municipio"] == FOZ_CODIGO
    assert body["data"][0]["rank_n10"] == 1
    ranks = [row["rank_n10"] for row in body["data"]]
    assert ranks == sorted(ranks)
    assert all(row["admissoes"] >= 10 for row in body["data"])


@SKIP_NO_GOLD
def test_ranking_n20_april():
    response = client.get(
        "/api/ict/v2/ranking",
        params={"competencia": "2026-04", "universe": "n20"},
    )
    assert response.status_code == 200
    body = assert_standard_json(response)
    assert body["meta"]["universe"] == "n20"
    assert body["meta"]["n_ranked"] == APRIL_N20
    assert len(body["data"]) == APRIL_N20
    assert body["data"][0]["codigo_municipio"] == FOZ_CODIGO
    codes = {row["codigo_municipio"] for row in body["data"]}
    assert GUARAPUAVA_CODIGO not in codes
    assert all(row["admissoes"] >= 20 for row in body["data"])
    assert all(row["rank_n20"] is not None for row in body["data"])


def test_invalid_competencia_returns_400():
    response = client.get(
        "/api/ict/v2/municipalities",
        params={"competencia": "2026-13"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_COMPETENCIA"


def test_path_traversal_competencia_returns_400():
    response = client.get(
        "/api/ict/v2/municipalities",
        params={"competencia": "2026-04/../01"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_COMPETENCIA"

    slash = client.get(
        "/api/ict/v2/municipalities",
        params={"competencia": r"..\..\secret"},
    )
    assert slash.status_code == 400
    assert slash.json()["error"]["code"] == "INVALID_COMPETENCIA"


def test_missing_gold_competencia_returns_404():
    response = client.get(
        "/api/ict/v2/municipalities",
        params={"competencia": "2099-01"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "ICTT_V2_NOT_FOUND"
    assert "data" not in body


def test_unknown_municipality_returns_404():
    response = client.get(
        "/api/ict/v2/municipalities/4199999",
        params={"competencia": "2026-04"},
    )
    if not APRIL_PARQUET.is_file():
        pytest.skip("Gold ICTT v2 de 2026-04 ausente")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ICTT_V2_MUNICIPALITY_NOT_FOUND"


def test_invalid_municipality_code_returns_400():
    response = client.get(
        "/api/ict/v2/municipalities/not-a-code",
        params={"competencia": "2026-04"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_MUNICIPALITY_CODE"


def test_invalid_universe_returns_400():
    response = client.get(
        "/api/ict/v2/ranking",
        params={"competencia": "2026-04", "universe": "official"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_UNIVERSE"


def test_csv_only_partition_does_not_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    folder = tmp_path / "ano=2026" / "mes=04" / ICTT_V2_SUBDIR
    folder.mkdir(parents=True)
    (folder / f"{ICTT_V2_PARQUET_STEM}.csv").write_text("competencia,municipio\n", encoding="utf-8")
    monkeypatch.setattr(repo_mod, "GOLD_CAGED_DIR", tmp_path)
    response = client.get(
        "/api/ict/v2/municipalities",
        params={"competencia": "2026-04"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ICTT_V2_NOT_FOUND"


def test_incompatible_schema_returns_500(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    folder = tmp_path / "ano=2026" / "mes=04" / ICTT_V2_SUBDIR
    folder.mkdir(parents=True)
    pd.DataFrame({"municipio": ["X"]}).to_parquet(folder / f"{ICTT_V2_PARQUET_STEM}.parquet")
    monkeypatch.setattr(repo_mod, "GOLD_CAGED_DIR", tmp_path)
    response = client.get(
        "/api/ict/v2/municipalities",
        params={"competencia": "2026-04"},
    )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "ICTT_V2_ARTIFACT_INVALID"


def test_incompatible_methodology_returns_500(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    folder = tmp_path / "ano=2026" / "mes=04" / ICTT_V2_SUBDIR
    folder.mkdir(parents=True)
    frame = _minimal_partition(methodology_version="1.0")
    assert set(REQUIRED_COLUMNS) <= set(frame.columns)
    frame.to_parquet(folder / f"{ICTT_V2_PARQUET_STEM}.parquet", index=False)
    monkeypatch.setattr(repo_mod, "GOLD_CAGED_DIR", tmp_path)
    response = client.get(
        "/api/ict/v2/municipalities",
        params={"competencia": "2026-04"},
    )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "ICTT_V2_ARTIFACT_INVALID"


def test_unreadable_parquet_returns_500(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    folder = tmp_path / "ano=2026" / "mes=04" / ICTT_V2_SUBDIR
    folder.mkdir(parents=True)
    (folder / f"{ICTT_V2_PARQUET_STEM}.parquet").write_text("not a parquet", encoding="utf-8")
    monkeypatch.setattr(repo_mod, "GOLD_CAGED_DIR", tmp_path)
    response = client.get(
        "/api/ict/v2/municipalities",
        params={"competencia": "2026-04"},
    )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "ICTT_V2_ARTIFACT_INVALID"


@SKIP_NO_GOLD
def test_list_reads_single_parquet_not_csv(monkeypatch: pytest.MonkeyPatch):
    reads: list[str] = []
    real_read = pd.read_parquet

    def spy_parquet(path, *args, **kwargs):
        reads.append(str(path))
        return real_read(path, *args, **kwargs)

    def fail_csv(*_args, **_kwargs):
        raise AssertionError("API V2 não deve ler CSV")

    monkeypatch.setattr(repo_mod.pd, "read_parquet", spy_parquet)
    monkeypatch.setattr(repo_mod.pd, "read_csv", fail_csv)
    response = client.get(
        "/api/ict/v2/municipalities",
        params={"competencia": "2026-04"},
    )
    assert response.status_code == 200
    assert len(reads) == 1
    normalized = reads[0].replace("\\", "/")
    assert normalized.endswith(".parquet")
    assert f"/{ICTT_V2_SUBDIR}/" in normalized


@SKIP_NO_GOLD
def test_v1_report_context_remains_unchanged():
    response = client.get(
        "/api/ict/v1/report-context",
        params={"scope": "pr", "ano": 2026, "mes": 4},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["uses_ai"] is False
    assert body["source"] == "deterministic_context"
    assert body["context"]["summary"]["municipios_total"] == 399
    assert body["context"]["summary"]["municipios_com_ict"] == 103
    assert body["context"]["top_10"][0]["municipio"] == "Curitiba"


def test_v1_is_not_aliased_to_v2():
    response = client.get("/api/ict")
    assert response.status_code == 404
    v1 = client.get("/api/ict/v1/report-context", params={"scope": "br", "ano": 2026, "mes": 4})
    assert v1.status_code == 400


def test_openapi_documents_v2_without_deprecating_v1():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    paths = spec["paths"]
    assert "/api/ict/v1/report-context" in paths
    for path in (
        "/api/ict/v2/competencias",
        "/api/ict/v2/methodology",
        "/api/ict/v2/municipalities",
        "/api/ict/v2/municipalities/{codigo_municipio}",
        "/api/ict/v2/ranking",
    ):
        assert path in paths
        description = paths[path]["get"].get("description", "")
        assert "ICTT methodology version 2.0" in description
        assert paths[path]["get"].get("deprecated") is not True
    v1 = paths["/api/ict/v1/report-context"]["get"]
    assert v1.get("deprecated") is not True
    tags = {item["name"]: item.get("description", "") for item in spec.get("tags", [])}
    assert "ICTT methodology version 2.0" in tags.get("ict-v2", "")


@SKIP_NO_GOLD
def test_smoke_v2_endpoints_status_and_cardinality():
    competencias = client.get("/api/ict/v2/competencias")
    methodology = client.get("/api/ict/v2/methodology")
    municipalities = client.get(
        "/api/ict/v2/municipalities",
        params={"competencia": "2026-04"},
    )
    ranking_n10 = client.get(
        "/api/ict/v2/ranking",
        params={"competencia": "2026-04", "universe": "n10"},
    )
    ranking_n20 = client.get(
        "/api/ict/v2/ranking",
        params={"competencia": "2026-04", "universe": "n20"},
    )
    assert competencias.status_code == 200
    assert methodology.status_code == 200
    assert municipalities.status_code == 200
    assert ranking_n10.status_code == 200
    assert ranking_n20.status_code == 200
    assert len(competencias.json()["competencias"]) == 4
    assert municipalities.json()["meta"]["n_municipalities"] == APRIL_N_MUNICIPALITIES
    assert municipalities.json()["meta"]["n_calculable"] == APRIL_N_CALCULABLE
    assert ranking_n10.json()["meta"]["n_ranked"] == APRIL_N_CALCULABLE
    assert ranking_n20.json()["meta"]["n_ranked"] == APRIL_N20


def test_parquet_path_stays_under_gold_root(tmp_path: Path):
    repository = IcttV2Repository(gold_root=tmp_path)
    path = repository.parquet_path(2026, 4)
    assert path.resolve().is_relative_to(tmp_path.resolve())
    assert path.name.endswith(".parquet")
    assert ICTT_V2_SUBDIR in path.parts
