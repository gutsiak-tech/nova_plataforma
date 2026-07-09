"""Rotas operacionais somente leitura (observabilidade)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.fallback_registry import get_fallback_snapshot
from app.core.security import require_ops_fallback_access

router = APIRouter(prefix="/api/ops", tags=["ops"])


@router.get("/fallbacks", dependencies=[Depends(require_ops_fallback_access)])
def fallbacks():
    """Snapshot em memória de fallbacks reais PostGIS → filesystem."""
    return get_fallback_snapshot()
