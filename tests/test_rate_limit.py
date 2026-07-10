"""Testes de rate limiting da API."""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


def _reload_client(monkeypatch: pytest.MonkeyPatch, **env: str) -> TestClient:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import app.core.config as config_module
    import app.core.production_config as production_config_module
    import app.core.rate_limit as rate_limit_module
    import app.main as main_module

    importlib.reload(config_module)
    importlib.reload(production_config_module)
    importlib.reload(rate_limit_module)
    importlib.reload(main_module)
    return TestClient(main_module.app)


def test_rate_limit_returns_429_when_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _reload_client(
        monkeypatch,
        APP_ENV="local",
        RATE_LIMIT_ENABLED="true",
        RATE_LIMIT_PER_MINUTE="2",
        ADMIN_BEARER_TOKEN="test-admin-token",
    )
    url = "/api/gold/v1/competencias"
    assert client.get(url).status_code == 200
    assert client.get(url).status_code == 200
    assert client.get(url).status_code == 429


def test_health_not_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _reload_client(
        monkeypatch,
        APP_ENV="local",
        RATE_LIMIT_ENABLED="true",
        RATE_LIMIT_PER_MINUTE="1",
    )
    for _ in range(5):
        assert client.get("/health").status_code == 200
