"""Testes de validação de configuração de produção."""

from __future__ import annotations

import pytest

from app.core.production_config import (
    ProductionConfigError,
    is_unsafe_admin_token,
    is_unsafe_postgres_password,
    is_unsafe_postgres_user,
    validate_production_config,
)


def test_unsafe_admin_token_detects_short_and_placeholders() -> None:
    assert is_unsafe_admin_token("")
    assert is_unsafe_admin_token("short")
    assert is_unsafe_admin_token("change-me-long-token")
    assert not is_unsafe_admin_token("local-production-smoke-secret")


def test_unsafe_postgres_credentials() -> None:
    assert is_unsafe_postgres_user("postgres")
    assert not is_unsafe_postgres_user("caged_readonly")
    assert is_unsafe_postgres_password("postgres")
    assert is_unsafe_postgres_password("change-me")
    assert not is_unsafe_postgres_password("secure-readonly-test-password")


def test_validate_production_config_allows_safe_values() -> None:
    validate_production_config(
        app_env="production",
        admin_bearer_token="local-production-smoke-secret",
        postgres_user="caged_readonly",
        postgres_password="secure-readonly-test-password",
        gold_backend="postgis",
    )


def test_validate_production_config_rejects_default_postgres() -> None:
    with pytest.raises(ProductionConfigError) as exc:
        validate_production_config(
            app_env="production",
            admin_bearer_token="local-production-smoke-secret",
            postgres_user="postgres",
            postgres_password="postgres",
            gold_backend="postgis",
        )
    assert "POSTGRES" in str(exc.value)


def test_validate_production_config_ignores_local_env() -> None:
    validate_production_config(
        app_env="local",
        admin_bearer_token="",
        postgres_user="postgres",
        postgres_password="postgres",
        gold_backend="postgis",
    )
