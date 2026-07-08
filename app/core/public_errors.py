"""Sanitização de erros expostos ao cliente."""

from __future__ import annotations

from typing import Any

from app.core.config import is_production_env

_PUBLIC_ERROR_DETAIL_KEYS = frozenset(
    {
        "ano",
        "mes",
        "scope",
        "table",
        "base_name",
        "sort_by",
        "sort_dir",
        "limit",
        "offset",
    }
)

_READINESS_PRODUCTION_MESSAGES: dict[str, str] = {
    "gold_dir_missing": "Gold data directory is not available.",
    "competencias_unavailable": "No Gold competencias are available.",
    "catalog_missing": "Gold catalog file is not available.",
    "catalog_unreadable": "Gold catalog could not be read.",
    "catalog_missing_unreadable": "Gold catalog is not available.",
    "default_config_missing": "Default competencia configuration is incomplete.",
    "default_competencia_unavailable": "Default competencia is not available in Gold data.",
    "gold_metadata_missing": "Gold metadata for the default competencia is not available.",
    "gold_metadata_unreadable": "Gold metadata for the default competencia could not be read.",
    "gold_metadata_error": "Gold metadata validation failed for the default competencia.",
    "gold_metadata_unknown_status": "Gold metadata has an unrecognized validation status.",
}

_READINESS_FALLBACK_MESSAGE = "A required readiness dependency is unavailable."


def sanitize_public_error_details(details: dict[str, Any] | None) -> dict[str, Any]:
    if not details:
        return {}
    if not is_production_env():
        return details
    return {key: value for key, value in details.items() if key in _PUBLIC_ERROR_DETAIL_KEYS}


def format_readiness_problems(coded_problems: list[tuple[str, str]]) -> list[str]:
    """Converte problemas codificados em mensagens públicas do /ready."""
    if not is_production_env():
        return [detail for _, detail in coded_problems]
    return [
        _READINESS_PRODUCTION_MESSAGES.get(code, _READINESS_FALLBACK_MESSAGE)
        for code, _ in coded_problems
    ]
