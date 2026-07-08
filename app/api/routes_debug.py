from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import require_admin_bearer
from app.db.queries import ping_database

router = APIRouter(
    prefix="/api/debug",
    tags=["debug"],
    dependencies=[Depends(require_admin_bearer)],
)


@router.get("/db-ping")
def debug_db_ping():
    """Ping mínimo ao PostGIS — apenas com ENABLE_DEBUG_ROUTES=true e Bearer token."""
    try:
        result = ping_database()
    except Exception:
        return {"status": "error", "database": "unavailable"}
    return {"status": "ok", "database": result}
