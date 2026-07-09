"""Testes de hardening básico: Bearer auth, debug flag, CORS configurável."""

from __future__ import annotations

import importlib
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


def _reload_app(monkeypatch: pytest.MonkeyPatch, **env: str) -> TestClient:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import app.api.routes_ops as ops_module
    import app.core.config as config_module
    import app.core.security as security_module
    import app.main as main_module

    importlib.reload(config_module)
    importlib.reload(security_module)
    importlib.reload(ops_module)
    importlib.reload(main_module)
    return TestClient(main_module.app)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    return _reload_app(
        monkeypatch,
        ADMIN_BEARER_TOKEN="test-admin-token",
        ENABLE_DEBUG_ROUTES="false",
        APP_ENV="local",
    )


@pytest.fixture()
def client_debug_enabled(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    return _reload_app(
        monkeypatch,
        ADMIN_BEARER_TOKEN="test-admin-token",
        ENABLE_DEBUG_ROUTES="true",
        APP_ENV="local",
    )


def test_public_gold_health_still_available(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_admin_endpoint_without_token_returns_401(client: TestClient) -> None:
    response = client.post("/api/admin/load/fact-municipio?ano=2026&mes=4")
    assert response.status_code == 401


def test_admin_endpoint_with_invalid_token_returns_403(client: TestClient) -> None:
    response = client.post(
        "/api/admin/load/fact-municipio?ano=2026&mes=4",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 403


def test_admin_endpoint_with_valid_token_attempts_load(client: TestClient) -> None:
    with patch("app.api.routes_admin.load_fact_emprego_municipio") as mock_load:
        mock_load.return_value = None
        response = client.post(
            "/api/admin/load/fact-municipio?ano=2026&mes=4",
            headers={"Authorization": "Bearer test-admin-token"},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    mock_load.assert_called_once_with(ano=2026, mes=4)


def test_debug_route_disabled_by_default(client: TestClient) -> None:
    response = client.get(
        "/api/debug/db-ping",
        headers={"Authorization": "Bearer test-admin-token"},
    )
    assert response.status_code == 404


def test_debug_route_enabled_requires_bearer(client_debug_enabled: TestClient) -> None:
    response = client_debug_enabled.get("/api/debug/db-ping")
    assert response.status_code == 401


def test_debug_route_enabled_with_bearer(client_debug_enabled: TestClient) -> None:
    with patch("app.api.routes_debug.ping_database", return_value="ok"):
        response = client_debug_enabled.get(
            "/api/debug/db-ping",
            headers={"Authorization": "Bearer test-admin-token"},
        )
    assert response.status_code == 200
    assert response.json()["database"] == "ok"


def test_cors_origins_parsed_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://a.example,https://b.example")
    import app.core.config as config_module

    importlib.reload(config_module)
    assert config_module.CORS_ALLOWED_ORIGINS == [
        "https://a.example",
        "https://b.example",
    ]


def test_admin_token_missing_in_production_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ADMIN_BEARER_TOKEN", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    import app.core.config as config_module
    import app.core.security as security_module

    importlib.reload(config_module)
    importlib.reload(security_module)

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        security_module.require_admin_bearer(credentials=None)
    assert exc.value.status_code == 503


def test_gold_error_details_sanitized_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    import app.core.config as config_module
    import app.core.public_errors as public_errors_module

    importlib.reload(config_module)
    importlib.reload(public_errors_module)

    details = {
        "ano": 2026,
        "mes": 4,
        "expected_path": "/secret/path/tabela.csv",
    }
    sanitized = public_errors_module.sanitize_public_error_details(details)
    assert sanitized == {"ano": 2026, "mes": 4}
    assert "expected_path" not in sanitized


def test_ready_problems_sanitized_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path
    from unittest.mock import MagicMock

    monkeypatch.setenv("APP_ENV", "production")
    import app.core.config as config_module
    import app.core.public_errors as public_errors_module
    import app.services.gold_readiness as readiness_module

    importlib.reload(config_module)
    importlib.reload(public_errors_module)
    importlib.reload(readiness_module)

    secret_gold = Path(r"C:\secret\nova_plataforma\data-lake\gold\caged")
    mock_catalog = MagicMock()
    mock_catalog.is_file.return_value = False
    with patch.object(readiness_module, "GOLD_CAGED_DIR", secret_gold):
        with patch.object(readiness_module, "GOLD_CATALOG_JSON", mock_catalog):
            with patch.object(
                readiness_module,
                "list_available_competencias",
                return_value=[],
            ):
                with patch.object(
                    readiness_module,
                    "get_competencias_payload",
                    return_value={"default": None, "items": []},
                ):
                    report = readiness_module.build_readiness_report()

    assert report["status"] == "not_ready"
    problems = report.get("problems", [])
    assert problems
    joined = " ".join(problems).lower()
    assert "data-lake" not in joined
    assert "secret" not in joined
    assert "nova_plataforma" not in joined
    assert "gold data directory is not available." in joined


def test_ready_problems_keep_details_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path
    from unittest.mock import MagicMock

    monkeypatch.setenv("APP_ENV", "local")
    import app.core.config as config_module
    import app.core.public_errors as public_errors_module
    import app.services.gold_readiness as readiness_module

    importlib.reload(config_module)
    importlib.reload(public_errors_module)
    importlib.reload(readiness_module)

    missing_gold = Path("/tmp/missing-gold-caged")
    mock_catalog = MagicMock()
    mock_catalog.is_file.return_value = False
    with patch.object(readiness_module, "GOLD_CAGED_DIR", missing_gold):
        with patch.object(readiness_module, "GOLD_CATALOG_JSON", mock_catalog):
            with patch.object(
                readiness_module,
                "list_available_competencias",
                return_value=[],
            ):
                with patch.object(
                    readiness_module,
                    "get_competencias_payload",
                    return_value={"default": None, "items": []},
                ):
                    report = readiness_module.build_readiness_report()

    assert report["status"] == "not_ready"
    problems = report.get("problems", [])
    assert any("missing-gold-caged" in problem for problem in problems)


def test_format_readiness_problems_production_strips_paths() -> None:
    from app.core.public_errors import format_readiness_problems

    coded = [
        (
            "gold_dir_missing",
            r"Diretório Gold não encontrado: C:\secret\data-lake\gold\caged",
        )
    ]
    with patch("app.core.public_errors.is_production_env", return_value=True):
        messages = format_readiness_problems(coded)
    assert messages == ["Gold data directory is not available."]
    assert "data-lake" not in messages[0].lower()
    assert "c:\\" not in messages[0].lower()


def test_format_readiness_problems_development_preserves_details() -> None:
    from app.core.public_errors import format_readiness_problems

    detail = "Diretório Gold não encontrado: /tmp/data-lake/gold/caged"
    coded = [("gold_dir_missing", detail)]
    with patch("app.core.public_errors.is_production_env", return_value=False):
        messages = format_readiness_problems(coded)
    assert messages == [detail]


def test_production_hides_openapi_docs(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _reload_app(monkeypatch, APP_ENV="production", ADMIN_BEARER_TOKEN="prod-token")
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_development_exposes_openapi_docs(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _reload_app(monkeypatch, APP_ENV="local", ADMIN_BEARER_TOKEN="dev-token")
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert "openapi" in openapi.json()


def test_security_headers_on_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "SAMEORIGIN"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert response.headers.get("permissions-policy") == "geolocation=(), microphone=(), camera=()"


def test_ops_fallbacks_public_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _reload_app(monkeypatch, APP_ENV="local", ADMIN_BEARER_TOKEN="dev-token")
    response = client.get("/api/ops/fallbacks")
    assert response.status_code == 200


def test_ops_fallbacks_blocked_in_production_without_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _reload_app(
        monkeypatch,
        APP_ENV="production",
        ADMIN_BEARER_TOKEN="prod-token",
    )
    response = client.get("/api/ops/fallbacks")
    assert response.status_code == 401


def test_ops_fallbacks_allowed_in_production_with_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _reload_app(
        monkeypatch,
        APP_ENV="production",
        ADMIN_BEARER_TOKEN="prod-token",
    )
    response = client.get(
        "/api/ops/fallbacks",
        headers={"Authorization": "Bearer prod-token"},
    )
    assert response.status_code == 200


def test_ops_fallbacks_hidden_when_production_token_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ADMIN_BEARER_TOKEN", raising=False)
    client = _reload_app(monkeypatch, APP_ENV="production")
    response = client.get("/api/ops/fallbacks")
    assert response.status_code == 404
