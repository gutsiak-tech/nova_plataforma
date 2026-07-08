"""Testes do endpoint de contexto analítico do ICT."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import fallback_registry as registry
from app.main import app
from app.repositories.gold_postgis_repository import PostgisUnavailableError

client = TestClient(app)

ICTT_APR_2026 = Path(
    "data-lake/gold/caged/ano=2026/mes=04/tabela_ictt_municipio_pr.parquet"
)


def _reload_client(monkeypatch: pytest.MonkeyPatch, **env: str) -> TestClient:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import app.core.config as config_module
    import app.main as main_module

    importlib.reload(config_module)
    importlib.reload(main_module)
    return TestClient(main_module.app)


@pytest.fixture(autouse=True)
def _clean_registry():
    registry.reset()
    yield
    registry.reset()


@pytest.mark.skipif(not ICTT_APR_2026.is_file(), reason="Gold ICTT de 2026-04 ausente")
def test_report_context_pr_returns_200():
    response = client.get("/api/ict/v1/report-context", params={"scope": "pr", "ano": 2026, "mes": 4})
    assert response.status_code == 200
    body = response.json()
    assert body["uses_ai"] is False
    assert body["source"] == "deterministic_context"
    assert body["cache_status"] in ("hit", "generated")
    assert body["context"]["summary"]["municipios_total"] == 399
    assert body["context"]["summary"]["municipios_com_ict"] == 103
    assert body["context"]["summary"]["municipios_sem_base"] == 296
    assert body["context"]["top_10"][0]["municipio"] == "Curitiba"


@pytest.mark.skipif(not ICTT_APR_2026.is_file(), reason="Gold ICTT de 2026-04 ausente")
def test_report_context_filesystem_headers(monkeypatch: pytest.MonkeyPatch):
    api = _reload_client(monkeypatch, GOLD_BACKEND="filesystem")
    response = api.get(
        "/api/ict/v1/report-context",
        params={"scope": "pr", "ano": 2026, "mes": 4},
    )
    assert response.status_code == 200
    assert response.headers.get("x-gold-backend") == "filesystem"
    assert response.headers.get("x-data-source") == "filesystem"
    assert response.headers.get("x-fallback-used") == "false"
    body = response.json()
    assert body["context"]["summary"]["municipios_total"] == 399
    assert body["uses_ai"] is False


@pytest.mark.skipif(not ICTT_APR_2026.is_file(), reason="Gold ICTT de 2026-04 ausente")
def test_report_context_postgis_success_headers(monkeypatch: pytest.MonkeyPatch):
    api = _reload_client(monkeypatch, GOLD_BACKEND="postgis")

    fake_payload = {
        "scope": "pr",
        "ano": 2026,
        "mes": 4,
        "competencia_str": "2026-04",
        "source": "deterministic_context",
        "uses_ai": False,
        "cache_status": "generated",
        "context": {
            "summary": {
                "municipios_total": 399,
                "municipios_com_ict": 103,
                "municipios_sem_base": 296,
            },
            "top_10": [{"municipio": "Curitiba", "ict": 100.0}],
        },
        "markdown": "# ok\n",
    }

    monkeypatch.setattr(
        "app.repositories.ict_report_repository._build_postgis_payload",
        lambda scope, ano, mes: fake_payload,
    )

    response = api.get(
        "/api/ict/v1/report-context",
        params={"scope": "pr", "ano": 2026, "mes": 4},
    )
    assert response.status_code == 200
    assert response.headers.get("x-gold-backend") == "postgis"
    assert response.headers.get("x-data-source") == "postgis"
    assert response.headers.get("x-fallback-used") == "false"
    assert response.json()["context"]["top_10"][0]["municipio"] == "Curitiba"
    assert registry.snapshot()["total_fallbacks"] == 0


@pytest.mark.skipif(not ICTT_APR_2026.is_file(), reason="Gold ICTT de 2026-04 ausente")
def test_report_context_postgis_fallback_registers_ops(monkeypatch: pytest.MonkeyPatch):
    api = _reload_client(monkeypatch, GOLD_BACKEND="postgis")

    def _boom(*_a, **_k):
        raise PostgisUnavailableError("sem_dados: simulated")

    monkeypatch.setattr(
        "app.repositories.ict_report_repository._build_postgis_payload",
        _boom,
    )

    response = api.get(
        "/api/ict/v1/report-context",
        params={"scope": "pr", "ano": 2026, "mes": 4},
    )
    assert response.status_code == 200
    assert response.headers.get("x-gold-backend") == "postgis"
    assert response.headers.get("x-data-source") == "fallback_filesystem"
    assert response.headers.get("x-fallback-used") == "true"
    body = response.json()
    assert body["source"] == "deterministic_context"
    assert body["context"]["summary"]["municipios_total"] == 399

    ops = api.get("/api/ops/fallbacks")
    assert ops.status_code == 200
    snap = ops.json()
    assert snap["total_fallbacks"] >= 1
    assert snap["by_endpoint"].get("/api/ict/v1/report-context", 0) >= 1


@pytest.mark.parametrize("scope", ["br", "rmc"])
def test_report_context_unsupported_scope_returns_400(scope: str):
    response = client.get(
        "/api/ict/v1/report-context",
        params={"scope": scope, "ano": 2026, "mes": 4},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == (
        "O relatório do ICT está disponível inicialmente apenas para o escopo Paraná."
    )


def test_report_context_does_not_use_ai_keys():
    response = client.get("/api/ict/v1/report-context", params={"scope": "pr", "ano": 2026, "mes": 4})
    if response.status_code != 200:
        pytest.skip("Gold ICTT de 2026-04 ausente")
    payload = response.text.lower()
    for token in ("openai", "groq", "langchain", "llamaindex", "gpt"):
        assert token not in payload
