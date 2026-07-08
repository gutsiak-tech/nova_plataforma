"""Rotas operacionais somente leitura (observabilidade)."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.fallback_registry import get_fallback_snapshot

router = APIRouter(prefix="/api/ops", tags=["ops"])


@router.get("/fallbacks")
def fallbacks():
    """Snapshot em memória de fallbacks reais PostGIS → filesystem."""
    return get_fallback_snapshot()
