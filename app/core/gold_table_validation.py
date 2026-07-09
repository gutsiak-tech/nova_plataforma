"""Validação de base_name para leitura Gold filesystem (anti path traversal)."""

from __future__ import annotations

import re

from app.services.gold_catalog_service import CURRENT_PIPELINE_TABLES

_BASE_NAME_PATTERN = re.compile(r"^[a-z0-9_]+$")

ALLOWED_GOLD_BASE_NAMES: frozenset[str] = frozenset(
    {
        (
            stem[: -len("_pr")]
            if stem.endswith("_pr")
            else stem[: -len("_rmc")]
            if stem.endswith("_rmc")
            else stem
        )
        for stem in CURRENT_PIPELINE_TABLES
    }
)


def validate_gold_base_name(base_name: str) -> str:
    """Retorna base_name normalizado ou levanta ValueError."""
    name = (base_name or "").strip()
    if not name or ".." in name or "/" in name or "\\" in name:
        raise ValueError("base_name inválido")
    if not _BASE_NAME_PATTERN.fullmatch(name):
        raise ValueError("base_name inválido")
    if name not in ALLOWED_GOLD_BASE_NAMES:
        raise ValueError("base_name inválido")
    return name
