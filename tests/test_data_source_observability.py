"""Testes de headers de observabilidade X-Gold-Backend / X-Data-Source / X-Fallback-Used."""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


def _reload_client(monkeypatch: pytest.MonkeyPatch, **env: str) -> TestClient:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import app.core.config as config_module
    import app.main as main_module

    importlib.reload(config_module)
    importlib.reload(main_module)
    return TestClient(main_module.app)


@pytest.mark.parametrize("scope", ["pr", "rmc", "br"])
def test_overview_filesystem_headers(monkeypatch: pytest.MonkeyPatch, scope: str):
    client = _reload_client(monkeypatch, GOLD_BACKEND="filesystem")
    response = client.get(
        "/api/gold/v1/overview",
        params={"scope": scope, "ano": 2026, "mes": 4},
    )
    assert response.status_code == 200
    assert response.headers.get("x-gold-backend") == "filesystem"
    assert response.headers.get("x-data-source") == "filesystem"
    assert response.headers.get("x-fallback-used") == "false"
    body = response.json()
    assert body["scope"] == scope
    assert "resumo" in body
    assert "rankings" in body


def test_overview_postgis_fallback_headers(monkeypatch: pytest.MonkeyPatch):
    from app.repositories.gold_postgis_repository import PostgisUnavailableError

    client = _reload_client(monkeypatch, GOLD_BACKEND="postgis")

    def _boom(*_a, **_k):
        raise PostgisUnavailableError("sem_dados: simulated")

    monkeypatch.setattr(
        "app.repositories.gold_postgis_repository.build_overview_payload",
        _boom,
    )
    monkeypatch.setattr(
        "app.repositories.gold_postgis_repository.is_overview_supported",
        lambda scope: True,
    )

    response = client.get(
        "/api/gold/v1/overview",
        params={"scope": "pr", "ano": 2026, "mes": 4},
    )
    assert response.status_code == 200
    assert response.headers.get("x-gold-backend") == "postgis"
    assert response.headers.get("x-data-source") == "fallback_filesystem"
    assert response.headers.get("x-fallback-used") == "true"


def test_tabela_uf_postgis_success_headers(monkeypatch: pytest.MonkeyPatch):
    client = _reload_client(monkeypatch, GOLD_BACKEND="postgis")

    def _fake(*_a, **_k):
        return {
            "month": {"ano": 2026, "mes": 4},
            "scope": "br",
            "table": "tabela_uf",
            "columns": ["uf", "admissoes", "desligamentos", "saldo"],
            "total": 1,
            "offset": 0,
            "count": 1,
            "rows": [{"uf": "Paraná", "admissoes": 1, "desligamentos": 0, "saldo": 1}],
        }

    monkeypatch.setattr(
        "app.repositories.gold_postgis_repository.build_table_payload",
        _fake,
    )

    response = client.get(
        "/api/gold/v1/table/tabela_uf",
        params={"scope": "br", "ano": 2026, "mes": 4, "limit": 5},
    )
    assert response.status_code == 200
    assert response.headers.get("x-data-source") == "postgis"
    assert response.headers.get("x-fallback-used") == "false"


def test_ictt_observability_postgis_and_fallback(monkeypatch: pytest.MonkeyPatch):
    from app.repositories.gold_postgis_repository import PostgisUnavailableError

    client = _reload_client(monkeypatch, GOLD_BACKEND="postgis")

    def _ok(*_a, **_k):
        return {
            "month": {"ano": 2026, "mes": 4},
            "scope": "pr",
            "table": "tabela_ictt_municipio",
            "columns": ["municipio", "ICTT"],
            "total": 1,
            "offset": 0,
            "count": 1,
            "rows": [{"municipio": "Curitiba", "ICTT": 100.0}],
        }

    monkeypatch.setattr(
        "app.repositories.gold_postgis_repository.is_table_supported",
        lambda base_name, scope: True,
    )
    monkeypatch.setattr(
        "app.repositories.gold_postgis_repository.build_table_payload",
        _ok,
    )
    response = client.get(
        "/api/gold/v1/table/tabela_ictt_municipio",
        params={"scope": "pr", "ano": 2026, "mes": 4, "limit": 5},
    )
    assert response.status_code == 200
    assert response.headers.get("x-gold-backend") == "postgis"
    assert response.headers.get("x-data-source") == "postgis"
    assert response.headers.get("x-fallback-used") == "false"

    def _boom(*_a, **_k):
        raise PostgisUnavailableError("query: simulated")

    monkeypatch.setattr(
        "app.repositories.gold_postgis_repository.build_table_payload",
        _boom,
    )
    response2 = client.get(
        "/api/gold/v1/table/tabela_ictt_municipio",
        params={"scope": "pr", "ano": 2026, "mes": 4, "limit": 5},
    )
    assert response2.status_code == 200
    assert response2.headers.get("x-data-source") == "fallback_filesystem"
    assert response2.headers.get("x-fallback-used") == "true"


def test_report_context_observability_via_orchestrator(monkeypatch: pytest.MonkeyPatch):
    from app.core import fallback_registry as registry
    from app.repositories.gold_postgis_repository import PostgisUnavailableError

    registry.reset()
    client = _reload_client(monkeypatch, GOLD_BACKEND="postgis")

    def _boom(*_a, **_k):
        raise PostgisUnavailableError("sem_dados: ict report simulated")

    monkeypatch.setattr(
        "app.repositories.ict_report_repository._build_postgis_payload",
        _boom,
    )

    response = client.get(
        "/api/ict/v1/report-context",
        params={"scope": "pr", "ano": 2026, "mes": 4},
    )
    if response.status_code != 200:
        pytest.skip("Gold ICTT de 2026-04 ausente")
    assert response.headers.get("x-data-source") == "fallback_filesystem"
    assert response.headers.get("x-fallback-used") == "true"
    assert registry.snapshot()["total_fallbacks"] >= 1
    registry.reset()
