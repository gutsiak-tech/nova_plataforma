"""Autenticação Bearer para endpoints administrativos e debug."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import ADMIN_BEARER_TOKEN, is_production_env

_bearer_scheme = HTTPBearer(auto_error=False)


def require_admin_bearer(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> None:
    """Exige Bearer token configurado via ADMIN_BEARER_TOKEN."""
    if not ADMIN_BEARER_TOKEN:
        if is_production_env():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Admin authentication is not configured.",
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_BEARER_TOKEN is not configured.",
        )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.credentials != ADMIN_BEARER_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
