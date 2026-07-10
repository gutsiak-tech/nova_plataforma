"""Validação de configuração obrigatória em APP_ENV=production."""

from __future__ import annotations

from app.core.config import (
    ADMIN_BEARER_TOKEN,
    POSTGRES_PASSWORD,
    POSTGRES_USER,
    is_production_env,
    resolve_gold_backend,
)

_MIN_ADMIN_TOKEN_LEN = 16
_UNSAFE_TOKEN_MARKERS = frozenset({"change-me", "changeme"})
_UNSAFE_POSTGRES_PASSWORDS = frozenset({"postgres", "changeme", "change-me", ""})


class ProductionConfigError(RuntimeError):
    """Configuração insegura para produção."""


def is_unsafe_admin_token(token: str | None) -> bool:
    value = (token or "").strip()
    if len(value) < _MIN_ADMIN_TOKEN_LEN:
        return True
    lowered = value.lower()
    return any(marker in lowered for marker in _UNSAFE_TOKEN_MARKERS)


def is_unsafe_postgres_user(user: str | None) -> bool:
    return (user or "").strip().lower() == "postgres"


def is_unsafe_postgres_password(password: str | None) -> bool:
    return (password or "").strip().lower() in _UNSAFE_POSTGRES_PASSWORDS


def validate_production_config(
    *,
    app_env: str | None = None,
    admin_bearer_token: str | None = None,
    postgres_user: str | None = None,
    postgres_password: str | None = None,
    gold_backend: str | None = None,
) -> None:
    """Levanta ProductionConfigError se produção estiver mal configurada."""
    env = (app_env if app_env is not None else __import__("os").getenv("APP_ENV", "local")).strip().lower()
    if env not in ("production", "prod"):
        return

    token = admin_bearer_token if admin_bearer_token is not None else ADMIN_BEARER_TOKEN
    user = postgres_user if postgres_user is not None else POSTGRES_USER
    password = postgres_password if postgres_password is not None else POSTGRES_PASSWORD
    backend = gold_backend if gold_backend is not None else resolve_gold_backend()

    errors: list[str] = []

    if is_unsafe_admin_token(token):
        errors.append(
            "ADMIN_BEARER_TOKEN must be a strong unique value (min 16 chars, not a placeholder)."
        )

    if is_unsafe_postgres_user(user) or is_unsafe_postgres_password(password):
        errors.append(
            "POSTGRES_USER and POSTGRES_PASSWORD must not use default or placeholder credentials."
        )

    if backend == "postgis" and is_unsafe_postgres_user(user):
        errors.append(
            "GOLD_BACKEND=postgis requires a dedicated read-only PostgreSQL user in production."
        )

    if errors:
        raise ProductionConfigError(" ".join(errors))


def assert_production_config() -> None:
    if is_production_env():
        validate_production_config()
