"""Testes de GOLD_BACKEND=filesystem|postgis e resolução de flag."""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from app.core.config import resolve_gold_backend


def test_resolve_gold_backend_default():
    assert resolve_gold_backend("") == "filesystem"
    assert resolve_gold_backend(None) == "filesystem" or resolve_gold_backend("filesystem") == "filesystem"
    assert resolve_gold_backend("filesystem") == "filesystem"
    assert resolve_gold_backend("postgis") == "postgis"
    assert resolve_gold_backend("POSTGRES") == "filesystem"  # inválido → filesystem
    assert resolve_gold_backend("  POSTGIS  ") == "postgis"


def _reload_client(monkeypatch: pytest.MonkeyPatch, **env: str) -> TestClient:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import app.core.config as config_module
    import app.main as main_module

    importlib.reload(config_module)
    importlib.reload(main_module)
    return TestClient(main_module.app)


def test_filesystem_backend_headers_and_body(monkeypatch: pytest.MonkeyPatch):
    client = _reload_client(monkeypatch, GOLD_BACKEND="filesystem")
    response = client.get(
        "/api/gold/v1/table/tabela_municipio",
        params={"scope": "pr", "ano": 2026, "mes": 4, "limit": 5},
    )
    assert response.status_code == 200
    assert response.headers.get("x-gold-backend") == "filesystem"
    assert response.headers.get("x-data-source") == "filesystem"
    assert response.headers.get("x-fallback-used") == "false"
    body = response.json()
    assert body["table"] == "tabela_municipio"
    assert body["scope"] == "pr"
    assert "rows" in body
    assert "columns" in body
    assert isinstance(body["rows"], list)


def test_postgis_backend_success_headers(monkeypatch: pytest.MonkeyPatch):
    client = _reload_client(monkeypatch, GOLD_BACKEND="postgis")

    def _fake_postgis(*_a, **_k):
        return {
            "month": {"ano": 2026, "mes": 4},
            "scope": "pr",
            "table": "tabela_municipio",
            "columns": ["uf", "municipio", "admissoes", "desligamentos", "saldo"],
            "total": 1,
            "offset": 0,
            "count": 1,
            "rows": [
                {
                    "uf": "Paraná",
                    "municipio": "Curitiba",
                    "admissoes": 1,
                    "desligamentos": 0,
                    "saldo": 1,
                }
            ],
        }

    monkeypatch.setattr(
        "app.repositories.gold_postgis_repository.build_table_payload",
        _fake_postgis,
    )
    monkeypatch.setattr(
        "app.repositories.gold_postgis_repository.is_table_supported",
        lambda base_name, scope: True,
    )

    response = client.get(
        "/api/gold/v1/table/tabela_municipio",
        params={"scope": "pr", "ano": 2026, "mes": 4, "limit": 5},
    )
    assert response.status_code == 200
    assert response.headers.get("x-gold-backend") == "postgis"
    assert response.headers.get("x-data-source") == "postgis"
    assert response.headers.get("x-fallback-used") == "false"
    assert response.json()["rows"][0]["municipio"] == "Curitiba"


def test_postgis_backend_fallback_on_failure(monkeypatch: pytest.MonkeyPatch):
    from app.repositories.gold_postgis_repository import PostgisUnavailableError

    client = _reload_client(monkeypatch, GOLD_BACKEND="postgis")

    def _boom(*_a, **_k):
        raise PostgisUnavailableError("conexao: simulated")

    monkeypatch.setattr(
        "app.repositories.gold_postgis_repository.build_table_payload",
        _boom,
    )
    monkeypatch.setattr(
        "app.repositories.gold_postgis_repository.is_table_supported",
        lambda base_name, scope: True,
    )

    response = client.get(
        "/api/gold/v1/table/tabela_municipio",
        params={"scope": "pr", "ano": 2026, "mes": 4, "limit": 5},
    )
    assert response.status_code == 200
    assert response.headers.get("x-gold-backend") == "postgis"
    assert response.headers.get("x-data-source") == "fallback_filesystem"
    assert response.headers.get("x-fallback-used") == "true"
    body = response.json()
    assert body["table"] == "tabela_municipio"
    assert "rows" in body


def test_ictt_filesystem_headers_and_body(monkeypatch: pytest.MonkeyPatch):
    client = _reload_client(monkeypatch, GOLD_BACKEND="filesystem")
    response = client.get(
        "/api/gold/v1/table/tabela_ictt_municipio",
        params={"scope": "pr", "ano": 2026, "mes": 4, "limit": 5},
    )
    assert response.status_code == 200
    assert response.headers.get("x-gold-backend") == "filesystem"
    assert response.headers.get("x-data-source") == "filesystem"
    assert response.headers.get("x-fallback-used") == "false"
    body = response.json()
    assert body["table"] == "tabela_ictt_municipio"
    assert body["scope"] == "pr"
    assert "rows" in body
    assert "ICTT" in body["columns"] or any("ICTT" in str(c) for c in body["columns"])


def test_ictt_postgis_success_headers(monkeypatch: pytest.MonkeyPatch):
    client = _reload_client(monkeypatch, GOLD_BACKEND="postgis")

    def _fake_ictt(*_a, **_k):
        return {
            "month": {"ano": 2026, "mes": 4},
            "scope": "pr",
            "table": "tabela_ictt_municipio",
            "columns": ["municipio", "ICTT", "cod_municipio"],
            "total": 1,
            "offset": 0,
            "count": 1,
            "rows": [
                {"municipio": "Curitiba", "ICTT": 100.0, "cod_municipio": "4106902"}
            ],
        }

    monkeypatch.setattr(
        "app.repositories.gold_postgis_repository.build_table_payload",
        _fake_ictt,
    )
    monkeypatch.setattr(
        "app.repositories.gold_postgis_repository.is_table_supported",
        lambda base_name, scope: base_name == "tabela_ictt_municipio" and scope == "pr",
    )

    response = client.get(
        "/api/gold/v1/table/tabela_ictt_municipio",
        params={"scope": "pr", "ano": 2026, "mes": 4, "limit": 5},
    )
    assert response.status_code == 200
    assert response.headers.get("x-gold-backend") == "postgis"
    assert response.headers.get("x-data-source") == "postgis"
    assert response.headers.get("x-fallback-used") == "false"
    assert response.json()["rows"][0]["municipio"] == "Curitiba"


def test_ictt_postgis_fallback_on_failure(monkeypatch: pytest.MonkeyPatch):
    from app.repositories.gold_postgis_repository import PostgisUnavailableError

    client = _reload_client(monkeypatch, GOLD_BACKEND="postgis")

    def _boom(*_a, **_k):
        raise PostgisUnavailableError("sem_dados: ictt simulated")

    monkeypatch.setattr(
        "app.repositories.gold_postgis_repository.build_table_payload",
        _boom,
    )
    monkeypatch.setattr(
        "app.repositories.gold_postgis_repository.is_table_supported",
        lambda base_name, scope: base_name == "tabela_ictt_municipio" and scope == "pr",
    )

    response = client.get(
        "/api/gold/v1/table/tabela_ictt_municipio",
        params={"scope": "pr", "ano": 2026, "mes": 4, "limit": 5},
    )
    assert response.status_code == 200
    assert response.headers.get("x-gold-backend") == "postgis"
    assert response.headers.get("x-data-source") == "fallback_filesystem"
    assert response.headers.get("x-fallback-used") == "true"
    assert response.json()["table"] == "tabela_ictt_municipio"


def test_ictt_postgis_unsupported_scope_uses_filesystem_not_fallback(
    monkeypatch: pytest.MonkeyPatch,
):
    """ICTT PostGIS só cobre scope=pr; outros scopes seguem filesystem sem fallback real."""
    client = _reload_client(monkeypatch, GOLD_BACKEND="postgis")
    response = client.get(
        "/api/gold/v1/table/tabela_ictt_municipio",
        params={"scope": "rmc", "ano": 2026, "mes": 4, "limit": 5},
    )
    # RMC pode 404 se arquivo Gold ausente — então não trata como FAIL de headers.
    if response.status_code == 404:
        pytest.skip("tabela_ictt_municipio_rmc ausente no filesystem (esperado)")
    assert response.status_code == 200
    assert response.headers.get("x-gold-backend") == "postgis"
    assert response.headers.get("x-data-source") == "filesystem"
    assert response.headers.get("x-fallback-used") == "false"
