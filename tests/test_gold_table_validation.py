"""Testes de whitelist base_name Gold (anti path traversal)."""

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


def test_invalid_base_name_path_traversal_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _reload_client(monkeypatch, GOLD_BACKEND="filesystem")
    response = client.get(
        "/api/gold/v1/table/../etc/passwd",
        params={"scope": "pr", "ano": 2026, "mes": 4},
    )
    assert response.status_code in (400, 404)


def test_unknown_base_name_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _reload_client(monkeypatch, GOLD_BACKEND="filesystem")
    response = client.get(
        "/api/gold/v1/table/tabela_inexistente_xyz",
        params={"scope": "pr", "ano": 2026, "mes": 4},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "INVALID_TABLE"


def test_validate_gold_base_name_rejects_dotdot() -> None:
    from app.core.gold_table_validation import validate_gold_base_name

    with pytest.raises(ValueError, match="inválido"):
        validate_gold_base_name("tabela_municipio/../secret")


def test_validate_gold_base_name_accepts_known_table() -> None:
    from app.core.gold_table_validation import validate_gold_base_name

    assert validate_gold_base_name("tabela_municipio") == "tabela_municipio"
    assert validate_gold_base_name("tabela_ictt_municipio") == "tabela_ictt_municipio"
